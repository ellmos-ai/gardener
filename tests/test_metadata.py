# -*- coding: utf-8 -*-
"""
Metadata and Discoverability Parity Tests for Gardener OS.
Asserts that pyproject.toml, README.md, README_de.md, and llms.txt remain in sync.
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class TestMetadataParity(unittest.TestCase):
    def setUp(self):
        self.pyproject_path = ROOT / "pyproject.toml"
        self.readme_en_path = ROOT / "README.md"
        self.readme_de_path = ROOT / "README_de.md"
        self.llms_txt_path = ROOT / "llms.txt"
        self.changelog_path = ROOT / "CHANGELOG.md"

        self.pyproject = self.pyproject_path.read_text(encoding="utf-8")
        self.readme_en = self.readme_en_path.read_text(encoding="utf-8")
        self.readme_de = self.readme_de_path.read_text(encoding="utf-8")
        self.llms_txt = self.llms_txt_path.read_text(encoding="utf-8")
        self.changelog = self.changelog_path.read_text(encoding="utf-8")

    def test_pyproject_version_matches(self):
        match = re.search(r'version\s*=\s*"([^"]+)"', self.pyproject)
        self.assertIsNotNone(match, "pyproject.toml missing version")
        version = match.group(1)
        self.assertEqual(version, "0.4.0")

        # Check READMEs reference version
        self.assertIn(f"v{version}", self.readme_en)
        self.assertIn(f"v{version}", self.readme_de)

    def test_readme_badges_and_test_count(self):
        # Assert test badges show 110 passed
        self.assertIn("tests-110%20passed-brightgreen.svg", self.readme_en)
        self.assertIn("tests-110%20passed-brightgreen.svg", self.readme_de)

        # Assert umbrella and ecosystem badges
        self.assertIn("ecosystem-ellmos--ai-informational.svg", self.readme_en)
        self.assertIn("umbrella-open--bricks-blue.svg", self.readme_en)
        self.assertIn("LLM--Ready-llms.txt-orange.svg", self.readme_en)

        self.assertIn("ecosystem-ellmos--ai-informational.svg", self.readme_de)
        self.assertIn("umbrella-open--bricks-blue.svg", self.readme_de)
        self.assertIn("LLM--Ready-llms.txt-orange.svg", self.readme_de)

    def test_llms_txt_consistency(self):
        self.assertIn("Last-checked: 2026-08-16", self.llms_txt)
        self.assertIn("110 passing tests", self.llms_txt)
        self.assertIn("https://github.com/ellmos-ai/gardener", self.llms_txt)
        self.assertIn("ellmos-ai/gardener", self.llms_txt)

    def test_mermaid_architecture_in_readmes(self):
        self.assertIn("```mermaid", self.readme_en)
        self.assertIn("```mermaid", self.readme_de)
        self.assertIn("everything", self.readme_en)
        self.assertIn("everything", self.readme_de)

    def test_sibling_tools_matrix(self):
        for doc in (self.readme_en, self.readme_de):
            self.assertIn("ellmos-core", doc)
            self.assertIn("clutch", doc)
            self.assertIn("ellmos-controlcenter-mcp", doc)
            self.assertIn("ellmos-filecommander-mcp", doc)
            self.assertIn("ellmos-codecommander-mcp", doc)
            self.assertIn("ellmos-clatcher-mcp", doc)
            self.assertIn("n8n-manager-mcp", doc)
            self.assertIn("open-bricks", doc)


if __name__ == "__main__":
    unittest.main()
