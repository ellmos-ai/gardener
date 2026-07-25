# Cross-Source-Wissensindex — Entscheidung und Hintergrund

> **Status:** umgesetzt als Gardener-Feature (kein eigenständiges Modul).
> **Kanonisch für die Umsetzung:** Abschnitt „Cross-source federated index" in
> [ROADMAP.md](../../ROADMAP.md) bzw. [ROADMAP_de.md](../../ROADMAP_de.md).
> Dieses Dokument hält nur **Hintergrund, Recherche und die Begründung** fest.

## Problem

Wissen, das ein Agent im Alltag tatsächlich braucht, liegt selten an einem
Ort. Es verteilt sich über mehrere lokale Werkzeuge — und jedes davon ist für
sich durchsuchbar, aber keines sucht über die anderen mit:

| Speicher | Volltextsuche? | Cross-Source? |
|---|---|---|
| **Gardener** (`gardener.db` / `user.db`) | **ja** (FTS5 + bm25) | nein |
| Strukturierte Memory-Werkzeuge (facts/notes/lessons) | meist nein (nur Kategorie-Filter) | nein |
| Datei-zentrierte Agenten-Systeme | substring/regex | nein |
| Agenten-Transkripte (JSONL-Chatverläufe) | — | nein |

Der Mangel ist **nicht** „jedem System fehlt eine Volltextsuche", sondern:
**kein Index sucht über alle Quellen hinweg.**

## Entscheidung: Gardener wird Träger (föderiert)

Gardener ist der passende Träger, weil er **bereits FTS5 hat** und weil
`observe()` konzeptionell schon der föderierte Mechanismus ist — „beobachten
statt besitzen", strikt read-only. Statt ein weiteres Modul zu bauen, wurde
`observe()` erweitert, sodass es auch **fremde Datenbanken und Transkripte**
read-only indexiert.

**Föderiert, nicht absorbierend:** Quellen bleiben, wo sie sind; Gardener
indexiert nur und zitiert über `meta.source_ref` zurück. `absorb` (ins Haus
holen) bleibt für Kleines und Kuratiertes; für fremde oder große Quellen —
etwa GB-große Transkripte — gilt der `observe`-Index.

## Rollenteilung im Memory-Stack

| Rolle | Prinzip |
|---|---|
| kuratiert/strukturiert (USMC) | push, explizit — „was ich bewusst merke" |
| organisch + Cross-Source-Suche (Gardener) | pull — absorb/observe/decay, Sucheinstieg über die anderen |
| Tasks (TASKPLAN) | eigenes Modul; Gardeners `type='task'` bleibt Beobachtungsgut |

## Prinzip: pull statt push

Die Kernlehre aus dem Betrieb solcher Speicher: nicht auf aktives Füttern
warten. Push-Speicher bleiben leer, wenn Agenten nicht konsequent mitschreiben.
Stattdessen **indexieren, was ohnehin entsteht** (pull/passiv). Das ist der
Grund, warum der `observe`-Ansatz gewählt wurde und nicht ein weiteres
push-basiertes Gedächtnis.

## Referenz- und Konkurrenzlandschaft

- **Pull/passiv (Vorbild):** [ctx](https://github.com/ctxrs/ctx) (Rust,
  Apache-2.0, `ctx mcp serve`) ·
  [cass](https://github.com/Dicklesworthstone/coding_agent_session_search) ·
  [agent-sessions](https://github.com/jazzyalex/agent-sessions) (macOS) ·
  [Context Mode](https://pi.dev/packages/context-mode) (FTS5 + BM25).
- **Push/kuratiert (bewusst nicht gewählt):** [mem0](https://mem0.ai) ·
  [agentmemory](https://github.com/rohitg00/agentmemory) ·
  [ReMe](https://github.com/agentscope-ai/ReMe).

**ctx empirisch geprüft:** funktioniert gut (mehrere hundert importierte
Sessions, brauchbare Suche), die Auto-Discovery war unter Windows allerdings
defekt — nur der explizite `--path`-Import lief. Das war ein zusätzliches
Argument für die eigene, generische Adapter-Lösung in Gardener, die neben
Transkripten auch beliebige lokale SQLite-Tabellen und Markdown-Verzeichnisse
abdeckt.
