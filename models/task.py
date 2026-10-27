"""Task and pipeline-phase models."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    AWAITING_REVIEW = "awaiting_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskPhase(str, Enum):
    INTAKE = "intake"
    SPEC = "spec"
    ARCHITECTURE = "architecture"
    CODING = "coding"
    TESTING = "testing"
    REVIEW = "review"
    DELIVERY = "delivery"


PHASE_ORDER = [
    TaskPhase.INTAKE,
    TaskPhase.SPEC,
    TaskPhase.ARCHITECTURE,
    TaskPhase.CODING,
    TaskPhase.TESTING,
    TaskPhase.REVIEW,
    TaskPhase.DELIVERY,
]


class PhaseResult(BaseModel):
    phase: TaskPhase
    status: TaskStatus = TaskStatus.PENDING
    output: str = ""
    artifacts: list[str] = Field(default_factory=list)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    reviewer_notes: str = ""


class Task(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex[:8])
    title: str
    description: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    current_phase: TaskPhase = TaskPhase.INTAKE
    overall_status: TaskStatus = TaskStatus.PENDING
    hitm_enabled: bool = True
    phases: dict[str, PhaseResult] = Field(default_factory=dict)
    logs: list[dict[str, Any]] = Field(default_factory=list)

    def model_post_init(self, __context: Any) -> None:
        if not self.phases:
            self.phases = {p.value: PhaseResult(phase=p) for p in TaskPhase}

    def log(self, message: str, level: str = "info", agent: str = "system") -> None:
        self.logs.append({
            "ts": datetime.utcnow().isoformat(),
            "level": level,
            "agent": agent,
            "message": message,
        })
        self.updated_at = datetime.utcnow()

    def advance_phase(self) -> TaskPhase | None:
        idx = PHASE_ORDER.index(self.current_phase)
        if idx + 1 < len(PHASE_ORDER):
            self.current_phase = PHASE_ORDER[idx + 1]
            self.phases[self.current_phase.value].started_at = datetime.utcnow()
            return self.current_phase
        return None

    @property
    def progress_pct(self) -> int:
        idx = PHASE_ORDER.index(self.current_phase)
        return int((idx / (len(PHASE_ORDER) - 1)) * 100)
