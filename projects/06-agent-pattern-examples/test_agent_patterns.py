"""Offline unit tests for Project 06: Agent Pattern Examples."""

from __future__ import annotations

import time
import unittest

from models import PlanStep
from patterns.evaluator_optimizer import (
    evaluate_summary,
    run_evaluator_optimizer,
)
from patterns.human_in_loop import (
    classify_risk,
    request_action,
    simulate_execution,
)
from patterns.parallelization import run_parallel
from patterns.planning import build_plan, validate_plan
from patterns.reflection import critique_text, run_reflection
from patterns.routing import route_request, run_specialist


class ReflectionTests(unittest.TestCase):
    def test_empty_draft_scores_zero(self):
        critique = critique_text("")
        self.assertEqual(critique.score, 0)
        self.assertIn("empty", critique.issues)

    def test_good_draft_passes(self):
        critique = critique_text(
            "An agentic workflow helps teams because explicit checks make "
            "the control flow easier to inspect and test."
        )
        self.assertTrue(critique.passed)

    def test_short_draft_is_revised(self):
        result, trace = run_reflection("Agents help", max_rounds=3)
        self.assertNotEqual(result, "Agents help")
        self.assertTrue(result.endswith("."))
        self.assertEqual(trace.stop_reason, "quality_threshold_met")

    def test_reflection_is_bounded(self):
        _, trace = run_reflection("x", max_rounds=1)
        revision_events = [
            event for event in trace.events
            if event.action == "revise"
        ]
        self.assertLessEqual(len(revision_events), 1)

    def test_invalid_reflection_rounds_rejected(self):
        with self.assertRaises(ValueError):
            run_reflection("draft", max_rounds=0)


class PlanningTests(unittest.TestCase):
    def test_build_goal_creates_implementation_plan(self):
        steps, trace = build_plan("Build a small agent")
        self.assertGreaterEqual(len(steps), 4)
        self.assertIn("testable implementation", steps[1].title.casefold())
        self.assertEqual(trace.stop_reason, "valid_plan_created")

    def test_research_goal_creates_evidence_plan(self):
        steps, _ = build_plan("Research agent frameworks")
        titles = " ".join(step.title for step in steps).casefold()
        self.assertIn("evidence", titles)
        self.assertIn("compare", titles)

    def test_blank_goal_rejected(self):
        with self.assertRaises(ValueError):
            build_plan("   ")

    def test_duplicate_ids_rejected(self):
        with self.assertRaises(ValueError):
            validate_plan([
                PlanStep("P1", "A"),
                PlanStep("P1", "B"),
            ])

    def test_unknown_dependency_rejected(self):
        with self.assertRaises(ValueError):
            validate_plan([
                PlanStep("P1", "A", ("P9",)),
            ])

    def test_dependency_cycle_rejected(self):
        with self.assertRaises(ValueError):
            validate_plan([
                PlanStep("P1", "A", ("P2",)),
                PlanStep("P2", "B", ("P1",)),
            ])


class RoutingTests(unittest.TestCase):
    def test_calculator_route(self):
        decision, _ = route_request("Calculate 12 * 7")
        self.assertEqual(decision.route, "calculator")

    def test_research_route(self):
        decision, _ = route_request(
            "Research and compare agentic RAG frameworks"
        )
        self.assertEqual(decision.route, "research")

    def test_general_fallback(self):
        decision, _ = route_request("Please help with this task")
        self.assertEqual(decision.route, "general")

    def test_blank_request_rejected(self):
        with self.assertRaises(ValueError):
            route_request(" ")

    def test_calculator_specialist(self):
        result = run_specialist("calculator", "12 * 7")
        self.assertEqual(result, "Calculator result: 84")

    def test_calculator_blocks_unsupported_expression(self):
        result = run_specialist(
            "calculator",
            "__import__('os').system('id')",
        )
        self.assertIn(
            "no arithmetic expression was found",
            result.casefold(),
        )


class EvaluatorOptimizerTests(unittest.TestCase):
    def test_empty_candidate_scores_zero(self):
        evaluation = evaluate_summary("")
        self.assertEqual(evaluation.score, 0)

    def test_good_candidate_passes(self):
        candidate = (
            "An agentic workflow improves reliability by making control flow, "
            "stopping conditions, and quality checks explicit."
        )
        self.assertTrue(evaluate_summary(candidate).passed)

    def test_weak_candidate_improves(self):
        result, evaluation, trace = run_evaluator_optimizer(
            "Useful automation",
            max_rounds=4,
        )
        self.assertGreaterEqual(evaluation.score, 85)
        self.assertIn("agentic", result.casefold())
        self.assertEqual(trace.stop_reason, "quality_threshold_met")

    def test_optimizer_is_bounded(self):
        _, _, trace = run_evaluator_optimizer("x", max_rounds=1)
        optimize_events = [
            event for event in trace.events
            if event.action == "optimize"
        ]
        self.assertLessEqual(len(optimize_events), 1)

    def test_invalid_optimizer_rounds_rejected(self):
        with self.assertRaises(ValueError):
            run_evaluator_optimizer("candidate", max_rounds=0)


class ParallelizationTests(unittest.TestCase):
    def test_parallel_results_preserve_input_order(self):
        results, trace = run_parallel(["alpha", "beta", "gamma"])
        self.assertEqual(
            [result.task for result in results],
            ["alpha", "beta", "gamma"],
        )
        self.assertEqual(trace.stop_reason, "all_tasks_settled")

    def test_parallel_success_values(self):
        results, _ = run_parallel(["alpha", "beta"])
        self.assertEqual(
            [result.value for result in results],
            ["ALPHA", "BETA"],
        )

    def test_parallel_failure_is_isolated(self):
        results, _ = run_parallel(["alpha", "fail:broken", "gamma"])
        self.assertEqual(results[0].status, "ok")
        self.assertEqual(results[1].status, "error")
        self.assertIn("RuntimeError", results[1].error)
        self.assertEqual(results[2].status, "ok")

    def test_empty_parallel_tasks_rejected(self):
        with self.assertRaises(ValueError):
            run_parallel([])

    def test_invalid_worker_count_rejected(self):
        with self.assertRaises(ValueError):
            run_parallel(["x"], max_workers=0)


class HumanInLoopTests(unittest.TestCase):
    def test_read_action_is_low_risk(self):
        risk, _ = classify_risk("read the report")
        self.assertEqual(risk, "low")

    def test_publish_action_is_high_risk(self):
        risk, _ = classify_risk("publish the report")
        self.assertEqual(risk, "high")

    def test_ambiguous_action_is_medium_risk(self):
        risk, _ = classify_risk("organize the project")
        self.assertEqual(risk, "medium")

    def test_low_risk_auto_approved(self):
        decision, trace = request_action("read the report")
        self.assertTrue(decision.approved)
        self.assertEqual(trace.stop_reason, "auto_approved_low_risk")

    def test_high_risk_blocked_without_approval(self):
        decision, trace = request_action("publish the report")
        self.assertFalse(decision.approved)
        self.assertEqual(trace.stop_reason, "waiting_for_human_approval")
        self.assertTrue(simulate_execution(decision).startswith("BLOCKED"))

    def test_high_risk_allowed_with_explicit_approval(self):
        decision, trace = request_action(
            "publish the report",
            approved=True,
        )
        self.assertTrue(decision.approved)
        self.assertEqual(trace.stop_reason, "human_approved")
        self.assertTrue(
            simulate_execution(decision).startswith("SIMULATED ONLY")
        )

    def test_blank_action_rejected(self):
        with self.assertRaises(ValueError):
            classify_risk(" ")


if __name__ == "__main__":
    unittest.main()
