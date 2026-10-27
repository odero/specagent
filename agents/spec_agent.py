"""Spec Agent — generates the project spec using SpecKit."""
from __future__ import annotations

from models.agent_state import AgentType, AgentStatus
from models.spec import Spec
from agents.base import BaseAgent
from speckit import SpecKit


class SpecAgent(BaseAgent):
    agent_type = AgentType.SPEC

    def __init__(self) -> None:
        super().__init__()
        self._kit = SpecKit()

    async def run(self, raw_ask: str, task_id: str) -> Spec:
        await self._set_status(AgentStatus.THINKING, "Analysing feature request")
        await self._log("Starting spec generation...")

        await self._set_status(AgentStatus.WORKING, "Generating spec with SpecKit")
        spec = await self._kit.generate(raw_ask, task_id)

        story_count = len(spec.user_stories)
        criteria_count = sum(len(us.acceptance_criteria) for us in spec.user_stories)
        await self._log(
            f"Spec generated: {story_count} user stories, {criteria_count} acceptance criteria",
            level="success",
        )
        await self._set_status(
            AgentStatus.CELEBRATING,
            f"Spec ready — {story_count} stories",
        )
        return spec
