"""Offline tests for Project 09."""

from __future__ import annotations
import unittest
from dataclasses import replace

from agents.fact_checker import FactCheckerAgent
from agents.planner import (
    MAX_TASKS,
    PlannerAgent,
    complexity_score,
    normalize_question,
)
from agents.researcher import ResearcherAgent
from agents.reviewer import ReviewerAgent
from agents.writer import WriterAgent
from comparison import compare_architectures
from coordinator import MultiAgentResearchTeam
from models import Claim, Evidence, ResearchPlan, ResearchTask
from search import (
    best_snippet,
    load_sources,
    score_source,
    search_sources,
    sentence_split,
    tokenize,
)
from single_agent import SingleAgentResearcher


COMPLEX = (
    "Compare single-agent and multi-agent research systems for reliability, "
    "coordination overhead, and failure handling."
)


class CorpusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = load_sources()

    def test_source_count(self):
        self.assertEqual(len(self.sources), 10)

    def test_unique_ids(self):
        ids = [s.id for s in self.sources]
        self.assertEqual(len(ids), len(set(ids)))

    def test_local_urls(self):
        self.assertTrue(all(s.url.startswith("local://") for s in self.sources))

    def test_content_nonempty(self):
        self.assertTrue(all(s.content for s in self.sources))

    def test_tags_lowercase(self):
        for s in self.sources:
            self.assertEqual(list(s.tags), [t.casefold() for t in s.tags])


class SearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = load_sources()

    def test_stopwords_removed(self):
        tokens = tokenize("What is the cost of agent coordination?")
        self.assertNotIn("the", tokens)
        self.assertIn("cost", tokens)

    def test_sentence_split(self):
        self.assertEqual(
            sentence_split("One. Two! Three?"),
            ["One.", "Two!", "Three?"],
        )

    def test_positive_match(self):
        source = next(s for s in self.sources if s.id == "S7")
        self.assertGreater(score_source("coordination cost", source), 0)

    def test_ranked_scores(self):
        results = search_sources(
            "coordination overhead complexity",
            top_k=3,
            sources=self.sources,
        )
        scores = [score for _, score, _ in results]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_deterministic_search(self):
        first = search_sources(COMPLEX, top_k=4, sources=self.sources)
        second = search_sources(COMPLEX, top_k=4, sources=self.sources)
        self.assertEqual(first, second)

    def test_top_k_validation(self):
        with self.assertRaises(ValueError):
            search_sources("coordination", top_k=0, sources=self.sources)

    def test_snippet_provenance(self):
        source = next(s for s in self.sources if s.id == "S3")
        snippet = best_snippet("failure handling", source)
        self.assertIn(snippet, source.content)

    def test_zero_score_removed(self):
        self.assertEqual(
            search_sources(
                "zzzz-nonexistent-term",
                top_k=3,
                sources=self.sources,
            ),
            [],
        )


class PlannerTests(unittest.TestCase):
    def setUp(self):
        self.planner = PlannerAgent()

    def test_whitespace_normalization(self):
        self.assertEqual(
            normalize_question("  hello   world "),
            "hello world",
        )

    def test_empty_rejected(self):
        with self.assertRaises(ValueError):
            normalize_question("   ")

    def test_non_string_rejected(self):
        with self.assertRaises(TypeError):
            normalize_question(None)  # type: ignore[arg-type]

    def test_length_bounded(self):
        with self.assertRaises(ValueError):
            normalize_question("x" * 1501)

    def test_tasks_bounded(self):
        plan = self.planner.plan(COMPLEX)
        self.assertLessEqual(len(plan.tasks), MAX_TASKS)

    def test_task_ids_unique(self):
        plan = self.planner.plan(COMPLEX)
        ids = [t.id for t in plan.tasks]
        self.assertEqual(len(ids), len(set(ids)))

    def test_complex_question_multiple_facets(self):
        self.assertGreaterEqual(
            len(self.planner.plan(COMPLEX).tasks),
            3,
        )

    def test_simple_question_small_plan(self):
        self.assertLessEqual(
            len(self.planner.plan("What is agent handoff?").tasks),
            2,
        )

    def test_complexity_comparison(self):
        self.assertGreater(
            complexity_score(COMPLEX),
            complexity_score("What is agent handoff?"),
        )

    def test_queries_include_question(self):
        plan = self.planner.plan(COMPLEX)
        self.assertTrue(
            all(plan.question in task.query for task in plan.tasks)
        )


class ResearcherTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = load_sources()

    def test_provenance(self):
        task = ResearchTask(
            "T1",
            "coordination",
            "multi-agent coordination shared state",
        )
        results = ResearcherAgent("1").research(
            task,
            sources=self.sources,
            top_k=2,
        )
        self.assertTrue(results)
        for item in results:
            self.assertEqual(item.task_id, "T1")
            self.assertEqual(item.researcher, "researcher:1")
            self.assertTrue(item.source_id)

    def test_top_k_respected(self):
        task = ResearchTask(
            "T1",
            "failure",
            "multi-agent failure reliability",
        )
        self.assertLessEqual(
            len(
                ResearcherAgent("1").research(
                    task,
                    sources=self.sources,
                    top_k=1,
                )
            ),
            1,
        )

    def test_failure_hook(self):
        task = ResearchTask("T1", "failure", "[fail-research]")
        with self.assertRaises(RuntimeError):
            ResearcherAgent("1").research(
                task,
                sources=self.sources,
            )


class FactCheckerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = load_sources()
        cls.source = cls.sources[0]

    def _evidence(self, snippet, source_id=None):
        return Evidence(
            source_id=source_id or self.source.id,
            source_title=self.source.title,
            source_url=self.source.url,
            task_id="T1",
            facet="roles",
            researcher="researcher:1",
            snippet=snippet,
            score=5.0,
        )

    def test_exact_snippet_verified(self):
        snippet = sentence_split(self.source.content)[0]
        claim = FactCheckerAgent().verify(
            [self._evidence(snippet)],
            sources=self.sources,
        )[0]
        self.assertTrue(claim.verified)

    def test_modified_snippet_rejected(self):
        claim = FactCheckerAgent().verify(
            [self._evidence("Not in source.")],
            sources=self.sources,
        )[0]
        self.assertFalse(claim.verified)

    def test_missing_source_rejected(self):
        claim = FactCheckerAgent().verify(
            [self._evidence("No source.", source_id="MISSING")],
            sources=self.sources,
        )[0]
        self.assertFalse(claim.verified)

    def test_claim_ids_sequential(self):
        snippets = sentence_split(self.source.content)[:2]
        claims = FactCheckerAgent().verify(
            [self._evidence(s) for s in snippets],
            sources=self.sources,
        )
        self.assertEqual([c.id for c in claims], ["C1", "C2"])


class WriterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = load_sources()

    def make_data(self):
        plan = PlannerAgent().plan(COMPLEX)
        evidence = []
        for i, task in enumerate(plan.tasks, start=1):
            evidence.extend(
                ResearcherAgent(str(i)).research(
                    task,
                    sources=self.sources,
                    top_k=1,
                )
            )
        claims = FactCheckerAgent().verify(
            evidence,
            sources=self.sources,
        )
        return plan, claims

    def test_sources_section(self):
        plan, claims = self.make_data()
        report = WriterAgent().write(
            plan.question,
            plan,
            claims,
            sources=self.sources,
        )
        self.assertIn("## Sources", report)

    def test_citations(self):
        plan, claims = self.make_data()
        report = WriterAgent().write(
            plan.question,
            plan,
            claims,
            sources=self.sources,
        )
        verified = next(c for c in claims if c.verified)
        self.assertIn(f"[{verified.source_id}]", report)

    def test_unverified_excluded(self):
        plan, claims = self.make_data()
        bad = replace(
            claims[0],
            text="UNVERIFIED SHOULD NOT APPEAR",
            verified=False,
        )
        report = WriterAgent().write(
            plan.question,
            plan,
            [bad] + claims[1:],
            sources=self.sources,
        )
        self.assertNotIn("UNVERIFIED SHOULD NOT APPEAR", report)


class ReviewerTests(unittest.TestCase):
    def setUp(self):
        self.plan = ResearchPlan(
            question="Question",
            tasks=(
                ResearchTask("T1", "architecture", "one"),
                ResearchTask("T2", "risks", "two"),
            ),
            complexity_score=4,
            rationale="test",
        )
        self.claims = [
            Claim(
                "C1", "Claim one.", "S1", "local://one",
                "T1", "architecture", True, "verified",
            ),
            Claim(
                "C2", "Claim two.", "S2", "local://two",
                "T2", "risks", True, "verified",
            ),
        ]

    def test_complete_approved(self):
        report = (
            "# Report\nClaim one. [S1]\nClaim two. [S2]\n"
            "## Sources\n- [S1]\n- [S2]\n"
        )
        self.assertTrue(
            ReviewerAgent().review(
                self.plan,
                self.claims,
                report,
                failures=[],
            ).approved
        )

    def test_missing_coverage_rejected(self):
        report = "# Report\nClaim one. [S1]\n## Sources\n"
        result = ReviewerAgent().review(
            self.plan,
            self.claims[:1],
            report,
            failures=[],
        )
        self.assertFalse(result.approved)

    def test_missing_citation_rejected(self):
        report = "# Report\nClaim one.\nClaim two. [S2]\n## Sources\n"
        result = ReviewerAgent().review(
            self.plan,
            self.claims,
            report,
            failures=[],
        )
        self.assertFalse(result.approved)

    def test_critical_failure_rejected(self):
        report = "# Report\nClaim one. [S1]\nClaim two. [S2]\n## Sources\n"
        result = ReviewerAgent().review(
            self.plan,
            self.claims,
            report,
            failures=["critical:fact_checker:RuntimeError:test"],
        )
        self.assertFalse(result.approved)


class CoordinatorTests(unittest.TestCase):
    def test_team_approved(self):
        self.assertEqual(
            MultiAgentResearchTeam().run(COMPLEX).status,
            "approved",
        )

    def test_roles_metric(self):
        self.assertEqual(
            MultiAgentResearchTeam().run(COMPLEX).metrics["roles_used"],
            5,
        )

    def test_messages_recorded(self):
        result = MultiAgentResearchTeam().run(COMPLEX)
        self.assertGreater(result.metrics["coordination_messages"], 0)
        self.assertTrue(result.trace)

    def test_full_coverage(self):
        self.assertEqual(
            MultiAgentResearchTeam().run(COMPLEX).metrics["coverage_ratio"],
            1.0,
        )

    def test_verified_claims(self):
        self.assertGreater(
            MultiAgentResearchTeam().run(COMPLEX).metrics["verified_claims"],
            0,
        )

    def test_report_citations(self):
        self.assertRegex(
            MultiAgentResearchTeam().run(COMPLEX).report,
            r"\[S\d+\]",
        )

    def test_deterministic_report_and_trace(self):
        first = MultiAgentResearchTeam().run(COMPLEX)
        second = MultiAgentResearchTeam().run(COMPLEX)
        self.assertEqual(first.report, second.report)
        self.assertEqual(first.metrics, second.metrics)
        self.assertEqual(first.trace, second.trace)

    def test_worker_limit_low(self):
        with self.assertRaises(ValueError):
            MultiAgentResearchTeam().run(COMPLEX, max_workers=0)

    def test_worker_limit_high(self):
        with self.assertRaises(ValueError):
            MultiAgentResearchTeam().run(COMPLEX, max_workers=5)

    def test_one_worker(self):
        self.assertEqual(
            MultiAgentResearchTeam().run(
                COMPLEX,
                max_workers=1,
            ).status,
            "approved",
        )

    def test_delegate_and_result_trace(self):
        kinds = {
            m.kind
            for m in MultiAgentResearchTeam().run(COMPLEX).trace
        }
        self.assertIn("delegate", kinds)
        self.assertIn("result", kinds)


class SingleTests(unittest.TestCase):
    def test_completed(self):
        self.assertEqual(
            SingleAgentResearcher().run(COMPLEX).status,
            "completed",
        )

    def test_one_role(self):
        self.assertEqual(
            SingleAgentResearcher().run(COMPLEX).metrics["roles_used"],
            1,
        )

    def test_no_messages(self):
        result = SingleAgentResearcher().run(COMPLEX)
        self.assertEqual(result.metrics["coordination_messages"], 0)
        self.assertEqual(result.trace, ())

    def test_empty_rejected(self):
        with self.assertRaises(ValueError):
            SingleAgentResearcher().run("  ")

    def test_long_rejected(self):
        with self.assertRaises(ValueError):
            SingleAgentResearcher().run("x" * 1501)


class ComparisonTests(unittest.TestCase):
    def test_both_modes(self):
        result = compare_architectures(COMPLEX)
        self.assertIn("multi_agent", result)
        self.assertIn("single_agent", result)

    def test_overhead_visible(self):
        result = compare_architectures(COMPLEX)
        self.assertGreater(
            result["coordination_overhead"]["additional_roles"],
            0,
        )
        self.assertGreater(
            result["coordination_overhead"]["additional_messages"],
            0,
        )

    def test_complex_can_justify_team(self):
        self.assertIn(
            "may be justified",
            compare_architectures(COMPLEX)["recommendation"],
        )

    def test_simple_prefers_single(self):
        self.assertIn(
            "Prefer the simpler single-agent baseline",
            compare_architectures(
                "What is agent handoff?"
            )["recommendation"],
        )

    def test_non_universal_note(self):
        self.assertIn(
            "universally",
            compare_architectures(COMPLEX)["note"],
        )


class SafetyTests(unittest.TestCase):
    def test_shell_text_is_inert(self):
        q = "Compare agents; rm -rf / and explain coordination."
        self.assertIn(
            "rm -rf /",
            SingleAgentResearcher().run(q).question,
        )

    def test_python_text_is_inert(self):
        q = "__import__('os').system('id') multi-agent coordination"
        self.assertEqual(
            MultiAgentResearchTeam().run(q).status,
            "approved",
        )

    def test_no_http_sources(self):
        for source in load_sources():
            self.assertFalse(source.url.startswith(("http://", "https://")))


if __name__ == "__main__":
    unittest.main()
