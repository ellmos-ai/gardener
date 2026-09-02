<img src="assets/banner.png" width="100%" alt="Gardener banner">

<p align="center">
  <img src="logo.jpg" alt="gardener logo" width="300">
</p>

# gardener — Database-Based OS for LLMs

[![CI](https://github.com/ellmos-ai/gardener/actions/workflows/ci.yml/badge.svg)](https://github.com/ellmos-ai/gardener/actions/workflows/ci.yml)
[![Version: 0.4.2](https://img.shields.io/badge/version-0.4.2-blue.svg)](https://github.com/ellmos-ai/gardener)
[![Python 3.10-3.13](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![Platforms](https://img.shields.io/badge/platforms-Linux%20%7C%20Windows%20%7C%20macOS-lightgrey.svg)](https://github.com/ellmos-ai/gardener)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests: 135 passed](https://img.shields.io/badge/tests-135%20passed-brightgreen.svg)](https://github.com/ellmos-ai/gardener)
[![Privacy: Local-First](https://img.shields.io/badge/privacy-Local--First%20%7C%20Zero--Egress-brightgreen.svg)](SECURITY.md)
[![Security Policy](https://img.shields.io/badge/security-Bilingual%20Policy-informational.svg)](SECURITY.md)
[![LLM OS](https://img.shields.io/badge/LLM--OS-SQLite%20Substrate-blueviolet.svg)](https://github.com/ellmos-ai/gardener)
[![Part of ellmos-ai](https://img.shields.io/badge/ecosystem-ellmos--ai-informational.svg)](https://github.com/ellmos-ai)
[![open-bricks](https://img.shields.io/badge/umbrella-open--bricks-blue.svg)](https://github.com/open-bricks)
[![LLM-Ready](https://img.shields.io/badge/LLM--Ready-llms.txt-orange.svg)](llms.txt)

> [!NOTE]
> **LLM / Agent Integration**: Gardener provides a single-table FTS5 SQLite substrate (`gardener.db` / `user.db`) with `find`, `get`, `put`, and `run` primitives. See [`llms.txt`](llms.txt) for machine-readable context.

**🇩🇪 [Deutsche Version](README_de.md)**

> Status: Prototype (v0.4.2) | Author: Lukas Geiger + Claude

## What is Gardener?

An operating system built for LLMs. Everything lives in a searchable
database. Four functions are all you need.

## Discovery Context

Use the canonical search phrase `ellmos-ai/gardener` when you need this
repository. The short name `gardener` collides with gardening sites, Sesame
Street results, and unrelated database-operating-system research. This project
is specifically the ellmos SQLite memory substrate for LLM agents: one
`everything` table, FTS5 search, and the four primitives `find`, `get`, `put`,
and `run`.

## Quickstart

```python
from gardener import Gardener
af = Gardener()

# Search
af.find("taxes")

# Read
af.get("receipt-scanner")

# Write
af.put("note", content="Important!", type="memory", tags="todo")

# Execute
af.run("file-info", input={"path": "/path/to/file"})
```

## CLI

```bash
python gardener.py find <query>
python gardener.py gui [--port N] [--no-browser]
python gardener.py get <name>
python gardener.py put <name> <text>
python gardener.py run <name>
python gardener.py absorb <file>
python gardener.py materialize <name>
python gardener.py sync
python gardener.py observe
python gardener.py observe-source add <id> <kind> [key=value ...]
python gardener.py observe-source list
python gardener.py observe-source remove <id>
python gardener.py observe-source refresh [id]
python gardener.py status
```

The CLI help defaults to German. Set `GARDENER_LANG=en` for English help
text; unsupported languages fall back to German and English.

### Search GUI (for humans)

`python gardener.py gui` starts a small local web UI for the FTS5 search
(search box, type filter, BM25-ranked hits with match snippets, entry
detail view). Pure standard library, no dependencies; it binds to
127.0.0.1 only and is strictly read-only against both databases.

## Architecture

```mermaid
flowchart TD
    subgraph UI ["Interfaces & Control"]
        CLI["gardener CLI<br/>(find, get, put, run, gui)"]
        API["Python API<br/>(Gardener class)"]
        GUI["Search GUI<br/>(127.0.0.1 HTTP Server)"]
    end

    subgraph CORE ["Gardener Core Engine"]
        FTS["SQLite FTS5 Search<br/>(BM25 Ranking & Snippets)"]
        EXEC["Execution Engine<br/>(Materialize & Run Tool)"]
        OBS["Federated Observe Engine<br/>(Secret Redaction & Cloud Alert)"]
    end

    subgraph SUBSTRATE ["SQLite Dual-Database Substrate"]
        GDB[("gardener.db (System)<br/>• Knowledge<br/>• System Tools<br/>• Seed Blueprints")]
        UDB[("user.db (User Space)<br/>• Memory / Memos<br/>• Tasks & Priorities<br/>• Observed Foreign Data")]
    end

    subgraph SOURCES ["Federated Observe Sources (Read-Only)"]
        S1["Markdown Dirs & Rules<br/>(patterns=['*.md', '*.txt'])"]
        S2[".remember Note Files"]
        S3["Foreign SQLite DBs<br/>(mode=ro, BACH/USMC)"]
        S4["Multi-Agent Transcripts<br/>(Claude, Codex, Gemini, Kimi)"]
    end

    CLI --> CORE
    API --> CORE
    GUI --> FTS
    CORE --> SUBSTRATE
    SOURCES --> OBS --> UDB
```

```
Gardener/
  gardener.py          # Core: Gardener class + CLI
  sources.py           # Read-only adapters for observed foreign sources
  seed.py              # Initial system knowledge
  i18n.py              # CLI string lookup
  locales/             # Translation catalogue for CLI strings
  tests/               # unittest suite (also runnable with pytest)
  KONZEPT.md           # Design documentation (German)
  README.md            # This file
  workspace/           # Materialized code for execution
  blobs/               # Storage for large files (>50MB)

Local (not in cloud, override with GARDENER_DATA):
  ~/.gardener/
    gardener.db        # System: Knowledge, tools, blueprints
    user.db            # User: Memory, tasks, personal data
    blobs/             # Large files

User directory (cloud ok, override with GARDENER_HOME):
  ~/gardener/
    .absorber/         # Files here → automatically absorbed into DB
    .output/           # Materialized files appear here
    documents/         # Observed files (LLM reads along)
```

## Data Model

One table for (almost) everything:

| Type | Description | Target DB |
|------|-------------|-----------|
| knowledge | Knowledge, docs, rules | gardener.db |
| tool | Executable code | gardener.db |
| memory | Memories, notes | user.db |
| task | Tasks | user.db |
| document | Absorbed files | user.db |
| observed | Observed files | user.db |
| config | Configuration | user.db |
| export | Marked for materialization | user.db |

## Memory (No Separate Memory System!)

Instead of 5 tables: everything in `everything` with types and meta fields.
The FTS5 search IS the associative memory.

```python
af.memo("Quick note")                    # Working memory (decays fast)
af.lesson("Title", "Insight")            # Best practice (barely decays)
af.session_end("Summary")               # Session report
af.recall("taxes")                       # Remember (searches + boosts weight)
af.consolidate()                         # Sleep: Decay + Forget
```

```bash
gardener memo <text>            # Note
gardener lesson <title> [text]  # Lesson
gardener recall <query>         # Remember
gardener consolidate            # Consolidate
gardener session-end <text>     # End session
```

Details: [KONZEPT.md#memory](KONZEPT.md#memory-kein-separates-gedächtnis-system-design-entscheidung)

## Tasks (No Separate System!)

Tasks are entries of type `task` in the `everything` table. **No separate
task system needed.** `find("taxes")` finds knowledge AND tasks simultaneously.

```python
af.task("taxes-2025", content="File return", priority="high", due="2026-05-31")
af.tasks()                     # All tasks
af.tasks(status="open")        # Open only
af.task_done("taxes-2025")     # Mark done
```

```bash
gardener task <name> [text]     # Create
gardener tasks [status]         # List
gardener done <name>            # Mark done
```

Details: [KONZEPT.md#tasks](KONZEPT.md#tasks-kein-separates-system-design-entscheidung)

## Three Relationships with Files

1. **Observe:** File stays in folder, LLM reads along (looking out the window)
2. **Absorb:** File gets pulled into the DB (now lives in the house)
3. **Direct edit:** LLM edits file in folder (working in front of the house)

## Transporter

```python
af.absorb("/path/to/file.pdf")     # File → DB (dematerialize)
af.materialize("file.pdf")          # DB → File (rematerialize)
```

## Cross-Source Federated Index

`observe()` watches Gardener's own home folder. **Observe-sources** extend
the same read-only principle to knowledge that lives in *other* tools:
their originals are never touched, moved, or copied in — only their text
is added to Gardener's FTS index, and every indexed entry carries a
`source_ref` in its `meta` so a search hit can be traced back to exactly
where it came from (file path, DB table + row, or transcript line).
`find()` already searches `gardener.db` + `user.db` in one query, so
observed cross-source hits show up right alongside your own entries —
no separate search call needed.

Four source kinds:

| Kind | What it indexes | Key config |
|------|------------------|------------|
| `markdown_dir` | A directory of markdown files, one entry per file. The `path` may itself be a glob spanning several directories (e.g. a per-project memory convention). `patterns` widens this to other file kinds (e.g. `.txt` notes). `exclude_patterns` drops filenames matching a pattern back out of what `patterns`/`glob` matched — e.g. a help-text directory that ships one canonical language plus several machine-translated siblings (`patterns=["*.txt"]`, `exclude_patterns=["*_en.txt", "*_es.txt"]`), where `patterns` alone cannot express "not this suffix". `extra_tags` appends static tags to every item, so a downstream consumer can tell sources apart beyond the fixed `type='observed'` (e.g. a rule file worth surfacing as a hint vs. a rotating registry that should stay searchable but not surfaced). | `path`, `patterns` (list, default `["*.md"]`), `glob` (single-pattern legacy alias), `exclude_patterns` (list), `extra_tags` (string or list) |
| `remember_files` | Small note files anywhere below a root, found via a recursive glob. | `path`, `glob` (default `**/.remember`) |
| `sqlite_table` | A single table in a foreign SQLite database, opened strictly read-only (`mode=ro`). Column names are whitelisted against the live schema before use. `content` may name several columns, joined in order — a row whose meaning is split across two text fields (a lesson's problem *and* its solution) stays fully searchable. | `db_path`, `table`, `columns` (`content` required, string or list; `id`/`name`/`tags` optional) |
| `agent_transcripts` | JSONL chat transcripts, indexed line by line, **text turns only** (tool calls/results and internal "thinking" blocks are skipped). Ships built-in field mappings for Claude Code, Gemini Antigravity, Codex, and Kimi transcript formats; any other line-based JSON transcript can be indexed via a generic dotted-path role/text mapping. `default_role` covers single-role archives that carry no role field at all, such as a bare prompt history. Large, growing files are tailed from a saved byte offset — a refresh never re-reads what it already indexed. `path` may be a **list** of globs, and `key_by="name"` keys the offset state on the filename instead of the full path — together they cover hosts that *rotate* transcripts between directories (Codex moves finished rollouts from `sessions/` to `archived_sessions/`), which would otherwise re-index every moved file under a second name. | `path` (glob or list of globs, `**` recurses), `format` (`claude_code` default, `gemini_antigravity`, `codex`, `kimi`, or `generic` with `role_field`/`text_field`/`default_role`), `key_by` (`path` default, or `name`) |

```bash
# Index this machine's Claude Code project memories
gardener observe-source add claude-memories markdown_dir path="~/.claude/projects/*/memory"

# Index .remember notes anywhere below a root
gardener observe-source add notes remember_files path="~/notes"

# Index a table in a foreign, read-only SQLite database
gardener observe-source add tasks-db sqlite_table db_path="~/.some-tool/tool.db" table=tasks

# Index Claude Code transcripts (main conversation, text turns only)
gardener observe-source add claude-transcripts agent_transcripts path="~/.claude/projects/*/**/*.jsonl"

gardener observe-source list
gardener observe-source refresh              # all sources
gardener observe-source refresh claude-memories
gardener observe-source remove claude-memories
```

```python
af.observe_source_add("claude-memories", "markdown_dir",
                       path="~/.claude/projects/*/memory")
af.observe_sources()                          # refresh all configured sources
af.find("taxes")                              # own entries + observed hits, one query

# List-valued config like `patterns` needs the Python API -- the CLI's
# plain key=value form only accepts strings, not JSON.
af.observe_source_add("mixed-notes", "markdown_dir",
                       path="~/notes", patterns=["*.md", "*.txt"])
```

The `sqlite_table` adapter's `columns` mapping lets it point at any
foreign table without Gardener knowing its schema in advance — e.g. a
task or notes table kept by a different local tool. Configuration lives
in `config.json` under `observe_sources`; nothing here is hardcoded to a
specific machine or tool.

### Indexing several coding agents at once

The four kinds are enough to put every agent on a machine into one
search, whatever each of them happens to use as storage:

```python
# Markdown memories and rule files (Codex, Gemini, ...)
af.observe_source_add("codex-memories", "markdown_dir", path="~/.codex/memories")
af.observe_source_add("gemini-rules", "markdown_dir", path="~/.gemini",
                       patterns=["GEMINI.md", "memory.md", "memory.txt"])

# A prompt history with no role field per line
af.observe_source_add("kimi-prompts", "agent_transcripts",
                       path="~/.kimi-code/user-history/*.jsonl",
                       format="generic", text_field="content",
                       default_role="user")

# Transcripts the host rotates between two directories: one source over
# both, keyed on the filename, so a moved file keeps its identity
af.observe_source_add("codex-sessions", "agent_transcripts",
                       path=["~/.codex/sessions/**/*.jsonl",
                             "~/.codex/archived_sessions/*.jsonl"],
                       format="codex", key_by="name")

# Transcripts that only exist inside a zip: read streaming, never
# unpacked. Incrementality is per archive -- an archive is finished, so
# an unchanged (mtime, size) skips the whole file unopened.
af.observe_source_add("gemini-archive", "agent_transcripts",
                       path="~/.gemini/antigravity/conversations_archive/*.zip",
                       format="gemini_antigravity",
                       zip_inner="*/.system_generated/logs/transcript.jsonl")

# A curated memory database, read-only, problem+solution in one entry
af.observe_source_add("usmc-lessons", "sqlite_table",
                       db_path="~/.usmc/usmc_memory.db", table="usmc_lessons",
                       columns={"id": "id", "name": "title",
                                "content": ["problem", "solution"],
                                "tags": "category"})
```

### Indexing a foreign system's own knowledge base

A local "OS-in-a-box" system typically keeps its documentation two ways
at once: structured rows in its own SQLite database (wiki articles,
skill definitions) and plain files on disk (README/architecture docs,
a generated per-command help directory). Both are `observed`, not
absorbed — Gardener never touches the foreign system's files or DB:

```python
# Two tables of the foreign system's own knowledge base
af.observe_source_add("bach-wiki", "sqlite_table",
                       db_path="~/.bach/bach.db", table="wiki_articles",
                       columns={"id": "path", "name": "title",
                                "content": "content", "tags": "category"})
af.observe_source_add("bach-skills", "sqlite_table",
                       db_path="~/.bach/bach.db", table="skills",
                       columns={"id": "id", "name": "name",
                                "content": ["description", "content"],
                                "tags": "category"})

# README/architecture-style docs at fixed, named paths -- non-recursive
# `patterns` naturally keeps a docs/ subfolder (e.g. docs/help/) out
# without an extra exclude
af.observe_source_add("bach-system-docs", "markdown_dir",
                       path="~/OneDrive/.../BACH/system",
                       patterns=["ARCHITECTURE.md", "CHANGELOG.md",
                                 "FEATURES.md", "ROADMAP.md"])

# A generated per-command help directory that ships one canonical
# language plus five machine-translated siblings per key -- indexing
# every language would flood FTS ranking with near-duplicates for
# little marginal value, so only the canonical language is kept
af.observe_source_add("bach-help-de", "markdown_dir",
                       path="~/OneDrive/.../BACH/system/docs/help",
                       patterns=["*.txt"],
                       exclude_patterns=["*_en.txt", "*_es.txt",
                                         "*_ja.txt", "*_ru.txt", "*_zh.txt"])
```

### Searching one source instead of all of them

Sources differ in size by three orders of magnitude. On this machine
`codex-sessions` holds 260,000 transcript lines while `usmc-working` holds
518 notes — so BM25 hands the whole first page to the transcripts, and a
subject-matter search comes back looking empty. `find()` therefore takes a
source filter:

```bash
gardener find --source usmc-working store welle
gardener find --source usmc-working,usmc-facts store
gardener find --source usmc-working              # no query: list the source
gardener find --type memory --limit 5 store      # also exposed: type, limit
```

```python
af.find("store welle", source="usmc-working")
af.find("store", source=["usmc-working", "usmc-facts"])
af.find("", source="usmc-working", limit=50)     # list, newest first
```

The filter is a `WHERE` condition on the `observed/<source-id>/…` namespace
and runs **before** the ranking, in all three stages of `find()` (exact FTS,
multi-word OR fallback, LIKE fallback). A source id matches the whole path
segment, so `--source usmc` does not pull in `usmc-working`; a leading
`observed/` may be written or omitted. `--source` and the `source` field in a
result are different things — the field names the database (`user`/`system`).

> [!NOTE]
> **Older versions without `--source`:** pass the source id as a search word,
> `gardener find usmc-working store`. Entry names are part of the full-text
> index, so this works — it just ranks weaker than a real filter, because the
> id competes with the query terms instead of restricting the candidate set.

This is the query-time counterpart to `extra_tags` below: `extra_tags` labels a
source when it is registered, for consumers that group several sources under one
name; `--source` narrows a single search to a named source and needs no foresight.

### What a source can never index

A source config points an adapter at whatever glob it likes, so the
guard against indexing secrets cannot live in the configs — it lives in
the adapters. `sources.is_excluded()` is checked per file, and no
config can switch it off:

- **Path segments** (matched whole, case-insensitively): `CREDENTIALS`,
  `.ssh`, `.gnupg`, `.gardener` (Gardener's own runtime dir),
  `node_modules`, `.git`, `.venv`/`venv`, `__pycache__`, `.absorber`,
  `.output`.
- **Filenames:** `.npmrc`, `.netrc`, `.pgpass`, `.env`, `auth.json`,
  `credentials.json`, `secrets.json`, `token.json`, `id_rsa`/`id_ed25519`, …
- **Suffixes:** `.pem`, `.key`, `.p12`, `.pfx`, `.keystore`, `.jks`, …

Because segments are matched whole rather than as string prefixes, a
sibling named `credentials-howto.md` is *not* excluded — only an actual
`CREDENTIALS/` directory is. `gardener.py` derives its `observe()`/
`sync()` skip list from the same constants, so there is one list to
maintain and the home-folder walk cannot drift apart from the adapters.

### Secrets are redacted on the way in

The never-index list keeps credential *stores* out. It cannot help with a
token someone pasted into the middle of an agent session — that text is
part of the transcript. So the text itself is redacted, in `scan()`, the
one gate every adapter's items pass through:

```text
//registry.npmjs.org/:_authToken=npm_***REDACTED***
```

**The semantics are deliberate: an agent that needs the real token must go
to the source file. The index tells it where the credential lives, never
what it is.**

13 families follow the documented formats used by GitHub secret scanning,
gitleaks and detect-secrets (Anthropic, OpenAI, GitHub PATs, AWS key ids,
Slack, Google, GitLab, npm, `Authorization: Bearer`, PEM blocks). Each
anchors on a fixed length, a restricted character class and — where the
vendor provides one — a literal marker (`T3BlbkFJ`). That anchoring, not
the prefix, is what keeps prose out: `skalar`, `ghpx_…`, `AKIAA`,
`npm_install` and a bare "Bearer" in a sentence are left alone. Entropy
heuristics and keyword detectors are deliberately excluded — both are
high-recall/low-precision, and a step that runs unattended must not guess.

A signature found in a **cloud-synced** file (under `GARDENER_CLOUD_ROOT`,
default `~/OneDrive`) is a finding in its own right, because the value has
left the machine. One line per finding — date, path, family, **never the
value** — is appended idempotently to `GARDENER_CLOUD_ALERT_FILE`, counted
in `observe_sources()`' stats and warned about on stderr. The same
signature in a local transcript raises no alert: it never left.

### Tagging a source for downstream filtering

`type` is always `observed` for everything an observe-source indexes — a
consumer that queries the DB directly (rather than through `recall()`,
which already restricts itself to `memory`/`lesson`/`session`) cannot use
`type` to tell a rule file apart from a rotating check registry. `extra_tags`
adds a second, source-level axis for exactly that:

```python
# Findable and worth surfacing as a hint
af.observe_source_add("team-policies", "markdown_dir",
                       path="~/policies", extra_tags=["policy"])

# Findable, but a consumer may reasonably choose not to surface it —
# a rotating log is rarely useful as an injected hint, even though it's
# still worth having in find()
af.observe_source_add("check-registry", "markdown_dir",
                       path="~/registries", patterns=["CHECKS-REG.md"],
                       extra_tags=["register-log"])
```

Everything indexed this way is `observed` — foreign material, reachable
through `find()`. It deliberately does not become `memory`/`lesson`, the
types `recall()` draws on, so that bulk material cannot drown out the
entries that were curated on purpose.

## Seeding

```bash
python seed.py    # Populates gardener.db with base knowledge and example tools
```

Seeding also registers a default set of `observe-sources` (which folders/tables become
searchable) from `sources.reference.json`, so `find()` isn't empty on first use. This is
voluntary at two levels, so a standalone install (no ellmos ecosystem) stays unaffected
unless you opt in:

- **`base` tier** (agent-neutral: transcripts, memories, skills, commands) is on by default
  -- that's the point of a fresh Gardener. Missing paths are silently skipped, never an error.
- **`system` tier** (assumes ellmos infrastructure: USMC, taskplan, policies, tickets) is
  **off by default** and needs explicit opt-in: `GARDENER_SEED_ECOSYSTEM_SOURCES=1`. It
  includes the read-only `_control-center/_PLANS` metadata/report source as
  `plans-register`; the canonical plans remain in their owning documents.
- To skip observe-source seeding entirely (including `base`): `GARDENER_SEED_OBSERVE_SOURCES=0`.

Existing sources are never overwritten either way.

## Comparison: Gardener vs Rinnsal

Gardener and [Rinnsal](https://github.com/ellmos-ai/rinnsal) are both lightweight
LLM operating systems from the ellmos ecosystem. Here are the differences:

| Feature | Detail | **Gardener** | **Rinnsal** |
|---|---|---|---|
| **Core API** | Style | 4 functions (find/get/put/run) | ~20 CLI commands, module-based |
| **Data Model** | Tables | 1 (`everything` + type field) | 4+ (facts, notes, lessons, sessions) |
| | FTS5 Search | Yes (core feature, IS the memory) | No (structured queries) |
| **Memory** | Working | memo() with decay | notes (session-scoped) |
| | Long-term | lesson() + weighting | facts (confidence score) |
| | Consolidation | consolidate() (decay+forget) | No |
| | Recall/Boost | recall() boosts weight | No |
| | Context Export | No | api.context() (LLM-ready) |
| **Tasks** | Priorities | Yes (meta field) | critical/high/medium/low |
| | Agent Assignment | No | Yes |
| | Deadlines | Yes (due field) | No |
| **Files** | Absorb (file→DB) | Yes | No |
| | Materialize (DB→file) | Yes | No |
| | Observe (watch) | Yes | No |
| | Blob Storage (>50MB) | Yes | No |
| **Automation** | Chains | No | Marble-run model |
| | Ollama | No | Yes (REST client) |
| **Connectors** | Telegram/Discord/HA | No (planned) | Yes |
| **Architecture** | Dependencies | Zero | Zero |
| | Event Bus | No | Yes |
| | Multi-Agent | No | Yes (event bus + USMC) |

**In short:** Gardener = radical minimalism (1 table, search = everything).
Rinnsal = more structure, but connectors and chains out of the box.

## Extensibility

Gardener is designed as a core that can be extended with ellmos modules:

| Module | Function | Status |
|--------|----------|--------|
| [connectors](https://github.com/ellmos-ai/connectors) | Telegram, Discord, Webhook, etc. | Planned |
| [USMC](https://github.com/ellmos-ai/usmc) | Cross-Agent Shared Memory | Integrable |
| [clutch](https://github.com/ellmos-ai/clutch) | Smart Model Routing | Integrable |
| [swarm-ai](https://github.com/ellmos-ai/swarm-ai) | Parallel LLM Patterns | Integrable |

The vision: The LLM serves itself from a library of modules.
Gardener provides search, memory, and the execution environment —
everything else is added as a plugin when needed.

### Sibling Projects & Ecosystem

Gardener is part of the **ellmos-ai** and **open-bricks** ecosystems for modular, local-first LLM tooling:

| Repository | Focus / Description | Category |
|---|---|---|
| [ellmos-core](https://github.com/ellmos-ai/ellmos-core) | Modular agent execution kernel & prompt evidence engine | Core Framework |
| [clutch](https://github.com/ellmos-ai/clutch) | Universal multi-provider LLM CLI client (Anthropic, Gemini, OpenAI, Ollama) | CLI & Routing |
| [BACH](https://github.com/ellmos-ai/bach) | File-centric text-based OS for LLMs (filesystem substrate) | OS Architecture |
| [USMC](https://github.com/ellmos-ai/usmc) | Universal Shared Memory Core for multi-agent state persistence | Memory Substrate |
| [Rinnsal](https://github.com/ellmos-ai/rinnsal) | Lightweight structured event-driven agent infrastructure | Agent Runtime |
| [ellmos-controlcenter-mcp](https://github.com/ellmos-ai/ellmos-controlcenter-mcp) | Central MCP tool coordinator, profile management & dynamic routing | MCP Gateway |
| [ellmos-filecommander-mcp](https://github.com/ellmos-ai/ellmos-filecommander-mcp) | Local-first file operations, safe trash bin & dual-language MCP server | MCP Server |
| [ellmos-codecommander-mcp](https://github.com/ellmos-ai/ellmos-codecommander-mcp) | AST analysis, code transformation & refactoring MCP server | MCP Server |
| [ellmos-clatcher-mcp](https://github.com/ellmos-ai/ellmos-clatcher-mcp) | Structured scratchpad, validation & state caching MCP server | MCP Server |
| [n8n-manager-mcp](https://github.com/ellmos-ai/n8n-manager-mcp) | Local-first workflow management and inspection MCP server | MCP Server |
| [skills](https://github.com/ellmos-ai/skills) | Curated multi-agent skills catalog and execution fabric | Skills Library |
| [DevCenter](https://github.com/dev-bricks/DevCenter) | Developer workspace orchestration and management | Developer Tools |
| [open-bricks](https://github.com/open-bricks) | Umbrella organization for modular open-source building blocks | Ecosystem Umbrella |

## Security Model (Read This)

Gardener is a **local, single-user tool with no sandbox — by design**. Be
aware of what that means before feeding it untrusted content:

- `run(name)` executes the Python code stored in an entry's content **with
  the full permissions of your user account**. There is no isolation, no
  restricted builtins, no network or filesystem limits.
- The seeded `shell` tool executes arbitrary shell commands
  (`subprocess.run(..., shell=True)`).
- Anything that can call `put()` can therefore achieve code execution via
  `run()`. If you expose Gardener through another layer (e.g. an MCP server
  or a chat agent), that layer inherits this power — add your own
  authorization there.

**Rule of thumb:** only absorb, put, and run content you trust as much as
code you would execute yourself.

## Design Document

Detailed design documentation: [KONZEPT.md](KONZEPT.md) (German)

---

## Haftung / Liability

Dieses Projekt ist eine **unentgeltliche Open-Source-Schenkung** im Sinne der §§ 516 ff. BGB. Die Haftung des Urhebers ist gemäß **§ 521 BGB** auf **Vorsatz und grobe Fahrlässigkeit** beschränkt. Ergänzend gelten die Haftungsausschlüsse aus GPL-3.0 / MIT / Apache-2.0 §§ 15–16 (je nach gewählter Lizenz).

Nutzung auf eigenes Risiko. Keine Wartungszusage, keine Verfügbarkeitsgarantie, keine Gewähr für Fehlerfreiheit oder Eignung für einen bestimmten Zweck.

This project is an unpaid open-source donation. Liability is limited to intent and gross negligence (§ 521 German Civil Code). Use at your own risk. No warranty, no maintenance guarantee, no fitness-for-purpose assumed.

