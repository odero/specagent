"""Reviewer Agent — code review + spec compliance report."""
from __future__ import annotations

from models.agent_state import AgentType, AgentStatus
from models.spec import Spec
from agents.base import BaseAgent
from speckit import SpecKit


_REVIEW_SYSTEM = """\
You are a staff software engineer conducting a thorough code review.

Produce a structured Markdown review covering:
1. **Spec Compliance** — does the code meet every acceptance criterion? (cite by criterion text)
2. **Code Quality** — readability, structure, naming, SOLID principles
3. **Security** — any vulnerabilities (OWASP top 10, secrets in code, etc.)
4. **Performance** — obvious bottlenecks, N+1 queries, blocking I/O
5. **Test Coverage** — gaps in the test suite
6. **Suggested Improvements** — concrete, actionable items with before/after snippets
7. **Verdict** — APPROVE / REQUEST_CHANGES / REJECT with one-sentence justification

Be specific and constructive. Reference line numbers or file names where possible."""


class ReviewerAgent(BaseAgent):
    agent_type = AgentType.REVIEWER

    def __init__(self) -> None:
        super().__init__()
        self._kit = SpecKit()

    async def run(
        self,
        spec: Spec,
        code_files: dict[str, str],
        test_files: dict[str, str],
    ) -> tuple[str, str]:
        """Returns (review_report_md, verdict: 'APPROVE'|'REQUEST_CHANGES'|'REJECT')."""
        await self._set_status(AgentStatus.THINKING, "Reading all deliverables")
        await self._log("Starting code review...")

        # Build combined artifact string
        all_files = {**code_files, **test_files}
        code_summary = "\n\n".join(
            f"### {path}\n```python\n{content[:2000]}\n```"
            for path, content in list(all_files.items())[:8]
        )
        prompt = f"## SPEC\n{spec.to_markdown()}\n\n## DELIVERABLES\n{code_summary}"

        await self._set_status(AgentStatus.WORKING, "Reviewing code")

        tokens: list[str] = []
        async for token in self._stream_complete(
            system=_REVIEW_SYSTEM,
            user=prompt,
            temperature=0.2,
        ):
            tokens.append(token)

        review = "".join(tokens)

        # Run spec validation
        combined_code = "\n\n".join(
            f"# {p}\n{c}" for p, c in code_files.items()
        )
        spec = await self._kit.validate(spec, combined_code, "generated code")

        # Extract verdict
        verdict = "APPROVE"
        upper = review.upper()
        if "REQUEST_CHANGES" in upper:
            verdict = "REQUEST_CHANGES"
        elif "REJECT" in upper:
            verdict = "REJECT"

        await self._log(f"Review complete — verdict: {verdict}", level="success")
        await self._set_status(AgentStatus.CELEBRATING, f"Review done: {verdict}")
        return review, verdict
