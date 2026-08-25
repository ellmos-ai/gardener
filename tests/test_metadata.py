# -*- coding: utf-8 -*-
"""
Metadata and Discoverability Parity Tests for Gardener OS.
Asserts that pyproject.toml, README.md, README_de.md, SECURITY.md, CI workflows, and llms.txt remain in sync.
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class TestMetadataParity(unittest.TestCase):
    def setUp(self):
        self.pyproject_path = ROOT / "pyproject.toml"
        self.readme_en_path = ROOT / "README.md"
        self.readme_de_path = ROOT / "README_de.md"
        self.security_path = ROOT / "SECURITY.md"
        self.ci_workflow_path = ROOT / ".github" / "workflows" / "ci.yml"
        self.llms_txt_path = ROOT / "llms.txt"
        self.changelog_path = ROOT / "CHANGELOG.md"

        self.pyproject = self.pyproject_path.read_text(encoding="utf-8")
        self.readme_en = self.readme_en_path.read_text(encoding="utf-8")
        self.readme_de = self.readme_de_path.read_text(encoding="utf-8")
        self.security = self.security_path.read_text(encoding="utf-8")
        self.ci_workflow = self.ci_workflow_path.read_text(encoding="utf-8")
        self.llms_txt = self.llms_txt_path.read_text(encoding="utf-8")
        self.changelog = self.changelog_path.read_text(encoding="utf-8")

    def test_pyproject_version_matches(self):
        match = re.search(r'version\s*=\s*"([^"]+)"', self.pyproject)
        self.assertIsNotNone(match, "pyproject.toml missing version")
        version = match.group(1)
        self.assertEqual(version, "0.4.2")

        # Check READMEs reference version
        self.assertIn(f"v{version}", self.readme_en)
        self.assertIn(f"v{version}", self.readme_de)
        self.assertIn(f"[{version}]", self.changelog)

    def test_readme_badges_and_test_count(self):
        # Assert test badges show 124 passed
        self.assertIn("tests-124%20passed-brightgreen.svg", self.readme_en)
        self.assertIn("tests-124%20passed-brightgreen.svg", self.readme_de)

        # Assert umbrella and ecosystem badges
        self.assertIn("ecosystem-ellmos--ai-informational.svg", self.readme_en)
        self.assertIn("umbrella-open--bricks-blue.svg", self.readme_en)
        self.assertIn("LLM--Ready-llms.txt-orange.svg", self.readme_en)

        self.assertIn("ecosystem-ellmos--ai-informational.svg", self.readme_de)
        self.assertIn("umbrella-open--bricks-blue.svg", self.readme_de)
        self.assertIn("LLM--Ready-llms.txt-orange.svg", self.readme_de)

        # Assert CI badge
        self.assertIn("actions/workflows/ci.yml/badge.svg", self.readme_en)
        self.assertIn("actions/workflows/ci.yml/badge.svg", self.readme_de)

    def test_llms_txt_consistency(self):
        self.assertIn("Last-checked: 2026-08-25", self.llms_txt)
        self.assertIn("124 passing tests", self.llms_txt)
        self.assertIn("https://github.com/ellmos-ai/gardener", self.llms_txt)
        self.assertIn("ellmos-ai/gardener", self.llms_txt)
        self.assertIn("SECURITY.md", self.llms_txt)

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

    def test_ci_workflow_integrity(self):
        self.assertTrue(self.ci_workflow_path.is_file(), ".github/workflows/ci.yml must exist")
        self.assertIn("actions/checkout@v4", self.ci_workflow)
        self.assertIn("actions/setup-python@v5", self.ci_workflow)
        for os_target in ("ubuntu-latest", "windows-latest", "macos-latest"):
            self.assertIn(os_target, self.ci_workflow)
        for py_ver in ("'3.10'", "'3.11'", "'3.12'", "'3.13'"):
            self.assertIn(py_ver, self.ci_workflow)
        self.assertIn("ruff check .", self.ci_workflow)
        self.assertIn("pytest -v", self.ci_workflow)

    def test_security_policy_exists_and_invariants(self):
        self.assertTrue(self.security_path.is_file(), "SECURITY.md must exist")
        self.assertIn("## English", self.security)
        self.assertIn("## Deutsch", self.security)
        self.assertIn("security@ellmos.ai", self.security)
        self.assertIn("Zero-Egress", self.security)
        self.assertIn("Local-First", self.security)
        self.assertIn("Non-Elevation", self.security)
        self.assertIn("https://github.com/ellmos-ai/gardener/security/advisories", self.security)

    def test_pyproject_pep621_classifiers_and_urls(self):
        self.assertIn("classifiers = [", self.pyproject)
        self.assertIn("Development Status :: 4 - Beta", self.pyproject)
        self.assertIn("Operating System :: OS Independent", self.pyproject)
        self.assertIn("Programming Language :: Python :: 3.10", self.pyproject)
        self.assertIn("Programming Language :: Python :: 3.13", self.pyproject)

        for key in ("Homepage", "Documentation", "Repository", "Issues", "Changelog", "Security", "Umbrella"):
            self.assertIn(f"{key} = ", self.pyproject)


if __name__ == "__main__":
    unittest.main()
