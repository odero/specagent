"""Tester Agent — generates a comprehensive test suite."""
from __future__ import annotations

import json

from models.agent_state import AgentType, AgentStatus
from models.spec import Spec
from agents.base import BaseAgent


_SYSTEM = """\
You are a senior QA engineer and test architect. Given a spec and implementation files,
produce a comprehensive test suite.

Coverage requirements:
- Unit tests for every public function/method
- Integration tests for all API endpoints
- Edge cases and error paths
- At least one test per acceptance criterion

Use pytest with descriptive test names. Include fixtures, mocks, and parametrize where useful.

Output format (ONLY valid JSON, no fences):
{
  "tests/test_unit.py": "full test file",
  "tests/test_integration.py": "full test file",
  "tests/conftest.py": "fixtures"
}"""


class TesterAgent(BaseAgent):
    agent_type = AgentType.TESTER

    async def run(self, spec: Spec, code_files: dict[str, str]) -> dict[str, str]:
        await self._set_status(AgentStatus.THINKING, "Analysing code to test")
        await self._log("Planning test coverage...")

        code_summary = "\n\n".join(
            f"### {path}\n```python\n{content[:2000]}\n```"
            for path, content in list(code_files.items())[:6]
        )
        prompt = f"## SPEC\n{spec.to_markdown()}\n\n## CODE\n{code_summary}"

        await self._set_status(AgentStatus.WORKING, "Writing tests")

        tokens: list[str] = []
        async for token in self._stream_complete(
            system=_SYSTEM,
            user=prompt,
            temperature=0.2,
        ):
            tokens.append(token)

        raw = "".join(tokens).strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]

        try:
            test_files: dict[str, str] = json.loads(raw)
        except json.JSONDecodeError:
            test_files = {"tests/test_generated.py": raw}

        await self._log(f"Tests written: {len(test_files)} files", level="success")
        await self._set_status(AgentStatus.CELEBRATING, "Tests ready")
        return test_files
