# Gardener ROADMAP

**🇩🇪 [Deutsche Version](ROADMAP_de.md)**

> Updated: 2026-03-12

## Prototype (v0.1) — DONE

- [x] Core: find/get/put/run
- [x] Two DBs: gardener.db + user.db (transparent via ATTACH)
- [x] FTS5 full-text search with triggers
- [x] .absorber/ (mailbox) + .output/ (output)
- [x] config.json sync modes (selective/always_absorb/observe_only)
- [x] Blob heap for large files (>50MB)
- [x] Workspace materialization for code execution
- [x] Three relationship types: observe / absorb / direct edit
- [x] Tasks (task/tasks/done/task_status)
- [x] Memory (memo/lesson/session_end/recall/consolidate)
- [x] Decay/boost/forget (weighting in meta field)
- [x] Bridge tools: shell, http-fetch, backup, encoding-fix
- [x] Skin tools: text-stats, file-info, folder-scanner
- [x] list/delete management
- [x] CLI with 19 commands
- [x] seed.py (base knowledge + tools)
- [x] Documentation: KONZEPT.md, README.md, ERKENNTNISSE.md

---

## Next Steps (v0.2)

### Learning & Evolution

Tools, skills, and knowledge entries should age and stay fresh
just like memory entries:

- **Decay for everything:** Not just memory/lesson/session, but also
  tools and knowledge get weight. Unused tools fade,
  frequently used ones stay fresh.
- **Usage tracking:** `run()` increases a tool's weight.
  `get()` increases knowledge weight. What's needed, lives.
- **Natural selection:** When a better tool for the same task
  is found, it replaces the old one. The old one fades through
  non-use and is eventually removed by `consolidate()`.
- **Experience = weight:** A tool that ran 100 times has more
  weight than one that ran twice. This mirrors real experience.

```
New tool:       weight=0.5 (unproven)
After 10x run:  weight=0.8 (proven)
After 100x run: weight=1.0 (core tool)
Never used:     weight drops → consolidate() removes it
Replaced:       Old tool no longer called → fades
```

This is learning: not keeping everything, but keeping the better
and letting the worse be forgotten.

### Further Topics v0.2

- [ ] Use pinning meaningfully (pinned=1 prevents decay)
- [ ] Specialized tables as needed (shelves registry is prepared)
- [ ] Port more bridge tools as needed (from BACH)

---

## Later (v0.3+)

- [ ] Self-healing/respawn (restore system entries from gardener.db)
- [ ] DB viewer (port from BACH)
- [ ] MCP server (Gardener as MCP: find/get/put/run as tools)
- [ ] Versioning (change history in DB)
- [ ] Permissions model (who can change what in gardener.db?)
- [ ] Workspace management (cleanup, max size)
- [ ] External integrations (MCP, APIs)
- [ ] Multi-LLM (multiple LLMs share user.db)

---

## Architecture Decisions (Log)

| Date | Decision | Reason |
|------|----------|--------|
| 2026-03-12 | One table (everything) | Everything in one search |
| 2026-03-12 | No separate task system | Tasks = type='task' in everything |
| 2026-03-12 | No separate memory system | Memory/lessons = types in everything |
| 2026-03-12 | No dematerialize | absorb() IS dematerialization |
| 2026-03-12 | FTS5 instead of trigger table | Search IS the associative memory |
| 2026-03-12 | Body model | House=mind, skin=filter tools, outside=bridge tools |
| 2026-03-12 | Text boundary | In house no tool, at skin filter, outside tools |
| 2026-03-12 | DB viewer from BACH | Don't rebuild, port |
| 2026-03-12 | Sketchboard model | LLM IS the house (context), DB is photo album (memory) |
| 2026-03-12 | Decay for everything (planned) | Tools/knowledge should also age |


---

## Cross-source federated index (v0.3+)

Gardener becomes the search entry point for knowledge that is *distributed*
across tools, not just for its own database. `observe()` is conceptually
already the right federated mechanism: watch, don't own — strictly read-only.

**Status: first stage shipped** (`sources.py`, `Gardener.observe_source_*` /
`observe_sources()`, CLI `gardener observe-source add/list/remove/refresh`,
17 tests). Details: the "Cross-Source Federated Index" section in
README.md / README_de.md, and the 2026-07-23 entry in CHANGELOG.md.

- [x] `observe()` extended to **foreign knowledge sources** through four
  read-only adapters (`markdown_dir`, `remember_files`, `sqlite_table`,
  `agent_transcripts`). `sqlite_table` is generic — path, table and column
  mapping come from `config.json` — so it covers a foreign tool's task or
  notes table without hardcoding its schema. Sources stay **where they are**
  (SQLite opened strictly `mode=ro`); Gardener only indexes, it never copies
  them in. `agent_transcripts` reads GB-sized JSONL transcripts incrementally
  from a stored byte offset, so an unchanged file is never re-read.
  **Open:** dedicated `format` presets for transcript formats other than
  Claude Code (currently: the built-in `claude_code` mapping plus a generic
  dotted-path role/text mapping for everything else).
- [x] Hits cite their way back to the source: every observed entry carries
  `meta.source_ref` (file path, DB table + row, or transcript line + uuid).
- [x] Federated FTS search over own and observed sources in a single query:
  `find()` already searched `gardener.db` + `user.db` together, and
  cross-source entries land in `user.db` like any other `observed` entry, so
  they show up automatically.
- [x] Source list widened: **agent memory directories** (`markdown_dir`,
  covering a configurable per-project memory convention) and **`.remember`
  files** (`remember_files`) are adapters of their own. The
  `agent_transcripts` adapter is an independent, generic implementation — no
  private paths or contents were carried over from any internal tooling.

Boundary: `absorb` = bring it into the house (small, curated) vs. the
`observe` index = federated (foreign, large, read-only). Prior art: `ctx`
(ctxrs, Apache-2.0, pull/passive), which covers coding-agent transcripts but
not arbitrary local databases — hence the in-house adapter set. Background and
research: [docs/decisions/knowledge-index.md](docs/decisions/knowledge-index.md).


## Gardener as a memory module

Gardener is understood primarily as a **memory module** that also happens to
work as an extremely small operating system on its own. Within the ellmos
memory stack the roles are split three ways:

- **USMC** — curated session and core memory, and the entry point/facade of
  the memory system.
- **Gardener** — the memory *supplier*: organic growth (absorb / observe /
  decay) plus the cross-source index.
- **TASKPLAN** — the task system as a separate module.

This also settles an older open design question: task management belongs to
TASKPLAN, while Gardener's `type='task'` entries stay what they always were —
organic observation material, not a task system.

- **BACH transfer (planned):** move BACH's stronger memory functions over to
  USMC; BACH then re-imports the shared memory stack instead of maintaining
  its own.
