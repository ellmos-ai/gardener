# -*- coding: utf-8 -*-
"""
Metadata, Governance and Discoverability Parity Tests for Gardener OS.
Asserts that pyproject.toml, README.md, README_de.md, SECURITY.md, THIRD_PARTY_LICENSES.md,
CI workflows, and llms.txt remain in strict 1:1 synchronization.
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
        self.third_party_licenses_path = ROOT / "THIRD_PARTY_LICENSES.md"
        self.third_party_licenses_txt_path = ROOT / "THIRD_PARTY_LICENSES.txt"
        self.ci_workflow_path = ROOT / ".github" / "workflows" / "ci.yml"
        self.stale_workflow_path = ROOT / ".github" / "workflows" / "stale.yml"
        self.welcome_workflow_path = ROOT / ".github" / "workflows" / "welcome.yml"
        self.auto_assign_workflow_path = ROOT / ".github" / "workflows" / "auto-assign.yml"
        self.label_sync_workflow_path = ROOT / ".github" / "workflows" / "label-sync.yml"
        self.notice_path = ROOT / "NOTICE"
        self.llms_txt_path = ROOT / "llms.txt"
        self.changelog_path = ROOT / "CHANGELOG.md"
        self.marketing_log_path = ROOT / "MARKETING-LOG.txt"
        self.gitignore_path = ROOT / ".gitignore"
        self.manifest_in_path = ROOT / "MANIFEST.in"

        self.pyproject = self.pyproject_path.read_text(encoding="utf-8")
        self.readme_en = self.readme_en_path.read_text(encoding="utf-8")
        self.readme_de = self.readme_de_path.read_text(encoding="utf-8")
        self.security = self.security_path.read_text(encoding="utf-8")
        self.third_party_licenses = self.third_party_licenses_path.read_text(encoding="utf-8")
        self.third_party_licenses_txt = self.third_party_licenses_txt_path.read_text(encoding="utf-8")
        self.ci_workflow = self.ci_workflow_path.read_text(encoding="utf-8")
        self.stale_workflow = self.stale_workflow_path.read_text(encoding="utf-8")
        self.welcome_workflow = self.welcome_workflow_path.read_text(encoding="utf-8")
        self.auto_assign_workflow = self.auto_assign_workflow_path.read_text(encoding="utf-8")
        self.label_sync_workflow = self.label_sync_workflow_path.read_text(encoding="utf-8")
        self.notice = self.notice_path.read_text(encoding="utf-8")
        self.llms_txt = self.llms_txt_path.read_text(encoding="utf-8")
        self.changelog = self.changelog_path.read_text(encoding="utf-8")
        self.marketing_log = self.marketing_log_path.read_text(encoding="utf-8")
        self.gitignore = self.gitignore_path.read_text(encoding="utf-8")

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
        # Assert test badges show 229 passed
        self.assertIn("tests-233%20passed-brightgreen.svg", self.readme_en)
        self.assertIn("tests-233%20passed-brightgreen.svg", self.readme_de)

        # Assert Level 1 SBOM badge
        self.assertIn("Level_1_SBOM-Plain_Text_Audited-brightgreen.svg", self.readme_en)
        self.assertIn("Level_1_SBOM-Plain_Text_Audited-brightgreen.svg", self.readme_de)

        # Assert NOTICE attribution badge
        self.assertIn("Attribution-NOTICE-blue.svg", self.readme_en)
        self.assertIn("Attribution-NOTICE-blue.svg", self.readme_de)

        # Assert Verified badge
        self.assertIn("verified-2026--11--02-blue.svg", self.readme_en)
        self.assertIn("verified-2026--11--02-blue.svg", self.readme_de)

        # Assert code style Ruff
        self.assertIn("code%20style-ruff-000000.svg", self.readme_en)
        self.assertIn("code%20style-ruff-000000.svg", self.readme_de)

        # Assert RunAsInvoker non-elevation execution badge
        self.assertIn("execution-RunAsInvoker-success.svg", self.readme_en)
        self.assertIn("execution-RunAsInvoker-success.svg", self.readme_de)

        # Assert security badge with SLA
        self.assertIn("security-48h%20SLA-blue.svg", self.readme_en)
        self.assertIn("sicherheit-48h%20SLA-blue.svg", self.readme_de)

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
        self.assertIn("Last-checked: 2026-11-02", self.llms_txt)
        self.assertIn("233 passing tests", self.llms_txt)
        self.assertIn("https://github.com/ellmos-ai/gardener", self.llms_txt)
        self.assertIn("ellmos-ai/gardener", self.llms_txt)
        self.assertIn("NOTICE", self.llms_txt)
        self.assertIn("SECURITY.md", self.llms_txt)
        self.assertIn("MARKETING-LOG", self.llms_txt)
        self.assertIn("THIRD_PARTY_LICENSES", self.llms_txt)
        self.assertIn("THIRD_PARTY_LICENSES.txt", self.llms_txt)
        self.assertIn("[PERSONA-01]", self.llms_txt)

    def test_mermaid_architecture_in_readmes(self):
        self.assertIn("```mermaid", self.readme_en)
        self.assertIn("```mermaid", self.readme_de)
        self.assertIn("flowchart TD", self.readme_en)
        self.assertIn("flowchart TD", self.readme_de)
        self.assertIn("everything", self.readme_en)
        self.assertIn("everything", self.readme_de)

    def test_sequence_diagram_in_readmes(self):
        self.assertIn("sequenceDiagram", self.readme_en)
        self.assertIn("sequenceDiagram", self.readme_de)
        self.assertIn("autonumber", self.readme_en)
        self.assertIn("autonumber", self.readme_de)
        self.assertIn("materialize", self.readme_en)
        self.assertIn("Materialisiere", self.readme_de)

    def test_quick_navigation_18_points_parity(self):
        for i in range(1, 19):
            self.assertIn(f"## {i}.", self.readme_en, f"Section {i} missing in README.md")
            self.assertIn(f"## {i}.", self.readme_de, f"Section {i} missing in README_de.md")
            sec_id = f"sec-{i:02d}"
            self.assertIn(f'id="{sec_id}"', self.readme_en, f'Anchor id="{sec_id}" missing in README.md')
            self.assertIn(f'id="{sec_id}"', self.readme_de, f'Anchor id="{sec_id}" missing in README_de.md')
            self.assertIn(f"(#{sec_id})", self.readme_en, f'Nav jump (#{sec_id}) missing in README.md')
            self.assertIn(f"(#{sec_id})", self.readme_de, f'Nav jump (#{sec_id}) missing in README_de.md')

        # Verify key reciprocal anchors exist in both READMEs
        key_anchors = [
            "1-features", "features", "what-is-gardener",
            "2-architecture", "architecture",
            "3-target-personas--discoverability", "target-personas", "discovery-context",
            "4-comparative-matrix-vs-alternatives", "comparative-matrix",
            "5-dual-mermaid-diagrams", "dual-mermaid-diagrams",
            "6-governance--runtime-invariants", "governance--runtime-invariants",
            "7-data-model--everything-substrate", "data-model",
            "8-sqlite-substrate--fts5-engine", "sqlite-substrate",
            "9-search-gui--web-companion", "search-gui",
            "10-installation--quickstart", "quickstart",
            "11-cli--headless-automation", "cli",
            "12-unified-task--memory-management", "memory-no-separate-memory-system", "tasks-no-separate-system",
            "13-file-lifecycle-absorb-materialize--sync", "three-relationships-with-files",
            "14-federated-sources--secret-redaction", "cross-source-federated-index",
            "15-gardener-vs-rinnsal", "comparison-gardener-vs-rinnsal",
            "16-testing--quality-verification", "testing",
            "17-third-party-licenses--software-inventory", "third-party-licenses", "licenses",
            "18-security-policy-sibling-ecosystem--liability", "security-model-read-this", "sibling-projects--ecosystem", "haftung--liability",
        ]
        for anchor in key_anchors:
            self.assertIn(f'id="{anchor}"', self.readme_en, f'Anchor id="{anchor}" missing in README.md')
            self.assertIn(f'id="{anchor}"', self.readme_de, f'Anchor id="{anchor}" missing in README_de.md')

    def test_target_personas_and_high_intent_queries(self):
        personas = ["[PERSONA-01]", "[PERSONA-02]", "[PERSONA-03]", "[PERSONA-04]"]
        for p in personas:
            self.assertIn(p, self.readme_en, f"Persona {p} missing in README.md")
            self.assertIn(p, self.readme_de, f"Persona {p} missing in README_de.md")

        queries = [
            "sqlite llm operating system",
            "local-first agent memory substrate",
            "offline fts5 agent knowledge base",
            "zero egress multi-agent memory",
            "ellmos-ai gardener sqlite",
        ]
        for q in queries:
            self.assertIn(q, self.readme_en, f"Query '{q}' missing in README.md")
            self.assertIn(q, self.readme_de, f"Query '{q}' missing in README_de.md")

    def test_comparative_matrix_vs_alternatives(self):
        for doc in (self.readme_en, self.readme_de):
            self.assertIn("MemGPT", doc)
            self.assertIn("LangChain", doc)
            self.assertIn("ChromaDB", doc)
            self.assertIn("INV-LOCAL-01", doc)
            self.assertIn("INV-RUNAS-02", doc)
            self.assertIn("INV-FTS-03", doc)
            self.assertIn("INV-SEC-04", doc)
            self.assertIn("INV-CLOUD-05", doc)
            self.assertIn("INV-RO-06", doc)
            self.assertIn("INV-TRAV-07", doc)
            self.assertIn("INV-SUB-08", doc)
            self.assertIn("INV-DOCS-09", doc)
            self.assertIn("INV-SLA-10", doc)

    def test_governance_invariants_table_parity(self):
        invariants = [
            "INV-LOCAL-01",
            "INV-RUNAS-02",
            "INV-FTS-03",
            "INV-SEC-04",
            "INV-CLOUD-05",
            "INV-RO-06",
            "INV-TRAV-07",
            "INV-SUB-08",
            "INV-DOCS-09",
            "INV-SLA-10",
        ]
        for inv in invariants:
            self.assertIn(inv, self.readme_en)
            self.assertIn(inv, self.readme_de)

    def test_third_party_licenses_md_integrity(self):
        self.assertTrue(self.third_party_licenses_path.is_file(), "THIRD_PARTY_LICENSES.md must exist")
        self.assertIn("Python Standard Library", self.third_party_licenses)
        self.assertIn("PSF-2.0", self.third_party_licenses)
        self.assertIn("pytest", self.third_party_licenses)
        self.assertIn("ruff", self.third_party_licenses)
        self.assertIn("setuptools", self.third_party_licenses)
        self.assertIn("MIT", self.third_party_licenses)
        self.assertIn("RunAsInvoker", self.third_party_licenses)
        self.assertIn("Zero-Copyleft", self.third_party_licenses)
        self.assertIn("INV-LOCAL-01", self.third_party_licenses)
        self.assertIn("INV-SLA-10", self.third_party_licenses)

    def test_german_statutory_notice(self):
        self.assertIn("521 BGB", self.readme_de)
        self.assertIn("Gefälligkeit", self.readme_de)
        self.assertIn("Schenkung", self.readme_de)

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
        self.assertIn("timeout-minutes: 15", self.ci_workflow)
        self.assertIn("pip install -e .", self.ci_workflow)
        self.assertIn("ruff check .", self.ci_workflow)
        self.assertIn("python -m pytest -ra -v", self.ci_workflow)

    def test_auxiliary_workflows_hardening(self):
        self.assertTrue(self.stale_workflow_path.is_file(), ".github/workflows/stale.yml must exist")
        self.assertIn("timeout-minutes: 10", self.stale_workflow)
        self.assertIn("cancel-in-progress: true", self.stale_workflow)

        self.assertTrue(self.welcome_workflow_path.is_file(), ".github/workflows/welcome.yml must exist")
        self.assertIn("timeout-minutes: 5", self.welcome_workflow)
        self.assertIn("cancel-in-progress: true", self.welcome_workflow)

        self.assertTrue(self.auto_assign_workflow_path.is_file(), ".github/workflows/auto-assign.yml must exist")
        self.assertIn("timeout-minutes: 5", self.auto_assign_workflow)
        self.assertIn("cancel-in-progress: true", self.auto_assign_workflow)
        self.assertIn("issues: write", self.auto_assign_workflow)
        self.assertIn("pull-requests: write", self.auto_assign_workflow)

        self.assertTrue(self.label_sync_workflow_path.is_file(), ".github/workflows/label-sync.yml must exist")
        self.assertIn("timeout-minutes: 5", self.label_sync_workflow)
        self.assertIn("cancel-in-progress: true", self.label_sync_workflow)
        self.assertIn("issues: write", self.label_sync_workflow)

    def test_ci_concurrency_and_bytecode_gate(self):
        self.assertIn("concurrency:", self.ci_workflow)
        self.assertIn("cancel-in-progress: true", self.ci_workflow)
        self.assertIn("python -m compileall -q .", self.ci_workflow)

    def test_security_policy_exists_and_invariants(self):
        self.assertTrue(self.security_path.is_file(), "SECURITY.md must exist")
        self.assertIn("## English", self.security)
        self.assertIn("## Deutsch", self.security)
        self.assertIn("security@ellmos.ai", self.security)
        self.assertIn("security@open-bricks.org", self.security)
        self.assertIn("support@lukasgeiger.com", self.security)
        self.assertIn("48 hours", self.security)
        self.assertIn("48 Stunden", self.security)
        self.assertIn("5 business days", self.security)
        self.assertIn("5 Werktagen", self.security)
        self.assertIn("Zero-Egress", self.security)
        self.assertIn("Local-First", self.security)
        self.assertIn("Non-Elevation", self.security)
        self.assertIn("https://github.com/ellmos-ai/gardener/security/advisories", self.security)

    def test_pyproject_project_table_structure(self):
        # keywords/classifiers placed after [project.optional-dependencies] are parsed
        # as extras and break `pip install -e .` (pep508 error).
        try:
            import tomllib
        except ModuleNotFoundError:  # Python 3.10
            self.skipTest("tomllib requires Python 3.11+")
        project = tomllib.loads(self.pyproject)["project"]
        self.assertEqual(set(project["optional-dependencies"]), {"dev", "test"})
        self.assertIn("Development Status :: 4 - Beta", project["classifiers"])
        self.assertIn("sqlite", project["keywords"])

    def test_pyproject_pep621_classifiers_and_urls(self):
        self.assertIn("classifiers = [", self.pyproject)
        self.assertIn("Development Status :: 4 - Beta", self.pyproject)
        self.assertIn("Operating System :: OS Independent", self.pyproject)
        self.assertIn("Programming Language :: Python :: 3.10", self.pyproject)
        self.assertIn("Programming Language :: Python :: 3.13", self.pyproject)
        self.assertIn('"THIRD_PARTY_LICENSES.txt"', self.pyproject)

        for key in (
            "Homepage", "Documentation", "Repository", "Source Code", "Issues", "Bug Tracker",
            "Changelog", "Security", "Notice", "Parent Organization", "Umbrella", "Umbrella Ecosystem",
            "LLM Ready", "Marketing Log", "Third-Party Licenses", "Level 1 SBOM",
            "Third-Party Licenses (Text)", "Plain-Text License"
        ):
            self.assertIn(f'"{key}" = ' if " " in key else f"{key} = ", self.pyproject)

    def test_ascii_architecture_topology_projections(self):
        # Assert 4-view ASCII architectural diagrams in English README
        self.assertIn("VIEW 1: CLIENT RUNTIMES, AGENT CLIENTS & USER INTERFACES", self.readme_en)
        self.assertIn("VIEW 2: GARDENER SOVEREIGN CORE ENGINE & MEMORY ORCHESTRATOR", self.readme_en)
        self.assertIn("VIEW 3: DUAL SQLITE SUBSTRATE, FTS5 BM25 ENGINE & FEDERATED INGESTION", self.readme_en)
        self.assertIn("VIEW 4: AIR-GAP DEFENSE PERIMETER, ZERO-EGRESS & GOVERNANCE", self.readme_en)

        # Assert 4-view ASCII architectural diagrams in German README
        self.assertIn("SICHT 1: CLIENT-LAUFZEITEN, AGENTEN-SCHNITTSTELLEN & BENUTZEROBERFLÄCHEN", self.readme_de)
        self.assertIn("SICHT 2: AUTONOME KERN-ENGINE, PRIMITIVE & SPEICHER-ORCHESTRIERER", self.readme_de)
        self.assertIn("SICHT 3: DUALES SQLITE-SUBSTRAT, FTS5-BM25-ENGINE & FÖDERIERTE BEOBACHTUNG", self.readme_de)
        self.assertIn("SICHT 4: AIR-GAP-SICHERHEITSGRENZE, ZERO-EGRESS & GOVERNANCE-PERIMETER", self.readme_de)

    def test_third_party_licenses_plain_text_companion(self):
        self.assertTrue(self.third_party_licenses_txt_path.is_file(), "THIRD_PARTY_LICENSES.txt must exist")
        self.assertIn("Python Standard Library", self.third_party_licenses_txt)
        self.assertIn("PSF-2.0", self.third_party_licenses_txt)
        self.assertIn("pytest", self.third_party_licenses_txt)
        self.assertIn("ruff", self.third_party_licenses_txt)
        self.assertIn("setuptools", self.third_party_licenses_txt)
        self.assertIn("MIT", self.third_party_licenses_txt)
        self.assertIn("RunAsInvoker", self.third_party_licenses_txt)
        self.assertIn("Zero-Copyleft", self.third_party_licenses_txt)
        self.assertIn("INV-LOCAL-01", self.third_party_licenses_txt)
        self.assertIn("INV-SLA-10", self.third_party_licenses_txt)

    def test_pyproject_pytest_and_ruff_config(self):
        self.assertIn("[tool.pytest.ini_options]", self.pyproject)
        self.assertIn('addopts = "-ra -v --basetemp=.pytest_temp"', self.pyproject)
        self.assertIn("norecursedirs = [", self.pyproject)
        self.assertIn(".pytest_temp", self.pyproject)
        self.assertIn("[tool.ruff.lint]", self.pyproject)
        self.assertIn('"B"', self.pyproject)
        self.assertIn('"C4"', self.pyproject)
        self.assertIn('"SIM"', self.pyproject)

    def test_gitignore_hardened_patterns(self):
        self.assertTrue(self.gitignore_path.is_file(), ".gitignore must exist")
        self.assertIn("*.sync-conflict-*", self.gitignore)
        self.assertIn("LOCK.*", self.gitignore)
        self.assertIn("LOCK.user.*", self.gitignore)
        self.assertIn("LOCK.until.*", self.gitignore)
        self.assertIn("LOCK.condition.*", self.gitignore)
        self.assertIn("LOCK.permissions.json", self.gitignore)
        self.assertIn(".automation-lock", self.gitignore)
        self.assertIn("*.lock", self.gitignore)
        self.assertIn("uv.lock", self.gitignore)
        self.assertIn("!package-lock.json", self.gitignore)
        self.assertIn("* (copy)*", self.gitignore)
        self.assertIn("* (kopie)*", self.gitignore)
        self.assertIn("*-WORKSTATION*", self.gitignore)
        self.assertIn("*-WORKSTATION-LG*", self.gitignore)
        self.assertIn("*-ASUS*", self.gitignore)
        self.assertIn("*-ASUS-GEI*", self.gitignore)
        self.assertIn("*-LAPTOP*", self.gitignore)
        self.assertIn("*-Mac Studio*", self.gitignore)
        self.assertIn("*-MacBook*", self.gitignore)
        self.assertIn("*-IDEAPAD*", self.gitignore)
        self.assertIn("*.sync-temp-*", self.gitignore)
        self.assertIn(".pytest_temp/", self.gitignore)
        self.assertIn("*.orig", self.gitignore)
        self.assertIn("*.rej", self.gitignore)
        self.assertIn(".ruff_cache/", self.gitignore)
        self.assertIn(".pytest_cache/", self.gitignore)
        self.assertIn(".coverage.*", self.gitignore)

    def test_marketing_log_and_changelog_recency(self):
        self.assertTrue(self.marketing_log_path.is_file(), "MARKETING-LOG.txt must exist")
        self.assertIn("2026-09-08", self.marketing_log)
        self.assertIn("2026-09-16", self.marketing_log)
        self.assertIn("2026-09-18", self.marketing_log)
        self.assertIn("2026-09-26", self.marketing_log)
        self.assertIn("2026-09-28", self.marketing_log)
        self.assertIn("2026-09-30", self.marketing_log)
        self.assertIn("2026-10-01", self.marketing_log)
        self.assertIn("2026-10-02", self.marketing_log)
        self.assertIn("2026-10-03", self.marketing_log)
        self.assertIn("Pfad A", self.marketing_log)
        self.assertIn("Pfad B", self.marketing_log)
        self.assertIn("ellmos-ai/gardener", self.marketing_log)
        self.assertIn("2026-09-08", self.changelog)
        self.assertIn("2026-09-16", self.changelog)
        self.assertIn("2026-09-18", self.changelog)
        self.assertIn("2026-09-26", self.changelog)
        self.assertIn("2026-09-28", self.changelog)
        self.assertIn("2026-09-30", self.changelog)
        self.assertIn("2026-10-01", self.changelog)
        self.assertIn("2026-10-02", self.changelog)
        self.assertIn("2026-10-03", self.changelog)
        self.assertIn("2026-11-02", self.changelog)

    def test_license_and_liability_notice(self):
        license_path = ROOT / "LICENSE"
        self.assertTrue(license_path.is_file(), "LICENSE must exist")
        license_text = license_path.read_text(encoding="utf-8")
        self.assertIn("MIT License", license_text)
        self.assertIn("Lukas Geiger", license_text)

        # Assert BGB § 521 liability limitation notice in both READMEs
        for doc in (self.readme_en, self.readme_de):
            self.assertIn("521 BGB", doc)
            self.assertIn("Liability", doc)

    def test_notice_attribution_file_integrity(self):
        self.assertTrue(self.notice_path.is_file(), "NOTICE must exist")
        self.assertIn("gardener (gardener-os)", self.notice)
        self.assertIn("Lukas Geiger", self.notice)
        self.assertIn("ellmos-ai", self.notice)
        self.assertIn("open-bricks", self.notice)

    def test_cli_entrypoint_is_callable(self):
        import gardener
        self.assertTrue(callable(gardener.main), "gardener.main must be a callable entrypoint")

    def test_offline_zero_egress_contract(self):
        # Assert Invariant #1: Core engine and ingestion modules must never import remote network clients
        for module_name in ("gardener.py", "sources.py"):
            mod_code = (ROOT / module_name).read_text(encoding="utf-8")
            for forbidden in ("urllib.request", "requests", "httpx", "aiohttp"):
                self.assertNotIn(forbidden, mod_code, f"{module_name} must not import {forbidden}")

    def test_bilingual_architecture_docs_parity(self):
        design_path = ROOT / "DESIGN.md"
        konzept_path = ROOT / "KONZEPT.md"
        self.assertTrue(design_path.is_file(), "DESIGN.md must exist")
        self.assertTrue(konzept_path.is_file(), "KONZEPT.md must exist")

        design = design_path.read_text(encoding="utf-8")
        konzept = konzept_path.read_text(encoding="utf-8")

        # Assert reciprocal cross-links
        self.assertIn("KONZEPT.md", design)
        self.assertIn("DESIGN.md", konzept)

        # Assert federated cross-source index section and 4 adapters documented in both
        for adapter in ("markdown_dir", "remember_files", "sqlite_table", "agent_transcripts"):
            self.assertIn(adapter, design)
            self.assertIn(adapter, konzept)

        # Assert provenance and query scoping
        self.assertIn("source_ref", design)
        self.assertIn("source_ref", konzept)
        self.assertIn("--source", design)
        self.assertIn("--source", konzept)

        # Assert absorb vs. observe custody distinction table and mental model
        self.assertIn("absorb", design)
        self.assertIn("absorb", konzept)
        self.assertIn("observe_source", design)
        self.assertIn("observe_source", konzept)
        self.assertIn("Mailbox", design)
        self.assertIn("Telescope", design)
        self.assertIn("Briefkasten", konzept)
        self.assertIn("Fernrohr", konzept)


    def test_pep621_explicit_dependencies_contract(self):
        self.assertIn("dependencies = []", self.pyproject)
        self.assertIn("[project.optional-dependencies]", self.pyproject)
        self.assertIn('"pytest>=7.0"', self.pyproject)
        self.assertIn('"ruff>=0.5"', self.pyproject)
        self.assertIn("python -m pip check", self.ci_workflow)

    def test_manifest_in_and_package_data_integrity(self):
        self.assertTrue(self.manifest_in_path.is_file(), "MANIFEST.in must exist")
        manifest = self.manifest_in_path.read_text(encoding="utf-8")
        self.assertIn("recursive-include locales *.json", manifest)
        self.assertIn("include LICENSE", manifest)
        self.assertIn("include NOTICE", manifest)
        self.assertIn("include THIRD_PARTY_LICENSES.md", manifest)
        self.assertIn("include THIRD_PARTY_LICENSES.txt", manifest)
        self.assertIn("[tool.setuptools.package-data]", self.pyproject)

    def test_natural_filter_and_query_syntax_matrix_parity(self):
        for doc in (self.readme_en, self.readme_de):
            self.assertIn("Natural Filter & Query Syntax Matrix" if doc is self.readme_en else "Bilinguale Filter- & Abfragesyntax-Matrix", doc)
            self.assertIn("title:<term>", doc)
            self.assertIn("titel:<term>", doc)
            self.assertIn("inhalt:<term>", doc)
            self.assertIn("schlagwort:<term>", doc)
            self.assertIn("+<term>", doc)
            self.assertIn("-<term>", doc)
            self.assertIn("type:<t1>,<t2>", doc)
            self.assertIn("limit:<N>", doc)
            self.assertIn("is:pinned", doc)

    def test_gui_default_port_harmonization(self):
        # Both READMEs must document port 8765 matching search_gui.py DEFAULT_PORT
        self.assertIn("python gardener.py gui", self.readme_en)
        self.assertIn("python gardener.py gui", self.readme_de)
        self.assertIn("8765", self.readme_en)
        self.assertIn("8765", self.readme_de)
        self.assertNotIn("8420", self.readme_en)
        self.assertNotIn("8420", self.readme_de)


if __name__ == "__main__":
    unittest.main()
