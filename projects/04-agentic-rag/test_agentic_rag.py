"""Offline unit tests for Project 04: Agentic RAG."""

from __future__ import annotations

import unittest
from pathlib import Path

from agentic_rag import (
    AgenticRAG,
    evaluate_evidence,
    needs_retrieval,
    rewrite_query,
)
from chunking import build_chunks, chunk_document, load_documents
from models import Document
from vector_store import LocalVectorStore, tokenize


PROJECT_DIR = Path(__file__).parent
DOCUMENTS = load_documents(PROJECT_DIR / "data" / "knowledge_base.json")
CHUNKS = build_chunks(DOCUMENTS, chunk_size=70, overlap=15)
STORE = LocalVectorStore(CHUNKS)


class ChunkingTests(unittest.TestCase):
    def test_document_ids_are_unique(self):
        ids = [document.id for document in DOCUMENTS]
        self.assertEqual(len(ids), len(set(ids)))

    def test_chunking_creates_chunks(self):
        self.assertGreater(len(CHUNKS), len(DOCUMENTS) - 1)

    def test_overlap_validation(self):
        document = Document(
            id="x",
            title="X",
            source_url="https://example.com",
            tags=("test",),
            text=" ".join(["word"] * 40),
        )
        with self.assertRaises(ValueError):
            chunk_document(document, chunk_size=20, overlap=20)


class VectorStoreTests(unittest.TestCase):
    def test_tokenizer_removes_stopwords(self):
        tokens = tokenize("What is the difference between RAG and retrieval?")
        self.assertIn("rag", tokens)
        self.assertIn("retrieval", tokens)
        self.assertNotIn("the", tokens)

    def test_rag_search_returns_rag_documents(self):
        hits = STORE.search(
            "agentic rag retrieval query rewrite evidence",
            top_k=4,
        )
        ids = {hit.chunk.document_id for hit in hits}
        self.assertIn("agentic-rag", ids)

    def test_embedding_query_finds_vector_document(self):
        hits = STORE.search(
            "embeddings vectors cosine similarity semantic retrieval",
            top_k=4,
        )
        ids = {hit.chunk.document_id for hit in hits}
        self.assertIn("embeddings-vector-search", ids)

    def test_results_sorted_by_score(self):
        hits = STORE.search("tfidf vectors sparse retrieval", top_k=4)
        scores = [hit.score for hit in hits]
        self.assertEqual(scores, sorted(scores, reverse=True))


class RoutingTests(unittest.TestCase):
    def test_greeting_skips_retrieval(self):
        self.assertFalse(needs_retrieval("hello"))

    def test_knowledge_question_uses_retrieval(self):
        self.assertTrue(
            needs_retrieval(
                "What makes Agentic RAG different from normal RAG?"
            )
        )

    def test_query_rewrite_expands_rag(self):
        rewritten = rewrite_query("Explain Agentic RAG", 1)
        self.assertIn("retrieval augmented generation", rewritten.casefold())


class AgentLoopTests(unittest.TestCase):
    def test_known_question_gets_grounded_answer(self):
        agent = AgenticRAG(STORE, max_rounds=3, top_k=4)
        state, answer = agent.run(
            "What makes Agentic RAG different from a fixed RAG pipeline?"
        )
        self.assertTrue(state.sufficient)
        self.assertEqual(state.stop_reason, "evidence_sufficient")
        self.assertIn("## Grounded Answer", answer)
        self.assertIn("## Retrieved Sources", answer)
        self.assertIn("[C1]", answer)

    def test_direct_route_has_no_retrieval_rounds(self):
        agent = AgenticRAG(STORE, max_rounds=3, top_k=4)
        state, answer = agent.run("hello")
        self.assertFalse(state.retrieval_needed)
        self.assertEqual(state.round, 0)
        self.assertEqual(state.stop_reason, "retrieval_not_needed")
        self.assertIn("Hello", answer)

    def test_unknown_question_abstains(self):
        agent = AgenticRAG(STORE, max_rounds=2, top_k=3)
        state, answer = agent.run(
            "Explain medieval glassmaking recipes from fourteenth-century Venice."
        )
        self.assertFalse(state.sufficient)
        self.assertEqual(state.stop_reason, "max_rounds_reached")
        self.assertIn("not have enough evidence", answer)

    def test_loop_is_bounded(self):
        agent = AgenticRAG(STORE, max_rounds=2, top_k=1)
        state, _ = agent.run(
            "Explain an unrelated topic about deep-sea mollusk taxonomy."
        )
        self.assertLessEqual(state.round, 2)

    def test_retrieval_events_expose_metrics(self):
        agent = AgenticRAG(STORE, max_rounds=3, top_k=4)
        state, _ = agent.run(
            "How do query rewriting and evidence sufficiency work in Agentic RAG?"
        )
        retrieve_events = [
            event for event in state.events if event["action"] == "retrieve"
        ]
        self.assertTrue(retrieve_events)
        self.assertIn("top_score", retrieve_events[0]["metrics"])
        self.assertIn("query_coverage", retrieve_events[0]["metrics"])

    def test_hits_are_deduplicated(self):
        agent = AgenticRAG(STORE, max_rounds=3, top_k=4)
        state, _ = agent.run(
            "Explain embeddings, vector stores, and retrieval quality in RAG."
        )
        ids = [hit.chunk.id for hit in state.hits]
        self.assertEqual(len(ids), len(set(ids)))

    def test_evidence_evaluator_rejects_no_hits(self):
        sufficient, metrics = evaluate_evidence("rag retrieval", [])
        self.assertFalse(sufficient)
        self.assertEqual(metrics["reason"], "no_hits")


if __name__ == "__main__":
    unittest.main()
