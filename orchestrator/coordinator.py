"""Coordinator — Microsoft Semantic Kernel-backed orchestrator.

Pipeline:
  INTAKE → SPEC → ARCHITECTURE → CODING → TESTING → REVIEW → DELIVERY

Human-in-the-Loop (HITM) checkpoints occur after SPEC, ARCHITECTURE, and REVIEW
when hitm_mode is enabled.
"""
from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path

from openai import AsyncOpenAI
from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion
from semantic_kernel.connectors.ai.open_ai import OpenAIChatPromptExecutionSettings

from config import settings
from core.event_bus import bus
from core.state_manager import state
from models.task import Task, TaskStatus, TaskPhase
from models.agent_state import AgentStatus, AgentType
from agents import SpecAgent, ArchitectAgent, CoderAgent, TesterAgent, ReviewerAgent


class Coordinator:
    """Orchestrates all agents through the full development pipeline."""

    def __init__(self) -> None:
        self._kernel = self._build_kernel()
        self._spec_agent = SpecAgent()
        self._arch_agent = ArchitectAgent()
        self._coder_agent = CoderAgent()
        self._tester_agent = TesterAgent()
        self._reviewer_agent = ReviewerAgent()

    # --------------------------------------------------------- Kernel setup
    def _build_kernel(self) -> Kernel:
        kernel = Kernel()
        client = AsyncOpenAI(
            api_key=settings.effective_api_key,
            base_url=settings.openai_base_url,
        )
        service = OpenAIChatCompletion(
            ai_model_id=settings.effective_model,
            async_client=client,
        )
        kernel.add_service(service)
        return kernel

    # --------------------------------------------------------- Main pipeline
    async def run(self, title: str, description: str, hitm: bool | None = None) -> None:
        hitm_enabled = settings.hitm_mode if hitm is None else hitm
        task = state.start_task(title, description, hitm=hitm_enabled)
        await bus.emit("task.log", {
            "message": f"Starting pipeline — HITM={'ON' if hitm_enabled else 'OFF'}",
            "level": "info",
            "agent": "coordinator",
        })

        try:
            # ── SPEC ─────────────────────────────────────────────────────────
            await self._transition(task, TaskPhase.SPEC)
            spec = await self._spec_agent.run(description, task.id)
            state.spec = spec
            await bus.emit("spec.updated", {})
            task.phases[TaskPhase.SPEC.value].output = spec.summary
            task.phases[TaskPhase.SPEC.value].status = TaskStatus.COMPLETED
            task.phases[TaskPhase.SPEC.value].completed_at = datetime.utcnow()
            await self._idle_all_except(AgentType.SPEC)

            if hitm_enabled:
                approved = await self._hitm_gate(
                    "spec_review",
                    "Spec is ready for your review.",
                    {"spec_markdown": spec.to_markdown()},
                )
                if not approved:
                    await self._abort(task, "Spec rejected by reviewer")
                    return

            # ── ARCHITECTURE ─────────────────────────────────────────────────
            await self._transition(task, TaskPhase.ARCHITECTURE)
            arch_doc = await self._arch_agent.run(spec)
            task.phases[TaskPhase.ARCHITECTURE.value].output = arch_doc[:500]
            task.phases[TaskPhase.ARCHITECTURE.value].status = TaskStatus.COMPLETED
            task.phases[TaskPhase.ARCHITECTURE.value].completed_at = datetime.utcnow()
            await self._idle_all_except(AgentType.ARCHITECT)

            if hitm_enabled:
                approved = await self._hitm_gate(
                    "arch_review",
                    "Architecture document is ready.",
                    {"architecture_markdown": arch_doc},
                )
                if not approved:
                    await self._abort(task, "Architecture rejected by reviewer")
                    return

            # ── CODING ───────────────────────────────────────────────────────
            await self._transition(task, TaskPhase.CODING)
            code_files = await self._coder_agent.run(spec, arch_doc)
            task.phases[TaskPhase.CODING.value].output = f"{len(code_files)} files generated"
            task.phases[TaskPhase.CODING.value].status = TaskStatus.COMPLETED
            task.phases[TaskPhase.CODING.value].completed_at = datetime.utcnow()
            await self._idle_all_except(AgentType.CODER)

            # ── TESTING (parallel with coding artifacts) ──────────────────────
            await self._transition(task, TaskPhase.TESTING)
            test_files = await self._tester_agent.run(spec, code_files)
            task.phases[TaskPhase.TESTING.value].output = f"{len(test_files)} test files"
            task.phases[TaskPhase.TESTING.value].status = TaskStatus.COMPLETED
            task.phases[TaskPhase.TESTING.value].completed_at = datetime.utcnow()
            await self._idle_all_except(AgentType.TESTER)

            # ── REVIEW ────────────────────────────────────────────────────────
            await self._transition(task, TaskPhase.REVIEW)
            review_report, verdict = await self._reviewer_agent.run(spec, code_files, test_files)
            task.phases[TaskPhase.REVIEW.value].output = f"Verdict: {verdict}"
            task.phases[TaskPhase.REVIEW.value].status = TaskStatus.COMPLETED
            task.phases[TaskPhase.REVIEW.value].completed_at = datetime.utcnow()
            await self._idle_all_except(AgentType.REVIEWER)

            if hitm_enabled:
                approved = await self._hitm_gate(
                    "review_gate",
                    f"Code review complete. Verdict: {verdict}",
                    {"review_report": review_report, "verdict": verdict},
                )
                if not approved:
                    await self._abort(task, "Delivery rejected after review")
                    return

            # ── DELIVERY ──────────────────────────────────────────────────────
            await self._transition(task, TaskPhase.DELIVERY)
            await self._deliver(task, spec, arch_doc, code_files, test_files, review_report)
            task.overall_status = TaskStatus.COMPLETED
            await bus.emit("task.log", {
                "message": "✅ Delivery complete!",
                "level": "success",
                "agent": "coordinator",
            })

        except asyncio.CancelledError:
            task.overall_status = TaskStatus.FAILED
            await bus.emit("task.log", {
                "message": "Pipeline cancelled",
                "level": "error",
                "agent": "coordinator",
            })
            raise
        except Exception as exc:
            task.overall_status = TaskStatus.FAILED
            await bus.emit("task.log", {
                "message": f"Pipeline error: {exc}",
                "level": "error",
                "agent": "coordinator",
            })
            raise

    # -------------------------------------------------------------- helpers
    async def _transition(self, task: Task, phase: TaskPhase) -> None:
        task.current_phase = phase
        task.phases[phase.value].status = TaskStatus.IN_PROGRESS
        task.phases[phase.value].started_at = datetime.utcnow()
        await bus.emit("task.phase", {
            "phase": phase.value,
            "status": TaskStatus.IN_PROGRESS.value,
        }, source="coordinator")
        await bus.emit("task.log", {
            "message": f"▶ Phase: {phase.value.upper()}",
            "level": "info",
            "agent": "coordinator",
        })

    async def _idle_all_except(self, keep: AgentType) -> None:
        for agent_type in AgentType:
            if agent_type != keep:
                await bus.emit("agent.status", {
                    "agent": agent_type.value,
                    "status": AgentStatus.IDLE.value,
                    "activity": "Standing by",
                })

    async def _hitm_gate(self, checkpoint_id: str, message: str, data: dict) -> bool:
        """Returns True if approved, False if rejected."""
        await bus.emit("task.log", {
            "message": f"⏸ HITM checkpoint: {message}",
            "level": "warning",
            "agent": "coordinator",
        })
        # Mark relevant agents as awaiting review
        for t in AgentType:
            await bus.emit("agent.status", {
                "agent": t.value,
                "status": AgentStatus.AWAITING_HITM.value,
                "activity": "Waiting for your approval",
            })

        result = await state.create_hitm_checkpoint(checkpoint_id, {
            "message": message,
            **data,
        })
        approved = result.get("approved", False)
        notes = result.get("notes", "")

        await bus.emit("task.log", {
            "message": f"{'✅ Approved' if approved else '❌ Rejected'}" + (f": {notes}" if notes else ""),
            "level": "success" if approved else "error",
            "agent": "coordinator",
        })
        return approved

    async def _abort(self, task: Task, reason: str) -> None:
        task.overall_status = TaskStatus.REJECTED
        await bus.emit("task.log", {
            "message": f"Pipeline aborted: {reason}",
            "level": "error",
            "agent": "coordinator",
        })
        for t in AgentType:
            await bus.emit("agent.status", {
                "agent": t.value,
                "status": AgentStatus.IDLE.value,
                "activity": "Aborted",
            })

    async def _deliver(
        self,
        task: Task,
        spec,
        arch_doc: str,
        code_files: dict[str, str],
        test_files: dict[str, str],
        review_report: str,
    ) -> None:
        out_dir = settings.output_dir / task.id
        out_dir.mkdir(parents=True, exist_ok=True)

        # Spec
        (out_dir / "spec.md").write_text(spec.to_markdown(), encoding="utf-8")
        # Architecture
        (out_dir / "architecture.md").write_text(arch_doc, encoding="utf-8")
        # Code files
        for path, content in code_files.items():
            file_path = out_dir / path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")
        # Test files
        for path, content in test_files.items():
            file_path = out_dir / path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")
        # Review report
        (out_dir / "review_report.md").write_text(review_report, encoding="utf-8")

        task.phases[TaskPhase.DELIVERY.value].status = TaskStatus.COMPLETED
        task.phases[TaskPhase.DELIVERY.value].output = str(out_dir)
        task.phases[TaskPhase.DELIVERY.value].completed_at = datetime.utcnow()

        await bus.emit("task.log", {
            "message": f"📦 Deliverables saved to {out_dir}",
            "level": "success",
            "agent": "coordinator",
        })
