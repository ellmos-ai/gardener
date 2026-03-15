# -*- coding: utf-8 -*-
"""
Gardener -- LLM-natives Betriebssystem
======================================

Vier Funktionen. Eine Suche. Zwei Datenbanken.

    from gardener import Gardener
    af = Gardener()
    af.find("steuer")
    af.get("beleg-scanner")
    af.put("notiz", content="Wichtig!", type="memory")
    af.run("beleg-scanner", input={"pfad": "rechnung.pdf"})

Konzept: KONZEPT.md
"""
import json
import hashlib
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union


# ---------------------------------------------------------------------------
# Konfiguration
# ---------------------------------------------------------------------------

# DB lebt lokal (nicht in Cloud-Sync)
LOCAL_DATA_DIR = Path(os.environ.get(
    "GARDENER_DATA",
    os.path.expanduser("~/.gardener")
))

# Der Ordner den der User sieht (kann in OneDrive liegen)
DEFAULT_HOME = Path(os.environ.get(
    "GARDENER_HOME",
    os.path.expanduser("~/gardener")
))

# Schwellenwerte fuer Blob-Halde
BLOB_THRESHOLD_DIRECT = 1_000_000      # < 1MB: direkt in DB
BLOB_THRESHOLD_WARN   = 50_000_000     # < 50MB: BLOB in DB mit Warnung
# > 50MB: nur Index + Halde


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

SCHEMA_SYSTEM = """
CREATE TABLE IF NOT EXISTS everything (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL DEFAULT 'knowledge',
    name TEXT NOT NULL UNIQUE,
    content TEXT DEFAULT '',
    tags TEXT DEFAULT '',
    meta TEXT DEFAULT '{}',
    pinned INTEGER DEFAULT 0,
    created TEXT NOT NULL,
    updated TEXT NOT NULL
);

CREATE VIRTUAL TABLE IF NOT EXISTS everything_fts
    USING fts5(name, content, tags, content=everything, content_rowid=id);

-- Trigger fuer FTS-Sync
CREATE TRIGGER IF NOT EXISTS everything_ai AFTER INSERT ON everything BEGIN
    INSERT INTO everything_fts(rowid, name, content, tags)
    VALUES (new.id, new.name, new.content, new.tags);
END;

CREATE TRIGGER IF NOT EXISTS everything_ad AFTER DELETE ON everything BEGIN
    INSERT INTO everything_fts(everything_fts, rowid, name, content, tags)
    VALUES ('delete', old.id, old.name, old.content, old.tags);
END;

CREATE TRIGGER IF NOT EXISTS everything_au AFTER UPDATE ON everything BEGIN
    INSERT INTO everything_fts(everything_fts, rowid, name, content, tags)
    VALUES ('delete', old.id, old.name, old.content, old.tags);
    INSERT INTO everything_fts(rowid, name, content, tags)
    VALUES (new.id, new.name, new.content, new.tags);
END;

-- Optionale Fachtabellen: Regal-Registry
CREATE TABLE IF NOT EXISTS shelves (
    name TEXT PRIMARY KEY,
    description TEXT DEFAULT '',
    schema_json TEXT DEFAULT '{}',
    created TEXT NOT NULL
);

-- Blob-Index (fuer Dateien auf der Halde)
CREATE TABLE IF NOT EXISTS blobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    everything_id INTEGER REFERENCES everything(id) ON DELETE CASCADE,
    blob_hash TEXT NOT NULL,
    original_name TEXT,
    size INTEGER,
    mimetype TEXT,
    blob_path TEXT NOT NULL,
    created TEXT NOT NULL
);
"""


# ---------------------------------------------------------------------------
# Gardener Core
# ---------------------------------------------------------------------------

class Gardener:
    """Das LLM-native Betriebssystem. Vier Funktionen, eine Suche."""

    def __init__(self, home: Optional[Path] = None, data_dir: Optional[Path] = None):
        self.home = Path(home) if home else DEFAULT_HOME
        self.data_dir = Path(data_dir) if data_dir else LOCAL_DATA_DIR
        self.blob_dir = self.data_dir / "blobs"
        self.workspace_dir = self.data_dir / "workspace"
        self.absorber_dir = self.home / ".absorber"
        self.output_dir = self.home / ".output"

        # Verzeichnisse anlegen
        for d in (self.home, self.data_dir, self.blob_dir,
                  self.workspace_dir, self.absorber_dir, self.output_dir):
            d.mkdir(parents=True, exist_ok=True)

        # Config laden
        self.config = self._load_config()

        # Datenbanken initialisieren
        self.system_db_path = self.data_dir / "gardener.db"
        self.user_db_path = self.data_dir / "user.db"

        self._init_db(self.system_db_path)
        self._init_db(self.user_db_path)

    # ------------------------------------------------------------------
    # DB Setup
    # ------------------------------------------------------------------

    def _init_db(self, db_path: Path):
        """Initialisiert eine Datenbank mit dem Schema."""
        conn = sqlite3.connect(str(db_path))
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.executescript(SCHEMA_SYSTEM)
        conn.commit()
        conn.close()

    def _conn(self, target: str = "user") -> sqlite3.Connection:
        """Gibt eine Connection zurueck. 'user' oder 'system'."""
        path = self.user_db_path if target == "user" else self.system_db_path
        conn = sqlite3.connect(str(path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")

        # Andere DB attachen fuer uebergreifende Suche
        other = self.system_db_path if target == "user" else self.user_db_path
        conn.execute(f"ATTACH DATABASE ? AS other", (str(other),))
        return conn

    def _now(self) -> str:
        return datetime.now().isoformat(timespec="seconds")

    # ------------------------------------------------------------------
    # API: find()
    # ------------------------------------------------------------------

    def find(self, query: str, type: Optional[str] = None,
             limit: int = 20) -> List[Dict]:
        """Durchsucht beide Datenbanken. Der primaere Zugang zu allem.

        Args:
            query: Suchbegriff (Volltextsuche)
            type: Optional filtern nach Typ (knowledge, tool, task, memory, ...)
            limit: Max. Ergebnisse

        Returns:
            Liste von Eintraegen als Dicts
        """
        conn = self._conn("user")
        results = []

        # FTS-Suche in beiden DBs
        for db_prefix, db_label in [("main", "user"), ("other", "system")]:
            try:
                sql = f"""
                    SELECT e.*, '{db_label}' as source
                    FROM {db_prefix}.everything e
                    JOIN {db_prefix}.everything_fts fts ON e.id = fts.rowid
                    WHERE everything_fts MATCH ?
                """
                params = [query]

                if type:
                    sql += f" AND e.type = ?"
                    params.append(type)

                sql += f" ORDER BY rank LIMIT ?"
                params.append(limit)

                rows = conn.execute(sql, params).fetchall()
                for row in rows:
                    results.append(self._row_to_dict(row))
            except Exception:
                # FTS match kann fehlschlagen bei Sonderzeichen
                # Fallback auf LIKE-Suche
                sql = f"""
                    SELECT e.*, '{db_label}' as source
                    FROM {db_prefix}.everything e
                    WHERE (e.name LIKE ? OR e.content LIKE ? OR e.tags LIKE ?)
                """
                like = f"%{query}%"
                params = [like, like, like]

                if type:
                    sql += f" AND e.type = ?"
                    params.append(type)

                sql += f" LIMIT ?"
                params.append(limit)

                rows = conn.execute(sql, params).fetchall()
                for row in rows:
                    results.append(self._row_to_dict(row))

        conn.close()

        # Nach Relevanz sortieren (pinned zuerst, dann nach updated)
        results.sort(key=lambda x: (
            -x.get("pinned", 0),
            x.get("updated", "")
        ), reverse=True)

        return results[:limit]

    # ------------------------------------------------------------------
    # API: get()
    # ------------------------------------------------------------------

    def get(self, name: str) -> Optional[Dict]:
        """Holt einen einzelnen Eintrag nach Name.

        Sucht zuerst in user.db, dann in gardener.db.
        """
        conn = self._conn("user")

        for db_prefix, db_label in [("main", "user"), ("other", "system")]:
            row = conn.execute(
                f"SELECT *, '{db_label}' as source FROM {db_prefix}.everything WHERE name = ?",
                (name,)
            ).fetchone()
            if row:
                result = self._row_to_dict(row)
                conn.close()
                return result

        conn.close()
        return None

    # ------------------------------------------------------------------
    # API: put()
    # ------------------------------------------------------------------

    def put(self, name: str, content: str = "", type: str = "memory",
            tags: str = "", meta: Optional[Dict] = None,
            pinned: bool = False, target: str = "auto") -> Dict:
        """Schreibt oder aktualisiert einen Eintrag.

        Args:
            name: Eindeutiger Name
            content: Inhalt (Markdown, Text, Code)
            type: Typ (knowledge, tool, task, memory, config, document, export)
            tags: Komma-separierte Tags
            meta: Zusaetzliche strukturierte Daten (JSON)
            pinned: Fest gespeichert (ueberlebt Sync)
            target: 'user', 'system', oder 'auto' (auto = user fuer die meisten)

        Returns:
            Der geschriebene Eintrag als Dict
        """
        now = self._now()
        meta_json = json.dumps(meta or {}, ensure_ascii=False)

        # Auto-Target: system nur fuer knowledge und tool
        if target == "auto":
            target = "system" if type in ("knowledge", "tool") else "user"

        conn = self._conn(target)
        db = "main"  # Immer in die primaere DB schreiben

        # Upsert
        existing = conn.execute(
            f"SELECT id FROM {db}.everything WHERE name = ?", (name,)
        ).fetchone()

        if existing:
            conn.execute(f"""
                UPDATE {db}.everything
                SET content = ?, type = ?, tags = ?, meta = ?,
                    pinned = ?, updated = ?
                WHERE name = ?
            """, (content, type, tags, meta_json, int(pinned), now, name))
        else:
            conn.execute(f"""
                INSERT INTO {db}.everything
                    (name, content, type, tags, meta, pinned, created, updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (name, content, type, tags, meta_json, int(pinned), now, now))

        conn.commit()
        conn.close()

        return self.get(name)

    # ------------------------------------------------------------------
    # API: run()
    # ------------------------------------------------------------------

    def run(self, name: str, input: Optional[Dict] = None) -> Tuple[bool, str]:
        """Fuehrt den Code-Block eines Eintrags aus.

        Materialisiert den Code in einen Workspace, fuehrt ihn aus,
        gibt das Ergebnis zurueck.

        Args:
            name: Name des Eintrags (muss type='tool' sein)
            input: Parameter fuer die Ausfuehrung

        Returns:
            (success, output) Tuple
        """
        entry = self.get(name)
        if not entry:
            return False, f"Eintrag '{name}' nicht gefunden."

        # Code-Block aus Content extrahieren
        code = self._extract_code(entry["content"])
        if not code:
            return False, f"Kein ausfuehrbarer Code-Block in '{name}' gefunden."

        # Workspace materialisieren
        ws_dir = self.workspace_dir / name.replace("/", "_")
        ws_dir.mkdir(parents=True, exist_ok=True)
        script_path = ws_dir / "run.py"

        # Runner-Script erstellen
        runner = self._build_runner(code, input or {})
        script_path.write_text(runner, encoding="utf-8")

        # Ausfuehren
        try:
            result = subprocess.run(
                [sys.executable, str(script_path)],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=str(ws_dir),
                env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            )

            output = result.stdout
            if result.returncode != 0:
                output += f"\n[STDERR] {result.stderr}" if result.stderr else ""
                return False, output.strip()

            return True, output.strip()

        except subprocess.TimeoutExpired:
            return False, f"Timeout: '{name}' hat laenger als 60s gedauert."
        except Exception as e:
            return False, f"Fehler bei Ausfuehrung von '{name}': {e}"

    # ------------------------------------------------------------------
    # Erweiterte Operationen
    # ------------------------------------------------------------------

    def absorb(self, file_path: Union[str, Path]) -> Dict:
        """Absorbiert eine Datei in die DB (Transporter: Materialisiert → DB).

        Kleine Dateien: Inhalt direkt in DB.
        Grosse Dateien: Index in DB + Datei auf Halde.
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Datei nicht gefunden: {file_path}")

        size = file_path.stat().st_size
        name = file_path.name
        content = ""
        meta = {
            "original_path": str(file_path),
            "size": size,
            "absorbed": True,
            "absorbed_at": self._now(),
        }

        # Text extrahieren (wenn moeglich)
        try:
            if file_path.suffix.lower() in ('.txt', '.md', '.py', '.json', '.csv',
                                             '.yaml', '.yml', '.xml', '.html', '.css',
                                             '.js', '.ts', '.sh', '.bat', '.sql', '.log'):
                content = file_path.read_text(encoding="utf-8", errors="replace")
                meta["mimetype"] = "text/plain"
            else:
                meta["mimetype"] = self._guess_mimetype(file_path.suffix)
        except Exception:
            meta["mimetype"] = "application/octet-stream"

        # Groesse entscheidet ueber Speicherort
        if size > BLOB_THRESHOLD_WARN:
            # Halde: nur Index + Datei kopieren
            blob_hash = self._hash_file(file_path)
            blob_dest = self.blob_dir / f"{blob_hash}{file_path.suffix}"
            shutil.copy2(str(file_path), str(blob_dest))
            meta["blob_path"] = str(blob_dest)
            meta["blob_hash"] = blob_hash
            meta["storage"] = "halde"
        elif size > BLOB_THRESHOLD_DIRECT:
            # In DB als BLOB (ueber blobs-Tabelle)
            meta["storage"] = "blob"
            blob_hash = self._hash_file(file_path)
            blob_dest = self.blob_dir / f"{blob_hash}{file_path.suffix}"
            shutil.copy2(str(file_path), str(blob_dest))
            meta["blob_path"] = str(blob_dest)
            meta["blob_hash"] = blob_hash
        else:
            # Klein genug: direkt in content (wenn Text) oder blob
            meta["storage"] = "inline"
            if not content:
                blob_hash = self._hash_file(file_path)
                blob_dest = self.blob_dir / f"{blob_hash}{file_path.suffix}"
                shutil.copy2(str(file_path), str(blob_dest))
                meta["blob_path"] = str(blob_dest)
                meta["blob_hash"] = blob_hash

        # Tags aus Dateiendung
        tags = f"datei,{file_path.suffix.lstrip('.')}"

        return self.put(name, content=content, type="document",
                        tags=tags, meta=meta, target="user", pinned=True)

    def materialize(self, name: str, dest: Optional[Path] = None) -> Optional[Path]:
        """Materialisiert einen DB-Eintrag als Datei (Transporter: DB → Datei).

        Args:
            name: Name des Eintrags
            dest: Zielordner (Default: ~/gardener/export/)

        Returns:
            Pfad zur materialisierten Datei oder None
        """
        entry = self.get(name)
        if not entry:
            return None

        dest = dest or self.output_dir
        dest.mkdir(parents=True, exist_ok=True)

        meta = entry.get("meta", {})
        if isinstance(meta, str):
            meta = json.loads(meta)

        # Blob von Halde?
        blob_path = meta.get("blob_path")
        if blob_path and Path(blob_path).exists():
            original_name = meta.get("original_name", name)
            out_path = dest / original_name
            shutil.copy2(blob_path, str(out_path))
            return out_path

        # Text-Content als Datei schreiben
        suffix = meta.get("format", "md")
        filename = meta.get("filename", f"{name}.{suffix}")
        out_path = dest / filename
        out_path.write_text(entry["content"], encoding="utf-8")
        return out_path

    def observe(self, directory: Optional[Path] = None) -> List[Dict]:
        """Beobachtet den Ordner und aktualisiert die DB (Blick aus dem Fenster).

        Scannt den Home-Ordner und erstellt/aktualisiert observed-Eintraege.

        Returns:
            Liste der beobachteten Dateien
        """
        directory = directory or self.home
        observed = []

        for file_path in directory.rglob("*"):
            if not file_path.is_file():
                continue
            # Interne Ordner ueberspringen
            rel = file_path.relative_to(directory)
            if str(rel).startswith(("export", ".gardener", "__pycache__")):
                continue

            name = f"observed/{rel}"
            content = ""

            # Text extrahieren wenn moeglich
            if file_path.suffix.lower() in ('.txt', '.md', '.py', '.json', '.csv',
                                             '.yaml', '.yml', '.xml', '.html'):
                try:
                    content = file_path.read_text(encoding="utf-8", errors="replace")
                except Exception:
                    content = f"[Datei nicht lesbar: {file_path.suffix}]"
            else:
                content = f"[Binaerdatei: {file_path.name}, {file_path.stat().st_size} Bytes]"

            meta = {
                "path": str(file_path),
                "size": file_path.stat().st_size,
                "modified": datetime.fromtimestamp(
                    file_path.stat().st_mtime
                ).isoformat(timespec="seconds"),
                "observed": True,
            }

            entry = self.put(name, content=content, type="observed",
                             tags=f"datei,{file_path.suffix.lstrip('.')}",
                             meta=meta, target="user")
            observed.append(entry)

        return observed

    def sync(self) -> Dict:
        """Fuehrt einen Sync-Zyklus durch: Absorber leeren + Ordner beobachten.

        1. .absorber/ → Dateien absorbieren und aus Ordner entfernen
        2. Rest des Home-Ordners → beobachten (nur Text lesen)
        3. Falls mode='always_absorb' → alles absorbieren

        Returns:
            {"absorbed": int, "observed": int, "mode": str}
        """
        mode = self.config.get("mode", "selective")
        absorbed_count = 0
        observed_count = 0

        # --- 1. Absorber leeren ---
        if self.absorber_dir.exists():
            for file_path in list(self.absorber_dir.rglob("*")):
                if not file_path.is_file():
                    continue
                try:
                    self.absorb(file_path)
                    file_path.unlink()  # Datei verschwindet nach Absorption
                    absorbed_count += 1
                except Exception as e:
                    # Fehler loggen aber weitermachen
                    self.put(f"sync-error/{file_path.name}",
                             content=f"Absorb fehlgeschlagen: {e}",
                             type="memory", tags="error,sync")

        # --- 2. Ordner beobachten oder absorbieren ---
        for file_path in self.home.rglob("*"):
            if not file_path.is_file():
                continue

            # Interne Ordner ueberspringen
            rel = str(file_path.relative_to(self.home))
            if rel.startswith((".absorber", ".output", ".gardener", "__pycache__")):
                continue

            if mode == "always_absorb":
                try:
                    self.absorb(file_path)
                    file_path.unlink()
                    absorbed_count += 1
                except Exception:
                    pass
            else:
                # Beobachten (nur Text extrahieren, Datei nicht anfassen)
                name = f"observed/{rel}"
                content = ""

                if file_path.suffix.lower() in ('.txt', '.md', '.py', '.json', '.csv',
                                                 '.yaml', '.yml', '.xml', '.html'):
                    try:
                        content = file_path.read_text(encoding="utf-8", errors="replace")
                    except Exception:
                        content = f"[Nicht lesbar: {file_path.suffix}]"
                else:
                    content = f"[Binaerdatei: {file_path.name}, {file_path.stat().st_size} Bytes]"

                meta = {
                    "path": str(file_path),
                    "size": file_path.stat().st_size,
                    "modified": datetime.fromtimestamp(
                        file_path.stat().st_mtime
                    ).isoformat(timespec="seconds"),
                    "observed": True,
                }

                self.put(name, content=content, type="observed",
                         tags=f"datei,{file_path.suffix.lstrip('.')}",
                         meta=meta, target="user")
                observed_count += 1

        return {"absorbed": absorbed_count, "observed": observed_count, "mode": mode}

    # ------------------------------------------------------------------
    # Task-Komfort (Tasks = Eintraege vom Typ 'task' in user.db)
    # ------------------------------------------------------------------

    def tasks(self, status: Optional[str] = None) -> List[Dict]:
        """Listet alle Tasks. Optional nach Status filtern.

        Status-Werte: open, doing, done, blocked, waiting
        """
        conn = self._conn("user")
        sql = "SELECT *, 'user' as source FROM main.everything WHERE type = 'task'"
        params = []

        if status:
            sql += " AND json_extract(meta, '$.status') = ?"
            params.append(status)

        sql += " ORDER BY json_extract(meta, '$.priority') DESC, updated DESC"
        rows = conn.execute(sql, params).fetchall()
        conn.close()
        return [self._row_to_dict(row) for row in rows]

    def task(self, name: str, content: str = "", priority: str = "normal",
             due: Optional[str] = None, tags: str = "") -> Dict:
        """Erstellt oder aktualisiert einen Task.

        Args:
            name: Task-Name (wird zum Key)
            content: Beschreibung
            priority: low, normal, high, critical
            due: Faelligkeitsdatum (ISO)
            tags: Komma-separierte Tags
        """
        meta = {"status": "open", "priority": priority}
        if due:
            meta["due"] = due

        return self.put(name, content=content, type="task",
                        tags=f"task,{tags}" if tags else "task",
                        meta=meta, target="user")

    def task_done(self, name: str) -> Optional[Dict]:
        """Markiert einen Task als erledigt."""
        entry = self.get(name)
        if not entry or entry.get("type") != "task":
            return None
        meta = entry.get("meta", {})
        if isinstance(meta, str):
            meta = json.loads(meta)
        meta["status"] = "done"
        meta["done_at"] = self._now()
        return self.put(name, content=entry["content"], type="task",
                        tags=entry.get("tags", ""), meta=meta, target="user")

    def task_status(self, name: str, status: str) -> Optional[Dict]:
        """Setzt den Status eines Tasks (open, doing, done, blocked, waiting)."""
        entry = self.get(name)
        if not entry or entry.get("type") != "task":
            return None
        meta = entry.get("meta", {})
        if isinstance(meta, str):
            meta = json.loads(meta)
        meta["status"] = status
        return self.put(name, content=entry["content"], type="task",
                        tags=entry.get("tags", ""), meta=meta, target="user")

    # ------------------------------------------------------------------
    # Memory & Lernen (alles in everything, keine Extra-Tabellen)
    # ------------------------------------------------------------------

    def memo(self, text: str, tags: str = "") -> Dict:
        """Schreibt ins Arbeitsgedaechtnis (Working Memory).

        Kurzlebige Notizen fuer die aktuelle Session.
        Werden bei Konsolidierung verdichtet oder vergessen.
        """
        name = f"memo/{self._now().replace(':', '-')}"
        return self.put(name, content=text, type="memory",
                        tags=f"working,{tags}" if tags else "working",
                        meta={"weight": 0.5, "accessed": 0,
                              "session": self._now()[:10]},
                        target="user")

    def lesson(self, title: str, content: str = "",
               severity: str = "medium", tags: str = "") -> Dict:
        """Speichert eine Lektion (Best Practice / Lesson Learned).

        Lessons haben hohes Gewicht und verfallen langsamer.
        severity: low, medium, high, critical
        """
        weight_map = {"low": 0.5, "medium": 0.7, "high": 0.9, "critical": 1.0}
        name = f"lesson/{title.lower().replace(' ', '-')[:50]}"
        return self.put(name, content=content or title, type="lesson",
                        tags=f"lesson,{severity},{tags}" if tags else f"lesson,{severity}",
                        meta={"weight": weight_map.get(severity, 0.7),
                              "severity": severity, "accessed": 0,
                              "decay_rate": 0.99},  # Lessons verfallen langsam
                        target="user")

    def session_end(self, summary: str) -> Dict:
        """Speichert einen Session-Bericht (Episodisches Gedaechtnis).

        Format empfohlen: "THEMA: Was. ERLEDIGT: Was. NAECHSTE: Was."
        """
        name = f"session/{self._now()[:10]}"
        return self.put(name, content=summary, type="session",
                        tags="session,episodisch",
                        meta={"weight": 0.8, "accessed": 0,
                              "decay_rate": 0.97},
                        target="user")

    def recall(self, query: str, limit: int = 5) -> List[Dict]:
        """Erinnert sich -- sucht in Memory, Lessons und Sessions.

        Wie find(), aber auf Gedaechtnis-Typen beschraenkt und
        erhoeht das Gewicht abgerufener Eintraege (Boost).
        """
        conn = self._conn("user")
        results = []

        for mem_type in ("memory", "lesson", "session"):
            try:
                sql = """
                    SELECT *, 'user' as source
                    FROM main.everything e
                    JOIN main.everything_fts fts ON e.id = fts.rowid
                    WHERE everything_fts MATCH ? AND e.type = ?
                    ORDER BY rank LIMIT ?
                """
                rows = conn.execute(sql, (query, mem_type, limit)).fetchall()
                for row in rows:
                    d = self._row_to_dict(row)
                    results.append(d)
                    # Boost: Gewicht erhoehen bei Abruf
                    self._boost(conn, row["id"])
            except Exception:
                sql = """
                    SELECT *, 'user' as source
                    FROM main.everything e
                    WHERE (e.name LIKE ? OR e.content LIKE ?) AND e.type = ?
                    LIMIT ?
                """
                like = f"%{query}%"
                rows = conn.execute(sql, (like, like, mem_type, limit)).fetchall()
                for row in rows:
                    d = self._row_to_dict(row)
                    results.append(d)
                    self._boost(conn, row["id"])

        conn.commit()
        conn.close()

        # Nach Gewicht sortieren
        results.sort(key=lambda x: x.get("meta", {}).get("weight", 0.5), reverse=True)
        return results[:limit]

    def consolidate(self) -> Dict:
        """Konsolidiert das Gedaechtnis (= Schlaf).

        1. Decay: Gewicht aller Eintraege reduzieren
        2. Forget: Eintraege unter Schwellenwert deaktivieren
        3. Stats zurueckgeben

        Einfacher als BACHs 6-Stufen-Pipeline, aber gleicher Effekt:
        Wichtiges bleibt, Unwichtiges verblasst.
        """
        conn = self._conn("user")
        now = self._now()
        stats = {"decayed": 0, "forgotten": 0, "kept": 0}

        # Alle Memory-artigen Eintraege mit Gewicht
        rows = conn.execute("""
            SELECT id, name, type, meta FROM main.everything
            WHERE type IN ('memory', 'lesson', 'session')
        """).fetchall()

        for row in rows:
            meta = row["meta"]
            if isinstance(meta, str):
                try:
                    meta = json.loads(meta)
                except (json.JSONDecodeError, TypeError):
                    meta = {}

            weight = meta.get("weight", 0.5)
            decay_rate = meta.get("decay_rate", 0.95)

            # Decay anwenden
            new_weight = weight * decay_rate
            meta["weight"] = round(new_weight, 4)
            meta["last_decay"] = now

            if new_weight < 0.05:
                # Vergessen: Eintrag loeschen (unter Schwelle)
                conn.execute("DELETE FROM main.everything WHERE id = ?", (row["id"],))
                stats["forgotten"] += 1
            else:
                # Gewicht aktualisieren
                conn.execute(
                    "UPDATE main.everything SET meta = ? WHERE id = ?",
                    (json.dumps(meta, ensure_ascii=False), row["id"])
                )
                if new_weight < weight:
                    stats["decayed"] += 1
                else:
                    stats["kept"] += 1

        conn.commit()
        conn.close()
        return stats

    def _boost(self, conn: sqlite3.Connection, entry_id: int, amount: float = 0.1):
        """Erhoeht das Gewicht eines Eintrags (Boost bei Abruf)."""
        row = conn.execute(
            "SELECT meta FROM main.everything WHERE id = ?", (entry_id,)
        ).fetchone()
        if not row:
            return

        meta = row["meta"]
        if isinstance(meta, str):
            try:
                meta = json.loads(meta)
            except (json.JSONDecodeError, TypeError):
                meta = {}

        weight = min(1.0, meta.get("weight", 0.5) + amount)
        accessed = meta.get("accessed", 0) + 1
        meta["weight"] = round(weight, 4)
        meta["accessed"] = accessed
        meta["last_accessed"] = self._now()

        conn.execute(
            "UPDATE main.everything SET meta = ? WHERE id = ?",
            (json.dumps(meta, ensure_ascii=False), entry_id)
        )

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def delete(self, name: str) -> bool:
        """Loescht einen Eintrag aus der DB.

        Sucht in user.db, dann in system.db.
        Returns: True wenn geloescht, False wenn nicht gefunden.
        """
        for target in ("user", "system"):
            conn = self._conn(target)
            row = conn.execute(
                "SELECT id FROM main.everything WHERE name = ?", (name,)
            ).fetchone()
            if row:
                conn.execute("DELETE FROM main.everything WHERE id = ?", (row["id"],))
                conn.commit()
                conn.close()
                return True
            conn.close()
        return False

    def list(self, type: Optional[str] = None, limit: int = 50) -> List[Dict]:
        """Listet alle Eintraege. Optional nach Typ filtern.

        Ohne Suchbegriff -- einfach alles zeigen.
        """
        conn = self._conn("user")
        results = []

        for db_prefix, db_label in [("main", "user"), ("other", "system")]:
            sql = f"SELECT *, '{db_label}' as source FROM {db_prefix}.everything"
            params = []

            if type:
                sql += " WHERE type = ?"
                params.append(type)

            sql += " ORDER BY updated DESC LIMIT ?"
            params.append(limit)

            rows = conn.execute(sql, params).fetchall()
            for row in rows:
                results.append(self._row_to_dict(row))

        conn.close()
        return results[:limit]

    def status(self) -> Dict:
        """Gibt den Status des Systems zurueck."""
        info = {
            "home": str(self.home),
            "data_dir": str(self.data_dir),
            "system_db": str(self.system_db_path),
            "user_db": str(self.user_db_path),
        }

        # Counts
        conn = self._conn("user")
        for db_prefix, db_label in [("main", "user"), ("other", "system")]:
            count = conn.execute(
                f"SELECT COUNT(*) FROM {db_prefix}.everything"
            ).fetchone()[0]
            info[f"{db_label}_entries"] = count

            # Nach Typ
            rows = conn.execute(
                f"SELECT type, COUNT(*) as cnt FROM {db_prefix}.everything GROUP BY type"
            ).fetchall()
            info[f"{db_label}_types"] = {row["type"]: row["cnt"] for row in rows}

        conn.close()

        # Blob-Halde
        blob_count = len(list(self.blob_dir.glob("*")))
        blob_size = sum(f.stat().st_size for f in self.blob_dir.glob("*") if f.is_file())
        info["blobs"] = {"count": blob_count, "size_mb": round(blob_size / 1_000_000, 1)}

        return info

    # ------------------------------------------------------------------
    # Config
    # ------------------------------------------------------------------

    def _load_config(self) -> Dict:
        """Laedt config.json aus dem Home-Ordner."""
        config_path = self.home / "config.json"
        if config_path.exists():
            try:
                return json.loads(config_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass

        # Default-Config erstellen
        default = {
            "mode": "selective",
            "_modes": {
                "selective": "Nur .absorber/ wird absorbiert (Default)",
                "always_absorb": "Alles im Home-Ordner wird absorbiert",
                "observe_only": "Nichts absorbieren, nur beobachten"
            }
        }
        config_path.write_text(
            json.dumps(default, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return default

    # ------------------------------------------------------------------
    # Hilfsfunktionen
    # ------------------------------------------------------------------

    def _row_to_dict(self, row: sqlite3.Row) -> Dict:
        """Konvertiert eine DB-Row in ein Dict."""
        d = dict(row)
        # meta als JSON parsen
        if "meta" in d and isinstance(d["meta"], str):
            try:
                d["meta"] = json.loads(d["meta"])
            except (json.JSONDecodeError, TypeError):
                pass
        return d

    def _extract_code(self, content: str) -> Optional[str]:
        """Extrahiert den ersten ```python Code-Block aus Markdown."""
        pattern = r'```python\s*\n(.*?)```'
        match = re.search(pattern, content, re.DOTALL)
        if match:
            return match.group(1).strip()
        return None

    def _build_runner(self, code: str, input_data: Dict) -> str:
        """Baut ein ausfuehrbares Runner-Script."""
        input_json = json.dumps(input_data, ensure_ascii=False)
        return f'''# -*- coding: utf-8 -*-
# Auto-generated Gardener Runner
import json
import sys

input = json.loads({repr(input_json)})

{code}

if 'execute' in dir():
    result = execute(input)
    if result is not None:
        print(json.dumps(result, ensure_ascii=False, indent=2))
'''

    def _hash_file(self, file_path: Path) -> str:
        """Berechnet SHA256 einer Datei."""
        h = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()[:16]

    def _guess_mimetype(self, suffix: str) -> str:
        """Einfache Mimetype-Erkennung."""
        types = {
            '.pdf': 'application/pdf',
            '.doc': 'application/msword',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.xls': 'application/vnd.ms-excel',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.mp4': 'video/mp4',
            '.mp3': 'audio/mpeg',
            '.zip': 'application/zip',
        }
        return types.get(suffix.lower(), 'application/octet-stream')


# ---------------------------------------------------------------------------
# CLI (minimal)
# ---------------------------------------------------------------------------

def main():
    """Minimales CLI fuer Gardener."""
    af = Gardener()

    if len(sys.argv) < 2:
        print("Gardener -- LLM-natives Betriebssystem")
        print()
        s = af.status()
        print(f"  Home:      {s['home']}")
        print(f"  Daten:     {s['data_dir']}")
        print(f"  System-DB: {s['system_entries']} Eintraege")
        print(f"  User-DB:   {s['user_entries']} Eintraege")
        print(f"  Halde:     {s['blobs']['count']} Dateien ({s['blobs']['size_mb']} MB)")
        print()
        print("Befehle:")
        print("  gardener find <query>        Suchen")
        print("  gardener get <name>          Eintrag lesen")
        print("  gardener put <name> <text>   Eintrag schreiben")
        print("  gardener run <name>          Tool ausfuehren")
        print("  gardener absorb <datei>      Datei absorbieren (Transporter IN)")
        print("  gardener materialize <name>  Eintrag als Datei (Transporter OUT)")
        print("  gardener sync                Absorber leeren + Ordner beobachten")
        print("  gardener observe             Ordner scannen (nur beobachten)")
        print("  gardener memo <text>         Notiz ins Arbeitsgedaechtnis")
        print("  gardener lesson <titel> [text] Lektion speichern (Best Practice)")
        print("  gardener recall <query>      Erinnern (sucht in Memory/Lessons/Sessions)")
        print("  gardener consolidate         Gedaechtnis konsolidieren (Decay/Forget)")
        print("  gardener session-end <text>  Session-Bericht speichern")
        print("  gardener tasks [status]      Tasks auflisten (open/doing/done)")
        print("  gardener task <name> [text]  Task erstellen")
        print("  gardener done <name>         Task als erledigt markieren")
        print("  gardener list [typ]          Alle Eintraege auflisten")
        print("  gardener delete <name>       Eintrag loeschen")
        print("  gardener status              System-Status")
        return

    cmd = sys.argv[1]

    if cmd == "find":
        query = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""
        results = af.find(query)
        for r in results:
            src = r.get("source", "?")
            print(f"  [{r['type']:10s}] {r['name']:30s} ({src})")
        if not results:
            print("  Keine Ergebnisse.")

    elif cmd == "get":
        name = sys.argv[2] if len(sys.argv) > 2 else ""
        entry = af.get(name)
        if entry:
            print(f"Name:    {entry['name']}")
            print(f"Typ:     {entry['type']}")
            print(f"Tags:    {entry['tags']}")
            print(f"Source:  {entry.get('source', '?')}")
            print(f"Updated: {entry['updated']}")
            print(f"---")
            print(entry['content'][:2000])
        else:
            print(f"  Nicht gefunden: {name}")

    elif cmd == "put":
        name = sys.argv[2] if len(sys.argv) > 2 else "unnamed"
        content = " ".join(sys.argv[3:]) if len(sys.argv) > 3 else ""
        entry = af.put(name, content=content)
        print(f"  [OK] {entry['name']} ({entry['type']})")

    elif cmd == "run":
        name = sys.argv[2] if len(sys.argv) > 2 else ""
        ok, output = af.run(name)
        print(f"  [{'OK' if ok else 'FEHLER'}] {output}")

    elif cmd == "absorb":
        path = sys.argv[2] if len(sys.argv) > 2 else ""
        entry = af.absorb(path)
        print(f"  [OK] {entry['name']} absorbiert ({entry['meta'].get('storage', '?')})")

    elif cmd == "materialize":
        name = sys.argv[2] if len(sys.argv) > 2 else ""
        result = af.materialize(name)
        if result:
            print(f"  [OK] Materialisiert: {result}")
        else:
            print(f"  Nicht gefunden: {name}")

    elif cmd == "observe":
        observed = af.observe()
        print(f"  {len(observed)} Dateien beobachtet")
        for o in observed[:10]:
            print(f"    {o['name']}")

    elif cmd == "sync":
        result = af.sync()
        print(f"  Modus: {result['mode']}")
        print(f"  Absorbiert: {result['absorbed']}")
        print(f"  Beobachtet: {result['observed']}")

    elif cmd == "list":
        type_filter = sys.argv[2] if len(sys.argv) > 2 else None
        entries = af.list(type=type_filter)
        for e in entries:
            src = e.get("source", "?")
            print(f"  [{e['type']:10s}] {e['name']:40s} ({src})")
        if not entries:
            print("  Keine Eintraege.")

    elif cmd == "delete":
        name = sys.argv[2] if len(sys.argv) > 2 else ""
        if af.delete(name):
            print(f"  [OK] '{name}' geloescht")
        else:
            print(f"  Nicht gefunden: {name}")

    elif cmd == "status":
        s = af.status()
        print(json.dumps(s, indent=2, ensure_ascii=False))

    elif cmd == "memo":
        text = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""
        entry = af.memo(text)
        print(f"  [OK] Memo gespeichert: {entry['name']}")

    elif cmd == "lesson":
        title = sys.argv[2] if len(sys.argv) > 2 else ""
        content = " ".join(sys.argv[3:]) if len(sys.argv) > 3 else ""
        entry = af.lesson(title, content)
        print(f"  [OK] Lesson: {entry['name']}")

    elif cmd == "recall":
        query = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""
        results = af.recall(query)
        for r in results:
            w = r.get("meta", {}).get("weight", 0)
            bar = "*" * int(w * 5) + " " * (5 - int(w * 5))
            print(f"  [{bar}] {r['name']:40s} ({r['type']})")
        if not results:
            print("  Keine Erinnerungen gefunden.")

    elif cmd == "consolidate":
        stats = af.consolidate()
        print(f"  Decay:     {stats['decayed']} Eintraege verblasst")
        print(f"  Vergessen: {stats['forgotten']} Eintraege geloescht")
        print(f"  Behalten:  {stats['kept']} Eintraege stabil")

    elif cmd == "session-end":
        summary = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""
        entry = af.session_end(summary)
        print(f"  [OK] Session gespeichert: {entry['name']}")

    elif cmd == "tasks":
        status_filter = sys.argv[2] if len(sys.argv) > 2 else None
        tasks = af.tasks(status_filter)
        if not tasks:
            print("  Keine Tasks.")
        for t in tasks:
            m = t.get("meta", {})
            st = m.get("status", "?")
            pr = m.get("priority", "normal")
            due = m.get("due", "")
            marker = "[x]" if st == "done" else "[ ]"
            print(f"  {marker} {t['name']:30s} ({pr}) {due}")

    elif cmd == "task":
        name = sys.argv[2] if len(sys.argv) > 2 else "unnamed"
        content = " ".join(sys.argv[3:]) if len(sys.argv) > 3 else ""
        entry = af.task(name, content=content)
        print(f"  [OK] Task '{entry['name']}' erstellt")

    elif cmd == "done":
        name = sys.argv[2] if len(sys.argv) > 2 else ""
        entry = af.task_done(name)
        if entry:
            print(f"  [OK] Task '{name}' erledigt")
        else:
            print(f"  Task nicht gefunden: {name}")

    else:
        print(f"  Unbekannter Befehl: {cmd}")


if __name__ == "__main__":
    main()
