"""Coordinator for the deterministic research team."""

from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor, as_completed

from agents.fact_checker import FactCheckerAgent
from agents.planner import PlannerAgent
from agents.researcher import ResearcherAgent
from agents.reviewer import ReviewerAgent
from agents.writer import WriterAgent
from models import RunResult, TeamMessage, TeamState
from search import load_sources

MAX_WORKERS = 4


class MultiAgentResearchTeam:
    def __init__(self) -> None:
        self.planner = PlannerAgent()
        self.fact_checker = FactCheckerAgent()
        self.writer = WriterAgent()
        self.reviewer = ReviewerAgent()

    @staticmethod
    def _message(
        state: TeamState,
        sender: str,
        recipient: str,
        kind: str,
        content: str,
    ) -> None:
        state.messages.append(
            TeamMessage(
                sender=sender,
                recipient=recipient,
                kind=kind,
                content=content,
            )
        )

    def run(
        self,
        question: str,
        *,
        top_k_per_task: int = 2,
        max_workers: int = MAX_WORKERS,
    ) -> RunResult:
        if max_workers < 1 or max_workers > MAX_WORKERS:
            raise ValueError(
                f"max_workers must be between 1 and {MAX_WORKERS}."
            )

        sources = load_sources()
        state = TeamState(question=question, status="planning")

        state.plan = self.planner.plan(question)
        self._message(
            state,
            "coordinator",
            self.planner.name,
            "delegate",
            f"Plan research for: {state.plan.question}",
        )
        self._message(
            state,
            self.planner.name,
            "coordinator",
            "result",
            state.plan.rationale,
        )

        state.status = "researching"
        futures = {}

        with ThreadPoolExecutor(
            max_workers=min(max_workers, len(state.plan.tasks))
        ) as executor:
            for index, task in enumerate(state.plan.tasks, start=1):
                worker = ResearcherAgent(str(index))
                self._message(
                    state,
                    "coordinator",
                    worker.name,
                    "delegate",
                    f"{task.id} | {task.facet} | {task.query}",
                )
                future = executor.submit(
                    worker.research,
                    task,
                    sources=sources,
                    top_k=top_k_per_task,
                )
                futures[future] = (worker, task)

            task_evidence: dict[str, list] = {}
            completion_messages: dict[str, TeamMessage] = {}

            for future in as_completed(futures):
                worker, task = futures[future]
                try:
                    evidence = future.result()
                    task_evidence[task.id] = evidence
                    completion_messages[task.id] = TeamMessage(
                        sender=worker.name,
                        recipient="coordinator",
                        kind="result",
                        content=(
                            f"{task.id}: returned {len(evidence)} evidence item(s)."
                        ),
                    )
                except Exception as exc:
                    failure = (
                        f"research:{task.id}:{type(exc).__name__}:{exc}"
                    )
                    state.failures.append(failure)
                    task_evidence[task.id] = []
                    completion_messages[task.id] = TeamMessage(
                        sender=worker.name,
                        recipient="coordinator",
                        kind="failure",
                        content=failure,
                    )

        # Append completion messages in plan order so the trace is deterministic.
        for task in state.plan.tasks:
            state.messages.append(completion_messages[task.id])
            state.evidence.extend(task_evidence.get(task.id, []))

        state.status = "fact_checking"
        self._message(
            state,
            "coordinator",
            self.fact_checker.name,
            "delegate",
            f"Verify {len(state.evidence)} evidence item(s).",
        )

        try:
            state.claims = self.fact_checker.verify(
                state.evidence,
                sources=sources,
            )
        except Exception as exc:
            state.failures.append(
                f"critical:fact_checker:{type(exc).__name__}:{exc}"
            )
            state.status = "failed"
            return self._result(state)

        verified_count = sum(claim.verified for claim in state.claims)
        self._message(
            state,
            self.fact_checker.name,
            "coordinator",
            "result",
            f"Verified {verified_count}/{len(state.claims)} claim(s).",
        )

        state.status = "writing"
        self._message(
            state,
            "coordinator",
            self.writer.name,
            "delegate",
            "Write only from verified claims.",
        )
        state.draft = self.writer.write(
            state.plan.question,
            state.plan,
            state.claims,
            sources=sources,
        )
        self._message(
            state,
            self.writer.name,
            "coordinator",
            "result",
            f"Draft contains {len(state.draft)} character(s).",
        )

        state.status = "reviewing"
        self._message(
            state,
            "coordinator",
            self.reviewer.name,
            "delegate",
            "Apply explicit acceptance criteria.",
        )
        state.review = self.reviewer.review(
            state.plan,
            state.claims,
            state.draft,
            failures=state.failures,
        )
        self._message(
            state,
            self.reviewer.name,
            "coordinator",
            "result",
            (
                "approved"
                if state.review.approved
                else "rejected: " + ", ".join(state.review.issues)
            ),
        )

        if state.review.approved:
            state.report = state.draft
            state.status = "approved"
        else:
            state.report = ""
            state.status = "review_failed"

        return self._result(state)

    @staticmethod
    def _result(state: TeamState) -> RunResult:
        plan_tasks = len(state.plan.tasks) if state.plan else 0
        verified = sum(claim.verified for claim in state.claims)
        unique_sources = len(
            {claim.source_id for claim in state.claims if claim.verified}
        )
        covered_tasks = len(
            {claim.task_id for claim in state.claims if claim.verified}
        )

        metrics = {
            "roles_used": 5,
            "planned_tasks": plan_tasks,
            "evidence_items": len(state.evidence),
            "verified_claims": verified,
            "unique_sources": unique_sources,
            "covered_tasks": covered_tasks,
            "coverage_ratio": (
                round(covered_tasks / plan_tasks, 3)
                if plan_tasks else 0.0
            ),
            "coordination_messages": len(state.messages),
            "worker_failures": sum(
                failure.startswith("research:")
                for failure in state.failures
            ),
        }

        return RunResult(
            mode="multi-agent",
            question=state.plan.question if state.plan else state.question,
            report=state.report,
            status=state.status,
            metrics=metrics,
            trace=tuple(state.messages),
            failures=tuple(state.failures),
        )
