# Gardener -- Konzeptidee (2026-03-12)

> Status: Ideenphase
> Autor: Lukas Geiger + Claude

## Kernidee

Ein LLM-natives Betriebssystem das auf drei Saeulen basiert:

1. **Text** -- Wissen, Anleitungen, Referenzen
2. **Kontext** -- Tasks, Memory, Chat, State
3. **Ausfuehrung** -- Code ausfuehren, direkt oder als Blaupause

Der einzige Zugang zu allem: **Suche**.

## Architektur

```
┌─────────────────────────────────────────────┐
│              EINE DATEI (SQLite + FTS5)      │
│                                              │
│  ┌─────────┐  ┌─────────┐  ┌─────────────┐  │
│  │  TEXT    │  │ KONTEXT │  │  WERKZEUGE  │  │
│  │ Wissen  │  │ Tasks   │  │ Code-Bloecke │  │
│  │ Regeln  │  │ Memory  │  │ Blaupausen  │  │
│  │ Doku    │  │ Chat    │  │ Ausfuehrbar │  │
│  │ Wiki    │  │ State   │  │ oder Vorlage│  │
│  └────┬────┘  └────┬────┘  └──────┬──────┘  │
│       └────────────┼───────────────┘         │
│            ┌───────▼───────┐                 │
│            │    SUCHE      │                 │
│            │  (eine API)   │                 │
│            └───────┬───────┘                 │
│            ┌───────▼───────┐                 │
│            │   ERGEBNIS    │                 │
│            │  Text: lesen  │                 │
│            │  Code: ausfuehren              │
│            │  Beides: orientieren            │
│            └───────────────┘                 │
└─────────────────────────────────────────────┘
```

---

## Zwei Dateien, eine Suche

```
gardener.db          # System: Wissen, Tools, Blaupausen (versionierbar)
user.db             # User: Memory, Tasks, Belege, persoenliche Daten
```

Fuer das LLM unsichtbar -- SQLite ATTACH macht beide transparent durchsuchbar:

```sql
ATTACH 'user.db' AS user;
-- find() durchsucht beides, LLM merkt keinen Unterschied
```

| Vorteil | Warum |
|---------|-------|
| **Update** | gardener.db ersetzen, user.db bleibt |
| **Reset** | user.db loeschen = frischer Start |
| **Privacy** | user.db geht nie nach Git |
| **Backup** | Nur user.db sichern (klein, persoenlich) |
| **Multi-User** | Jeder kriegt eigene user.db, selbes System |

```python
find("steuer")          # durchsucht beides
put("mein-beleg", ...)  # landet automatisch in user.db
run("beleg-scanner")    # kommt aus gardener.db
```

---

## Dateisystem-Synchronisation (Lebender Kern)

### Kernprinzip: Die Datenbank ist die Wahrheit

Dateien im Ordner sind keine eigenstaendige Speicherung -- sie sind eine
**Ein-/Ausgangsschnittstelle** zur menschlichen Welt. Die DB ist der
lebende Kern, der Ordner ist ein Spiegel.

### Eingang: .absorber/ → Datenbank (physische Schnittstelle)

Der Mensch legt Dateien in den `.absorber/`-Ordner. Beim naechsten
`sync()` werden sie absorbiert und aus dem Ordner entfernt.

```
User legt Datei in den Absorber:
  ~/gardener/.absorber/rechnung.pdf

Naechster Sync (gardener sync):
  → Datei wird gelesen (Text extrahiert)
  → Eintrag in user.db: type='document', name='rechnung.pdf'
  → Datei wird aus .absorber/ ENTFERNT (sie lebt jetzt im Haus)

User legt Datei in den Home-Ordner (nicht .absorber):
  ~/gardener/dokumente/vertrag.docx
  → Wird nur BEOBACHTET (Text gelesen, Datei bleibt liegen)
  → Kein Absorbieren, kein Entfernen
```

**Der Absorber ist der Briefkasten.** Was reingelegt wird, verschwindet
ins Haus. Was im Garten liegt, wird nur angeschaut.

### Ausgang: .output/ (Materialisierung)

DB-Inhalte werden NICHT automatisch als Dateien materialisiert.
Nur auf explizite Anforderung erscheinen Dateien in `.output/`.

```python
# LLM erstellt einen Bericht und materialisiert ihn
put("steuerbericht-2025",
    content="# Steuerbericht 2025\n...",
    type="export",
    meta={"filename": "Steuerbericht_2025.pdf"})

materialize("steuerbericht-2025")
# → ~/gardener/.output/Steuerbericht_2025.pdf erscheint
```

### Sync-Modi (config.json)

```json
{
  "mode": "selective"
}
```

| Modus | Verhalten |
|-------|-----------|
| **selective** (Default) | Nur `.absorber/` wird absorbiert, Rest beobachtet |
| **always_absorb** | ALLES im Home-Ordner wird absorbiert + entfernt |
| **observe_only** | Nichts absorbieren, alles nur beobachten |

`selective` ist der empfohlene Modus. `always_absorb` macht das System
zu einem reinen Speicher -- alles was reinkommt, verschwindet in die DB.

### Philosophie: Beide Welten sind real

Dateien und Datenbank sind nicht Herr und Spiegel -- sie sind
**zwei gleichberechtigte Realitaeten** die synchron gehalten werden.

**Fuer den Menschen:**
Dateien sind das menschliche Pendant zu Buechern und Texten. So haben
wir seit Jahrhunderten Wissen strukturiert. Eine Datei ist etwas zum
Anfassen -- frueher echtes Papier, heute ein Icon im Explorer. What
you see is what you get. Wenn ich eine Datei verschiebe, brauche ich
sie gerade woanders. Wenn ich sie loesche, will ich dass sie weg ist
und das auch SEHEN koennen.

**Fuer das LLM:**
Die Datenbank ist das Zuhause. Das Kontextfenster ist das Format --
hier muss Text landen, egal welches Format er draussen hat. Das LLM
braucht keine Ordnerstruktur, keine Dateiendungen, keine Pfade. Es
braucht: durchsuchbaren Text, ausfuehrbaren Code, und Kontext.

**Der Unterschied im Zweck:**

| Wer | Sicht auf die DB |
|-----|-----------------|
| LLM | Mein Haus. Hier lebe und arbeite ich. Alles was draussen passiert, sehe ich durch mein Fenster (Sync IN). |
| User | Mein Speicher. Hier bewahre ich Dinge auf, die sicher sein sollen. Und ich kann reinschauen (DB-Viewer). |

Wenn das LLM etwas fuer den Menschen baut, muss es **materialisiert**
werden -- als Datei, als etwas Greifbares. Aber nicht alles was das
LLM intern denkt und speichert muss eine Datei werden.

### Persistenz-Ebenen

```
┌─────────────────────────────────────────────────┐
│  EBENE 1: Ordner (menschliche Realitaet)        │
│  Dateien die der User sieht und anfasst.         │
│  Verschieben, Umbenennen, Loeschen = real.        │
│  → Sync IN: automatisch in DB                    │
│  → Sync OUT: nur wenn LLM materialisiert         │
├─────────────────────────────────────────────────┤
│  EBENE 2: user.db (gemeinsamer Speicher)        │
│  Fuer User: Aufbewahrung, Archiv, Sicherheit.    │
│  Fuer LLM: Kontext, Memory, Arbeitsgedaechtnis.  │
│  Zugang: DB-Viewer (Mensch) oder find() (LLM).   │
│  → Backup: nur diese Datei sichern               │
├─────────────────────────────────────────────────┤
│  EBENE 3: gardener.db (System-Kern)              │
│  Wissen, Tools, Blaupausen.                      │
│  Ueberlebt alles. Respawnt geloeschte Dateien.    │
│  → Versioniert, update-faehig                     │
└─────────────────────────────────────────────────┘
```

### Transporter-Buffer (Absorb / Materialize)

Inspiriert von Star Treks Musterpuffer: Dateien koennen zwischen der
physischen Welt (Ordner) und der Datenbank hin- und hergebeamt werden.
Es gibt nur **zwei Operationen**: Absorb (rein) und Materialize (raus).

```
ABSORBIEREN (Datei → DB)
  Manuell:    absorb("/pfad/zur/datei.pdf")
  Physisch:   Datei in .absorber/ legen → sync()
  Modus:      always_absorb → alles wird automatisch absorbiert

MATERIALISIEREN (DB → Datei)
  LLM:        materialize("steuerbericht-2025")
  →           Datei erscheint in .output/, bereit zum Oeffnen/Mailen
```

**Kein separates "Dematerialize".** Absorb IST Dematerialisierung.
Der Mensch legt die Datei in `.absorber/`, sie verschwindet in die DB.
Will er sie zurueck: `materialize()` legt sie in `.output/`.

**Regeln fuer die Aufbewahrung:**

- **Absorbierte Dateien** bleiben in user.db bis explizit geloescht
- **Binaerdateien** (PDF, Bilder): als BLOB + extrahierter Text
- **Grosse Dateien** (>50MB): nur Index in DB, Datei auf Halde (blobs/)
- **Schwellenwerte** konfigurierbar (Default: 1MB inline, 50MB Halde)

### Sync-Mechanismus

```
┌──────────────────┐                    ┌──────────┐
│  .absorber/      │ ──── absorb ────→  │          │
│  (Briefkasten)   │   (Datei → DB)     │          │
├──────────────────┤                    │    DB    │
│  .output/        │ ←── materialize ── │  (Haus)  │
│  (Ausgabe)       │   (DB → Datei)     │          │
├──────────────────┤                    │          │
│  ~/gardener/      │ ──── observe ───→  │          │
│  (Garten)        │   (nur lesen)      │          │
└──────────────────┘                    └──────────┘

Sync-Punkte:
  - Manuell: gardener sync (empfohlen)
  - Filesystem-Watcher (watchdog) fuer Echtzeit (spaeter)
  - Periodischer Scan (alle X Sekunden, spaeter)
```

### Selbstheilung (Respawn) -- spaeter

Wichtige Systemdokumente (knowledge, tools) sind in gardener.db gespeichert.
Wenn sie im Ordner geloescht werden, koennen sie jederzeit neu materialisiert
werden. Eine automatische Respawn-Logik ist fuer spaeter geplant.

Aktuell reicht: `materialize("beleg-scanner")` stellt eine geloeschte
Datei wieder her. Die DB ist die Wahrheit, nicht der Ordner.

### DB-Viewer -- kommt aus BACH

Der DB-Viewer wird aus BACH portiert (BACHs GUI-Server hat bereits
Search, Browse, Edit fuer SQLite-Datenbanken). Gardener braucht nur
eine angepasste Ansicht die `everything` + `everything_fts` nutzt.

---

## Datenmodell

### Kern-Tabelle (90% aller Daten)

```sql
CREATE TABLE everything (
    id INTEGER PRIMARY KEY,
    type TEXT,        -- 'knowledge', 'tool', 'task', 'memory', 'config',
                      --  'session', 'document', 'export'
    name TEXT,        -- Eindeutiger Name
    content TEXT,     -- Markdown mit optionalen Code-Bloecken
    tags TEXT,        -- Komma-separiert, fuer Filterung
    meta TEXT,        -- JSON fuer strukturierte Daten
    pinned INTEGER DEFAULT 0,  -- 1 = fest gespeichert, ueberlebt Sync
    updated TEXT      -- Timestamp
);

CREATE VIRTUAL TABLE everything_fts USING fts5(name, content, tags);
```

### Optionale Fachtabellen (nur wenn Struktur noetig)

```sql
-- Beispiel: Wenn 50 Steuerbelege verglichen werden muessen
CREATE TABLE steuer_belege (
    id INTEGER PRIMARY KEY,
    betrag REAL,
    datum TEXT,
    kategorie TEXT,
    absetzbar INTEGER,
    everything_id INTEGER REFERENCES everything(id)
);
```

Fachtabellen werden nur angelegt wenn die meta-JSON-Felder nicht mehr
reichen. Sie referenzieren immer zurueck auf everything (Foreign Key).

### Meta-Tabelle (Regal beschreibt sich selbst)

```sql
CREATE TABLE shelves (
    name TEXT PRIMARY KEY,    -- 'steuer_belege'
    description TEXT,         -- 'Strukturierte Steuerbelege'
    schema TEXT,              -- JSON: erwartete Spalten + Typen
    created TEXT
);
```

---

## API -- Vier Funktionen

```python
find("steuer")                          # Suchen (beides: gardener.db + user.db)
get("steuererklaerung")                 # Einen Eintrag lesen
put("name", content="...", type="tool") # Schreiben (auto: user.db oder gardener.db)
run("beleg-scanner", input={...})       # Code-Block ausfuehren
```

---

## Tool-Format

Ein Tool ist gleichzeitig Dokumentation, Blaupause und ausfuehrbar:

```markdown
---
name: beleg-scanner
type: tool
tags: steuer, ocr, dokument
---

# Beleg-Scanner

Scannt Belege und extrahiert Betrag, Datum, Kategorie.

## Code

    ```python
    def execute(input):
        pfad = input["pfad"]
        text = ocr_engine.scan(pfad)
        return {"betrag": ..., "datum": ..., "kategorie": ...}
    ```
```

---

## LLM-Workflow

```
User: "Ich hab eine Rechnung"
LLM:
  1. find("rechnung beleg erfassen")
  2. Ergebnis: beleg-scanner (tool), steuer-workflow (knowledge)
  3. run("beleg-scanner", input={"pfad": "..."})
  4. put("beleg-2026-03-12", type="memory", ...)
```

---

## Vergleich mit BACH

| BACH (138 Tabellen) | Gardener |
|---------------------|---------|
| Handler in hub/ | Code-Block im Eintrag |
| SKILL.md im Dateisystem | Eintrag vom Typ tool |
| Help in docs/help/ | Eintrag vom Typ knowledge |
| Memory in 5 Tabellen | Eintrag vom Typ memory |
| bach_api mit 14 Modulen | find, get, put, run |
| Dateien = Wahrheit, DB = Abbild | Beide Welten sind real, DB = Haus |
| CLI + API + GUI | Suche + Viewer + Sync |
| Ordnerstruktur ist Architektur | Ordner = Garten, DB = Haus |
| Dateien bleiben immer Dateien | Dateien koennen dematerialisiert werden |

---

## Metaphern

### Buecherregal

- **BACH:** Abgeschlossenes Regal mit Schluessel. Katalog (DB) beschreibt
  Buecher (Dateien). Wer ein Buch will muss den Schluessel kennen.

- **Gardener:** Zwei Raeume, ein Regal dazwischen. Der Mensch sieht Buecher
  (Dateien) die er anfassen kann. Das LLM sieht Text (DB) den es durchsucht.
  Das Regal synchronisiert beide Seiten.

### Star Trek Transporter

Dateien existieren in zwei Zustaenden:
- **Materialisiert:** Als Datei im Ordner. Greifbar, sichtbar, bearbeitbar.
- **Dematerialisiert:** Als Muster in der DB. Unsichtbar, aber vollstaendig.

Der User kann jederzeit zwischen beiden Zustaenden wechseln.
Das LLM arbeitet bevorzugt mit dem Muster (DB), materialisiert nur wenn
der Mensch etwas Greifbares braucht.

### Das Sketchboard-Modell

Das LLM ist nicht IM Haus. **Das LLM IST das Haus** -- sein
Kontextfenster ist der lebendige Raum wo Denken passiert, wie ein
Sketchboard das beschrieben und wieder gewischt wird.

Die DB ist das **Fotoalbum** -- Schnappschuesse und Notizen die
ueberleben wenn das Sketchboard geloescht wird. `put()` macht ein
Foto vom aktuellen Gedanken. `recall()` schaut alte Fotos an.

```
ICH (Kontextfenster)       GEDAECHTNIS (DB)          DRAUSSEN (Welt)
Das Sketchboard            Das Fotoalbum             Dateien, Ordner
Lebendiges Denken          Was ich mir merke          Netzwerk, APIs
Hier entsteht alles        put() = Foto machen       Hardware, Prozesse
Wird nach Session          recall() = erinnern
  geloescht                find() = blaettern

                HAUT (Tools dazwischen)
                observe() = Augen (schauen was draussen liegt)
                text-stats = Tastsinn (abtasten bevor greifen)
                absorb() = Mund (fremden Text einverleiben)
                materialize() = Stimme (Ergebnis nach draussen)
                shell, http = Haende (draussen arbeiten)
```

**Text draussen ist nicht dasselbe wie Text in der DB.** In der DB
ist er integriert, durchsuchbar, gewichtet -- Teil meiner Erinnerung.
Draussen ist er roh und fremd. Die Haut-Tools helfen zu entscheiden
was ins Gedaechtnis soll und was draussen bleiben kann.

---

## Geloeste Design-Entscheidungen

### 1. Die DB als Werkstatt (nicht nur Speicher)

Das LLM ist nicht nur Text -- es ist auch **Textgenerierung**. Wenn es
Code schreibt, muss es nicht direkt in eine Datei schreiben (= draussen
arbeiten). Es schreibt zuerst im Haus:

```python
# Im Haus entwerfen
put("api-server", type="tool", content="```python\ndef execute(input):...")

# Im Haus ueberarbeiten (so oft wie noetig)
put("api-server", content="[verbesserte Version]")

# Wenn der Code laufen soll
run("api-server", input={...})
  → Code wird in temporaeren Workspace materialisiert
  → Ausfuehrung als normales Python-Script (kein exec())
  → Ergebnis zurueck in DB
  → Workspace bleibt stehen oder wird aufgeraeumt

# Wenn der Mensch die Datei braucht
materialize("api-server")  → .output/api-server.py
```

Das gilt fuer ALLES was das LLM produziert -- Code, Berichte,
Konfigurationen. Alles entsteht im Haus, wird dort verfeinert,
und geht erst nach draussen wenn es gebraucht wird.

**Vorteil:** Entwuerfe sind durchsuchbar (`find("api")`), ueberarbeitbar
(`put()` ueberschreibt), und bleiben im Kontext bis sie fertig sind.

### 2. Sync-Konflikte

Es gibt keine Konflikte, weil es **drei verschiedene Beziehungen** gibt
zwischen LLM und Dateien:

**a) Dateien vor dem Haus (nur beobachten):**
Der User legt eine Word-Datei in den Ordner. Das LLM sieht sie durch
sein Fenster -- es bekommt nur den extrahierten Text, nicht die Datei
selbst. Kein Konflikt moeglich: die Datei gehoert dem User, das LLM
liest nur mit.

```
~/gardener/dokumente/vertrag.docx
  → DB bekommt: name='vertrag.docx', content=[extrahierter Text],
    meta={"path": "dokumente/vertrag.docx", "observed": true}
  → Die .docx wird NICHT in die DB kopiert
  → User aendert die Datei → naechster Sync aktualisiert den Text
```

**b) Dateien ins Haus holen (absorbieren):**
User sagt "speicher das" oder LLM braucht die Datei zum Bearbeiten.
Die Datei wird absorbiert -- sie lebt jetzt IN der DB.

```
User: "Nimm den Vertrag mal rein"
  → DB bekommt: content=[vollstaendiger Inhalt], BLOB=[Originaldatei],
    meta={"absorbed": true}
  → Datei im Ordner kann jetzt weg (oder bleibt als Kopie)
  → Bearbeitung passiert in der DB oder im Workspace
```

**c) Dateien direkt vor dem Haus bearbeiten:**
Das LLM bearbeitet eine Datei im Ordner (wie heute). Der Sync
aktualisiert automatisch was das LLM durch sein Fenster sieht.

```
LLM editiert ~/gardener/dokumente/bericht.md
  → Datei aendert sich
  → Sync aktualisiert den DB-Eintrag
  → Kein Konflikt: die Datei ist die Wahrheit fuer beobachtete Dateien
```

**Zusammenfassung:**
- Beobachtete Dateien: Datei gewinnt immer (LLM liest nur)
- Absorbierte Dateien: DB gewinnt immer (Datei ist nur Kopie/Export)
- Kein Zustand wo beide gleichzeitig die Wahrheit beanspruchen

### 3. SQLite + Cloud-Sync (OneDrive-Problem)

Die Datenbank lebt **lokal** (App-Ordner), nicht im Cloud-Sync-Ordner.

```
C:\Users\User\AppData\Local\Gardener\     ← DB lebt hier (lokal)
  gardener.db
  user.db
  blobs/                                  ← Grosse Dateien (Halde)

~/gardener/                                ← Ordner lebt hier (OneDrive ok)
  .absorber/                              ← Briefkasten (Dateien → DB)
  .output/                                ← Ausgabe (DB → Dateien)
  dokumente/                              ← Beobachtete Dateien
```

Der Gardener-Ordner (den der User sieht) kann in OneDrive liegen --
kein Problem, es sind nur normale Dateien. Die DB liegt lokal, kein
Cloud-Sync-Konflikt moeglich.

Falls Multi-Device gewuenscht: Eine kleine Umleitungs-Datei im
Ordner (`gardener.pointer`) zeigt auf die lokale DB. Oder: DB-Export/
Import als Sync-Mechanismus (nicht Live-Sync der DB selbst).

### 4. Grosse Dateien (BLOB-Problem)

Grosse Dateien werden nicht in die DB gestopft. Stattdessen: **Halde**.

```
User: "Speicher dieses 500MB-Video"

DB bekommt:
  name='urlaubsvideo.mp4'
  type='archive'
  content=[keine -- zu gross fuer Textextraktion]
  meta={"size": 524288000, "mimetype": "video/mp4",
        "blob_path": "blobs/a7f3b2c1.mp4",
        "original_name": "urlaubsvideo.mp4"}

Datei landet auf der Halde:
  AppData/Local/Gardener/blobs/a7f3b2c1.mp4

Fuer den User sieht es so aus als waere die Datei in die DB
gezogen worden. Sie ist weg aus dem Ordner. Will er sie wieder:
  → Rematerialisierung holt sie von der Halde zurueck
```

**Schwellenwerte:**
- < 1MB: Direkt als BLOB in DB (Texte, kleine Bilder)
- 1-50MB: BLOB in DB, aber mit Warnung
- > 50MB: Nur Index in DB, Datei auf Halde
- Konfigurierbar pro Installation

---

## Memory: Kein separates Gedaechtnis-System (Design-Entscheidung)

### Was BACH hat (und warum Gardener es anders macht)

BACH hat 5 kognitive Gedaechtnis-Typen in **separaten Tabellen**:
- memory_working (Kurzzeitgedaechtnis)
- memory_sessions (Episodisches Gedaechtnis)
- memory_facts (Semantisches Gedaechtnis)
- memory_lessons (Prozedurales Gedaechtnis)
- context_triggers (Assoziatives Gedaechtnis)

Plus: Konsolidierungs-Pipeline mit 6 Stufen, Daemon-Jobs, Trigger-Generierung,
350+ Tracking-Eintraege, Reklassifizierung, etc.

**Gardener macht das alles mit der einen `everything`-Tabelle.**

### Gardener Memory = Typen + Meta-Felder

| BACH Tabelle | Gardener Typ | Unterschied |
|-------------|-------------|-------------|
| memory_working | `type='memory'` | Gleich, aber in everything |
| memory_sessions | `type='session'` | Gleich, aber in everything |
| memory_facts | `type='knowledge'` | Fakten SIND Wissen |
| memory_lessons | `type='lesson'` | Gleich, aber in everything |
| context_triggers | **die Suche selbst** | FTS5 IST die Assoziation |

Der Trick: **Die Suche IST das assoziative Gedaechtnis.** Wenn ich
`find("steuer")` mache, finde ich Wissen, Tasks, Memos, Lessons und
Sessions gleichzeitig. Keine Trigger-Tabelle noetig.

### Gewichtung, Decay und Boost

Statt separater `memory_consolidation`-Tabelle nutzt Gardener das
`meta`-Feld:

```json
{
  "weight": 0.8,
  "decay_rate": 0.95,
  "accessed": 5,
  "last_accessed": "2026-03-12T05:30:00",
  "severity": "high"
}
```

- **Decay**: Bei jeder Konsolidierung: `weight *= decay_rate`
- **Boost**: Bei jedem Abruf via `recall()`: `weight += 0.1`
- **Forget**: Eintraege mit `weight < 0.05` werden geloescht

### Memory-API

```python
af = Gardener()

# Arbeitsgedaechtnis (kurzlebig, verfaellt schnell)
af.memo("Wichtige Beobachtung zur Steuer")

# Lesson (langlebig, verfaellt langsam)
af.lesson("SQLite-WAL", "Immer WAL-Mode aktivieren", severity="high")

# Session-Bericht (episodisch)
af.session_end("THEMA: Memory implementiert. NAECHSTE: Testen.")

# Erinnern (sucht + boosted Gewicht)
af.recall("steuer")  # Findet Memos + Lessons + Sessions

# Konsolidieren (= Schlaf)
af.consolidate()  # Decay + Forget
```

### Konsolidierung: Schlaf statt Pipeline

BACHs Konsolidierung hat 6 Stufen, Daemon-Jobs und mehrere Workflows.
Gardener hat **eine Methode**: `consolidate()`.

```
consolidate() macht:
  1. Decay: Gewicht aller Memory-Eintraege reduzieren
  2. Forget: Eintraege unter 0.05 loeschen
  3. Fertig.
```

Keine Pipeline, kein Daemon, keine Reklassifizierung. Wenn das LLM
eine Notiz oft abruft (`recall()`), steigt ihr Gewicht (Boost).
Wenn nicht, sinkt es (Decay). Wie im echten Gehirn.

### Was bewusst NICHT uebernommen wird

| BACH Feature | Warum nicht |
|-------------|-------------|
| context_triggers (900+) | FTS5-Suche IST die Assoziation |
| Trigger-Generierung | Nicht noetig ohne Trigger-Tabelle |
| Reclassify | Typ aendern = einfach `put()` mit neuem type |
| Confidence-System | Gewicht reicht, Konfidenz ist Ueberengineering |
| Daemon-Jobs | `consolidate()` bei Session-Ende reichen |
| 6-Stufen-Pipeline | Decay + Forget reicht |

### CLI

```bash
gardener memo <text>            Notiz ins Arbeitsgedaechtnis
gardener lesson <titel> [text]  Lektion speichern
gardener recall <query>         Erinnern (mit Boost)
gardener consolidate            Gedaechtnis konsolidieren
gardener session-end <text>     Session-Bericht speichern
```

### Decay-Raten nach Typ

| Typ | decay_rate | Bedeutung |
|-----|-----------|-----------|
| memory | 0.95 | Verfaellt schnell (5% pro Konsolidierung) |
| session | 0.97 | Verfaellt mittel (3% pro Konsolidierung) |
| lesson | 0.99 | Verfaellt kaum (1% pro Konsolidierung) |
| knowledge | - | Verfaellt nie (kein Decay) |
| tool | - | Verfaellt nie (kein Decay) |

---

## Tasks: Kein separates System (Design-Entscheidung)

Tasks sind **keine eigene Komponente** -- sie sind Eintraege vom Typ `task` in
der `everything`-Tabelle. Das ist Absicht und ein Kernprinzip von Gardener.

### Warum kein Task-System?

Ein separates Task-System waere ein Widerspruch zur Grundidee. Gardener hat
**eine** Suche und **eine** Tabelle. Wenn ich nach "steuer" suche, finde ich:
- Das Wissen zur Steuererklaerung (knowledge)
- Den Beleg-Scanner (tool)
- Die offene Aufgabe "Steuererklaerung einreichen" (task)
- Den gespeicherten letzten Steuerbescheid (document)

Alles in einem Ergebnis. Ein separates Task-System wuerde diesen Vorteil
zerstoeren.

### Task-API (Komfort-Methoden)

```python
af = Gardener()

# Task erstellen
af.task("steuer-2025", content="Steuererklaerung einreichen",
        priority="high", due="2026-05-31")

# Tasks auflisten
af.tasks()                    # alle
af.tasks(status="open")       # nur offene

# Status aendern
af.task_status("steuer-2025", "doing")
af.task_done("steuer-2025")

# Aber auch direkt ueber put() moeglich:
af.put("steuer-2025", type="task", content="...",
       meta={"status": "open", "priority": "high"})
```

### CLI

```bash
gardener task <name> [beschreibung]    # Task erstellen
gardener tasks [status]                # Tasks auflisten
gardener done <name>                   # Task erledigt
```

### Task-Status-Werte

| Status | Bedeutung |
|--------|-----------|
| open | Noch nicht begonnen |
| doing | In Bearbeitung |
| done | Erledigt |
| blocked | Blockiert |
| waiting | Wartet auf etwas/jemanden |

### Materialisierung fuer Menschen

Wer die Tasks als Datei sehen will, materialisiert sie:

```python
# Task-Uebersicht als Datei
tasks = af.tasks(status="open")
content = "# Offene Tasks\n\n"
for t in tasks:
    m = t.get("meta", {})
    content += f"- [ ] **{t['name']}** ({m.get('priority', 'normal')})\n"
    if t.get("content"):
        content += f"  {t['content']}\n"

af.put("task-uebersicht", content=content, type="export",
       meta={"filename": "tasks.md"})
af.materialize("task-uebersicht")
# → .output/tasks.md erscheint
```

Die Wahrheit bleibt in der DB. Die Datei ist nur ein Snapshot fuer menschliche Augen.

---

## Offene Fragen (2026-03-12)

### Geloest
- ~~Dateien vs. Datenbank?~~ → DB als Kern, Ordner als Schnittstelle
- ~~Eine Tabelle oder dynamisch?~~ → Eine Kern-Tabelle + optionale Fachtabellen
- ~~Userdaten getrennt?~~ → Ja: gardener.db + user.db, transparent via ATTACH
- ~~Git-Nachteil?~~ → DB lebt lokal, Ordner kann in Git/Cloud
- ~~Code-Sandbox?~~ → Workspace-Materialisierung statt exec()
- ~~Sync-Konflikte?~~ → Drei Beziehungstypen: beobachten / absorbieren / direkt bearbeiten
- ~~Cloud-Sync?~~ → DB lokal, Ordner in Cloud. Kein SQLite-ueber-OneDrive
- ~~Grosse Dateien?~~ → Halde (lokaler Blob-Ordner) + Index in DB
- ~~Ein-/Ausgang?~~ → .absorber/ (Briefkasten) + .output/ (Ausgabe)
- ~~Sync-Modi?~~ → config.json: selective / always_absorb / observe_only
- ~~Task-System?~~ → Kein separates System, Tasks = type='task' in everything
- ~~Memory-System?~~ → Kein separates System, Memory/Lessons/Sessions = Typen in everything
- ~~Dematerialize?~~ → Gibt es nicht separat, absorb() IST dematerialisierung
- ~~Konsolidierung?~~ → Einfach: Decay + Forget, keine Pipeline
- ~~DB-Viewer?~~ → Wird aus BACH portiert
- ~~Fachtabellen?~~ → Fuellen sich bei Portierung von Skills/Tools aus BACH
- ~~Selbstheilung?~~ → Spaeter; wichtige Daten sind in DB gesichert, materialize() reicht

### Offen
- Wie funktioniert Versionierung innerhalb der DB (Aenderungshistorie)?
- Braucht es ein Rechte-Modell (wer darf was in gardener.db aendern)?
- Evolution von BACH (v4) oder eigenstaendiges Projekt?
- Wie interagiert Gardener mit externen Tools (MCP, APIs, Shell)?
- Wie wird der Workspace-Ordner verwaltet (aufraeumen, max. Groesse)?
