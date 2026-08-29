"""Reviewer agent."""

from __future__ import annotations
from models import Claim, ResearchPlan, ReviewResult


class ReviewerAgent:
    name = "reviewer"

    def review(
        self,
        plan: ResearchPlan,
        claims: list[Claim],
        report: str,
        *,
        failures: list[str],
    ) -> ReviewResult:
        verified = [claim for claim in claims if claim.verified]
        covered_tasks = {claim.task_id for claim in verified}

        checks = {
            "all_tasks_covered": all(
                task.id in covered_tasks for task in plan.tasks
            ),
            "verified_claims_present": bool(verified),
            "citations_present": all(
                f"[{claim.source_id}]" in report for claim in verified
            ),
            "sources_section_present": "## Sources" in report,
            "no_critical_failures": not any(
                failure.startswith("critical:")
                for failure in failures
            ),
        }

        issues = tuple(
            label.replace("_", " ")
            for label, passed in checks.items()
            if not passed
        )

        return ReviewResult(
            approved=all(checks.values()),
            checks=checks,
            issues=issues,
        )
