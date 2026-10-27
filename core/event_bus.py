"""Async publish-subscribe event bus.

Used for agent-to-orchestrator, agent-to-agent, and orchestrator-to-dashboard
communication without tight coupling.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Awaitable
from uuid import uuid4


@dataclass
class Event:
    type: str                           # e.g. "agent.status", "task.phase", "hitm.request"
    payload: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: uuid4().hex[:8])
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    source: str = "system"


Handler = Callable[[Event], Awaitable[None]]


class EventBus:
    """Lightweight async pub/sub bus."""

    def __init__(self) -> None:
        self._handlers: dict[str, list[Handler]] = {}
        self._wildcard: list[Handler] = []

    def subscribe(self, event_type: str, handler: Handler) -> None:
        """Subscribe to a specific event type or '*' for all events."""
        if event_type == "*":
            self._wildcard.append(handler)
        else:
            self._handlers.setdefault(event_type, []).append(handler)

    def unsubscribe(self, event_type: str, handler: Handler) -> None:
        if event_type == "*":
            self._wildcard.remove(handler)
        else:
            lst = self._handlers.get(event_type, [])
            if handler in lst:
                lst.remove(handler)

    async def publish(self, event: Event) -> None:
        handlers = list(self._handlers.get(event.type, [])) + list(self._wildcard)
        await asyncio.gather(*[h(event) for h in handlers], return_exceptions=True)

    async def emit(
        self,
        event_type: str,
        payload: dict[str, Any] | None = None,
        source: str = "system",
    ) -> None:
        await self.publish(Event(type=event_type, payload=payload or {}, source=source))


# Global singleton used across the app
bus = EventBus()
