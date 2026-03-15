# Gardener -- LLM-natives Betriebssystem

> Status: Prototyp | Autor: Lukas Geiger + Claude | 2026-03-12

## Was ist Gardener?

Ein Betriebssystem das fuer LLMs gebaut ist. Alles lebt in einer durchsuchbaren
Datenbank. Vier Funktionen reichen fuer alles.

## Quickstart

```python
from gardener import Gardener
af = Gardener()

# Suchen
af.find("steuer")

# Lesen
af.get("beleg-scanner")

# Schreiben
af.put("notiz", content="Wichtig!", type="memory", tags="todo")

# Ausfuehren
af.run("datei-info", input={"pfad": "/pfad/zur/datei"})
```

## CLI

```bash
python gardener.py find <query>
python gardener.py get <name>
python gardener.py put <name> <text>
python gardener.py run <name>
python gardener.py absorb <datei>
python gardener.py materialize <name>
python gardener.py sync
python gardener.py observe
python gardener.py status
```

## Architektur

```
Gardener/
  gardener.py          # Kern: Gardener-Klasse + CLI
  seed.py             # Initiales Systemwissen
  KONZEPT.md          # Designdokumentation
  README.md           # Diese Datei
  workspace/          # Materialisierter Code zur Ausfuehrung
  blobs/              # Halde fuer grosse Dateien (>50MB)

Lokal (nicht in Cloud):
  AppData/Local/Gardener/
    gardener.db        # System: Wissen, Tools, Blaupausen
    user.db           # User: Memory, Tasks, persoenliche Daten
    blobs/            # Grosse Dateien

User-Ordner (Cloud ok):
  ~/gardener/
    .absorber/        # Dateien hier → automatisch in DB absorbiert
    .output/          # Materialisierte Dateien erscheinen hier
    dokumente/        # Beobachtete Dateien (LLM liest mit)
```

## Datenmodell

Eine Tabelle fuer (fast) alles:

| Typ | Beschreibung | Ziel-DB |
|-----|-------------|---------|
| knowledge | Wissen, Doku, Regeln | gardener.db |
| tool | Ausfuehrbarer Code | gardener.db |
| memory | Erinnerungen, Notizen | user.db |
| task | Aufgaben | user.db |
| document | Absorbierte Dateien | user.db |
| observed | Beobachtete Dateien | user.db |
| config | Konfiguration | user.db |
| export | Zur Materialisierung markiert | user.db |

## Memory (kein separates Gedaechtnis-System!)

Statt 5 Tabellen: alles in `everything` mit Typen und Meta-Feldern.
Die FTS5-Suche IST das assoziative Gedaechtnis.

```python
af.memo("Kurznotiz")                    # Working Memory (verfaellt schnell)
af.lesson("Titel", "Erkenntnis")        # Best Practice (verfaellt kaum)
af.session_end("Zusammenfassung")       # Session-Bericht
af.recall("steuer")                     # Erinnern (sucht + boosted Gewicht)
af.consolidate()                        # Schlaf: Decay + Forget
```

```bash
gardener memo <text>            # Notiz
gardener lesson <titel> [text]  # Lektion
gardener recall <query>         # Erinnern
gardener consolidate            # Konsolidieren
gardener session-end <text>     # Session beenden
```

Details: [KONZEPT.md#memory](KONZEPT.md#memory-kein-separates-gedaechtnis-system-design-entscheidung)

## Tasks (kein separates System!)

Tasks sind Eintraege vom Typ `task` in der `everything`-Tabelle. **Kein separates
Task-System noetig.** `find("steuer")` findet Wissen UND Tasks gleichzeitig.

```python
af.task("steuer-2025", content="Einreichen", priority="high", due="2026-05-31")
af.tasks()                     # Alle Tasks
af.tasks(status="open")        # Nur offene
af.task_done("steuer-2025")    # Erledigt
```

```bash
gardener task <name> [text]     # Erstellen
gardener tasks [status]         # Auflisten
gardener done <name>            # Erledigt
```

Details: [KONZEPT.md#tasks](KONZEPT.md#tasks-kein-separates-system-design-entscheidung)

## Drei Beziehungen zu Dateien

1. **Beobachten:** Datei im Ordner, LLM liest mit (Blick aus dem Fenster)
2. **Absorbieren:** Datei wird in die DB gezogen (lebt jetzt im Haus)
3. **Direkt bearbeiten:** LLM editiert Datei im Ordner (arbeitet vor dem Haus)

## Transporter

```python
af.absorb("/pfad/zur/datei.pdf")   # Datei → DB (dematerialisieren)
af.materialize("datei.pdf")         # DB → Datei (rematerialisieren)
```

## Seeding

```bash
python seed.py    # Fuellt gardener.db mit Grundwissen und Beispiel-Tools
```

## Konzept

Ausfuehrliche Designdokumentation: [KONZEPT.md](KONZEPT.md)
