"""Architect Agent — produces a detailed technical architecture document."""
from __future__ import annotations

from models.agent_state import AgentType, AgentStatus
from models.spec import Spec
from agents.base import BaseAgent


_SYSTEM = """\
You are a principal software architect. Given a project spec, produce a comprehensive
technical architecture document in Markdown.

Include:
1. **System Overview** — high-level description and goals
2. **Architecture Diagram** (ASCII art — boxes and arrows)
3. **Component Breakdown** — each component, its responsibility, and technology
4. **Data Flow** — how data moves through the system
5. **API Design** — key endpoints / interfaces (REST, events, etc.)
6. **Data Models** — entity schemas with fields and types
7. **Technology Stack** — justified choices for each layer
8. **Non-Functional Requirements** — performance, security, scalability notes
9. **Implementation Roadmap** — ordered list of implementation tasks

Be specific, opinionated, and production-ready. Avoid vague statements."""


class ArchitectAgent(BaseAgent):
    agent_type = AgentType.ARCHITECT

    async def run(self, spec: Spec) -> str:
        await self._set_status(AgentStatus.THINKING, "Studying the spec")
        await self._log("Designing technical architecture...")

        await self._set_status(AgentStatus.WORKING, "Drawing up architecture")

        tokens: list[str] = []
        async for token in self._stream_complete(
            system=_SYSTEM,
            user=spec.to_markdown(),
            temperature=0.3,
        ):
            tokens.append(token)

        architecture_doc = "".join(tokens)
        await self._log(
            f"Architecture document ready ({len(architecture_doc)} chars)",
            level="success",
        )
        await self._set_status(AgentStatus.CELEBRATING, "Architecture complete")
        return architecture_doc
