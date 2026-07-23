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

## Cross-Source federated index (v0.3+) — 2026-07-06

Gardener wird der **Sucheinstieg über verteiltes Wissen**, nicht nur über die
eigene DB. Ausgangslage: Rinnsal und BACH haben **kein** FTS, Gardener hat es
bereits — und Gardeners `observe()` ist konzeptionell schon der richtige,
**föderierte** Mechanismus („beobachten statt besitzen", read-only).

**Status 2026-07-23: erste Ausbaustufe umgesetzt** (`sources.py`,
`Gardener.observe_source_*`/`observe_sources()`, CLI `gardener observe-source
add/list/remove/refresh`, 15 Tests). Details: README.md/README_de.md
Abschnitt "Cross-Source Federated Index", CHANGELOG.md 2026-07-23.

- [x] `observe()` auf **fremde Wissensquellen** erweitert: vier read-only-
  Adapter (`markdown_dir`, `remember_files`, `sqlite_table`,
  `agent_transcripts`). `sqlite_table` ist generisch (Pfad+Tabelle+Spalten-
  Mapping aus config.json) und deckt damit `rinnsal`-artige/`bach.db`-artige
  Tabellen ab, ohne deren Schema fest zu verdrahten. Quellen bleiben **wo sie
  sind** (SQLite strikt `mode=ro` geöffnet); Gardener indexiert nur — **kein
  `absorb`/Reinkopieren**. `agent_transcripts` liest GB-große JSONL-
  Transkripte inkrementell ab gespeichertem Byte-Offset (kein Re-Read bei
  unveränderten Dateien). **Offen:** eigene `format`-Presets für
  Codex-/Gemini-/Kimi-Transkriptformate (bislang: eingebautes `claude_code`-
  Mapping + generisches Dotted-Path-Role/Text-Mapping für alles andere).
- [x] Treffer zitieren zurück zur Quelle: jeder observed-Eintrag trägt
  `meta.source_ref` (Datei-/DB-Pfad, Tabelle+Zeile, oder Transkript-Zeile+uuid).
- [x] Föderierte FTS-Suche über eigene + beobachtete Quellen in einem Query:
  `find()` durchsuchte bereits `gardener.db`+`user.db` gemeinsam; Cross-
  Source-Einträge landen wie normale `observed`-Einträge in `user.db` und
  erscheinen damit automatisch mit.
- [x] Quellenliste erweitert [U 2026-07-11]: **Claude-Memories**
  (`markdown_dir`, deckt `~/.claude/projects/*/memory/` konfigurierbar ab)
  und **`.remember`-Dateien** (`remember_files`) sind eigene Adapter. Die
  **`_TOM-lm`-Adapter** (`_control-center/_TOM-lm/_tool/adapters/`) wurden als
  Vorlage gelesen (Extraktionslogik für Claude Code JSONL verstanden), aber
  bewusst NICHT übernommen — public Repo, keine privaten Pfade/Inhalte; der
  `agent_transcripts`-Adapter ist eine eigenständige, generische
  Neu-Implementierung.

Abgrenzung: `absorb` = ins Haus holen (klein/kuratiert) vs. `observe`-Index =
föderiert (fremd/groß, read-only). Vorbild `ctx` (ctxrs, **Apache-2.0**,
pull/passiv) — deckt aber nur Coding-Agent-Transkripte ab, nicht unsere DBs;
Eigenbau via Gardener bevorzugt. Hintergrund/Recherche:
`.AI/.MODULES/knowledge-index/KONZEPT.md`.


## Gardener als Memory-Modul + lawn-mower-Stack (2026-07-06)

Richtungsentscheidung mit User: Gardener wird primär als **Memory-Modul**
verstanden (Kategorie `.MEMORY` in `.MODULES`) — funktioniert zugleich als
absolut minimales OS.

- **lawn-mower (geplant):** ein **Stack**, der Gardener (organisch/emergent,
  absorb/observe/decay) + USMC (strukturiert/kuratiert, facts/lessons) kombiniert
  und das **Standard-Memory** wird.
- **BACH-Transfer (Roadmap):** BACH hat evtl. schönere/bessere Memory-Funktionen
  → diese nach **USMC** transferieren; BACH **reimportiert** später `lawn-mower`
  als sein Gedächtnis (nutzt dann den Standard-Memory-Stack statt Eigenbau).
- **Task-Faktenlage:** USMC = reines Memory (keine Tasks); Tasks liegen in
  Rinnsal (`rinnsal_tasks`); Gardener vermischt Tasks+Memory bewusst
  (`type='task'`). Offene Designfrage für den Memory-Stack.
- Physische Umordnung (`.MODULES/.MEMORY/gardener`) erst später/manuell — dann
  homebase-Engine-Pfad (`[engines.garden].path`) nachziehen.

### Update 2026-07-11 — .MEMORY-Säule, Gardener als Zulieferer [U 2026-07-11]

- Zielort ist jetzt eine **eigene Säule `.AI/.MEMORY/`** (statt `.MODULES/.MEMORY`);
  Gardener zieht aus `.OS` dorthin um.
- Rollenklärung: **USMC** (rehabilitiert, Deprecation aufgehoben) = kuratiertes
  Session-Memory + **Fassade/Einstiegspunkt** des Memory-Systems; **Gardener** =
  Memory-**Zulieferer** (Wildwuchs + Cross-Source-Index); **TASKPLAN** = Task-System
  als drittes Modul (extrahiert aus `rinnsal/tasks`).
- Das beantwortet die offene Task-Designfrage: Tasks wandern zu **TASKPLAN**;
  Gardeners `type='task'` bleibt nur organisches Beobachtungsgut, kein Task-System.
- lawn-mower als eigener Stack entfällt — geht in `.MEMORY` (USMC+GARDENER+TASKPLAN) auf.
- Physische Umordnung weiterhin später/manuell (siehe `.AI/.MEMORY/README.md`,
  Migrationsstand) — dann homebase-Engine-Pfad nachziehen.

### Folgeupdate 2026-07-11 — Baukasten-Rückführung [U 2026-07-11]

- Die funktionale `.MEMORY`-Kapselung bleibt erhalten, ist nun aber die
  Fähigkeitsfamilie `.AI/.MODULES/.MEMORY/` statt einer eigenen Root-Säule.
- GARDENER, USMC und TASKPLAN wurden nach katalog-first Vorbereitung physisch
  dorthin zurückgeführt. Homebase löst GARDENER zuerst über die Modul-ID auf und
  behält die beiden früheren Orte nur als Kompatibilitätsfallback.
