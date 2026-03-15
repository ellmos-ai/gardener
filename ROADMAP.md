# Gardener ROADMAP

> Aktualisiert: 2026-03-12

## Prototyp (v0.1) -- ERLEDIGT

- [x] Kern: find/get/put/run
- [x] Zwei DBs: gardener.db + user.db (transparent via ATTACH)
- [x] FTS5-Volltextsuche mit Triggern
- [x] .absorber/ (Briefkasten) + .output/ (Ausgabe)
- [x] config.json Sync-Modi (selective/always_absorb/observe_only)
- [x] Blob-Halde fuer grosse Dateien (>50MB)
- [x] Workspace-Materialisierung fuer Code-Ausfuehrung
- [x] Drei Beziehungstypen: beobachten / absorbieren / direkt bearbeiten
- [x] Tasks (task/tasks/done/task_status)
- [x] Memory (memo/lesson/session_end/recall/consolidate)
- [x] Decay/Boost/Forget (Gewichtung im meta-Feld)
- [x] Bridge-Tools: shell, http-fetch, backup, encoding-fix
- [x] Haut-Tools: text-stats, datei-info, ordner-scanner
- [x] list/delete Verwaltung
- [x] CLI mit 19 Befehlen
- [x] seed.py (Grundwissen + Tools)
- [x] Dokumentation: KONZEPT.md, README.md, ERKENNTNISSE.md

---

## Naechste Schritte (v0.2)

### Lernen & Evolution

Tools, Skills und Wissenseintraege sollen wie Memory-Eintraege
altern und frisch bleiben koennen:

- **Decay fuer alles:** Nicht nur memory/lesson/session, sondern auch
  tools und knowledge bekommen Gewicht. Unbenutzte Tools verblassen,
  oft genutzte bleiben frisch.
- **Nutzungs-Tracking:** `run()` erhoeht das Gewicht eines Tools.
  `get()` erhoeht das Gewicht von Knowledge. Wer gebraucht wird, lebt.
- **Natuerliche Selektion:** Wenn ein besseres Tool fuer die gleiche
  Aufgabe gefunden wird, ersetzt es das alte. Das alte verfaellt durch
  Nicht-Nutzung und wird irgendwann von `consolidate()` entfernt.
- **Erfahrung = Gewicht:** Ein Tool das 100x gelaufen ist, hat mehr
  Gewicht als eines das 2x lief. Das spiegelt echte Erfahrung.

```
Neues Tool:     weight=0.5 (unbewiesen)
Nach 10x run:   weight=0.8 (bewaehrt)
Nach 100x run:  weight=1.0 (Kern-Tool)
Nie benutzt:    weight sinkt → consolidate() entfernt es
Ersetzt:        Altes Tool wird nicht mehr gerufen → verfaellt
```

Das ist Lernen: Nicht alles behalten, sondern das Bessere behalten
und das Schlechtere vergessen lassen.

### Weitere Themen v0.2

- [ ] Pinning sinnvoll nutzen (pinned=1 verhindert Decay)
- [ ] Fachtabellen bei Bedarf (shelves-Registry ist vorbereitet)
- [ ] Mehr Bridge-Tools nach Bedarf portieren (aus BACH)

---

## Spaeter (v0.3+)

- [ ] Selbstheilung/Respawn (System-Eintraege aus gardener.db wiederherstellen)
- [ ] DB-Viewer (aus BACH portieren)
- [ ] MCP-Server (Gardener als MCP: find/get/put/run als Tools)
- [ ] Versionierung (Aenderungshistorie in DB)
- [ ] Rechte-Modell (wer darf gardener.db aendern?)
- [ ] Workspace-Verwaltung (aufraeumen, max. Groesse)
- [ ] Externe Anbindungen (MCP, APIs)
- [ ] Multi-LLM (mehrere LLMs teilen sich user.db)

---

## Architektur-Entscheidungen (Logbuch)

| Datum | Entscheidung | Grund |
|-------|-------------|-------|
| 2026-03-12 | Eine Tabelle (everything) | Alles in einer Suche |
| 2026-03-12 | Kein separates Task-System | Tasks = type='task' in everything |
| 2026-03-12 | Kein separates Memory-System | Memory/Lessons = Typen in everything |
| 2026-03-12 | Kein Dematerialize | absorb() IST Dematerialisierung |
| 2026-03-12 | FTS5 statt Trigger-Tabelle | Die Suche IST das assoziative Gedaechtnis |
| 2026-03-12 | Koerper-Modell | Haus=Geist, Haut=Filter-Tools, Draussen=Bridge-Tools |
| 2026-03-12 | Text-Grenze | Im Haus kein Tool, an der Haut Filter, draussen Werkzeuge |
| 2026-03-12 | DB-Viewer aus BACH | Nicht neu bauen, portieren |
| 2026-03-12 | Sketchboard-Modell | LLM IST das Haus (Kontext), DB ist Fotoalbum (Gedaechtnis) |
| 2026-03-12 | Decay fuer alles (geplant) | Tools/Knowledge sollen auch altern koennen |
