import importlib
import gc
import json
import os
import sqlite3
import tempfile
import time
import unittest
from pathlib import Path


class ObserveSourceTestCase(unittest.TestCase):
    """Same pattern as GardenerTempCase in test_gardener_core.py, plus a
    dedicated `foreign` scratch directory for synthetic cross-source
    fixtures (markdown files, .remember files, a foreign SQLite DB, and
    JSONL transcripts) that live OUTSIDE Gardener's own home/data dirs --
    exactly the "observe a knowledge source that lives elsewhere"
    situation this feature targets. No real user data is touched.
    """

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        base = Path(self.temp.name)
        self.foreign = base / "foreign"
        self.foreign.mkdir(parents=True, exist_ok=True)
        os.environ["GARDENER_DATA"] = str(base / "data")
        os.environ["GARDENER_HOME"] = str(base / "home")

        import gardener
        self.gardener = importlib.reload(gardener)
        self.af = self.gardener.Gardener()

    def tearDown(self):
        gc.collect()
        for attempt in range(3):
            try:
                self.temp.cleanup()
                break
            except PermissionError:
                if attempt == 2:
                    raise
                time.sleep(0.1)

    def reopen(self):
        """Simulates a restart: fresh Gardener instance, same home/data dirs."""
        import gardener
        self.gardener = importlib.reload(gardener)
        self.af = self.gardener.Gardener()


class TestMarkdownDirSource(ObserveSourceTestCase):
    def test_indexes_files_across_wildcard_directories_with_citation(self):
        # Mirrors '~/.claude/projects/*/memory' -- several project
        # directories, each with its own memory subfolder.
        for project in ("proj-a", "proj-b"):
            mem_dir = self.foreign / "projects" / project / "memory"
            mem_dir.mkdir(parents=True, exist_ok=True)
            (mem_dir / "MEMORY.md").write_text(
                f"# Notes for {project}\nSteuerbelege pruefen.", encoding="utf-8")

        self.af.observe_source_add(
            "claude-memories", "markdown_dir",
            path=str(self.foreign / "projects" / "*" / "memory"),
        )
        result = self.af.observe_sources("claude-memories")
        self.assertEqual(result["claude-memories"]["indexed"], 2)

        hits = self.af.find("Steuerbelege")
        self.assertEqual(len(hits), 2)
        names = {h["name"] for h in hits}
        # Entry names are built from the file's absolute path (drive
        # letter stripped) since the source config is a directory glob
        # spanning several project dirs -- assert on the stable suffix,
        # not the volatile tempdir prefix.
        self.assertTrue(any(n.endswith("projects/proj-a/memory/MEMORY.md") for n in names))
        self.assertTrue(any(n.endswith("projects/proj-b/memory/MEMORY.md") for n in names))
        for n in names:
            self.assertTrue(n.startswith("observed/claude-memories/"))
        for h in hits:
            self.assertEqual(h["type"], "observed")
            ref = h["meta"]["source_ref"]
            self.assertEqual(ref["kind"], "markdown_dir")
            self.assertTrue(Path(ref["path"]).is_file())
            self.assertEqual(h["meta"]["source_id"], "claude-memories")

    def test_refresh_is_incremental(self):
        mem_dir = self.foreign / "memory"
        mem_dir.mkdir(parents=True, exist_ok=True)
        (mem_dir / "a.md").write_text("erster Eintrag", encoding="utf-8")

        self.af.observe_source_add("mem", "markdown_dir", path=str(mem_dir))
        first = self.af.observe_sources("mem")
        self.assertEqual(first["mem"], {"kind": "markdown_dir", "indexed": 1, "skipped": 0})

        second = self.af.observe_sources("mem")
        self.assertEqual(second["mem"], {"kind": "markdown_dir", "indexed": 0, "skipped": 1})

        # Changing the file makes it reindex again.
        time.sleep(0.05)
        (mem_dir / "a.md").write_text("geaendert", encoding="utf-8")
        third = self.af.observe_sources("mem")
        self.assertEqual(third["mem"]["indexed"], 1)
        hits = self.af.find("geaendert")
        self.assertEqual(len(hits), 1)
        self.assertTrue(hits[0]["name"].startswith("observed/mem/"))


class TestRememberFilesSource(ObserveSourceTestCase):
    def test_recursive_glob_finds_nested_remember_files(self):
        nested = self.foreign / "some" / "deep" / "project"
        nested.mkdir(parents=True, exist_ok=True)
        (nested / ".remember").write_text("Merke: WAL-Modus verwenden.", encoding="utf-8")
        (self.foreign / ".remember").write_text("Merke: root-level note.", encoding="utf-8")

        self.af.observe_source_add("remembers", "remember_files", path=str(self.foreign))
        result = self.af.observe_sources("remembers")
        self.assertEqual(result["remembers"]["indexed"], 2)

        hits = self.af.find("WAL-Modus")
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["meta"]["source_ref"]["kind"], "remember_files")


class TestSqliteTableSource(ObserveSourceTestCase):
    def _make_foreign_db(self):
        db_path = self.foreign / "rinnsal-like.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("""
            CREATE TABLE tasks (
                id INTEGER PRIMARY KEY,
                title TEXT,
                body TEXT,
                labels TEXT
            )
        """)
        conn.execute(
            "INSERT INTO tasks (id, title, body, labels) VALUES (?, ?, ?, ?)",
            (1, "Steuererklaerung", "Belege fuer 2025 zusammenstellen", "steuer,frist"),
        )
        conn.execute(
            "INSERT INTO tasks (id, title, body, labels) VALUES (?, ?, ?, ?)",
            (2, "Server-Backup", "Woechentliches Backup pruefen", "infra"),
        )
        conn.commit()
        conn.close()
        return db_path

    def test_reads_foreign_table_readonly_with_citation(self):
        db_path = self._make_foreign_db()

        self.af.observe_source_add(
            "rinnsal-tasks", "sqlite_table",
            db_path=str(db_path), table="tasks",
            columns={"id": "id", "name": "title", "content": "body", "tags": "labels"},
        )
        result = self.af.observe_sources("rinnsal-tasks")
        self.assertEqual(result["rinnsal-tasks"], {"kind": "sqlite_table", "indexed": 2, "skipped": 0})

        hits = self.af.find("Steuererklaerung")
        self.assertEqual(len(hits), 1)
        entry = hits[0]
        self.assertEqual(entry["type"], "observed")
        self.assertIn("steuer", entry["tags"])
        ref = entry["meta"]["source_ref"]
        self.assertEqual(ref["kind"], "sqlite_table")
        self.assertEqual(ref["table"], "tasks")
        self.assertEqual(ref["row_id"], 1)

        # mode=ro must leave the foreign DB completely untouched: no
        # WAL/journal side files, still a plain, readable database.
        self.assertFalse((self.foreign / "rinnsal-like.db-wal").exists())
        self.assertFalse((self.foreign / "rinnsal-like.db-journal").exists())
        conn = sqlite3.connect(str(db_path))
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0], 2)
        conn.close()

    def test_refresh_reindexes_only_changed_rows(self):
        db_path = self._make_foreign_db()
        self.af.observe_source_add(
            "rinnsal-tasks", "sqlite_table",
            db_path=str(db_path), table="tasks",
            columns={"id": "id", "name": "title", "content": "body"},
        )
        first = self.af.observe_sources("rinnsal-tasks")
        self.assertEqual(first["rinnsal-tasks"]["indexed"], 2)

        second = self.af.observe_sources("rinnsal-tasks")
        self.assertEqual(second["rinnsal-tasks"], {"kind": "sqlite_table", "indexed": 0, "skipped": 2})

        conn = sqlite3.connect(str(db_path))
        conn.execute("UPDATE tasks SET body = ? WHERE id = 1", ("Aktualisierter Text",))
        conn.commit()
        conn.close()

        third = self.af.observe_sources("rinnsal-tasks")
        self.assertEqual(third["rinnsal-tasks"], {"kind": "sqlite_table", "indexed": 1, "skipped": 1})

    def test_unknown_table_or_column_is_refused_not_injected(self):
        db_path = self._make_foreign_db()
        self.af.observe_source_add(
            "bad", "sqlite_table",
            db_path=str(db_path), table="tasks; DROP TABLE tasks",
            columns={"content": "body"},
        )
        result = self.af.observe_sources("bad")
        self.assertEqual(result["bad"], {"kind": "sqlite_table", "indexed": 0, "skipped": 0})

        conn = sqlite3.connect(str(db_path))
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0], 2)
        conn.close()


class TestAgentTranscriptSource(ObserveSourceTestCase):
    def _write_jsonl(self, path, lines):
        with open(path, "w", encoding="utf-8") as f:
            for entry in lines:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def _claude_code_fixture(self):
        return [
            {"type": "user", "sessionId": "s1", "uuid": "u1",
             "timestamp": "2026-07-01T10:00:00Z", "isMeta": False,
             "message": {"role": "user", "content": "Bitte Steuerbescheid pruefen."}},
            {"type": "assistant", "sessionId": "s1", "uuid": "u2",
             "timestamp": "2026-07-01T10:00:05Z",
             "message": {"role": "assistant", "content": [
                 {"type": "thinking", "text": "interner Gedanke, nicht indexieren"},
                 {"type": "text", "text": "Ich pruefe den Steuerbescheid jetzt."},
             ]}},
            {"type": "user", "sessionId": "s1", "uuid": "u3",
             "timestamp": "2026-07-01T10:00:06Z",
             "message": {"role": "user", "content": [
                 {"type": "tool_result", "content": "some tool output, kein Menschentext"},
             ]}},
            {"type": "user", "sessionId": "s1", "uuid": "u4",
             "timestamp": "2026-07-01T10:00:07Z", "isMeta": True,
             "message": {"role": "user", "content": "<system-reminder>...</system-reminder>"}},
            {"type": "assistant", "sessionId": "s1", "uuid": "u5",
             "timestamp": "2026-07-01T10:00:08Z", "isSidechain": True,
             "message": {"role": "assistant", "content": "Subagent-Nebengespraech"}},
        ]

    def test_extracts_only_real_text_turns(self):
        jsonl_path = self.foreign / "session-a.jsonl"
        self._write_jsonl(jsonl_path, self._claude_code_fixture())

        self.af.observe_source_add(
            "claude-transcripts", "agent_transcripts",
            path=str(self.foreign / "*.jsonl"),
        )
        result = self.af.observe_sources("claude-transcripts")
        # Only u1 (plain user text) and u2 (assistant text block) qualify;
        # u3 (tool_result-only), u4 (isMeta) and u5 (sidechain) are skipped.
        self.assertEqual(result["claude-transcripts"]["indexed"], 2)

        hits = self.af.find("Steuerbescheid")
        self.assertEqual(len(hits), 2)
        roles = {h["meta"]["source_ref"]["role"] for h in hits}
        self.assertEqual(roles, {"user", "assistant"})
        for h in hits:
            self.assertEqual(h["meta"]["source_ref"]["kind"], "agent_transcripts")
            self.assertEqual(h["meta"]["source_ref"]["session"], "s1")

        self.assertEqual(self.af.find("Nebengespraech"), [])
        self.assertEqual(self.af.find("system-reminder"), [])

    def test_incremental_tail_only_indexes_appended_lines(self):
        jsonl_path = self.foreign / "growing.jsonl"
        self._write_jsonl(jsonl_path, self._claude_code_fixture()[:1])  # just u1

        self.af.observe_source_add(
            "live-transcript", "agent_transcripts", path=str(jsonl_path),
        )
        first = self.af.observe_sources("live-transcript")
        self.assertEqual(first["live-transcript"]["indexed"], 1)

        # Unlike the other adapters, an unchanged transcript file is not
        # re-scanned at all (mtime+size fast-skip, by design -- see
        # sources.py docstring): already-indexed turns are never
        # re-visited, so there is nothing to count as "skipped" either.
        second = self.af.observe_sources("live-transcript")
        self.assertEqual(second["live-transcript"], {"kind": "agent_transcripts", "indexed": 0, "skipped": 0})

        # Append a new human turn, as if the session kept going.
        with open(jsonl_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "type": "user", "sessionId": "s1", "uuid": "u-new",
                "timestamp": "2026-07-01T10:05:00Z",
                "message": {"role": "user", "content": "Noch eine Frage zur Frist."},
            }, ensure_ascii=False) + "\n")

        third = self.af.observe_sources("live-transcript")
        self.assertEqual(third["live-transcript"], {"kind": "agent_transcripts", "indexed": 1, "skipped": 0})
        self.assertEqual(self.af.find("Frist")[0]["meta"]["source_ref"]["uuid"], "u-new")

    def test_generic_format_uses_configured_field_mapping(self):
        jsonl_path = self.foreign / "other-agent.jsonl"
        self._write_jsonl(jsonl_path, [
            {"speaker": "human", "body": "Wie lief das Deployment?"},
            {"speaker": "bot", "body": "Deployment war erfolgreich."},
            {"speaker": "human", "body": ""},
        ])

        self.af.observe_source_add(
            "other-agent", "agent_transcripts", path=str(jsonl_path),
            format="generic", role_field="speaker", text_field="body",
            roles=["human", "bot"],
        )
        result = self.af.observe_sources("other-agent")
        self.assertEqual(result["other-agent"]["indexed"], 2)
        self.assertEqual(len(self.af.find("Deployment")), 2)


class TestFederatedSearchAndCrud(ObserveSourceTestCase):
    def test_find_returns_own_and_observed_hits_in_one_query(self):
        self.af.put("eigene-notiz", content="Frist fuer Steuererklaerung: Mai.",
                    type="memory")

        mem_dir = self.foreign / "memory"
        mem_dir.mkdir(parents=True, exist_ok=True)
        (mem_dir / "note.md").write_text(
            "Externe Notiz: Frist fuer Steuererklaerung ebenfalls Mai.",
            encoding="utf-8")
        self.af.observe_source_add("ext", "markdown_dir", path=str(mem_dir))
        self.af.observe_sources("ext")

        hits = self.af.find("Steuererklaerung")
        self.assertEqual(len(hits), 2)
        sources_seen = {h.get("meta", {}).get("source_id", "own") for h in hits}
        self.assertEqual(sources_seen, {"own", "ext"})

    def test_add_list_remove_persists_across_restart(self):
        self.af.observe_source_add("s1", "markdown_dir", path=str(self.foreign))
        self.reopen()

        listed = self.af.observe_source_list()
        self.assertIn("s1", listed)
        self.assertEqual(listed["s1"]["kind"], "markdown_dir")

        self.assertTrue(self.af.observe_source_remove("s1"))
        self.reopen()
        self.assertEqual(self.af.observe_source_list(), {})
        self.assertFalse(self.af.observe_source_remove("s1"))

    def test_disabled_source_is_skipped_on_refresh(self):
        self.af.observe_source_add(
            "off", "markdown_dir", path=str(self.foreign), enabled=False)
        result = self.af.observe_sources("off")
        self.assertEqual(result["off"], {"skipped_disabled": True})

    def test_unknown_kind_raises_clean_error(self):
        with self.assertRaises(ValueError):
            self.af.observe_source_add("bad", "not-a-real-kind", path=".")

    def test_refresh_unknown_source_id_reports_error(self):
        self.assertIn("error", self.af.observe_sources("does-not-exist"))


if __name__ == "__main__":
    unittest.main()
