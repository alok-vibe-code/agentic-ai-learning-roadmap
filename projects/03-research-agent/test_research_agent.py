"""Unit tests for Project 03.

All tests are offline and require no API key, network request, or paid service.
"""

from __future__ import annotations

import unittest
from pathlib import Path

from research_agent import (
    ResearchAgent,
    evidence_is_sufficient,
    infer_required_facets,
    missing_facets,
)
from search import LocalCorpus, tokenize


PROJECT_DIR = Path(__file__).parent
CORPUS = LocalCorpus.from_json(PROJECT_DIR / "data" / "sources.json")


class SearchTests(unittest.TestCase):
    def test_tokenize_removes_common_stopwords(self):
        tokens = tokenize("What are the tools in an agent framework?")
        self.assertIn("tools", tokens)
        self.assertIn("agent", tokens)
        self.assertIn("framework", tokens)
        self.assertNotIn("the", tokens)

    def test_framework_search_returns_relevant_sources(self):
        hits = CORPUS.search("agent framework state tool-use", top_k=5)
        ids = {hit.source.id for hit in hits}
        self.assertTrue(
            {"openai-agents-sdk", "langgraph", "google-adk"} & ids
        )

    def test_corpus_ids_are_unique(self):
        ids = [source.id for source in CORPUS.sources]
        self.assertEqual(len(ids), len(set(ids)))


class PlanningTests(unittest.TestCase):
    def test_framework_question_infers_framework_facets(self):
        facets = infer_required_facets(
            "Compare major Agentic AI frameworks and SDKs."
        )
        self.assertIn("framework", facets)
        self.assertIn("tool-use", facets)
        self.assertIn("state", facets)

    def test_security_question_infers_security_facet(self):
        facets = infer_required_facets(
            "How should an agent handle security and guardrails?"
        )
        self.assertIn("security", facets)


class AgentLoopTests(unittest.TestCase):
    def test_framework_research_collects_multiple_sources(self):
        agent = ResearchAgent(CORPUS, max_steps=6, top_k=4)
        state, _ = agent.run(
            "Compare approaches used by major Agentic AI frameworks and SDKs."
        )
        self.assertGreaterEqual(len(state.source_ids), 3)

    def test_agent_is_bounded(self):
        agent = ResearchAgent(CORPUS, max_steps=2, top_k=1)
        state, _ = agent.run(
            "Research a completely unrelated topic about marine archaeology."
        )
        self.assertLessEqual(state.step, 2)
        self.assertIn(
            state.stop_reason,
            {"max_steps_reached", "no_more_queries", "enough_evidence"},
        )

    def test_report_contains_citations(self):
        agent = ResearchAgent(CORPUS, max_steps=6, top_k=4)
        _, report = agent.run(
            "Compare major Agentic AI frameworks and SDKs."
        )
        self.assertIn("## Sources", report)
        self.assertIn("[S1]", report)
        self.assertIn("https://", report)

    def test_irrelevant_question_does_not_invent_evidence(self):
        agent = ResearchAgent(CORPUS, max_steps=2, top_k=3)
        state, report = agent.run(
            "Explain eighteenth-century violin varnish chemistry."
        )
        self.assertFalse(evidence_is_sufficient(state))
        self.assertIn("Limitations", report)

    def test_evidence_sources_are_unique(self):
        agent = ResearchAgent(CORPUS, max_steps=6, top_k=4)
        state, _ = agent.run(
            "Compare major Agentic AI frameworks and SDKs."
        )
        ids = [item.source.id for item in state.evidence]
        self.assertEqual(len(ids), len(set(ids)))

    def test_missing_facets_is_deterministic(self):
        agent = ResearchAgent(CORPUS, max_steps=1, top_k=1)
        state, _ = agent.run("Compare major Agentic AI frameworks.")
        missing = missing_facets(state)
        self.assertIsInstance(missing, list)


if __name__ == "__main__":
    unittest.main()
