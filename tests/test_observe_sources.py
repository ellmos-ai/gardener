import importlib
import gc
import json
import os
import re
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


class TestMarkdownDirPatterns(ObserveSourceTestCase):
    def test_default_patterns_only_match_markdown(self):
        mem_dir = self.foreign / "memory"
        mem_dir.mkdir(parents=True, exist_ok=True)
        (mem_dir / "notes.md").write_text("Markdown-Notiz.", encoding="utf-8")
        (mem_dir / "notes.txt").write_text("Text-Notiz.", encoding="utf-8")

        self.af.observe_source_add("mem", "markdown_dir", path=str(mem_dir))
        result = self.af.observe_sources("mem")
        # Unchanged default behaviour: only the *.md file is picked up,
        # the .txt sibling is ignored.
        self.assertEqual(result["mem"]["indexed"], 1)
        self.assertEqual(self.af.find("Text-Notiz"), [])
        self.assertEqual(len(self.af.find("Markdown-Notiz")), 1)

    def test_patterns_config_also_indexes_txt_files(self):
        mem_dir = self.foreign / "memory"
        mem_dir.mkdir(parents=True, exist_ok=True)
        (mem_dir / "notes.md").write_text("Markdown-Notiz.", encoding="utf-8")
        (mem_dir / "notes.txt").write_text("Reine Textnotiz.", encoding="utf-8")
        (mem_dir / "ignored.json").write_text("{}", encoding="utf-8")

        self.af.observe_source_add(
            "mem", "markdown_dir", path=str(mem_dir), patterns=["*.md", "*.txt"])
        result = self.af.observe_sources("mem")
        self.assertEqual(result["mem"]["indexed"], 2)

        self.assertEqual(len(self.af.find("Markdown-Notiz")), 1)
        hits = self.af.find("Reine Textnotiz")
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["meta"]["source_ref"]["kind"], "markdown_dir")
        self.assertTrue(hits[0]["name"].endswith("notes.txt"))
        self.assertEqual(self.af.find("ignored"), [])

    def test_legacy_single_glob_still_works(self):
        # Backward compatibility: the older singular `glob` key (one
        # pattern) must keep working unchanged for existing configs.
        mem_dir = self.foreign / "memory"
        mem_dir.mkdir(parents=True, exist_ok=True)
        (mem_dir / "notes.md").write_text("Markdown-Notiz.", encoding="utf-8")
        (mem_dir / "notes.txt").write_text("Reine Textnotiz.", encoding="utf-8")

        self.af.observe_source_add(
            "mem", "markdown_dir", path=str(mem_dir), glob="*.txt")
        result = self.af.observe_sources("mem")
        self.assertEqual(result["mem"]["indexed"], 1)
        self.assertEqual(len(self.af.find("Reine Textnotiz")), 1)
        self.assertEqual(self.af.find("Markdown-Notiz"), [])

    def test_extra_tags_are_appended_for_downstream_filtering(self):
        # A consumer that bypasses recall() (going straight at the DB)
        # cannot rely on `type` alone -- observe-sources always set it to
        # 'observed'. extra_tags lets a source mark its items so such a
        # consumer can tell a rule file apart from a rotating registry.
        mem_dir = self.foreign / "memory"
        mem_dir.mkdir(parents=True, exist_ok=True)
        (mem_dir / "notes.md").write_text("Registrierte Notiz.", encoding="utf-8")

        self.af.observe_source_add(
            "mem", "markdown_dir", path=str(mem_dir), extra_tags=["register-log"])
        result = self.af.observe_sources("mem")
        self.assertEqual(result["mem"]["indexed"], 1)

        hits = self.af.find("Registrierte Notiz")
        self.assertEqual(len(hits), 1)
        tags = hits[0]["tags"]
        self.assertIn("markdown_dir", tags)
        self.assertIn("mem", tags)
        self.assertIn("register-log", tags)

    def test_extra_tags_accepts_a_single_string(self):
        # Config convenience: one tag doesn't need list syntax.
        mem_dir = self.foreign / "memory"
        mem_dir.mkdir(parents=True, exist_ok=True)
        (mem_dir / "notes.md").write_text("Eine Notiz.", encoding="utf-8")

        self.af.observe_source_add(
            "mem", "markdown_dir", path=str(mem_dir), extra_tags="policy")
        result = self.af.observe_sources("mem")
        self.assertEqual(result["mem"]["indexed"], 1)
        self.assertIn("policy", self.af.find("Eine Notiz")[0]["tags"])

    def test_no_extra_tags_leaves_tags_unchanged(self):
        # Backward compatibility: omitting extra_tags must not append a
        # trailing comma or otherwise change the existing tag format.
        mem_dir = self.foreign / "memory"
        mem_dir.mkdir(parents=True, exist_ok=True)
        (mem_dir / "notes.md").write_text("Unveraenderte Notiz.", encoding="utf-8")

        self.af.observe_source_add("mem", "markdown_dir", path=str(mem_dir))
        self.af.observe_sources("mem")
        self.assertEqual(self.af.find("Unveraenderte Notiz")[0]["tags"], "markdown_dir,mem")


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

    def test_content_list_indexes_every_named_column(self):
        # A USMC/BACH-style lesson splits its meaning over two text
        # columns; picking only one would leave the other unsearchable.
        db_path = self.foreign / "lessons.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute(
            "CREATE TABLE lessons (id INTEGER PRIMARY KEY, title TEXT, "
            "problem TEXT, solution TEXT)")
        conn.execute(
            "INSERT INTO lessons VALUES (?, ?, ?, ?)",
            (1, "OneDrive-Sperre", "Verschieben scheitert an Cloud-Lock",
             "FileCommander statt mv benutzen"),
        )
        conn.execute(  # NULL/empty column must not produce blank padding
            "INSERT INTO lessons VALUES (?, ?, ?, ?)",
            (2, "Nur-Problem", "Encoding kippt auf cp1252", None),
        )
        conn.commit()
        conn.close()

        self.af.observe_source_add(
            "usmc-lessons", "sqlite_table", db_path=str(db_path),
            table="lessons",
            columns={"id": "id", "name": "title",
                     "content": ["problem", "solution"]},
        )
        result = self.af.observe_sources("usmc-lessons")
        self.assertEqual(result["usmc-lessons"]["indexed"], 2)

        # Both halves of row 1 are findable, and land in the same entry.
        by_problem = self.af.find("Cloud-Lock")
        by_solution = self.af.find("FileCommander")
        self.assertEqual(len(by_problem), 1)
        self.assertEqual(len(by_solution), 1)
        self.assertEqual(by_problem[0]["name"], by_solution[0]["name"])
        self.assertIn("Verschieben scheitert", by_problem[0]["content"])
        self.assertIn("statt mv benutzen", by_problem[0]["content"])

        self.assertEqual(self.af.find("cp1252")[0]["content"].count("\n\n"), 1)

    def test_content_list_refuses_unknown_column(self):
        db_path = self._make_foreign_db()
        self.af.observe_source_add(
            "bad-cols", "sqlite_table", db_path=str(db_path), table="tasks",
            columns={"id": "id", "content": ["body", "does_not_exist"]},
        )
        result = self.af.observe_sources("bad-cols")
        self.assertEqual(result["bad-cols"]["indexed"], 0)

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

    def test_default_role_indexes_archive_without_role_field(self):
        # A bare prompt history (Kimi's user-history format): every line
        # is a user turn, no role field anywhere. Without default_role
        # the roles filter would drop every single line.
        jsonl_path = self.foreign / "prompt-history.jsonl"
        self._write_jsonl(jsonl_path, [
            {"content": "Bitte pruefe den Migrationsplan."},
            {"content": "Und danach den Rollback-Pfad."},
        ])

        self.af.observe_source_add(
            "prompt-history", "agent_transcripts", path=str(jsonl_path),
            format="generic", text_field="content", default_role="user",
        )
        result = self.af.observe_sources("prompt-history")
        self.assertEqual(result["prompt-history"]["indexed"], 2)

        hits = self.af.find("Rollback-Pfad")
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["meta"]["source_ref"]["role"], "user")

    def test_missing_role_without_default_indexes_nothing(self):
        # Same file, no default_role: the guard stays as before -- a line
        # with no resolvable role is skipped rather than silently
        # indexed under an invented role.
        jsonl_path = self.foreign / "roleless.jsonl"
        self._write_jsonl(jsonl_path, [{"content": "Text ohne Rolle."}])

        self.af.observe_source_add(
            "roleless", "agent_transcripts", path=str(jsonl_path),
            format="generic", text_field="content",
        )
        result = self.af.observe_sources("roleless")
        self.assertEqual(result["roleless"]["indexed"], 0)
        self.assertEqual(self.af.find("Rolle"), [])
    def test_gemini_antigravity_format_preset(self):
        jsonl_path = self.foreign / "transcript.jsonl"
        self._write_jsonl(jsonl_path, [
            {"step_index": 0, "source": "USER_EXPLICIT", "type": "USER_INPUT",
             "content": "Bitte Analyse für Datenbank erstellen.", "created_at": "2026-08-01T10:00:00Z"},
            {"step_index": 1, "source": "MODEL", "type": "PLANNER_RESPONSE",
             "content": "Ich habe die Datenbank analysiert und bereinigt.", "created_at": "2026-08-01T10:00:05Z"},
        ])

        self.af.observe_source_add(
            "gemini-transcripts", "agent_transcripts", path=str(jsonl_path),
            format="gemini_antigravity",
        )
        result = self.af.observe_sources("gemini-transcripts")
        self.assertEqual(result["gemini-transcripts"]["indexed"], 2)
        hits = self.af.find("Datenbank")
        self.assertEqual(len(hits), 2)
        roles = {h["meta"]["source_ref"]["role"] for h in hits}
        self.assertEqual(roles, {"user", "assistant"})

    def test_gemini_antigravity_skips_tool_action_steps(self):
        """source=MODEL alone is not an assistant turn.

        VIEW_FILE/RUN_COMMAND/LIST_DIRECTORY steps carry file dumps and
        command output, not prose -- indexing them was pulling tool
        noise into the index under role 'assistant'.
        """
        jsonl_path = self.foreign / "transcript.jsonl"
        self._write_jsonl(jsonl_path, [
            {"step_index": 0, "source": "USER_EXPLICIT", "type": "USER_INPUT",
             "content": "Bitte Kennzahl pruefen."},
            {"step_index": 1, "source": "MODEL", "type": "PLANNER_RESPONSE",
             "content": "Ich pruefe die Kennzahl jetzt."},
            {"step_index": 2, "source": "MODEL", "type": "VIEW_FILE",
             "content": "File Path: c:/tmp/kennzahl.txt Total Lines: 162"},
            {"step_index": 3, "source": "MODEL", "type": "RUN_COMMAND",
             "content": "Status: RUNNING | Kennzahl-Log"},
        ])

        self.af.observe_source_add(
            "gemini-noise", "agent_transcripts", path=str(jsonl_path),
            format="gemini_antigravity",
        )
        result = self.af.observe_sources("gemini-noise")
        self.assertEqual(result["gemini-noise"]["indexed"], 2)
        hits = self.af.find("Kennzahl")
        self.assertEqual(len(hits), 2)

    def test_codex_format_preset(self):
        """Codex: flat history plus the clean event_msg channel.

        response_item/message is deliberately NOT indexed -- its
        assistant turns duplicate agent_message and its user turns
        carry injected AGENTS.md/skill boilerplate.
        """
        history_path = self.foreign / "codex-history.jsonl"
        session_path = self.foreign / "rollout-session.jsonl"

        self._write_jsonl(history_path, [
            {"session_id": "codex-s1", "ts": 1780794418,
             "text": "Teste bitte den Refactoring-Schritt."}
        ])
        self._write_jsonl(session_path, [
            {"type": "event_msg", "payload": {
                "type": "user_message", "message": "Starte das Refactoring."}},
            {"type": "event_msg", "payload": {
                "type": "agent_message",
                "message": "Refactoring wurde ausgefuehrt.", "phase": "commentary"}},
            # Duplicate of the agent_message above -- must be skipped.
            {"type": "response_item", "payload": {
                "type": "message", "role": "assistant",
                "content": [{"type": "output_text",
                             "text": "Refactoring wurde ausgefuehrt."}]}},
            # Injected system prompt material -- must be skipped.
            {"type": "response_item", "payload": {
                "type": "message", "role": "developer",
                "content": [{"type": "input_text",
                             "text": "# AGENTS.md Refactoring instructions"}]}},
            {"type": "response_item", "payload": {"type": "reasoning"}},
            {"type": "event_msg", "payload": {"type": "token_count"}},
            # Sub-agent tool traffic wrapped in an agent_message -- a
            # verbatim tool call and its output, not prose.
            {"type": "event_msg", "payload": {
                "type": "agent_message",
                "message": "[external_agent_tool_call: Read]\n"
                           "file: C:/tmp/Refactoring.py"}},
            {"type": "event_msg", "payload": {
                "type": "agent_message",
                "message": "[external_agent_tool_result]\n"
                           "Refactoring DeprecationWarning ..."}},
        ])

        self.af.observe_source_add(
            "codex-history", "agent_transcripts",
            path=str(self.foreign / "*codex*.jsonl"), format="codex",
        )
        self.af.observe_source_add(
            "codex-sessions", "agent_transcripts",
            path=str(self.foreign / "*rollout*.jsonl"), format="codex",
        )
        res1 = self.af.observe_sources("codex-history")
        res2 = self.af.observe_sources("codex-sessions")
        self.assertEqual(res1["codex-history"]["indexed"], 1)
        self.assertEqual(res2["codex-sessions"]["indexed"], 2)
        # 1 history + 1 user_message + 1 agent_message, no duplicate.
        self.assertEqual(len(self.af.find("Refactoring")), 3)

    def test_kimi_format_preset(self):
        """Kimi wire.jsonl is an event stream, not a message list."""
        wire_path = self.foreign / "wire.jsonl"
        self._write_jsonl(wire_path, [
            {"type": "context.append_message", "message": {
                "role": "user",
                "content": [{"type": "text", "text": "Starte Integrationstest."}],
                "origin": {"kind": "user"}}},
            {"type": "context.append_loop_event", "event": {
                "type": "content.part",
                "part": {"type": "text", "text": "Integrationstest laeuft."}}},
            # Internal reasoning -- must be skipped.
            {"type": "context.append_loop_event", "event": {
                "type": "content.part",
                "part": {"type": "think", "think": "Integrationstest ueberlegen."}}},
            # Tool traffic -- must be skipped.
            {"type": "context.append_loop_event", "event": {
                "type": "tool.result", "result": "Integrationstest output"}},
            # Injected reminder wearing role 'user' -- must be skipped.
            {"type": "context.append_message", "message": {
                "role": "user",
                "content": [{"type": "text", "text": "Integrationstest Reminder."}],
                "origin": {"kind": "injection/todo_list_reminder"}}},
            {"type": "usage.record", "usage": {"tokens": 5}},
        ])

        self.af.observe_source_add(
            "kimi-transcripts", "agent_transcripts", path=str(wire_path),
            format="kimi",
        )
        result = self.af.observe_sources("kimi-transcripts")
        self.assertEqual(result["kimi-transcripts"]["indexed"], 2)
        hits = self.af.find("Integrationstest")
        self.assertEqual(len(hits), 2)
        self.assertEqual(
            {h["meta"]["source_ref"]["role"] for h in hits},
            {"user", "assistant"})

    def test_multi_path_source_with_name_key_survives_a_file_move(self):
        """A rotated transcript must not be indexed a second time.

        Codex moves finished rollouts from sessions/ to
        archived_sessions/. With one source spanning both directories
        and key_by='name', the moved file keeps its identity: same
        entry name, offset preserved, nothing re-indexed.
        """
        live = self.foreign / "sessions"
        archive = self.foreign / "archived_sessions"
        live.mkdir(parents=True, exist_ok=True)
        archive.mkdir(parents=True, exist_ok=True)
        rollout = live / "rollout-2026-08-02-abc.jsonl"
        self._write_jsonl(rollout, [
            {"type": "event_msg", "payload": {
                "type": "user_message", "message": "Wanderfall pruefen."}},
        ])

        self.af.observe_source_add(
            "codex-all", "agent_transcripts",
            path=[str(live / "*.jsonl"), str(archive / "*.jsonl")],
            format="codex", key_by="name",
        )
        first = self.af.observe_sources("codex-all")
        self.assertEqual(first["codex-all"]["indexed"], 1)
        names_before = {h["name"] for h in self.af.find("Wanderfall")}

        # Rotate the file into the archive directory.
        rollout.rename(archive / rollout.name)

        second = self.af.observe_sources("codex-all")
        self.assertEqual(second["codex-all"]["indexed"], 0)
        hits = self.af.find("Wanderfall")
        self.assertEqual(len(hits), 1)
        self.assertEqual({h["name"] for h in hits}, names_before)


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


class TestReplicaSourceTemplates(unittest.TestCase):
    """OP-MEMSYNC Teil B3: config builders for cross-host
    ``.republica`` sources. Pure functions, no Gardener instance
    needed -- see TestReplicaSourceLifecycle below for the wired-up
    behaviour (disabled / absent-directory / real-snapshot).
    """

    def test_refuses_to_build_a_config_for_the_current_host(self):
        import sources
        real_host = sources._current_host()
        self.assertTrue(real_host, "no hostname resolvable in this environment")
        with self.assertRaises(ValueError):
            sources.usmc_replica_source_configs(real_host)
        with self.assertRaises(ValueError):
            sources.gardener_replica_source_config(real_host)

    def test_refuses_an_empty_host(self):
        import sources
        with self.assertRaises(ValueError):
            sources.usmc_replica_source_configs("")
        with self.assertRaises(ValueError):
            sources.gardener_replica_source_config("")

    def test_usmc_template_covers_all_four_tables_disabled_by_default(self):
        import sources
        cfgs = sources.usmc_replica_source_configs(
            "OTHER-HOST", replicas_root=r"C:\fake\.republica")
        self.assertEqual(set(cfgs), {
            "replica-other-host-usmc-facts",
            "replica-other-host-usmc-lessons",
            "replica-other-host-usmc-working",
            "replica-other-host-usmc-sessions",
        })
        for source_id, cfg in cfgs.items():
            self.assertFalse(cfg["enabled"], source_id)
            self.assertTrue(
                cfg["db_path"].replace("/", "\\").endswith("OTHER-HOST\\usmc.sqlite"),
                cfg["db_path"])
        # Lessons split across two columns, matching the local usmc-lessons
        # source (see CHANGELOG 2026-08-01 / commit 2c721cf).
        self.assertEqual(
            cfgs["replica-other-host-usmc-lessons"]["columns"]["content"],
            ["problem", "solution"])

    def test_gardener_template_is_disabled_by_default(self):
        import sources
        cfgs = sources.gardener_replica_source_config(
            "OTHER-HOST", replicas_root=r"C:\fake\.republica")
        self.assertEqual(list(cfgs), ["replica-other-host-gardener"])
        cfg = cfgs["replica-other-host-gardener"]
        self.assertFalse(cfg["enabled"])
        self.assertEqual(cfg["table"], "everything")


class TestReplicaSourceLifecycle(ObserveSourceTestCase):
    """A replica source must never raise, whether it is (a) registered but
    disabled, or (b) armed while the transit-sync snapshot doesn't exist
    on disk yet -- exactly the "deaktiviert ODER sauber uebersprungen"
    requirement. (c) proves the template's column mapping is actually
    correct once a real snapshot does exist, not just that it degrades
    safely when absent.
    """

    def test_disabled_replica_is_a_clean_no_op(self):
        import sources
        cfgs = sources.usmc_replica_source_configs(
            "OTHER-HOST", replicas_root=str(self.foreign / ".republica"))
        for source_id, cfg in cfgs.items():
            self.af.observe_source_add(source_id, "sqlite_table", **cfg)
        result = self.af.observe_sources()
        for source_id in cfgs:
            self.assertEqual(result[source_id], {"skipped_disabled": True})

    def test_enabled_replica_without_a_directory_yet_is_still_a_clean_no_op(self):
        # Armed (enabled=True) but the transit-sync hasn't produced this
        # host's snapshot yet -- must behave exactly like any other
        # sqlite_table source pointed at a file that doesn't exist yet
        # (scan_sqlite_table's own db_file.is_file() guard).
        import sources
        cfgs = sources.usmc_replica_source_configs(
            "OTHER-HOST", replicas_root=str(self.foreign / ".republica"))
        for source_id, cfg in cfgs.items():
            self.af.observe_source_add(
                source_id, "sqlite_table", **{**cfg, "enabled": True})
        result = self.af.observe_sources()
        for source_id in cfgs:
            self.assertEqual(
                result[source_id],
                {"kind": "sqlite_table", "indexed": 0, "skipped": 0})
        self.assertEqual(self.af.find("irrelevant"), [])

    def test_armed_replica_against_a_real_foreign_snapshot_is_findable(self):
        import sources
        replicas_root = self.foreign / ".republica"
        db_path = Path(sources._replica_db_path(
            "OTHER-HOST", "usmc.sqlite", str(replicas_root)))
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(db_path))
        conn.execute(
            "CREATE TABLE usmc_lessons (id INTEGER PRIMARY KEY, category TEXT, "
            "severity TEXT, title TEXT, problem TEXT, solution TEXT, "
            "agent_id TEXT, is_active INTEGER, confidence REAL, "
            "times_shown INTEGER, created_at TEXT, updated_at TEXT)")
        conn.execute(
            "INSERT INTO usmc_lessons (id, category, title, problem, solution) "
            "VALUES (1, 'sync', 'Replica-Beispiel', "
            "'Snapshot fehlte auf dem Zielrechner', "
            "'Transit-Sync einmal laufen lassen')")
        conn.commit()
        conn.close()

        cfgs = sources.usmc_replica_source_configs(
            "OTHER-HOST", replicas_root=str(replicas_root))
        lessons_cfg = cfgs["replica-other-host-usmc-lessons"]
        self.af.observe_source_add(
            "replica-other-host-usmc-lessons", "sqlite_table",
            **{**lessons_cfg, "enabled": True})
        result = self.af.observe_sources("replica-other-host-usmc-lessons")
        self.assertEqual(
            result["replica-other-host-usmc-lessons"]["indexed"], 1)

        hits = self.af.find("Transit-Sync einmal laufen lassen")
        self.assertEqual(len(hits), 1)
        self.assertIn("Snapshot fehlte", hits[0]["content"])


class TestNeverIndexList(ObserveSourceTestCase):
    """A source config must not be able to pull secrets into the index.

    The block list is enforced inside the adapters, so an over-broad or
    mistyped glob cannot defeat it.
    """

    def test_is_excluded_matches_segments_filenames_and_suffixes(self):
        import sources
        for bad in (
            r"C:\_Local_DEV\CREDENTIALS\hetzner\webhosting_s.md",
            r"C:\_Local_DEV\credentials\x.txt",          # case-insensitive
            "/home/u/.ssh/config",
            "/home/u/.gardener/user.db",                 # never index itself
            "/proj/node_modules/pkg/readme.md",
            "/proj/.git/COMMIT_EDITMSG",
            "/home/u/.npmrc",
            "/home/u/project/.env",
            "/home/u/.codex/auth.json",
            "/home/u/certs/server.pem",
            "/home/u/keys/deploy.key",
        ):
            with self.subTest(path=bad):
                self.assertTrue(sources.is_excluded(bad), bad)

        for good in (
            "/home/u/notes/credentials-howto.md",        # sibling name
            "/home/u/.claude/projects/p/memory/MEMORY.md",
            "/home/u/docs/environment.md",
            "/home/u/.gemini/GEMINI.md",
        ):
            with self.subTest(path=good):
                self.assertFalse(sources.is_excluded(good), good)

    def test_markdown_dir_skips_excluded_files_and_dirs(self):
        root = self.foreign / "mixed"
        (root / "node_modules" / "pkg").mkdir(parents=True, exist_ok=True)
        root.mkdir(parents=True, exist_ok=True)
        (root / "notiz.md").write_text("Merksatz oeffentlich", encoding="utf-8")
        (root / "auth.json").write_text("Merksatz geheim", encoding="utf-8")
        (root / ".npmrc").write_text("Merksatz geheim", encoding="utf-8")
        (root / "node_modules" / "pkg" / "readme.md").write_text(
            "Merksatz geheim", encoding="utf-8")

        self.af.observe_source_add(
            "mixed", "markdown_dir", path=str(root),
            patterns=["**/*.md", "*.json", ".npmrc"])
        result = self.af.observe_sources("mixed")

        self.assertEqual(result["mixed"]["indexed"], 1)
        hits = self.af.find("Merksatz")
        self.assertEqual(len(hits), 1)
        self.assertIn("oeffentlich", hits[0]["content"])

    def test_agent_transcripts_skips_excluded_paths(self):
        secret_dir = self.foreign / "CREDENTIALS"
        secret_dir.mkdir(parents=True, exist_ok=True)
        ok_dir = self.foreign / "ok"
        ok_dir.mkdir(parents=True, exist_ok=True)

        def write(path, text):
            path.write_text(
                json.dumps({"type": "event_msg",
                            "payload": {"type": "user_message",
                                        "message": text}}) + "\n",
                encoding="utf-8")

        write(secret_dir / "leak.jsonl", "Kennwort Notfallzugang")
        write(ok_dir / "fine.jsonl", "Kennwort Thema besprochen")

        self.af.observe_source_add(
            "wide", "agent_transcripts",
            path=str(self.foreign / "**" / "*.jsonl"), format="codex")
        result = self.af.observe_sources("wide")

        self.assertEqual(result["wide"]["indexed"], 1)
        hits = self.af.find("Kennwort")
        self.assertEqual(len(hits), 1)
        self.assertIn("besprochen", hits[0]["content"])

    def test_gardener_home_walk_uses_the_same_list(self):
        """observe()/sync() derive their skip list from sources.py."""
        import gardener as gardener_mod
        for segment in ("credentials", ".ssh", "node_modules", ".git",
                        ".gardener", "__pycache__"):
            self.assertIn(segment, gardener_mod.INTERNAL_SKIP_PREFIXES)
        self.assertTrue(gardener_mod.Gardener._is_internal("CREDENTIALS/x.md"))
        self.assertTrue(gardener_mod.Gardener._is_internal("projekt/.npmrc"))
        self.assertFalse(gardener_mod.Gardener._is_internal("notizen/plan.md"))


class TestSecretRedaction(ObserveSourceTestCase):
    """Credential signatures are masked on the way into the index.

    All token bodies below are FAKE -- shaped like the real formats
    (right prefix, right length, right character class, right literal
    markers) so the patterns are exercised, but not valid credentials.
    """

    # (family, sample containing a fake token)
    POSITIVES = [
        ("anthropic-api-key", "sk-ant-api03-" + "A1b2C3d4_-" * 9 + "xyz" + "AA"),
        ("openai-api-key", "sk-" + "a" * 20 + "T3BlbkFJ" + "b" * 20),
        ("openai-project-key",
         "sk-proj-" + "c" * 30 + "T3BlbkFJ" + "d" * 30),
        ("github-token", "ghp_" + "e" * 36),
        ("github-fine-grained-pat",
         "github_pat_" + "f" * 22 + "_" + "g" * 59),
        ("aws-access-key-id", "AKIA" + "ABCDEFGH23456789"),
        ("slack-token", "xoxb-" + "1234567890-9876543210-abcdefgh"),
        ("google-api-key", "AIza" + "h" * 35),
        ("gitlab-pat", "glpat-" + "i" * 20),
        ("npm-token", "npm_" + "j" * 36),
        ("http-bearer", "Authorization: Bearer " + "k" * 30),
        ("private-key-block",
         "-----BEGIN RSA PRIVATE KEY-----\n" + "l" * 64
         + "\n-----END RSA PRIVATE KEY-----"),
    ]

    # Harmless look-alikes that must survive untouched.
    NEGATIVES = [
        "ghpx_abcdefghijklmnopqrstuvwxyz0123456789",   # 4 letters before _
        "Aski",
        "AKIAA",                                        # far too short
        "skalar und sk- allein",
        "Der Bearer des Rings",                         # no header, no body
        "AIzaX",                                        # too short
        "npm_install",                                  # too short
        "glpat-kurz",
    ]

    def _write_jsonl(self, path, lines):
        path.write_text(
            "\n".join(json.dumps(x, ensure_ascii=False) for x in lines) + "\n",
            encoding="utf-8")

    def test_positives_are_masked_and_family_reported(self):
        import sources
        for family, sample in self.POSITIVES:
            with self.subTest(family=family):
                out, families = sources.redact_secrets(
                    f"vorher {sample} nachher")
                self.assertIn(sources.REDACTION_MARKER, out)
                self.assertIn(family, families)
                # Surrounding prose survives; the secret body does not.
                self.assertIn("vorher", out)
                self.assertIn("nachher", out)
                # The high-entropy run inside the sample must be gone.
                secret_run = max(re.findall(r"[A-Za-z0-9_-]{12,}", sample),
                                 key=len)
                self.assertNotIn(secret_run, out)

    def test_negatives_are_left_alone(self):
        import sources
        for sample in self.NEGATIVES:
            with self.subTest(sample=sample):
                out, families = sources.redact_secrets(sample)
                self.assertEqual(out, sample)
                self.assertEqual(families, ())

    def test_prefix_stays_readable_so_the_family_is_recognisable(self):
        import sources
        out, _ = sources.redact_secrets("ghp_" + "e" * 36)
        self.assertTrue(out.startswith("ghp_"))
        self.assertEqual(out, "ghp_" + sources.REDACTION_MARKER)

    def test_redaction_reaches_the_index_through_every_adapter(self):
        """scan() is the gate, so markdown and transcripts are both covered."""
        token = "ghp_" + "e" * 36
        md_dir = self.foreign / "docs"
        md_dir.mkdir(parents=True, exist_ok=True)
        (md_dir / "notiz.md").write_text(
            f"Zugang Merkposten {token} Ende", encoding="utf-8")
        jsonl = self.foreign / "chat.jsonl"
        self._write_jsonl(jsonl, [
            {"type": "event_msg", "payload": {
                "type": "user_message",
                "message": f"Merkposten Schluessel {token}"}},
        ])

        self.af.observe_source_add("docs", "markdown_dir", path=str(md_dir))
        self.af.observe_source_add("chat", "agent_transcripts",
                                   path=str(jsonl), format="codex")
        self.af.observe_sources("docs")
        self.af.observe_sources("chat")

        hits = self.af.find("Merkposten")
        self.assertEqual(len(hits), 2)
        for hit in hits:
            self.assertNotIn("e" * 36, hit["content"])
            self.assertIn("ghp_***REDACTED***", hit["content"])

    def test_clean_text_is_untouched_and_reports_nothing(self):
        import sources
        text = "Ein ganz gewoehnlicher Satz ueber Schluessel und Tokens."
        out, families = sources.redact_secrets(text)
        self.assertEqual(out, text)
        self.assertEqual(families, ())


class TestCloudCredentialAlert(ObserveSourceTestCase):
    """A token inside a cloud-synced document is its own security finding."""

    def _point_alert_at(self, root, alert_file):
        self.gardener.CLOUD_ALERT_ROOT = root
        self.gardener.CLOUD_ALERT_FILE = alert_file

    def test_alert_written_for_cloud_path_and_is_idempotent(self):
        cloud = self.foreign / "CloudDrive"
        cloud.mkdir(parents=True, exist_ok=True)
        alert = self.foreign / "alert.md"
        self._point_alert_at(cloud, alert)

        (cloud / "notiz.md").write_text(
            "Zugangsdaten Merkposten ghp_" + "e" * 36, encoding="utf-8")
        self.af.observe_source_add("cloud", "markdown_dir", path=str(cloud))

        stats = self.af.observe_sources("cloud")
        self.assertEqual(stats["cloud"]["cloud_alerts"], 1)
        self.assertEqual(stats["cloud"]["cloud_alerts_new"], 1)

        body = alert.read_text(encoding="utf-8")
        self.assertIn("github-token", body)
        self.assertIn("notiz.md", body)
        # Never the value, never the surrounding text.
        self.assertNotIn("e" * 36, body)
        self.assertNotIn("Merkposten", body)

        # Second run over the same finding must not append a duplicate.
        (cloud / "notiz.md").write_text(
            "Zugangsdaten Merkposten ghp_" + "e" * 36 + " (ergaenzt)",
            encoding="utf-8")
        stats2 = self.af.observe_sources("cloud")
        self.assertEqual(stats2["cloud"]["cloud_alerts_new"], 0)
        self.assertEqual(alert.read_text(encoding="utf-8").count("github-token"), 1)

    def test_local_path_finding_raises_no_alert(self):
        """A token in a local transcript never left the machine."""
        cloud = self.foreign / "CloudDrive"
        cloud.mkdir(parents=True, exist_ok=True)
        alert = self.foreign / "alert.md"
        self._point_alert_at(cloud, alert)

        local = self.foreign / "local"
        local.mkdir(parents=True, exist_ok=True)
        (local / "notiz.md").write_text(
            "Merkposten ghp_" + "e" * 36, encoding="utf-8")
        self.af.observe_source_add("local", "markdown_dir", path=str(local))

        stats = self.af.observe_sources("local")
        self.assertNotIn("cloud_alerts", stats["local"])
        self.assertFalse(alert.exists())
        # Redaction still happened -- only the ALERT is path-scoped.
        hits = self.af.find("Merkposten")
        self.assertEqual(len(hits), 1)
        self.assertNotIn("e" * 36, hits[0]["content"])


class TestZipTranscriptSource(ObserveSourceTestCase):
    """Archived transcripts are read streaming, never unpacked to disk."""

    def _make_zip(self, path, members):
        import zipfile
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
            for name, lines in members.items():
                zf.writestr(name, "\n".join(json.dumps(x) for x in lines) + "\n")

    def test_indexes_jsonl_members_streaming(self):
        zpath = self.foreign / "brain_history.zip"
        self._make_zip(zpath, {
            "abc-123/.system_generated/logs/transcript.jsonl": [
                {"step_index": 0, "source": "USER_EXPLICIT",
                 "type": "USER_INPUT", "content": "Archivfrage stellen."},
                {"step_index": 1, "source": "MODEL",
                 "type": "PLANNER_RESPONSE",
                 "content": "Archivfrage beantwortet."},
                # Tool step -- must be skipped like everywhere else.
                {"step_index": 2, "source": "MODEL", "type": "RUN_COMMAND",
                 "content": "Archivfrage Kommando-Output"},
            ],
            "abc-123/task.md": [],   # non-JSONL member, must be ignored
        })

        self.af.observe_source_add(
            "gemini-archive", "agent_transcripts", path=str(zpath),
            format="gemini_antigravity", zip_inner="*/logs/transcript.jsonl")
        res = self.af.observe_sources("gemini-archive")
        self.assertEqual(res["gemini-archive"]["indexed"], 2)

        hits = self.af.find("Archivfrage")
        self.assertEqual(len(hits), 2)
        ref = hits[0]["meta"]["source_ref"]["path"]
        self.assertIn("brain_history.zip!", ref)
        # Nothing was unpacked next to the archive.
        self.assertEqual(
            sorted(p.name for p in self.foreign.iterdir()),
            ["brain_history.zip"])

    def test_unchanged_archive_is_skipped_whole(self):
        zpath = self.foreign / "arch.zip"
        self._make_zip(zpath, {
            "s1/logs/transcript.jsonl": [
                {"source": "USER_EXPLICIT", "type": "USER_INPUT",
                 "content": "Wiederholungsfall."}],
        })
        self.af.observe_source_add(
            "arch", "agent_transcripts", path=str(zpath),
            format="gemini_antigravity", zip_inner="*/logs/transcript.jsonl")

        first = self.af.observe_sources("arch")
        self.assertEqual(first["arch"]["indexed"], 1)
        second = self.af.observe_sources("arch")
        # Neither indexed nor even re-read: the archive is skipped whole.
        self.assertEqual(second["arch"]["indexed"], 0)
        self.assertEqual(second["arch"]["skipped"], 0)
        self.assertEqual(len(self.af.find("Wiederholungsfall")), 1)

    def test_archive_without_matching_members_yields_nothing(self):
        """Antigravity's newer archives hold SQLite/protobuf, no JSONL."""
        zpath = self.foreign / "newformat.zip"
        import zipfile
        with zipfile.ZipFile(zpath, "w") as zf:
            zf.writestr("conversations/abc.db", b"SQLite format 3\x00rest")
            zf.writestr("conversations/abc.pb", b"\x08\x0e \x03*\x9a\x01")

        self.af.observe_source_add(
            "newformat", "agent_transcripts", path=str(zpath),
            format="gemini_antigravity", zip_inner="*/logs/transcript.jsonl")
        res = self.af.observe_sources("newformat")
        self.assertEqual(res["newformat"]["indexed"], 0)
        self.assertNotIn("error", res["newformat"])

    def test_redaction_applies_inside_archives_too(self):
        zpath = self.foreign / "secret.zip"
        token = "ghp_" + "e" * 36
        self._make_zip(zpath, {
            "s1/logs/transcript.jsonl": [
                {"source": "USER_EXPLICIT", "type": "USER_INPUT",
                 "content": f"Archivgeheimnis {token}"}],
        })
        self.af.observe_source_add(
            "zsec", "agent_transcripts", path=str(zpath),
            format="gemini_antigravity", zip_inner="*/logs/transcript.jsonl")
        self.af.observe_sources("zsec")

        hits = self.af.find("Archivgeheimnis")
        self.assertEqual(len(hits), 1)
        self.assertNotIn("e" * 36, hits[0]["content"])
        self.assertIn("ghp_***REDACTED***", hits[0]["content"])


if __name__ == "__main__":
    unittest.main()
