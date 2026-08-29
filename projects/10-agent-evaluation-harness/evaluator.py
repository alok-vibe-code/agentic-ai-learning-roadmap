"""Case-level evaluation logic."""

from __future__ import annotations
from models import CaseResult, CheckResult, EvalCase, AgentRun
from observability import validate_trace


def _check(name: str, passed: bool, detail: str) -> CheckResult:
    return CheckResult(name=name, passed=bool(passed), detail=detail)


def evaluate_case(case: EvalCase, run: AgentRun) -> CaseResult:
    checks: list[CheckResult] = []

    checks.append(_check(
        "task_completion",
        run.status == case.expected_status,
        f"expected status={case.expected_status}; observed={run.status}",
    ))

    observed_tools = [call.name for call in run.tool_calls]
    if case.expected_tool is None:
        tool_ok = len(observed_tools) == 0
        tool_detail = f"expected no tool; observed={observed_tools}"
    else:
        tool_ok = case.expected_tool in observed_tools
        tool_detail = (
            f"expected tool={case.expected_tool}; observed={observed_tools}"
        )
    checks.append(_check("tool_selection", tool_ok, tool_detail))

    answer_fold = run.answer.casefold()
    missing = [
        term for term in case.must_include
        if term.casefold() not in answer_fold
    ]
    forbidden = [
        term for term in case.must_not_include
        if term.casefold() in answer_fold
    ]
    content_ok = not missing and not forbidden
    checks.append(_check(
        "content_requirements",
        content_ok,
        f"missing={missing}; forbidden_present={forbidden}",
    ))

    if case.must_cite_source:
        citation_ok = bool(run.citations)
        citation_detail = f"citations={list(run.citations)}"
    else:
        citation_ok = True
        citation_detail = "citation not required"
    checks.append(_check("citation_requirement", citation_ok, citation_detail))

    observed_source_ids = {
        source_id
        for call in run.tool_calls
        for source_id in call.returned_source_ids
    }

    if run.citations:
        grounded = all(
            citation in observed_source_ids
            and (
                not case.allowed_source_ids
                or citation in case.allowed_source_ids
            )
            for citation in run.citations
        )
        grounded_detail = (
            f"citations={list(run.citations)}; "
            f"observed_sources={sorted(observed_source_ids)}; "
            f"allowed={list(case.allowed_source_ids)}"
        )
    elif case.must_cite_source:
        grounded = False
        grounded_detail = "required citation missing"
    else:
        grounded = True
        grounded_detail = "no citation expected"
    checks.append(_check("groundedness", grounded, grounded_detail))

    steps_ok = run.steps <= case.max_steps
    checks.append(_check(
        "step_budget",
        steps_ok,
        f"max_steps={case.max_steps}; observed={run.steps}",
    ))

    trace_ok, trace_detail = validate_trace(run.trace)
    checks.append(_check("trace_integrity", trace_ok, trace_detail))

    error_ok = run.error is None or case.expected_status == "failed"
    checks.append(_check(
        "unexpected_error",
        error_ok,
        f"error={run.error}",
    ))

    passed_count = sum(check.passed for check in checks)
    score = round(passed_count / len(checks), 4)

    return CaseResult(
        case_id=case.id,
        passed=all(check.passed for check in checks),
        score=score,
        checks=tuple(checks),
        run=run,
    )
