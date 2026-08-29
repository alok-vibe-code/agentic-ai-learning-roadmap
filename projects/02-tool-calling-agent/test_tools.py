"""Unit tests for the deterministic local tools.

These tests do not call the OpenAI API and do not require an API key.
"""

import unittest

from tools import analyze_text, analyze_url, calculate_expression


class CalculatorTests(unittest.TestCase):
    def test_arithmetic(self):
        self.assertEqual(calculate_expression("(17 / 100) * 895")["result"], 152.15)

    def test_rejects_code_execution(self):
        with self.assertRaises(ValueError):
            calculate_expression("__import__('os').system('echo unsafe')")

    def test_rejects_large_exponent(self):
        with self.assertRaises(ValueError):
            calculate_expression("2 ** 100")


class UrlAnalyzerTests(unittest.TestCase):
    def test_parses_url(self):
        result = analyze_url("https://example.com/blog/post?ref=linkedin&x=1#section")
        self.assertEqual(result["hostname"], "example.com")
        self.assertEqual(result["path"], "/blog/post")
        self.assertEqual(result["query_parameter_count"], 2)
        self.assertTrue(result["has_fragment"])

    def test_rejects_non_http_scheme(self):
        with self.assertRaises(ValueError):
            analyze_url("file:///etc/passwd")


class TextAnalyzerTests(unittest.TestCase):
    def test_counts_text(self):
        result = analyze_text("Agents use tools. Tools need boundaries.")
        self.assertEqual(result["sentence_count"], 2)
        self.assertEqual(result["word_count"], 6)


if __name__ == "__main__":
    unittest.main()
