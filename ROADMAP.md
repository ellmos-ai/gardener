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
