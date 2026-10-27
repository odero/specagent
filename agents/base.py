"""Base agent — wraps OpenAI API, emits state events, handles streaming."""
from __future__ import annotations

import asyncio
from typing import AsyncIterator

from openai import AsyncOpenAI

from config import settings
from core.event_bus import bus
from models.agent_state import AgentType, AgentStatus


class BaseAgent:
    """All specialist agents inherit from this."""

    agent_type: AgentType  # must be set by subclass

    def __init__(self) -> None:
        self._client = AsyncOpenAI(
            api_key=settings.effective_api_key,
            base_url=settings.openai_base_url,
        )

    # -------------------------------------------------------- state helpers
    async def _set_status(self, status: AgentStatus, activity: str = "") -> None:
        await bus.emit("agent.status", {
            "agent": self.agent_type.value,
            "status": status.value,
            "activity": activity,
        }, source=self.agent_type.value)

    async def _log(self, message: str, level: str = "info") -> None:
        await bus.emit("task.log", {
            "agent": self.agent_type.value,
            "message": message,
            "level": level,
        }, source=self.agent_type.value)

    # -------------------------------------------------------- LLM helpers
    async def _complete(
        self,
        system: str,
        user: str,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        resp = await self._client.chat.completions.create(
            model=settings.effective_model,
            temperature=temperature if temperature is not None else settings.llm_temperature,
            max_tokens=max_tokens or settings.llm_max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return resp.choices[0].message.content or ""

    async def _stream_complete(
        self,
        system: str,
        user: str,
        temperature: float | None = None,
    ) -> AsyncIterator[str]:
        """Yield streamed tokens and emit output_preview events."""
        stream = await self._client.chat.completions.create(
            model=settings.effective_model,
            temperature=temperature if temperature is not None else settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
            stream=True,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        buffer = ""
        async for chunk in stream:
            if not chunk.choices:
                continue
            token = chunk.choices[0].delta.content or ""
            buffer += token
            yield token
            # every ~200 chars emit a preview so dashboard can show progress
            if len(buffer) % 200 < len(token):
                await bus.emit("agent.status", {
                    "agent": self.agent_type.value,
                    "status": AgentStatus.WORKING.value,
                    "output_preview": buffer[-200:],
                }, source=self.agent_type.value)
