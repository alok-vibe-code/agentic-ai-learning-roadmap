"""Static validation of the MCP adapter without importing the MCP SDK."""

from __future__ import annotations

import ast
import unittest
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent
SERVER_FILE = PROJECT_DIR / "server.py"
SERVER_TEXT = SERVER_FILE.read_text(encoding="utf-8")
SERVER_AST = ast.parse(SERVER_TEXT)


def decorated_functions(decorator_name: str) -> set[str]:
    found: set[str] = set()

    for node in ast.walk(SERVER_AST):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue

        for decorator in node.decorator_list:
            call = decorator if isinstance(decorator, ast.Call) else None
            target = call.func if call else decorator

            if (
                isinstance(target, ast.Attribute)
                and isinstance(target.value, ast.Name)
                and target.value.id == "mcp"
                and target.attr == decorator_name
            ):
                found.add(node.name)

    return found


class MCPSourceTests(unittest.TestCase):
    def test_uses_current_v2_high_level_import(self):
        self.assertIn(
            "from mcp.server import MCPServer",
            SERVER_TEXT,
        )
        self.assertNotIn("FastMCP", SERVER_TEXT)

    def test_creates_mcp_server(self):
        self.assertIn("MCPServer(", SERVER_TEXT)

    def test_expected_tools_registered(self):
        self.assertEqual(
            decorated_functions("tool"),
            {
                "get_page_title",
                "get_meta_description",
                "extract_headings",
                "get_canonical",
                "extract_internal_links",
                "check_robots_meta",
                "audit_page",
            },
        )

    def test_expected_prompt_registered(self):
        self.assertEqual(
            decorated_functions("prompt"),
            {"seo_audit"},
        )

    def test_two_resources_registered(self):
        self.assertEqual(
            decorated_functions("resource"),
            {"on_page_guidelines", "security_boundaries"},
        )

    def test_resource_uris_present(self):
        self.assertIn('"seo://guidelines/on-page"', SERVER_TEXT)
        self.assertIn('"seo://security/boundaries"', SERVER_TEXT)

    def test_guarded_run_is_present(self):
        self.assertIn(
            'if __name__ == "__main__":',
            SERVER_TEXT,
        )
        self.assertIn("mcp.run()", SERVER_TEXT)

    def test_server_instructions_mark_html_untrusted(self):
        lowered = SERVER_TEXT.casefold()
        self.assertIn("untrusted content", lowered)
        self.assertIn("does not fetch urls", lowered)

    def test_no_requests_dependency(self):
        self.assertNotIn("import requests", SERVER_TEXT)
        self.assertNotIn("from requests", SERVER_TEXT)

    def test_no_urllib_network_fetch(self):
        self.assertNotIn("urllib.request", SERVER_TEXT)
        self.assertNotIn("urlopen", SERVER_TEXT)

    def test_no_shell_execution(self):
        lowered = SERVER_TEXT.casefold()
        self.assertNotIn("subprocess", lowered)
        self.assertNotIn("os.system", lowered)

    def test_requirements_targets_mcp_v2(self):
        requirements = (
            PROJECT_DIR / "requirements.txt"
        ).read_text(encoding="utf-8")
        self.assertIn("mcp[cli]>=2,<3", requirements)

    def test_security_doc_exists(self):
        self.assertTrue(
            (PROJECT_DIR / "docs" / "security.md").exists()
        )

    def test_guidelines_resource_exists(self):
        self.assertTrue(
            (
                PROJECT_DIR
                / "resources"
                / "on_page_guidelines.json"
            ).exists()
        )


if __name__ == "__main__":
    unittest.main()
