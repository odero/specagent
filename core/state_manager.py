"""Global in-memory state manager.

Holds the single active Task, all AgentStates, and the current Spec.
Broadcast to WebSocket clients happens here.
"""
from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import Any

from models.task import Task, TaskStatus, TaskPhase
from models.agent_state import AgentState, AgentStatus, AgentType, AGENT_META
from models.spec import Spec
from core.event_bus import bus, Event


class StateManager:
    def __init__(self) -> None:
        self.task: Task | None = None
        self.spec: Spec | None = None
        self.agents: dict[AgentType, AgentState] = {
            t: AgentState(type=t) for t in AgentType
        }
        self._ws_clients: set[Any] = set()  # WebSocket connections
        self._hitm_futures: dict[str, asyncio.Future] = {}

        # Wire up events → state updates
        bus.subscribe("agent.status", self._on_agent_status)
        bus.subscribe("task.log", self._on_task_log)
        bus.subscribe("task.phase", self._on_task_phase)
        bus.subscribe("spec.updated", self._on_spec_updated)

    # ------------------------------------------------------------------ setup
    def start_task(self, title: str, description: str, hitm: bool = True) -> Task:
        self.task = Task(title=title, description=description, hitm_enabled=hitm)
        self.task.overall_status = TaskStatus.IN_PROGRESS
        self.task.phases[TaskPhase.INTAKE.value].status = TaskStatus.IN_PROGRESS
        asyncio.create_task(self._broadcast_state())
        return self.task

    # ----------------------------------------------------------- agent events
    async def _on_agent_status(self, event: Event) -> None:
        agent_type = AgentType(event.payload["agent"])
        status = AgentStatus(event.payload["status"])
        activity = event.payload.get("activity", "")
        output = event.payload.get("output_preview", "")
        agent = self.agents[agent_type]
        agent.update(status, activity)
        if output:
            agent.output_preview = output
        await self._broadcast_state()

    async def _on_task_log(self, event: Event) -> None:
        if self.task:
            self.task.log(
                event.payload.get("message", ""),
                event.payload.get("level", "info"),
                event.payload.get("agent", "system"),
            )
            await self._broadcast_state()

    async def _on_task_phase(self, event: Event) -> None:
        if self.task:
            phase = TaskPhase(event.payload["phase"])
            status = TaskStatus(event.payload.get("status", TaskStatus.IN_PROGRESS))
            self.task.current_phase = phase
            self.task.phases[phase.value].status = status
            if event.payload.get("output"):
                self.task.phases[phase.value].output = event.payload["output"]
            self.task.updated_at = datetime.utcnow()
            await self._broadcast_state()

    async def _on_spec_updated(self, event: Event) -> None:
        await self._broadcast_state()

    # -------------------------------------------------------------- HITM
    async def create_hitm_checkpoint(self, checkpoint_id: str, data: dict) -> dict:
        """Block until a WebSocket client resolves this checkpoint."""
        loop = asyncio.get_running_loop()
        fut: asyncio.Future = loop.create_future()
        self._hitm_futures[checkpoint_id] = fut

        await bus.emit("hitm.request", {
            "checkpoint_id": checkpoint_id,
            **data,
        })
        await self._broadcast_state()

        result = await fut
        del self._hitm_futures[checkpoint_id]
        return result

    def resolve_hitm(self, checkpoint_id: str, decision: dict) -> None:
        fut = self._hitm_futures.get(checkpoint_id)
        if fut and not fut.done():
            fut.set_result(decision)

    @property
    def pending_checkpoint(self) -> dict | None:
        return {"ids": list(self._hitm_futures.keys())} if self._hitm_futures else None

    # --------------------------------------------------------- WebSocket
    def register_ws(self, ws: Any) -> None:
        self._ws_clients.add(ws)

    def unregister_ws(self, ws: Any) -> None:
        self._ws_clients.discard(ws)

    async def _broadcast_state(self) -> None:
        if not self._ws_clients:
            return
        payload = json.dumps(self.snapshot(), default=str)
        dead = set()
        for ws in self._ws_clients:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.add(ws)
        self._ws_clients -= dead

    def snapshot(self) -> dict:
        return {
            "task": self.task.model_dump() if self.task else None,
            "spec": self.spec.model_dump() if self.spec else None,
            "agents": {
                t.value: {
                    **state.model_dump(),
                    "meta": AGENT_META[t],
                }
                for t, state in self.agents.items()
            },
            "pending_checkpoint": self.pending_checkpoint,
        }


# Singleton
state = StateManager()
