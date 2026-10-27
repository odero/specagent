"""SpecKit — Spec-Driven Development Engine.

Converts a raw feature/scenario ask into a structured, LLM-generated spec
and later validates deliverables against it.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from datetime import datetime

from openai import AsyncOpenAI

from config import settings
from models.spec import Spec, UserStory, AcceptanceCriterion, TechnicalSpec


_SPEC_SYSTEM = """\
You are an elite software product manager and technical architect.
Your job is to convert a feature request into a rigorous, structured specification.

Output ONLY valid JSON matching this exact schema (no markdown fences):
{
  "title": "short feature title",
  "summary": "2-3 sentence executive summary",
  "user_stories": [
    {
      "as_a": "role",
      "i_want": "capability",
      "so_that": "benefit",
      "priority": "high|medium|low|critical",
      "acceptance_criteria": [
        {"description": "measurable, testable criterion"}
      ]
    }
  ],
  "technical_spec": {
    "overview": "technical approach",
    "architecture_notes": "key architectural decisions",
    "components": ["list of major components"],
    "data_models": ["key data entities"],
    "apis": ["external/internal APIs involved"],
    "dependencies": ["libraries or services needed"],
    "constraints": ["technical or business constraints"],
    "open_questions": ["unresolved questions"]
  }
}

Generate 3-6 user stories. Each story must have 2-4 acceptance criteria.
Be specific and testable. Think production-grade."""


_VALIDATE_SYSTEM = """\
You are a QA engineer reviewing a code deliverable against a specification.
Given a spec and a code artifact, determine which acceptance criteria are met.

Output ONLY valid JSON:
{
  "met": ["criterion_id_1", "criterion_id_2"],
  "partial": ["criterion_id_3"],
  "unmet": ["criterion_id_4"],
  "notes": "brief overall assessment"
}"""


class SpecKit:
    """Spec-driven development engine."""

    def __init__(self) -> None:
        self._client = AsyncOpenAI(
            api_key=settings.effective_api_key,
            base_url=settings.openai_base_url,
        )

    async def generate(self, raw_ask: str, task_id: str = "") -> Spec:
        """Generate a full Spec from a feature/scenario description."""
        resp = await self._client.chat.completions.create(
            model=settings.effective_model,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
            messages=[
                {"role": "system", "content": _SPEC_SYSTEM},
                {"role": "user", "content": f"Feature request:\n\n{raw_ask}"},
            ],
        )
        raw = resp.choices[0].message.content or "{}"
        raw = self._strip_fences(raw)
        data = json.loads(raw)

        stories = []
        for us_data in data.get("user_stories", []):
            criteria = [
                AcceptanceCriterion(description=ac["description"])
                for ac in us_data.get("acceptance_criteria", [])
            ]
            stories.append(UserStory(
                as_a=us_data["as_a"],
                i_want=us_data["i_want"],
                so_that=us_data["so_that"],
                priority=us_data.get("priority", "medium"),
                acceptance_criteria=criteria,
            ))

        ts_data = data.get("technical_spec", {})
        tech = TechnicalSpec(
            overview=ts_data.get("overview", ""),
            architecture_notes=ts_data.get("architecture_notes", ""),
            components=ts_data.get("components", []),
            data_models=ts_data.get("data_models", []),
            apis=ts_data.get("apis", []),
            dependencies=ts_data.get("dependencies", []),
            constraints=ts_data.get("constraints", []),
            open_questions=ts_data.get("open_questions", []),
        )

        spec = Spec(
            task_id=task_id,
            title=data.get("title", raw_ask[:60]),
            raw_ask=raw_ask,
            summary=data.get("summary", ""),
            user_stories=stories,
            technical_spec=tech,
        )
        self._save(spec)
        return spec

    async def validate(self, spec: Spec, artifact: str, artifact_label: str = "") -> Spec:
        """Check artifact against spec criteria; updates spec in place."""
        criteria_map = {
            ac.id: ac
            for us in spec.user_stories
            for ac in us.acceptance_criteria
        }
        criteria_list = "\n".join(
            f"- id:{ac_id}  {ac.description}"
            for ac_id, ac in criteria_map.items()
        )
        prompt = (
            f"SPEC TITLE: {spec.title}\n\n"
            f"ACCEPTANCE CRITERIA:\n{criteria_list}\n\n"
            f"ARTIFACT ({artifact_label or 'code'}):\n```\n{artifact[:8000]}\n```"
        )
        resp = await self._client.chat.completions.create(
            model=settings.effective_model,
            temperature=0.1,
            max_tokens=1024,
            messages=[
                {"role": "system", "content": _VALIDATE_SYSTEM},
                {"role": "user", "content": prompt},
            ],
        )
        raw = self._strip_fences(resp.choices[0].message.content or "{}")
        result = json.loads(raw)

        for ac_id in result.get("met", []):
            if ac_id in criteria_map:
                criteria_map[ac_id].met = True
        return spec

    # ---------------------------------------------------------------- utils
    @staticmethod
    def _strip_fences(text: str) -> str:
        text = text.strip()
        text = re.sub(r"^```[a-z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
        return text.strip()

    def _save(self, spec: Spec) -> None:
        path = settings.specs_dir / f"spec_{spec.id}.md"
        path.write_text(spec.to_markdown(), encoding="utf-8")
