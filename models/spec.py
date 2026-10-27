"""Spec-driven development data models."""
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class AcceptanceCriterion(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex[:6])
    description: str
    met: bool = False
    notes: str = ""


class UserStory(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex[:6])
    as_a: str
    i_want: str
    so_that: str
    priority: str = "medium"  # low / medium / high / critical
    acceptance_criteria: list[AcceptanceCriterion] = Field(default_factory=list)

    @property
    def text(self) -> str:
        return f"As a {self.as_a}, I want {self.i_want}, so that {self.so_that}."


class TechnicalSpec(BaseModel):
    overview: str = ""
    architecture_notes: str = ""
    components: list[str] = Field(default_factory=list)
    data_models: list[str] = Field(default_factory=list)
    apis: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)


class Spec(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex[:8])
    task_id: str = ""
    title: str
    raw_ask: str
    summary: str = ""
    user_stories: list[UserStory] = Field(default_factory=list)
    technical_spec: TechnicalSpec = Field(default_factory=TechnicalSpec)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    approved: bool = False
    version: int = 1

    @property
    def acceptance_rate(self) -> float:
        criteria = [
            ac
            for us in self.user_stories
            for ac in us.acceptance_criteria
        ]
        if not criteria:
            return 0.0
        return sum(1 for c in criteria if c.met) / len(criteria)

    def to_markdown(self) -> str:
        lines = [
            f"# Spec: {self.title}",
            f"\n## Summary\n{self.summary}",
            "\n## User Stories",
        ]
        for us in self.user_stories:
            lines.append(f"\n### [{us.priority.upper()}] {us.text}")
            lines.append("**Acceptance Criteria:**")
            for ac in us.acceptance_criteria:
                tick = "✅" if ac.met else "⬜"
                lines.append(f"- {tick} {ac.description}")
        lines += [
            "\n## Technical Specification",
            f"\n### Overview\n{self.technical_spec.overview}",
            f"\n### Architecture\n{self.technical_spec.architecture_notes}",
        ]
        if self.technical_spec.components:
            lines.append("\n### Components")
            lines += [f"- {c}" for c in self.technical_spec.components]
        if self.technical_spec.dependencies:
            lines.append("\n### Dependencies")
            lines += [f"- {d}" for d in self.technical_spec.dependencies]
        if self.technical_spec.open_questions:
            lines.append("\n### Open Questions")
            lines += [f"- {q}" for q in self.technical_spec.open_questions]
        return "\n".join(lines)
