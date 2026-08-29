"""Offline tests for Project 05: Memory-Aware Assistant."""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from assistant import MemoryAwareAssistant, WorkingMemory
from policy import (
    MAX_VALUE_LENGTH,
    normalize_category,
    normalize_key,
    validate_memory_content,
)
from store import JSONMemoryStore, tokenize


UTC = timezone.utc
BASE_TIME = datetime(2026, 8, 29, 12, 0, tzinfo=UTC)


class PolicyTests(unittest.TestCase):
    def test_allowed_preference(self):
        decision = validate_memory_content(
            "preferred editor",
            "VS Code",
        )
        self.assertTrue(decision.allowed)

    def test_rejects_password(self):
        decision = validate_memory_content(
            "website password",
            "hunter2",
        )
        self.assertFalse(decision.allowed)

    def test_rejects_api_key_phrase(self):
        decision = validate_memory_content(
            "api key",
            "abc123",
        )
        self.assertFalse(decision.allowed)

    def test_rejects_secret_shape(self):
        decision = validate_memory_content(
            "service credential",
            "sk-abcdefghijklmnop1234",
        )
        self.assertFalse(decision.allowed)

    def test_rejects_financial_data(self):
        decision = validate_memory_content(
            "credit card",
            "4111 1111 1111 1111",
        )
        self.assertFalse(decision.allowed)

    def test_rejects_oversized_value(self):
        decision = validate_memory_content(
            "note",
            "x" * (MAX_VALUE_LENGTH + 1),
        )
        self.assertFalse(decision.allowed)

    def test_category_allowlist(self):
        self.assertEqual(normalize_category("Preference"), "preference")
        with self.assertRaises(ValueError):
            normalize_category("credential")

    def test_key_normalization(self):
        self.assertEqual(
            normalize_key("  Preferred   Editor "),
            "preferred editor",
        )


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.path = Path(self.tempdir.name) / "memory.json"
        self.store = JSONMemoryStore(self.path)

    def tearDown(self):
        self.tempdir.cleanup()

    def test_store_starts_empty(self):
        self.assertEqual(self.store.list_records(), [])

    def test_create_and_get_memory(self):
        record, created = self.store.upsert(
            "preference",
            "editor",
            "VS Code",
            now=BASE_TIME,
        )
        self.assertTrue(created)
        loaded = self.store.get(
            "preference",
            "editor",
            now=BASE_TIME,
        )
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.value, "VS Code")
        self.assertEqual(loaded.id, record.id)

    def test_upsert_updates_without_duplicate(self):
        first, created = self.store.upsert(
            "preference", "editor", "VS Code", now=BASE_TIME
        )
        second, created_again = self.store.upsert(
            "preference", "editor", "Zed", now=BASE_TIME + timedelta(minutes=1)
        )
        self.assertTrue(created)
        self.assertFalse(created_again)
        self.assertEqual(first.id, second.id)
        self.assertEqual(len(self.store.list_records()), 1)
        self.assertEqual(self.store.list_records()[0].value, "Zed")

    def test_expired_memory_not_returned(self):
        self.store.upsert(
            "episode",
            "temporary task",
            "Review Project 05",
            ttl_seconds=60,
            now=BASE_TIME,
        )
        later = BASE_TIME + timedelta(seconds=61)
        self.assertEqual(self.store.list_records(now=later), [])
        self.assertIsNone(
            self.store.get(
                "episode",
                "temporary task",
                now=later,
            )
        )

    def test_purge_expired_removes_record_from_file(self):
        self.store.upsert(
            "episode",
            "temporary task",
            "Review Project 05",
            ttl_seconds=10,
            now=BASE_TIME,
        )
        removed = self.store.purge_expired(
            now=BASE_TIME + timedelta(seconds=11)
        )
        self.assertEqual(removed, 1)
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(payload, [])

    def test_search_retrieves_relevant_memory(self):
        self.store.upsert(
            "preference",
            "preferred editor",
            "VS Code",
            now=BASE_TIME,
        )
        self.store.upsert(
            "workflow",
            "test command",
            "python -m unittest",
            now=BASE_TIME,
        )
        matches = self.store.search(
            "Which editor do I prefer?",
            now=BASE_TIME,
        )
        self.assertTrue(matches)
        self.assertEqual(matches[0].record.key, "preferred editor")

    def test_delete_removes_specific_memory(self):
        self.store.upsert(
            "project",
            "current project",
            "Memory assistant",
            now=BASE_TIME,
        )
        self.assertTrue(
            self.store.delete("project", "current project")
        )
        self.assertFalse(
            self.store.delete("project", "current project")
        )

    def test_clear_removes_all_records(self):
        self.store.upsert(
            "preference", "editor", "VS Code", now=BASE_TIME
        )
        self.store.upsert(
            "workflow", "tests", "python unittest", now=BASE_TIME
        )
        count = self.store.clear()
        self.assertEqual(count, 2)
        self.assertEqual(self.store.list_records(), [])

    def test_corrupted_store_is_not_silently_overwritten(self):
        self.path.write_text("{broken json", encoding="utf-8")
        with self.assertRaises(ValueError):
            self.store.list_records()
        self.assertEqual(
            self.path.read_text(encoding="utf-8"),
            "{broken json",
        )

    def test_sensitive_value_cannot_be_persisted(self):
        with self.assertRaises(ValueError):
            self.store.upsert(
                "preference",
                "api key",
                "abc123",
                now=BASE_TIME,
            )
        self.assertFalse(self.path.exists())

    def test_tokenizer_is_deterministic(self):
        tokens = tokenize("What is my preferred Python editor?")
        self.assertIn("preferred", tokens)
        self.assertIn("python", tokens)
        self.assertIn("editor", tokens)
        self.assertNotIn("my", tokens)


class AssistantTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.store = JSONMemoryStore(
            Path(self.tempdir.name) / "memory.json"
        )
        self.assistant = MemoryAwareAssistant(self.store)

    def tearDown(self):
        self.tempdir.cleanup()

    def test_working_memory_is_ephemeral_object_state(self):
        self.assistant.working.set("task", "Write tests")
        self.assertEqual(
            self.assistant.working.get("task"),
            "Write tests",
        )
        fresh = WorkingMemory()
        self.assertIsNone(fresh.get("task"))

    def test_remember_requires_explicit_method_call(self):
        self.assertEqual(self.store.list_records(), [])
        self.assistant.working.set(
            "conversation fact",
            "temporary",
        )
        self.assertEqual(self.store.list_records(), [])

    def test_assistant_remember_and_recall(self):
        message = self.assistant.remember(
            "preference",
            "python style",
            "Prefer type hints",
            now=BASE_TIME,
        )
        self.assertIn("Saved memory", message)
        matches = self.assistant.recall(
            "Python preference type hints",
            now=BASE_TIME,
        )
        self.assertTrue(matches)
        self.assertEqual(
            matches[0].record.value,
            "Prefer type hints",
        )

    def test_assistant_forget(self):
        self.assistant.remember(
            "project",
            "active project",
            "Memory-Aware Assistant",
            now=BASE_TIME,
        )
        self.assertEqual(
            self.assistant.forget(
                "project",
                "active project",
            ),
            "Memory deleted.",
        )

    def test_assistant_clear(self):
        self.assistant.remember(
            "preference", "editor", "VS Code", now=BASE_TIME
        )
        message = self.assistant.clear_persistent_memory()
        self.assertIn("Cleared 1", message)


if __name__ == "__main__":
    unittest.main()
