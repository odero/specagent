"""Agent state models."""
from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class AgentType(str, Enum):
    SPEC = "spec"
    ARCHITECT = "architect"
    CODER = "coder"
    TESTER = "tester"
    REVIEWER = "reviewer"


class AgentStatus(str, Enum):
    IDLE = "idle"
    THINKING = "thinking"
    WORKING = "working"
    AWAITING_HITM = "awaiting_hitm"
    CELEBRATING = "celebrating"
    ERROR = "error"


# Personality / display metadata per agent type
AGENT_META: dict[AgentType, dict] = {
    AgentType.SPEC: {
        "name": "Speck",
        "role": "Spec Writer",
        "emoji": "📋",
        "color": "#4a90d9",
        "sprite": "spec",
        "desk_pos": 0,
    },
    AgentType.ARCHITECT: {
        "name": "Arch",
        "role": "Architect",
        "emoji": "🏗️",
        "color": "#f5a623",
        "sprite": "architect",
        "desk_pos": 1,
    },
    AgentType.CODER: {
        "name": "Cody",
        "role": "Developer",
        "emoji": "💻",
        "color": "#7ed321",
        "sprite": "coder",
        "desk_pos": 2,
    },
    AgentType.TESTER: {
        "name": "Tess",
        "role": "QA Engineer",
        "emoji": "🧪",
        "color": "#bd10e0",
        "sprite": "tester",
        "desk_pos": 3,
    },
    AgentType.REVIEWER: {
        "name": "Rex",
        "role": "Code Reviewer",
        "emoji": "🔍",
        "color": "#e74c3c",
        "sprite": "reviewer",
        "desk_pos": 4,
    },
}


class AgentState(BaseModel):
    type: AgentType
    status: AgentStatus = AgentStatus.IDLE
    current_task_id: str | None = None
    current_activity: str = "Standing by"
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    output_preview: str = ""  # last ~200 chars of output for dashboard

    @property
    def meta(self) -> dict:
        return AGENT_META[self.type]

    def update(self, status: AgentStatus, activity: str = "") -> None:
        self.status = status
        if activity:
            self.current_activity = activity
        self.last_updated = datetime.utcnow()
