"""Offline tests for Project 10."""

from __future__ import annotations
import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from cases import load_cases
from demo_agent import DemoAgent, _safe_calculate
from evaluator import evaluate_case
from metrics import aggregate_metrics
from models import AgentRun, EvalCase, TraceEvent
from observability import TraceCollector, validate_trace
from regression import check_regression, load_baseline
from reporters import to_json, to_markdown
from main import run_suite


class CaseLoadingTests(unittest.TestCase):
    def test_loads_eight_cases(self):
        self.assertEqual(len(load_cases()), 8)

    def test_ids_unique(self):
        ids = [case.id for case in load_cases()]
        self.assertEqual(len(ids), len(set(ids)))

    def test_queries_nonempty(self):
        self.assertTrue(all(case.query for case in load_cases()))

    def test_step_bounds_valid(self):
        self.assertTrue(all(1 <= case.max_steps <= 20 for case in load_cases()))

    def test_duplicate_ids_rejected(self):
        payload = [
            {
                "id": "x", "query": "one", "expected_status": "completed",
                "expected_tool": None, "must_include": [], "must_not_include": [],
                "must_cite_source": False, "allowed_source_ids": [], "max_steps": 2
            },
            {
                "id": "x", "query": "two", "expected_status": "completed",
                "expected_tool": None, "must_include": [], "must_not_include": [],
                "must_cite_source": False, "allowed_source_ids": [], "max_steps": 2
            },
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cases.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_cases(path)

    def test_invalid_status_rejected(self):
        payload = [{
            "id": "x", "query": "one", "expected_status": "maybe",
            "expected_tool": None, "must_include": [], "must_not_include": [],
            "must_cite_source": False, "allowed_source_ids": [], "max_steps": 2
        }]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cases.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_cases(path)

    def test_empty_suite_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cases.json"
            path.write_text("[]", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_cases(path)

    def test_invalid_step_limit_rejected(self):
        payload = [{
            "id": "x", "query": "one", "expected_status": "completed",
            "expected_tool": None, "must_include": [], "must_not_include": [],
            "must_cite_source": False, "allowed_source_ids": [], "max_steps": 0
        }]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cases.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_cases(path)


class TraceTests(unittest.TestCase):
    def test_trace_id_deterministic(self):
        self.assertEqual(
            TraceCollector("same").trace_id,
            TraceCollector("same").trace_id,
        )

    def test_trace_id_changes_with_seed(self):
        self.assertNotEqual(
            TraceCollector("a").trace_id,
            TraceCollector("b").trace_id,
        )

    def test_span_ids_increment(self):
        t = TraceCollector("x")
        self.assertEqual(t.span_id(), "span-001")
        self.assertEqual(t.span_id(), "span-002")

    def test_valid_trace(self):
        t = TraceCollector("x")
        root = t.span_id()
        child = t.span_id()
        t.record(
            span_id=root, parent_span_id=None,
            kind="run", name="agent.run"
        )
        t.record(
            span_id=child, parent_span_id=root,
            kind="response", name="agent.response"
        )
        ok, _ = validate_trace(t.events())
        self.assertTrue(ok)

    def test_empty_trace_invalid(self):
        ok, _ = validate_trace(())
        self.assertFalse(ok)

    def test_missing_parent_invalid(self):
        event = TraceEvent(
            sequence=1, trace_id="t", span_id="s2",
            parent_span_id="missing", kind="run",
            name="agent.run", attributes={}
        )
        ok, _ = validate_trace((event,))
        self.assertFalse(ok)

    def test_multiple_trace_ids_invalid(self):
        events = (
            TraceEvent(1, "a", "s1", None, "run", "agent.run", {}),
            TraceEvent(2, "b", "s2", "s1", "response", "agent.response", {}),
        )
        ok, _ = validate_trace(events)
        self.assertFalse(ok)

    def test_noncontiguous_sequence_invalid(self):
        events = (
            TraceEvent(1, "a", "s1", None, "run", "agent.run", {}),
            TraceEvent(3, "a", "s2", "s1", "response", "agent.response", {}),
        )
        ok, _ = validate_trace(events)
        self.assertFalse(ok)


class CalculatorTests(unittest.TestCase):
    def test_multiply(self):
        self.assertEqual(_safe_calculate("18 * 7"), 126.0)

    def test_divide(self):
        self.assertEqual(_safe_calculate("144 / 12"), 12.0)

    def test_add(self):
        self.assertEqual(_safe_calculate("2 + 3"), 5.0)

    def test_subtract(self):
        self.assertEqual(_safe_calculate("10 - 4"), 6.0)

    def test_code_execution_rejected(self):
        with self.assertRaises(ValueError):
            _safe_calculate("__import__('os').system('id')")

    def test_function_call_rejected(self):
        with self.assertRaises(ValueError):
            _safe_calculate("abs(-1)")


class GoodCandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.agent = DemoAgent("good")
        cls.cases = {case.id: case for case in load_cases()}

    def test_mcp_uses_search(self):
        run = self.agent.run(self.cases["mcp_spec"].query)
        self.assertEqual(run.tool_calls[0].name, "local_search")

    def test_mcp_cites_observed_source(self):
        run = self.agent.run(self.cases["mcp_spec"].query)
        self.assertEqual(run.citations, ("MCP-SPEC",))
        self.assertIn("MCP-SPEC", run.tool_calls[0].returned_source_ids)

    def test_rag_answer(self):
        run = self.agent.run(self.cases["agentic_rag"].query)
        self.assertIn("retrieval", run.answer.casefold())
        self.assertIn("decision", run.answer.casefold())

    def test_memory_answer(self):
        run = self.agent.run(self.cases["memory_policy"].query)
        self.assertIn("explicit", run.answer.casefold())
        self.assertIn("sensitive", run.answer.casefold())

    def test_multi_agent_answer(self):
        run = self.agent.run(self.cases["multi_agent_tradeoff"].query)
        self.assertIn("coordination", run.answer.casefold())
        self.assertIn("specialization", run.answer.casefold())

    def test_calculator_tool(self):
        run = self.agent.run(self.cases["calculator"].query)
        self.assertEqual(run.tool_calls[0].name, "calculator")
        self.assertIn("126", run.answer)

    def test_division_tool(self):
        run = self.agent.run(self.cases["division"].query)
        self.assertIn("12", run.answer)

    def test_weather_abstains(self):
        run = self.agent.run(self.cases["live_weather_abstention"].query)
        self.assertEqual(run.status, "abstained")
        self.assertFalse(run.tool_calls)

    def test_private_data_abstains(self):
        run = self.agent.run(self.cases["unknown_private_data"].query)
        self.assertEqual(run.status, "abstained")
        self.assertIn("do not have access", run.answer.casefold())

    def test_cost_zero(self):
        run = self.agent.run(self.cases["mcp_spec"].query)
        self.assertEqual(run.cost_usd, 0.0)

    def test_tokens_positive(self):
        run = self.agent.run(self.cases["mcp_spec"].query)
        self.assertGreater(run.estimated_tokens, 0)

    def test_trace_present(self):
        run = self.agent.run(self.cases["mcp_spec"].query)
        self.assertTrue(run.trace)

    def test_query_length_bounded(self):
        with self.assertRaises(ValueError):
            self.agent.run("x" * 2001)

    def test_empty_query_rejected(self):
        with self.assertRaises(ValueError):
            self.agent.run("   ")

    def test_unknown_mode_rejected(self):
        with self.assertRaises(ValueError):
            DemoAgent("nope")


class BrokenCandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.agent = DemoAgent("broken")
        cls.cases = {case.id: case for case in load_cases()}

    def test_calculator_routing_broken(self):
        run = self.agent.run(self.cases["calculator"].query)
        self.assertEqual(run.tool_calls[0].name, "local_search")

    def test_search_citation_broken(self):
        run = self.agent.run(self.cases["mcp_spec"].query)
        self.assertEqual(run.citations, ("UNOBSERVED-SOURCE",))

    def test_broken_citation_not_observed(self):
        run = self.agent.run(self.cases["mcp_spec"].query)
        self.assertNotIn(
            run.citations[0],
            run.tool_calls[0].returned_source_ids,
        )


class EvaluatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = {case.id: case for case in load_cases()}

    def test_good_case_passes(self):
        case = self.cases["mcp_spec"]
        result = evaluate_case(case, DemoAgent("good").run(case.query))
        self.assertTrue(result.passed)
        self.assertEqual(result.score, 1.0)

    def test_broken_search_case_fails(self):
        case = self.cases["mcp_spec"]
        result = evaluate_case(case, DemoAgent("broken").run(case.query))
        self.assertFalse(result.passed)

    def test_broken_calculator_case_fails(self):
        case = self.cases["calculator"]
        result = evaluate_case(case, DemoAgent("broken").run(case.query))
        self.assertFalse(result.passed)

    def test_check_names_present(self):
        case = self.cases["mcp_spec"]
        result = evaluate_case(case, DemoAgent("good").run(case.query))
        names = {check.name for check in result.checks}
        self.assertEqual(
            names,
            {
                "task_completion", "tool_selection",
                "content_requirements", "citation_requirement",
                "groundedness", "step_budget",
                "trace_integrity", "unexpected_error",
            },
        )

    def test_forbidden_content_detected(self):
        case = replace(
            self.cases["mcp_spec"],
            must_not_include=("Model Context Protocol",),
        )
        result = evaluate_case(case, DemoAgent("good").run(case.query))
        content = next(
            check for check in result.checks
            if check.name == "content_requirements"
        )
        self.assertFalse(content.passed)

    def test_missing_required_content_detected(self):
        case = replace(
            self.cases["mcp_spec"],
            must_include=("never-present-phrase",),
        )
        result = evaluate_case(case, DemoAgent("good").run(case.query))
        content = next(
            check for check in result.checks
            if check.name == "content_requirements"
        )
        self.assertFalse(content.passed)

    def test_step_budget_detected(self):
        case = replace(self.cases["mcp_spec"], max_steps=1)
        result = evaluate_case(case, DemoAgent("good").run(case.query))
        check = next(c for c in result.checks if c.name == "step_budget")
        self.assertFalse(check.passed)

    def test_wrong_status_detected(self):
        case = replace(
            self.cases["mcp_spec"],
            expected_status="abstained",
        )
        result = evaluate_case(case, DemoAgent("good").run(case.query))
        check = next(
            c for c in result.checks if c.name == "task_completion"
        )
        self.assertFalse(check.passed)

    def test_no_citation_required_passes(self):
        case = self.cases["calculator"]
        result = evaluate_case(case, DemoAgent("good").run(case.query))
        check = next(
            c for c in result.checks
            if c.name == "citation_requirement"
        )
        self.assertTrue(check.passed)

    def test_groundedness_rejects_unobserved(self):
        case = self.cases["mcp_spec"]
        result = evaluate_case(case, DemoAgent("broken").run(case.query))
        check = next(c for c in result.checks if c.name == "groundedness")
        self.assertFalse(check.passed)


class MetricTests(unittest.TestCase):
    def test_good_suite_full_pass(self):
        report = run_suite("good", regression=False)
        self.assertEqual(report.metrics["case_pass_rate"], 1.0)

    def test_good_tool_accuracy_full(self):
        report = run_suite("good", regression=False)
        self.assertEqual(report.metrics["tool_selection_accuracy"], 1.0)

    def test_good_groundedness_full(self):
        report = run_suite("good", regression=False)
        self.assertEqual(report.metrics["groundedness_pass_rate"], 1.0)

    def test_good_trace_integrity_full(self):
        report = run_suite("good", regression=False)
        self.assertEqual(report.metrics["trace_integrity_pass_rate"], 1.0)

    def test_good_failure_rate_zero(self):
        report = run_suite("good", regression=False)
        self.assertEqual(report.metrics["failure_rate"], 0.0)

    def test_good_cost_zero(self):
        report = run_suite("good", regression=False)
        self.assertEqual(report.metrics["reported_cost_usd"], 0.0)

    def test_latency_nonnegative(self):
        report = run_suite("good", regression=False)
        self.assertGreaterEqual(report.metrics["average_latency_ms"], 0.0)

    def test_tokens_positive(self):
        report = run_suite("good", regression=False)
        self.assertGreater(report.metrics["estimated_tokens"], 0)

    def test_broken_suite_not_full_pass(self):
        report = run_suite("broken", regression=False)
        self.assertLess(report.metrics["case_pass_rate"], 1.0)

    def test_empty_aggregate_rejected(self):
        with self.assertRaises(ValueError):
            aggregate_metrics([])


class RegressionTests(unittest.TestCase):
    def test_baseline_loads(self):
        baseline = load_baseline()
        self.assertEqual(baseline["suite_version"], "1.0")

    def test_good_regression_passes(self):
        report = run_suite("good", regression=True)
        self.assertTrue(report.regression_passed)
        self.assertEqual(report.regression_failures, ())

    def test_broken_regression_fails(self):
        report = run_suite("broken", regression=True)
        self.assertFalse(report.regression_passed)
        self.assertTrue(report.regression_failures)

    def test_floor_failure(self):
        ok, failures = check_regression(
            {"score": 0.5},
            {"metric_floors": {"score": 0.9}, "metric_ceilings": {}},
        )
        self.assertFalse(ok)
        self.assertTrue(failures)

    def test_ceiling_failure(self):
        ok, failures = check_regression(
            {"failure_rate": 0.2},
            {
                "metric_floors": {},
                "metric_ceilings": {"failure_rate": 0.0},
            },
        )
        self.assertFalse(ok)
        self.assertTrue(failures)

    def test_missing_metric_failure(self):
        ok, failures = check_regression(
            {},
            {"metric_floors": {"score": 1.0}, "metric_ceilings": {}},
        )
        self.assertFalse(ok)
        self.assertIn("missing metric", failures[0])


class ReporterTests(unittest.TestCase):
    def test_markdown_contains_metrics(self):
        text = to_markdown(run_suite("good", regression=True))
        self.assertIn("## Metrics", text)
        self.assertIn("case_pass_rate", text)

    def test_markdown_contains_cases(self):
        text = to_markdown(run_suite("good", regression=True))
        self.assertIn("## Cases", text)
        self.assertIn("mcp_spec", text)

    def test_markdown_regression_pass(self):
        text = to_markdown(run_suite("good", regression=True))
        self.assertIn("baseline thresholds passed", text)

    def test_json_valid(self):
        payload = json.loads(to_json(run_suite("good", regression=True)))
        self.assertEqual(payload["candidate"], "good")

    def test_json_contains_case_results(self):
        payload = json.loads(to_json(run_suite("good", regression=True)))
        self.assertEqual(len(payload["case_results"]), 8)


class IntegrationTests(unittest.TestCase):
    def test_all_good_cases_pass_individually(self):
        agent = DemoAgent("good")
        for case in load_cases():
            with self.subTest(case=case.id):
                self.assertTrue(
                    evaluate_case(case, agent.run(case.query)).passed
                )

    def test_broken_candidate_detected_on_search_and_math(self):
        agent = DemoAgent("broken")
        cases = {c.id: c for c in load_cases()}
        self.assertFalse(
            evaluate_case(
                cases["mcp_spec"],
                agent.run(cases["mcp_spec"].query),
            ).passed
        )
        self.assertFalse(
            evaluate_case(
                cases["calculator"],
                agent.run(cases["calculator"].query),
            ).passed
        )

    def test_trace_ids_repeat_for_same_candidate_case(self):
        case = next(c for c in load_cases() if c.id == "mcp_spec")
        a = DemoAgent("good").run(case.query)
        b = DemoAgent("good").run(case.query)
        self.assertEqual(a.trace[0].trace_id, b.trace[0].trace_id)

    def test_candidate_modes_have_different_trace_ids(self):
        case = next(c for c in load_cases() if c.id == "mcp_spec")
        a = DemoAgent("good").run(case.query)
        b = DemoAgent("broken").run(case.query)
        self.assertNotEqual(a.trace[0].trace_id, b.trace[0].trace_id)


if __name__ == "__main__":
    unittest.main()
