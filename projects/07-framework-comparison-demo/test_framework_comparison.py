"""Offline tests for Project 07: Framework Comparison Demo."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from common_task import triage_request
from comparison import (
    STATUS_STRENGTH,
    capability_matrix,
    evaluate_framework,
    normalize_capability,
    recommend,
)
from models import CAPABILITY_KEYS
from profiles import DEFAULT_DATA_PATH, get_profile, load_profiles


PROJECT_DIR = Path(__file__).resolve().parent


class ProfileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.profiles = load_profiles()

    def test_three_profiles_are_bundled(self):
        self.assertEqual(len(self.profiles), 3)

    def test_framework_ids_are_expected(self):
        self.assertEqual(
            {profile.id for profile in self.profiles},
            {"openai-agents-sdk", "langgraph", "pydantic-ai"},
        )

    def test_framework_ids_are_unique(self):
        ids = [profile.id for profile in self.profiles]
        self.assertEqual(len(ids), len(set(ids)))

    def test_all_docs_urls_use_https(self):
        for profile in self.profiles:
            self.assertTrue(profile.docs_url.startswith("https://"))

    def test_all_profiles_have_verification_date(self):
        for profile in self.profiles:
            self.assertEqual(profile.verified_date, "2026-08-29")

    def test_all_capability_keys_present(self):
        for profile in self.profiles:
            self.assertEqual(
                set(profile.capabilities),
                set(CAPABILITY_KEYS),
            )

    def test_all_capability_values_are_known(self):
        for profile in self.profiles:
            for status in profile.capabilities.values():
                self.assertIn(status, STATUS_STRENGTH)

    def test_get_profile(self):
        profile = get_profile("langgraph", self.profiles)
        self.assertEqual(profile.name, "LangGraph")

    def test_unknown_profile_rejected(self):
        with self.assertRaises(KeyError):
            get_profile("does-not-exist", self.profiles)

    def test_framework_data_is_valid_json_list(self):
        payload = json.loads(DEFAULT_DATA_PATH.read_text(encoding="utf-8"))
        self.assertIsInstance(payload, list)
        self.assertTrue(payload)


class CommonTaskTests(unittest.TestCase):
    def test_billing_route(self):
        result = triage_request(
            "I was charged twice and need help with billing."
        )
        self.assertEqual(result.route, "billing")

    def test_technical_route(self):
        result = triage_request(
            "The API integration returns a timeout error."
        )
        self.assertEqual(result.route, "technical")

    def test_account_route(self):
        result = triage_request(
            "I cannot access my account."
        )
        self.assertEqual(result.route, "account")

    def test_general_fallback(self):
        result = triage_request(
            "Can you explain how this service works?"
        )
        self.assertEqual(result.route, "general")

    def test_tied_routes_fall_back_to_general(self):
        result = triage_request(
            "My account API access is broken."
        )
        self.assertEqual(result.route, "general")

    def test_refund_requires_human(self):
        result = triage_request(
            "I need a refund for the duplicate charge."
        )
        self.assertTrue(result.requires_human)
        self.assertEqual(result.risk, "high")

    def test_delete_requires_human(self):
        result = triage_request(
            "Please delete my account."
        )
        self.assertTrue(result.requires_human)

    def test_read_only_technical_request_is_low_risk(self):
        result = triage_request(
            "Explain this API timeout error."
        )
        self.assertFalse(result.requires_human)
        self.assertEqual(result.risk, "low")

    def test_blank_request_rejected(self):
        with self.assertRaises(ValueError):
            triage_request("   ")


class CapabilityNormalizationTests(unittest.TestCase):
    def test_hitl_alias(self):
        self.assertEqual(
            normalize_capability("hitl"),
            "human_approval",
        )

    def test_state_alias(self):
        self.assertEqual(
            normalize_capability("state"),
            "state_management",
        )

    def test_offline_alias(self):
        self.assertEqual(
            normalize_capability("offline"),
            "offline_testing",
        )

    def test_hyphenated_name(self):
        self.assertEqual(
            normalize_capability("provider-flexibility"),
            "provider_flexibility",
        )

    def test_unknown_capability_rejected(self):
        with self.assertRaises(ValueError):
            normalize_capability("magic")


class RecommendationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.profiles = load_profiles()

    def test_no_requirements_keeps_everyone_eligible(self):
        results = recommend(self.profiles)
        self.assertTrue(all(result.eligible for result in results))

    def test_offline_testing_hard_requirement_filters_provider_dependent(self):
        results = recommend(
            self.profiles,
            required=["offline_testing"],
        )
        by_id = {result.framework_id: result for result in results}
        self.assertFalse(by_id["openai-agents-sdk"].eligible)
        self.assertTrue(by_id["langgraph"].eligible)
        self.assertTrue(by_id["pydantic-ai"].eligible)

    def test_mcp_requirement_is_accepted_for_all_profiles(self):
        results = recommend(
            self.profiles,
            required=["mcp"],
        )
        self.assertTrue(all(result.eligible for result in results))

    def test_preference_score_is_deterministic(self):
        first = recommend(
            self.profiles,
            preferred=["provider_flexibility", "offline_testing"],
        )
        second = recommend(
            self.profiles,
            preferred=["provider_flexibility", "offline_testing"],
        )
        self.assertEqual(first, second)

    def test_duplicate_preference_does_not_double_count(self):
        profile = get_profile("langgraph", self.profiles)
        one = evaluate_framework(
            profile,
            preferred=["offline_testing"],
        )
        duplicate = evaluate_framework(
            profile,
            preferred=["offline_testing", "offline_testing"],
        )
        self.assertEqual(
            one.preference_score,
            duplicate.preference_score,
        )

    def test_missing_requirement_is_exposed(self):
        profile = get_profile("openai-agents-sdk", self.profiles)
        result = evaluate_framework(
            profile,
            required=["offline_testing"],
        )
        self.assertIn(
            "offline_testing",
            result.missing_requirements,
        )

    def test_eligible_frameworks_sort_before_ineligible(self):
        results = recommend(
            self.profiles,
            required=["offline_testing"],
        )
        eligible_flags = [result.eligible for result in results]
        self.assertEqual(eligible_flags, sorted(eligible_flags, reverse=True))


class MatrixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.profiles = load_profiles()

    def test_matrix_has_one_row_per_capability(self):
        matrix = capability_matrix(self.profiles)
        self.assertEqual(len(matrix), len(CAPABILITY_KEYS))

    def test_every_matrix_row_has_framework_values(self):
        matrix = capability_matrix(self.profiles)
        for row in matrix:
            self.assertEqual(len(row), 1 + len(self.profiles))

    def test_matrix_order_matches_capability_order(self):
        matrix = capability_matrix(self.profiles)
        self.assertEqual(
            [row[0] for row in matrix],
            list(CAPABILITY_KEYS),
        )


class ReferenceTests(unittest.TestCase):
    def test_reference_files_exist(self):
        for filename in (
            "openai_agents_sdk.md",
            "langgraph.md",
            "pydantic_ai.md",
        ):
            self.assertTrue(
                (PROJECT_DIR / "reference" / filename).exists()
            )

    def test_openai_reference_has_official_docs(self):
        text = (
            PROJECT_DIR / "reference" / "openai_agents_sdk.md"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "https://openai.github.io/openai-agents-python/",
            text,
        )

    def test_langgraph_reference_has_official_docs(self):
        text = (
            PROJECT_DIR / "reference" / "langgraph.md"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "https://docs.langchain.com/oss/python/langgraph/overview",
            text,
        )

    def test_pydantic_reference_has_testing_docs(self):
        text = (
            PROJECT_DIR / "reference" / "pydantic_ai.md"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "https://pydantic.dev/docs/ai/guides/testing/",
            text,
        )

    def test_every_profile_has_complete_task_mapping(self):
        expected = {"entry", "routing", "tools", "state", "approval", "result"}
        for profile in load_profiles():
            self.assertEqual(set(profile.task_mapping), expected)


if __name__ == "__main__":
    unittest.main()
