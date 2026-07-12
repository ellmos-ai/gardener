# Cross-Source-Wissensindex — Entscheidung und Hintergrund

> **Status:** Konzept/Recherche. **Realisierung: als Gardener-Feature**
> (kein eigenständiges Modul) — Entscheidung mit User 2026-07-06.
> **Kanonisch (Umsetzung):** `ROADMAP.md` + `TODO.md` in diesem
> GARDENER-Modul, Abschnitt „Cross-Source federated index".
> Dieses Dokument hält nur **Hintergrund, Recherche und die Begründung** fest.
> Herkunft: ctx-Evaluierungs-/n8n-manager-Strang (Luca King / ctxrs, Juli 2026).
> Frühere Ablage: `.AI/.MODULES/knowledge-index/KONZEPT.md`, aufgelöst am
> 2026-07-12, weil `knowledge-index` kein eigenständiges Modul ist.
> Siehe auch: `n8n-workflow-manager`, `n8n-manager-mcp`.

## Problem

Verteiltes Wissen über die ellmos-Speicher ist siloiert und uneinheitlich
durchsuchbar (empirisch 2026-07-06):

| Speicher | FTS? | Cross-Source? |
|---|---|---|
| **Gardener** (`~/.gardener/gardener.db`) | **ja** (FTS5 + bm25) | nein |
| **Rinnsal** (`~/.rinnsal/*.db`, `usmc_*`) | **nein** (nur Kategorie-Filter) | nein |
| **BACH** (`bach.db`) | **nein** (substring/regex) | nein |
| Agent-Transkripte (Codex/Claude/Kimi/Gemini) | — | nein |

Der Mangel ist **nicht** „FTS pro System", sondern: **kein Index sucht über
alle Quellen.**

## Entscheidung: Gardener wird Träger (föderiert)

Gardener ist der richtige Träger — es hat **schon FTS5**, und `observe()` ist
konzeptionell bereits der **pull/föderierte** Mechanismus („beobachten statt
besitzen", read-only). Statt eines neuen Moduls wird `observe()` erweitert, um
auch **fremde DBs + Transkripte** read-only zu indexieren.

**Wichtig — föderiert, nicht absorbieren:** Quellen bleiben, wo sie sind;
Gardener indexiert nur und zitiert zurück. `absorb` (ins Haus holen) bleibt für
Kleines/Kuratiertes; für fremde/große Quellen (z. B. 1-GB-Transkripte) gilt der
`observe`-Index.

## Stack-Bild

| Rolle | Komponente | Prinzip |
|---|---|---|
| kuratiert/strukturiert | **Rinnsal-Memory** (`usmc_*`) | push, explizit — „was ich bewusst merke" |
| organisch + Cross-Source-Suche | **Gardener** | pull — absorb/observe/decay + Sucheinstieg über die anderen |

**USMC-Klarstellung (User 2026-07-06):** „USMC deprecated" gilt **nur für den
lokalen Stack auf diesem System** (lokale USMC-DB nicht weiter befüllen, Gardener
ist hier kanonisch). **USMC als Modul bleibt** (GitHub `ellmos-ai`) und ist für
Stacks/andere Systeme nutzbar. Offener Punkt: Rinnsal sollte das USMC-Modul
**importieren** statt sein Schema nachzubauen (siehe `rinnsal/TODO.md`).

## Update 2026-07-11 — `.MEMORY`-Modularisierung

Präzisierung mit User: Das Memory-System wird als eigene Säule gekapselt, mit
drei Modulen:

| Modul | Rolle |
|---|---|
| **USMC** | Kuratiertes Session-/Kern-Gedächtnis („memory gepflegt") + **Fassade/Einstiegspunkt** des Memory-Systems. **Rehabilitiert** — die Deprecation [U 2026-07-04, E03] ist aufgehoben |
| **GARDENER** | Memory-**Zulieferer**: organischer Wildwuchs (absorb/decay) + Cross-Source-Index (`observe()`, FTS5) — Träger dieses Konzepts |
| **TASKPLAN** | Task-System/Taskmemory als eigenes Modul — extrahiert aus `rinnsal/tasks`; Rinnsal importiert es zurück, BACH + `_tasks`-Scanner später als Consumer |

Der geplante lawn-mower-Stack (Gardener+USMC) geht in dieser Struktur auf.
Umsetzung/Migrationsstand: `.AI/.MODULES/.MEMORY/README.md`, `GARDENER/ROADMAP.md`,
`rinnsal/TODO.md`, `_control-center/MANIFEST.md`.

**Folgeentscheidung [U 2026-07-11]:** Die fachliche Kapselung bleibt, wurde aber
für den Stack-Baukasten als Untermodul nach `.AI/.MODULES/.MEMORY/` zurückgeführt.
Der frühere Root `.AI/.MEMORY/` war damit eine dokumentierte Zwischenstation.

## Prinzip pull statt push

Kernlehre (Gardener/USMC-Erfahrung, ctx-Vorbild): nicht auf aktives Füttern
warten (push-Speicher bleiben leer, wenn Agenten nicht mitmachen), sondern
**indexieren, was ohnehin da ist** (pull/passiv). Das ist der Grund, warum der
`observe`-Ansatz (statt eines weiteren push-Gedächtnisses) richtig ist.

## Referenz-/Konkurrenzlandschaft (Recherche 2026-07-06)

- **Pull/passiv (Vorbild):** [ctx](https://github.com/ctxrs/ctx) (ctxrs, Rust,
  **Apache-2.0** — bewusst gewählt, nicht erzwungen; Patent-Grant; `ctx mcp serve`,
  6 SDKs) · [cass](https://github.com/Dicklesworthstone/coding_agent_session_search)
  (22 Provider) · [agent-sessions](https://github.com/jazzyalex/agent-sessions)
  (macOS) · [Context Mode](https://pi.dev/packages/context-mode) (Pi, FTS5+BM25).
- **Push/kuratiert (bewusst nicht):** [mem0](https://mem0.ai) ·
  [agentmemory](https://github.com/rohitg00/agentmemory) ·
  [ReMe](https://github.com/agentscope-ai/ReMe).

**ctx empirisch (2026-07-06):** funktioniert (590 Codex-Sessions/95k Events
importiert, Suche gut), aber **Auto-Discovery auf Windows defekt** (nur
expliziter `--path`-Import) — ein Grund mehr für Eigenbau via Gardener.
