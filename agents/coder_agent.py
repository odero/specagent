"""Coder Agent — generates production code from spec + architecture."""
from __future__ import annotations

import json

from models.agent_state import AgentType, AgentStatus
from models.spec import Spec
from agents.base import BaseAgent


_SYSTEM = """\
You are an elite software engineer (GitHub Copilot level). Given a spec and an
architecture document, produce complete, production-ready code.

Rules:
- Output a JSON object where each key is a file path and each value is the full file content.
- Include ALL files needed to run the feature (no placeholders, no TODO stubs).
- Follow best practices: type hints, docstrings, error handling, logging.
- Write idiomatic, clean code. Prefer composition over inheritance.
- Include a brief inline comment explaining non-obvious logic.

Output format (ONLY valid JSON, no fences):
{
  "path/to/file.py": "full file content",
  "path/to/another.py": "full file content"
}"""


class CoderAgent(BaseAgent):
    agent_type = AgentType.CODER

    async def run(self, spec: Spec, architecture: str) -> dict[str, str]:
        await self._set_status(AgentStatus.THINKING, "Reading spec and architecture")
        await self._log("Starting code generation...")

        prompt = (
            f"## SPEC\n{spec.to_markdown()}\n\n"
            f"## ARCHITECTURE\n{architecture}"
        )

        await self._set_status(AgentStatus.WORKING, "Writing code")

        tokens: list[str] = []
        async for token in self._stream_complete(
            system=_SYSTEM,
            user=prompt,
            temperature=0.2,
        ):
            tokens.append(token)

        raw = "".join(tokens).strip()
        # Strip markdown fences if present
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]

        try:
            files: dict[str, str] = json.loads(raw)
        except json.JSONDecodeError:
            await self._log("JSON parse failed — wrapping raw output", level="warning")
            files = {"generated_code.py": raw}

        file_count = len(files)
        await self._log(f"Code generated: {file_count} files", level="success")
        await self._set_status(AgentStatus.CELEBRATING, f"{file_count} files written")
        return files
