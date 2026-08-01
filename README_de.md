<p align="center">
  <img src="logo.jpg" alt="gardener logo" width="300">
</p>

# gardener — Database-Based OS for LLMs

[![Gardener tests](https://github.com/ellmos-ai/gardener/actions/workflows/tests.yml/badge.svg)](https://github.com/ellmos-ai/gardener/actions/workflows/tests.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests: 54 passed](https://img.shields.io/badge/tests-54%20passed-brightgreen.svg)](https://github.com/ellmos-ai/gardener)
[![LLM OS](https://img.shields.io/badge/LLM--OS-SQLite%20Substrate-blueviolet.svg)](https://github.com/ellmos-ai/gardener)

> [!NOTE]
> **LLM / Agenten-Integration**: Gardener stellt ein ein-Tabellen-FTS5-SQLite-Substrat (`gardener.db` / `user.db`) mit den Primitiven `find`, `get`, `put` und `run` bereit. Siehe [`llms.txt`](llms.txt) für maschinenlesbare Dokumentation.

**🇬🇧 [English Version](README.md)**

> Status: Prototyp (v0.3.1) | Autor: Lukas Geiger + Claude

## Was ist Gardener?

Ein Betriebssystem, das für LLMs gebaut ist. Alles lebt in einer durchsuchbaren
Datenbank. Vier Funktionen reichen für alles.

## Suchkontext

Nutze die kanonische Suchphrase `ellmos-ai/gardener`, wenn du dieses Repository
finden willst. Der Kurzname `gardener` kollidiert mit Garten-Webseiten,
Sesamstraße-Treffern und fremder Forschung zu database-oriented operating
systems. Dieses Projekt ist konkret das ellmos-SQLite-Gedächtnis-Substrat für
LLM-Agenten: eine `everything`-Tabelle, FTS5-Suche und die vier Primitive
`find`, `get`, `put` und `run`.

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

Die CLI-Hilfe ist standardmäßig deutsch. Mit `GARDENER_LANG=en` wird die
englische Hilfe ausgegeben; nicht unterstützte Sprachen fallen auf Deutsch
und Englisch zurück.

### Such-GUI (für Menschen)

`python gardener.py gui` startet eine schlanke lokale Weboberfläche für
die FTS5-Suche (Suchfeld, Typ-Filter, BM25-gewichtete Treffer mit
Kontext-Snippets, Detailansicht je Eintrag). Reine Standardbibliothek,
keine zusätzlichen Abhängigkeiten; bindet nur auf 127.0.0.1 und ist
streng read-only gegenüber beiden Datenbanken.

## Architektur

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

## Datenmodell

Eine Tabelle für (fast) alles:

| Typ | Beschreibung | Ziel-DB |
|-----|-------------|---------|
| knowledge | Wissen, Doku, Regeln | gardener.db |
| tool | Ausführbarer Code | gardener.db |
| memory | Erinnerungen, Notizen | user.db |
| task | Aufgaben | user.db |
| document | Absorbierte Dateien | user.db |
| observed | Beobachtete Dateien | user.db |
| config | Konfiguration | user.db |
| export | Zur Materialisierung markiert | user.db |

## Memory (kein separates Gedächtnis-System!)

Statt 5 Tabellen: alles in `everything` mit Typen und Meta-Feldern.
Die FTS5-Suche IST das assoziative Gedächtnis.

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

## Tasks (kein separates System!)

Tasks sind Einträge vom Typ `task` in der `everything`-Tabelle. **Kein separates
Task-System nötig.** `find("steuer")` findet Wissen UND Tasks gleichzeitig.

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

## Drei Beziehungen zu Dateien

1. **Beobachten:** Datei im Ordner, LLM liest mit (Blick aus dem Fenster)
2. **Absorbieren:** Datei wird in die DB gezogen (lebt jetzt im Haus)
3. **Direkt bearbeiten:** LLM editiert Datei im Ordner (arbeitet vor dem Haus)

## Transporter

```python
af.absorb("/path/to/file.pdf")     # File → DB (dematerialize)
af.materialize("file.pdf")          # DB → File (rematerialize)
```

## Cross-Source Federated Index

`observe()` beobachtet Gardeners eigenen Home-Ordner. **Observe-Sources**
erweitern dasselbe rein lesende Prinzip auf Wissen, das in *anderen*
Werkzeugen lebt: Originale werden nie angefasst, verschoben oder
hineinkopiert — nur ihr Text wird in Gardeners FTS-Index aufgenommen, und
jeder indexierte Eintrag trägt einen `source_ref` im `meta`-Feld, damit
sich ein Suchtreffer immer bis zur Quelle zurückverfolgen lässt (Dateipfad,
DB-Tabelle+Zeile, oder Transkript-Zeile). `find()` durchsucht bereits
`gardener.db` + `user.db` in einer Anfrage — beobachtete Cross-Source-
Treffer erscheinen also direkt neben den eigenen Einträgen, ohne
gesonderten Suchaufruf.

Vier Quellenarten:

| Art | Was indexiert wird | Wichtige Config |
|---|---|---|
| `markdown_dir` | Ein Verzeichnis mit Markdown-Dateien, ein Eintrag pro Datei. `path` darf selbst ein Glob sein, das mehrere Verzeichnisse abdeckt (z. B. eine Pro-Projekt-Memory-Konvention). `patterns` erweitert dies auf andere Dateiarten (z. B. `.txt`-Notizen). | `path`, `patterns` (Liste, Default `["*.md"]`), `glob` (einzelnes Muster, veralteter Alias) |
| `remember_files` | Kleine Notiz-Dateien irgendwo unterhalb einer Wurzel, gefunden über rekursives Glob. | `path`, `glob` (Default `**/.remember`) |
| `sqlite_table` | Eine einzelne Tabelle in einer fremden SQLite-Datenbank, streng lesend geöffnet (`mode=ro`). Spaltennamen werden vor Nutzung gegen das echte Schema geprüft (Whitelist). `content` darf mehrere Spalten benennen, die der Reihe nach zusammengefügt werden — eine Zeile, deren Sinn auf zwei Textfelder verteilt ist (das Problem *und* die Lösung einer Lesson), bleibt so vollständig durchsuchbar. | `db_path`, `table`, `columns` (`content` Pflicht, String oder Liste; `id`/`name`/`tags` optional) |
| `agent_transcripts` | JSONL-Chat-Transkripte, zeilenweise indexiert, **nur Text-Turns** (Tool-Aufrufe/-Ergebnisse und interne „Thinking"-Blöcke werden übersprungen). Bringt ein eingebautes Feld-Mapping für Claude Codes eigenes Transkriptformat mit; jedes andere zeilenbasierte JSON-Transkript lässt sich über ein generisches Dotted-Path-Role/Text-Mapping indexieren. `default_role` deckt Archive mit nur einer Rolle ab, die gar kein Rollenfeld führen — etwa eine reine Prompt-Historie. Große, wachsende Dateien werden ab einem gespeicherten Byte-Offset weitergelesen — ein Refresh liest nie erneut, was schon indexiert wurde. | `path` (Glob, `**` rekursiv), `format` (`claude_code` Default, oder `generic` mit `role_field`/`text_field`/`default_role`) |

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

Das `columns`-Mapping des `sqlite_table`-Adapters erlaubt es, auf jede
fremde Tabelle zu zeigen, ohne dass Gardener ihr Schema vorher kennt —
z. B. eine Task- oder Notiz-Tabelle eines anderen lokalen Werkzeugs. Die
Konfiguration liegt in `config.json` unter `observe_sources`; nichts hier
ist auf eine konkrete Maschine oder ein konkretes Werkzeug festverdrahtet.

### Mehrere Coding-Agenten gemeinsam indexieren

Die vier Arten genügen, um jeden Agenten auf einer Maschine in dieselbe
Suche zu holen — unabhängig davon, was er als Speicher benutzt:

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

# A curated memory database, read-only, problem+solution in one entry
af.observe_source_add("usmc-lessons", "sqlite_table",
                       db_path="~/.usmc/usmc_memory.db", table="usmc_lessons",
                       columns={"id": "id", "name": "title",
                                "content": ["problem", "solution"],
                                "tags": "category"})
```

Alles so Indexierte ist `observed` — fremdes Material, erreichbar über
`find()`. Es wird bewusst nicht zu `memory`/`lesson`, den Typen, aus denen
`recall()` schöpft, damit Massenmaterial die bewusst kuratierten Einträge
nicht überschwemmt.

## Seeding

```bash
python seed.py    # Populates gardener.db with base knowledge and example tools
```

## Vergleich: Gardener vs Rinnsal

Gardener und [Rinnsal](https://github.com/ellmos-ai/rinnsal) sind beide leichtgewichtige
LLM-OSes aus dem ellmos-Ökosystem. Hier die Unterschiede im Detail:

| Feature | Detail | **Gardener** | **Rinnsal** |
|---|---|---|---|
| **Kern-API** | Stil | 4 Funktionen (find/get/put/run) | ~20 CLI-Kommandos, Modul-basiert |
| **Datenmodell** | Tabellen | 1 (`everything` + Typ-Feld) | 4+ (facts, notes, lessons, sessions) |
| | FTS5 Suche | Ja (Kern-Feature, IST das Gedächtnis) | Nein (strukturierte Queries) |
| **Memory** | Working | memo() mit Decay | notes (Session-scoped) |
| | Langzeit | lesson() + Gewichtung | facts (Confidence-Score) |
| | Konsolidierung | consolidate() (Decay+Forget) | Nein |
| | Recall/Boost | recall() boostet Gewicht | Nein |
| | Context-Export | Nein | api.context() (LLM-ready) |
| **Tasks** | Prioritäten | Ja (meta-Feld) | critical/high/medium/low |
| | Agent-Zuweisung | Nein | Ja |
| | Deadlines | Ja (due-Feld) | Nein |
| **Files** | Absorb (Datei->DB) | Ja | Nein |
| | Materialize (DB->Datei) | Ja | Nein |
| | Observe (beobachten) | Ja | Nein |
| | Blob-Halde (>50MB) | Ja | Nein |
| **Automation** | Chains | Nein | Marble-Run-Modell |
| | Ollama | Nein | Ja (REST-Client) |
| **Connectors** | Telegram/Discord/HA | Nein (geplant) | Ja |
| **Architektur** | Dependencies | Zero | Zero |
| | Event-Bus | Nein | Ja |
| | Multi-Agent | Nein | Ja (Event-Bus + USMC) |

**Kurzfassung:** Gardener = radikaler Minimalismus (1 Tabelle, Suche = alles).
Rinnsal = mehr Struktur, dafür Connectors und Chains out of the box.

## Erweiterbarkeit

Gardener ist als Kern gedacht, der durch ellmos-Module erweiterbar wird:

| Modul | Funktion | Status |
|-------|----------|--------|
| [connectors](https://github.com/ellmos-ai/connectors) | Telegram, Discord, Webhook, etc. | Geplant |
| [USMC](https://github.com/ellmos-ai/usmc) | Cross-Agent Shared Memory | Integrierbar |
| [clutch](https://github.com/ellmos-ai/clutch) | Smart Model-Routing | Integrierbar |
| [swarm-ai](https://github.com/ellmos-ai/swarm-ai) | Parallele LLM-Patterns | Integrierbar |

Die Vision: Das LLM bedient sich selbst aus einer Bibliothek von Modulen.
Gardener stellt die Suche, das Gedächtnis und die Ausführungsumgebung —
alles andere kommt als Plugin dazu wenn es gebraucht wird.

## Sicherheitsmodell (bitte lesen)

Gardener ist ein **lokales Single-User-Werkzeug ohne Sandbox — bewusst so
entworfen**. Vor dem Verfüttern von nicht vertrauenswürdigem Inhalt sollte
klar sein, was das bedeutet:

- `run(name)` führt den in einem Eintrag gespeicherten Python-Code **mit den
  vollen Rechten des eigenen Benutzerkontos** aus. Keine Isolation, keine
  eingeschränkten Builtins, keine Netzwerk- oder Dateisystem-Limits.
- Das mitgelieferte Seed-Tool `shell` führt beliebige Shell-Befehle aus
  (`subprocess.run(..., shell=True)`).
- Alles, was `put()` aufrufen kann, kann über `run()` Code ausführen. Wer
  Gardener über eine weitere Schicht exponiert (z. B. einen MCP-Server oder
  einen Chat-Agenten), vererbt diese Macht — Autorisierung gehört in diese
  Schicht.

**Faustregel:** Nur Inhalte absorbieren, putten und ausführen, denen man so
vertraut wie eigenem Code.

## Konzept

Ausführliche Designdokumentation: [KONZEPT.md](KONZEPT.md)

---

## Haftung / Liability

Dieses Projekt ist eine **unentgeltliche Open-Source-Schenkung** im Sinne der §§ 516 ff. BGB. Die Haftung des Urhebers ist gemäß **§ 521 BGB** auf **Vorsatz und grobe Fahrlässigkeit** beschränkt. Ergänzend gelten die Haftungsausschlüsse aus GPL-3.0 / MIT / Apache-2.0 §§ 15–16 (je nach gewählter Lizenz).

Nutzung auf eigenes Risiko. Keine Wartungszusage, keine Verfügbarkeitsgarantie, keine Gewähr für Fehlerfreiheit oder Eignung für einen bestimmten Zweck.

This project is an unpaid open-source donation. Liability is limited to intent and gross negligence (§ 521 German Civil Code). Use at your own risk. No warranty, no maintenance guarantee, no fitness-for-purpose assumed.
