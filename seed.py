# -*- coding: utf-8 -*-
"""
Gardener Seed -- Initiales Wissen fuer das System
==================================================

Fuellt gardener.db mit Grundwissen, Beispiel-Tools und Regeln.
Das sind die Buecher die schon im Haus stehen wenn das LLM einzieht.
"""
from gardener import Gardener


def seed():
    af = Gardener()

    # ------------------------------------------------------------------
    # Systemwissen (gardener.db)
    # ------------------------------------------------------------------

    af.put("gardener-regeln", type="knowledge", target="system", tags="system,regeln",
           content="""# Gardener Regeln

## Vier Funktionen
- **find(query)** -- Durchsucht alles. Der primaere Zugang.
- **get(name)** -- Holt einen einzelnen Eintrag.
- **put(name, ...)** -- Schreibt oder aktualisiert.
- **run(name, input)** -- Fuehrt Code aus.

## Drei Beziehungen zu Dateien
1. **Beobachten:** Datei liegt im Ordner, LLM sieht den Text (Blick aus dem Fenster)
2. **Absorbieren:** Datei wird in die DB gezogen (lebt jetzt im Haus)
3. **Direkt bearbeiten:** LLM editiert Datei im Ordner (arbeitet vor dem Haus)

## Transporter-Buffer
- **Dematerialisieren:** Datei → DB (gardener.absorb)
- **Rematerialisieren:** DB → Datei (gardener.materialize)

## Speicherorte
- gardener.db: System-Wissen, Tools, Blaupausen (versionierbar)
- user.db: User-Daten, Memory, Tasks, absorbierte Dateien
- blobs/: Grosse Dateien auf der Halde (>50MB nur Index in DB)
""")

    af.put("gardener-api", type="knowledge", target="system", tags="system,api,referenz",
           content="""# Gardener API Referenz

## Python

```python
from gardener import Gardener
af = Gardener()

# Suchen
results = af.find("steuer")
results = af.find("scanner", type="tool")

# Lesen
entry = af.get("beleg-scanner")

# Schreiben
af.put("notiz", content="Wichtig!", type="memory", tags="todo")
af.put("mein-tool", content="...", type="tool", target="system")

# Ausfuehren
ok, output = af.run("mein-tool", input={"key": "value"})

# Transporter
af.absorb("/pfad/zur/datei.pdf")       # Datei → DB
af.materialize("datei.pdf")             # DB → Datei

# Beobachten
af.observe()                            # Ordner scannen

# Status
af.status()                             # System-Info
```

## CLI

```bash
python gardener.py find <query>
python gardener.py get <name>
python gardener.py put <name> <text>
python gardener.py run <name>
python gardener.py absorb <datei>
python gardener.py materialize <name>
python gardener.py observe
python gardener.py status
```

## Typen

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
""")

    # ------------------------------------------------------------------
    # Beispiel-Tools
    # ------------------------------------------------------------------

    af.put("datei-info", type="tool", target="system",
           tags="tool,datei,info,utility",
           content="""# Datei-Info

Zeigt Informationen ueber eine Datei an.

## Code

```python
def execute(input):
    import os
    from pathlib import Path

    pfad = Path(input.get("pfad", "."))
    if not pfad.exists():
        return {"error": f"Nicht gefunden: {pfad}"}

    stat = pfad.stat()
    return {
        "name": pfad.name,
        "size": stat.st_size,
        "size_human": f"{stat.st_size / 1024:.1f} KB",
        "extension": pfad.suffix,
        "is_file": pfad.is_file(),
        "is_dir": pfad.is_dir(),
    }
```
""")

    af.put("text-stats", type="tool", target="system",
           tags="tool,text,statistik,triage,vorschau",
           content="""# Text-Stats

Schnelle Statistik ueber einen Text -- Vorschau/Triage BEVOR
das LLM alles liest. Auch nuetzlich um dem Menschen eine
strukturierte Uebersicht zu geben.

Drei Zwecke:
1. Triage: Lohnt es sich den ganzen Text zu absorbieren?
2. Fuer den Menschen: Strukturierte Zusammenfassung
3. Vorschau: Erste Zeilen ohne den ganzen Text zu laden

## Code

```python
def execute(input):
    text = input.get("text", "")
    pfad = input.get("pfad", "")

    if pfad:
        from pathlib import Path
        p = Path(pfad)
        if not p.exists():
            return {"error": f"Nicht gefunden: {pfad}"}
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            return {"error": str(e)}

    if not text:
        return {"error": "Kein Text angegeben (text= oder pfad=)"}

    lines = text.strip().split("\\n")
    words = text.split()

    return {
        "zeilen": len(lines),
        "woerter": len(words),
        "zeichen": len(text),
        "erste_zeilen": "\\n".join(lines[:5]),
        "vorschau": text[:300] + "..." if len(text) > 300 else text,
        "zu_gross": len(text) > 50000,
    }
```
""")

    af.put("ordner-scanner", type="tool", target="system",
           tags="tool,datei,ordner,scan",
           content="""# Ordner-Scanner

Scannt einen Ordner und listet alle Dateien mit Groessen.

## Code

```python
def execute(input):
    from pathlib import Path

    pfad = Path(input.get("pfad", "."))
    if not pfad.exists() or not pfad.is_dir():
        return {"error": f"Kein Ordner: {pfad}"}

    dateien = []
    total_size = 0
    for f in sorted(pfad.rglob("*")):
        if f.is_file():
            size = f.stat().st_size
            total_size += size
            dateien.append({
                "name": str(f.relative_to(pfad)),
                "size": size,
            })

    return {
        "ordner": str(pfad),
        "anzahl": len(dateien),
        "gesamt_mb": round(total_size / 1_000_000, 2),
        "dateien": dateien[:50],
    }
```
""")

    # ------------------------------------------------------------------
    # Bridge-Tools (brauchen Zugang nach draussen)
    # ------------------------------------------------------------------

    af.put("shell", type="tool", target="system",
           tags="tool,shell,system,bridge",
           content="""# Shell

Fuehrt einen Shell-Befehl aus und gibt das Ergebnis zurueck.
Das ist die Bruecke nach draussen -- fuer alles was nicht Text ist.

## Code

```python
def execute(input):
    import subprocess, os
    cmd = input.get("cmd", "")
    if not cmd:
        return {"error": "Kein Befehl angegeben"}

    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True,
            timeout=30, env={**os.environ, "PYTHONIOENCODING": "utf-8"})
        return {
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "code": result.returncode,
            "ok": result.returncode == 0,
        }
    except subprocess.TimeoutExpired:
        return {"error": "Timeout (30s)", "ok": False}
```
""")

    af.put("http-fetch", type="tool", target="system",
           tags="tool,http,web,netzwerk,bridge",
           content="""# HTTP Fetch

Ruft eine URL ab und gibt den Inhalt zurueck.
Bruecke ins Netzwerk.

## Code

```python
def execute(input):
    import urllib.request, urllib.error
    url = input.get("url", "")
    if not url:
        return {"error": "Keine URL angegeben"}

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Gardener/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            content = resp.read().decode("utf-8", errors="replace")
            return {
                "url": url,
                "status": resp.status,
                "length": len(content),
                "content": content[:10000],
                "ok": True,
            }
    except urllib.error.URLError as e:
        return {"error": str(e), "ok": False}
```
""")

    af.put("backup", type="tool", target="system",
           tags="tool,backup,sicherung,bridge",
           content="""# Backup

Erstellt ein Backup der user.db. Eine Datei = ein Backup.
Viel einfacher als komplexe Backup-Rotation.

## Code

```python
def execute(input):
    import shutil
    from pathlib import Path
    from datetime import datetime

    data_dir = Path(input.get("data_dir", "~/.gardener")).expanduser()
    user_db = data_dir / "user.db"
    if not user_db.exists():
        return {"error": "user.db nicht gefunden"}

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = data_dir / "backups"
    backup_dir.mkdir(exist_ok=True)
    dest = backup_dir / f"user_{ts}.db"
    shutil.copy2(str(user_db), str(dest))

    # Alte Backups aufraeumen (max 10 behalten)
    backups = sorted(backup_dir.glob("user_*.db"))
    for old in backups[:-10]:
        old.unlink()

    return {
        "backup": str(dest),
        "size_mb": round(dest.stat().st_size / 1_000_000, 2),
        "kept": min(len(backups), 10),
        "ok": True,
    }
```
""")

    af.put("encoding-fix", type="tool", target="system",
           tags="tool,encoding,utf8,windows,bridge",
           content="""# Encoding Fix

Repariert Encoding-Probleme in Textdateien (Windows cp1252 → UTF-8).
Aus BACH portiert (c_encoding_fixer.py, vereinfacht).

## Code

```python
def execute(input):
    from pathlib import Path

    pfad = Path(input.get("pfad", ""))
    if not pfad.exists():
        return {"error": f"Nicht gefunden: {pfad}"}

    # Versuche verschiedene Encodings
    content = None
    detected = None
    for enc in ["utf-8", "cp1252", "latin-1", "iso-8859-1"]:
        try:
            content = pfad.read_text(encoding=enc)
            detected = enc
            break
        except (UnicodeDecodeError, UnicodeError):
            continue

    if content is None:
        return {"error": "Kein Encoding erkannt"}

    if detected == "utf-8":
        return {"pfad": str(pfad), "encoding": "utf-8", "status": "already ok"}

    # Konvertieren
    if not input.get("dry_run", True):
        pfad.write_text(content, encoding="utf-8")
        return {"pfad": str(pfad), "from": detected, "to": "utf-8", "fixed": True}

    return {"pfad": str(pfad), "from": detected, "to": "utf-8", "dry_run": True}
```
""")

    # ------------------------------------------------------------------
    # Systemwissen: Text-Erkenntnis
    # ------------------------------------------------------------------

    af.put("text-erkenntnis", type="knowledge", target="system",
           tags="system,architektur,philosophie",
           content="""# Die Text-Erkenntnis

Das LLM ist Text. Die DB ist Text. Alles im Haus ist Text.

## Was kein Tool braucht (das LLM kann es selbst)

- Code analysieren (LLM liest Code als Text)
- Text zusammenfassen (LLM IST ein Zusammenfasser)
- Tools finden (find() durchsucht alles)
- Kontext herstellen (recall() + eigenes Denken)
- Planen, Entscheiden, Reflektieren

## Was ein Tool braucht (Bruecke nach draussen)

- Dateien lesen/schreiben (Dateisystem)
- Shell-Befehle ausfuehren (Prozesse)
- URLs abrufen (Netzwerk)
- OCR (Hardware/Library)
- PDF generieren (externe Tools)

## Regel

Bevor ein neues Tool gebaut wird:
1. Kann ich es als Text tun? → Dann kein Tool.
2. Gibt es das in BACH? → Dann portieren/adaptieren.
3. Muss es wirklich nach draussen? → Dann Bridge-Tool.
""")

    # ------------------------------------------------------------------
    # User-Starteintraege
    # ------------------------------------------------------------------

    af.put("willkommen", type="memory", target="user", tags="system,start",
           content="""# Willkommen bei Gardener

Gardener ist dein LLM-natives Betriebssystem.

- Suche nach allem: `find("was auch immer")`
- Speichere Notizen: `put("meine-notiz", content="...")`
- Nutze Tools: `run("datei-info", input={"pfad": "/pfad"})`
- Absorbiere Dateien: `absorb("/pfad/zur/datei")`
""")

    # Ergebnis
    status = af.status()
    print(f"Seed abgeschlossen:")
    print(f"  System-DB: {status['system_entries']} Eintraege")
    print(f"  User-DB:   {status['user_entries']} Eintraege")


if __name__ == "__main__":
    seed()
