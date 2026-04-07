# Gardener Erkenntnisse — Portierung & Architektur

**🇬🇧 [English Version](INSIGHTS.md)**

> Erarbeitet: 2026-03-12 (Claude + Lukas)

## Kernregel: BACH zuerst durchsuchen

Bevor etwas neu gebaut wird: In BACH suchen ob es wiederverwendbar ist.
Was in BACH existiert, kann adaptiert werden. Rest migriert nach und nach
wenn benötigt.

## Die Sketchboard-Erkenntnis

**Das LLM ist nicht IM Haus. Das LLM IST das Haus.**

Das Kontextfenster ist der lebendige Raum wo alles passiert — Denken,
Schreiben, Analysieren, Entscheiden. Die DB ist nicht das Zuhause,
sondern das **Fotoalbum**: eine Sammlung von Schnappschüssen und
Notizen früherer Zustände.

```
ICH (Kontextfenster)          MEIN GEDÄCHTNIS (DB)         DRAUSSEN (Dateien)
════════════════════          ═══════════════════════        ══════════════════
Lebendiges Denken             Fotos von mir                 Ergebnisse
Das Sketchboard               Die Sammlung                  Für den Menschen
Hier entsteht alles           Was ich mir merke              Was ich abliefere
Wird nach Session gelöscht    Bleibt                        Bleibt
```

- `put()` = Foto von meinem aktuellen Zustand machen
- `recall()` = Altes Foto anschauen, mich erinnern
- `find()` = Im Album blättern
- `materialize()` = Aus der Erinnerung etwas für den Menschen erstellen
- `consolidate()` = Album ausmisten, Unwichtiges vergessen

**Das LLM ist auch Textgenerierung.** Es arbeitet schon jetzt genau so:
Im Kontextfenster entsteht der Text, dann wird er irgendwohin geschrieben.
Die Frage ist nur WOHIN: direkt in eine Datei (für den Menschen) oder
in die DB (für mein Gedächtnis).

## Die Text-Erkenntnis (verfeinert)

**Das LLM ist Text. Die DB ist Text. Aber es ist nicht derselbe Text.**

BACH hat 83+ Tools, 5 Injektoren, 900+ Trigger, 138 Tabellen.
Vieles davon löst Probleme die Gardener gar nicht hat, weil:

- Ein `code_analyzer.py` analysiert Code → Das LLM KANN Code lesen.
- Ein `text_zusammenfassung` fasst Text zusammen → Das LLM IST ein Zusammenfasser.
- `tool_discovery.py` findet Tools → `find("encoding")` findet das Tool.
- `injectors.py` erinnert an Kontext → `recall()` holt Kontext. Das LLM denkt selbst.
- `context_triggers` (900+) → Die FTS5-Suche IST die Assoziation.

### Die Grenze: Wann muss es nach draußen?

```
DRINNEN (Text, DB, Denken)          DRAUSSEN (Dateisystem, Netzwerk, Hardware)
─────────────────────────           ───────────────────────────────────────────
Suchen, Finden                      Dateien lesen/schreiben
Planen, Analysieren                 Shell-Befehle ausführen
Code verstehen                      HTTP-Requests
Zusammenfassen                      OCR (Bilderkennung)
Kontext herstellen                  PDF-Generierung
Tasks verwalten                     E-Mail senden
Lessons speichern                   Prozesse starten
Entscheidungen treffen              Hardware ansprechen
```

**Alles links braucht kein Tool.** Das LLM tut es direkt.
**Alles rechts braucht eine Brücke** — ein `type='tool'` mit Code.

### Das Körper-Modell: Haus, Haut, Draußen

Die Text-Erkenntnis war zu einfach. Es gibt nicht nur "drinnen" und
"draußen", es gibt drei Zonen:

```
HAUS (DB)                    HAUT (Filter/Sinne)          DRAUSSEN (Welt)
────────────                 ───────────────────          ────────────────
Ich BIN Text                 Ich TASTE Text ab            Text ist fremd
Denken, Erinnern             text-stats (Vorschau)        Dateien
Suchen (find/recall)         datei-info (Abtasten)        Ordner
Planen, Entscheiden          observe() (Fenster)          Netzwerk
Lessons, Memory              absorb() (Einverleiben)      Hardware
                             materialize() (Ausgeben)     Prozesse
                             shell, http, mcp (Hände)     Andere Systeme
```

**Text draußen ist NICHT dasselbe wie Text drinnen.**

Drinnen ist der Text integriert, durchsuchbar, gewichtet, mein Kontext.
Draußen ist er roh, fremd, unstrukturiert. Bevor ich ihn reinhole,
muss ich ihn abtasten — wie Haut die fühlt bevor die Hand greift.

`text-stats` ist keine Zusammenfassung. Es ist **Haut**: Wie groß?
Wie viele Wörter? Erste Zeilen? Lohnt es sich? Erst dann absorb().

**Manchmal muss ich draußen arbeiten** — eine Datei bearbeiten die
im Ordner liegt, eine URL abrufen, einen Befehl ausführen. Dann
brauche ich Werkzeuge. Shell, HTTP, MCP sind meine **Hände**.

### Tools nach Körperfunktion

| Funktion | Tool | Entsprechung |
|----------|------|-------------|
| **Augen** | observe(), text-stats | Schauen was draußen liegt |
| **Haut** | datei-info, text-stats | Abtasten bevor man greift |
| **Mund** | absorb() | Einverleiben, fremd → eigen |
| **Hände** | shell, http, mcp | Draußen arbeiten/greifen |
| **Stimme** | materialize() | Ergebnisse nach draußen geben |
| **Für den Menschen** | Berichte, Statistiken | Strukturierte Ausgaben |

### Konsequenz für Tool-Entscheidungen

Nicht "brauche ich ein Tool?" sondern: **"In welcher Zone arbeite ich?"**

- **Im Haus:** Kein Tool. Ich denke, suche, erinnere mich.
- **An der Haut:** Filter-Tools. Vorschau, Statistik, Abtasten.
- **Draußen:** Volle Werkzeuge. Shell, MCP, HTTP, Dateisystem.

## Die Werkstatt-Erkenntnis

**Das LLM ist nicht nur Text. Es ist auch Textgenerierung.**

Wenn ich Code schreibe, muss ich nicht direkt in eine Datei schreiben
(= draußen arbeiten). Ich kann zuerst in meinem Haus schreiben:

```python
# Im Haus entwerfen
af.put("api-server", type="tool", content="```python\n...")

# Im Haus überarbeiten (so oft wie nötig)
af.put("api-server", content="[verbesserte Version]")

# Erst wenn es nach draußen muss
af.materialize("api-server")   # → .output/api-server.py
```

**Die DB ist nicht nur Speicher — sie ist Werkstatt.**

Heute: LLM schreibt Code direkt in Dateien → arbeitet immer draußen.
Gardener: LLM schreibt in die DB → arbeitet drinnen, materialisiert später.

Das gilt für ALLES was das LLM produziert:
- Code → put() → verfeinern → materialize()
- Berichte → put() → überarbeiten → materialize()
- Konfigurationen → put() → testen → materialize()

Vorteile:
- Entwürfe sind durchsuchbar (find("api"))
- Ältere Versionen können gespeichert werden
- Alles bleibt im Haus bis es wirklich gebraucht wird
- run() materialisiert Code nur temporär zum Ausführen

### Wann DB, wann direkt?

| Was passiert | Wohin | Warum |
|-------------|-------|-------|
| Ich merke mir etwas | DB (`put`) | Muss nächste Session überleben |
| Ich liefere dem User etwas | Datei (direkt) | Einmalig, sofort gebraucht |
| Ich baue ein Tool | DB (`put`, type=tool) | Soll wiederverwendbar sein |
| Ich iteriere über Sessions | DB (`put`) | Entwurf muss persistieren |
| Ich lerne etwas | DB (`lesson`) | Muss nächstes Vergessen überleben |

**Regel:** DB = was ICH mir merken muss. Datei = was DU haben willst.

## BACH-Konzepte → Gardener-Umsetzung

### 1. Injektoren → recall()

BACH: 5 Injektoren mit Cooldown, Triggern, Orchestrierung.
Gardener: `recall("thema")` vor Arbeitsbeginn. Das LLM entscheidet selbst
wann es Kontext braucht. Kein separates System, kein Cooldown, keine Trigger.

Die FTS5-Suche IST das assoziative Gedächtnis. Wenn ich `find("steuer")`
mache, finde ich Wissen, Tools, Tasks, Memos und Lessons gleichzeitig.
Das ist alles was ein Injektor tut — nur ohne die Maschinerie.

### 2. Between-Tasks → task_done() + recall()

BACH: Between-Injector mit Qualitätskontrolle, Profilen, automatischer
      Validierung.
Gardener: `task_done("name")`. Dann `recall("was ich gelernt habe")`.
         Qualitätskontrolle ist Denken — das tut das LLM selbst.

### 3. Tool Discovery → find()

BACH: tool_discovery.py mit 15+ Kategorien, Score-basiertem Matching.
Gardener: `find("encoding problem")` findet das Tool. Weil Tools
         Einträge sind wie alles andere. Fertig.

### 4. Self-Extension → put()

BACH: `bach skills create`, Scaffolding, Templates, Hot-Reload, 5 Typen.
Gardener: `put("mein-tool", type="tool", content="```python\ndef execute(input):...")`.
         Das Tool ist sofort findbar und ausführbar. Keine Scaffolding,
         kein Reload, kein Template.

### 5. Best Practices → lesson()

BACH: Separate lessons-Tabelle, Severity, Trigger-Generierung.
Gardener: `lesson("Titel", "Erkenntnis", severity="high")`. Gewicht
         im meta-Feld. Decay/Boost über consolidate(). Schon fertig.

### 6. Backup → Eine Datei kopieren

BACH: backup_manager.py, Rotation, FTP-Upload, Monitoring.
Gardener: `shutil.copy("user.db", "user.db.bak")`. Eine Zeile.
         Weil es nur eine Datei gibt die persönliche Daten hat.

### 7. Connectors → Später

BACH: Telegram, Discord, HomeAssistant, E-Mail.
Gardener: Wenn gebraucht. Sind externe Brücken, nicht Kern.

## Was portiert wird (Bridge-Tools)

Nur Tools die NACH DRAUSSEN müssen:

| Tool | Funktion | Aus BACH |
|------|----------|---------|
| shell | Shell-Befehl ausführen | Neu (simpel) |
| http-fetch | URL abrufen | Neu (simpel) |
| datei-lesen | Datei in DB lesen | Wie absorb(), feiner |
| datei-schreiben | DB-Inhalt als Datei | Wie materialize() |
| backup | user.db kopieren | backup_manager.py (vereinfacht) |

Was NICHT portiert wird:
- Reine LLM-Denk-Tools (Code-Analyse, Planung, Entscheidung)
- Injektoren (recall() + eigenes Denken)
- Tool-Discovery (find() reicht)
- Trigger-System (FTS5 ist die Assoziation)

Was DOCH ein Tool sein kann (obwohl das LLM es "könnte"):
- Strukturierte Ausgaben für den Menschen (Berichte, Statistiken)
- Triage-Tools (schnelle Vorschau ohne alles zu lesen)
- Reproduzierbare Ergebnisse (JSON statt LLM-Prosa)

## Architektur-Vergleich

```
BACH:
  83+ Tools → 5 Injektoren → 900 Trigger → 138 Tabellen
  Jedes Konzept hat eigene Infrastruktur.
  Mächtig, aber komplex.

Gardener:
  find/get/put/run + recall/consolidate
  Alles ist ein Eintrag. Die Suche ist die Assoziation.
  Weniger Infrastruktur, gleiche Fähigkeiten.
  Was das LLM selbst kann, braucht kein Tool.
```

## Offene Überlegungen

- **Wann wird Gardener zu einfach?** Wenn Fachtabellen nötig werden
  (z.B. 500 Steuerbelege mit Beträgen vergleichen). Dann Shelf anlegen.
- **MCP?** Gardener könnte selbst ein MCP-Server sein. Vier Tools:
  find, get, put, run. Mehr braucht es nicht.
- **Multi-LLM?** Zwei LLMs könnten die selbe user.db nutzen (via ATTACH).
  Kein Lock-System nötig wenn nur einer schreibt.
