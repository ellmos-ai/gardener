<p align="center">
  <img src="logo.jpg" alt="gardener logo" width="300">
</p>

# gardener — Database-Based OS for LLMs

**🇩🇪 [Deutsche Version](README_de.md)**

> Status: Prototype | Author: Lukas Geiger + Claude | 2026-03-12

## What is Gardener?

An operating system built for LLMs. Everything lives in a searchable
database. Four functions are all you need.

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
python gardener.py get <name>
python gardener.py put <name> <text>
python gardener.py run <name>
python gardener.py absorb <file>
python gardener.py materialize <name>
python gardener.py sync
python gardener.py observe
python gardener.py status
```

## Architecture

```
Gardener/
  gardener.py          # Core: Gardener class + CLI
  seed.py              # Initial system knowledge
  KONZEPT.md           # Design documentation (German)
  README.md            # This file
  workspace/           # Materialized code for execution
  blobs/               # Storage for large files (>50MB)

Local (not in cloud):
  AppData/Local/Gardener/
    gardener.db        # System: Knowledge, tools, blueprints
    user.db            # User: Memory, tasks, personal data
    blobs/             # Large files

User directory (cloud ok):
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

Details: [KONZEPT.md#memory](KONZEPT.md#memory-kein-separates-gedaechtnis-system-design-entscheidung)

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

## Seeding

```bash
python seed.py    # Populates gardener.db with base knowledge and example tools
```

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

## Design Document

Detailed design documentation: [KONZEPT.md](KONZEPT.md) (German)

---

## Haftung / Liability

Dieses Projekt ist eine **unentgeltliche Open-Source-Schenkung** im Sinne der §§ 516 ff. BGB. Die Haftung des Urhebers ist gemäß **§ 521 BGB** auf **Vorsatz und grobe Fahrlässigkeit** beschränkt. Ergänzend gelten die Haftungsausschlüsse aus GPL-3.0 / MIT / Apache-2.0 §§ 15–16 (je nach gewählter Lizenz).

Nutzung auf eigenes Risiko. Keine Wartungszusage, keine Verfügbarkeitsgarantie, keine Gewähr für Fehlerfreiheit oder Eignung für einen bestimmten Zweck.

This project is an unpaid open-source donation. Liability is limited to intent and gross negligence (§ 521 German Civil Code). Use at your own risk. No warranty, no maintenance guarantee, no fitness-for-purpose assumed.

