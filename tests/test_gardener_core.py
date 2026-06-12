import importlib
import contextlib
import gc
import io
import os
import re
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class GardenerTempCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        base = Path(self.temp.name)
        os.environ["GARDENER_DATA"] = str(base / "data")
        os.environ["GARDENER_HOME"] = str(base / "home")

        import gardener

        self.gardener = importlib.reload(gardener)
        self.af = self.gardener.Gardener()

    def tearDown(self):
        gc.collect()
        for attempt in range(3):
            try:
                self.temp.cleanup()
                break
            except PermissionError:
                if attempt == 2:
                    raise
                time.sleep(0.1)


class TestGardenerCore(GardenerTempCase):
    def test_put_get_and_find_round_trip(self):
        self.af.put(
            "beleg-scanner",
            content="Scannt Belege und Rechnungen.",
            type="knowledge",
            tags="steuer,belege",
        )

        entry = self.af.get("beleg-scanner")
        self.assertIsNotNone(entry)
        self.assertEqual(entry["type"], "knowledge")

        results = self.af.find("Rechnungen")
        self.assertEqual(results[0]["name"], "beleg-scanner")

    def test_task_lifecycle_uses_everything_table(self):
        self.af.task("steuer-2026", "Unterlagen prüfen", priority="high")
        open_tasks = self.af.tasks(status="open")
        self.assertEqual([task["name"] for task in open_tasks], ["steuer-2026"])

        done = self.af.task_done("steuer-2026")
        self.assertIsNotNone(done)
        self.assertEqual(done["meta"]["status"], "done")

    def test_seeded_german_user_texts_use_real_umlauts(self):
        import seed

        seed = importlib.reload(seed)
        with contextlib.redirect_stdout(io.StringIO()):
            seed.seed()

        combined = []
        for db_name in ("gardener.db", "user.db"):
            db_path = Path(os.environ["GARDENER_DATA"]) / db_name
            with sqlite3.connect(db_path) as conn:
                rows = conn.execute("SELECT content FROM everything").fetchall()
            combined.extend(row[0] for row in rows)

        text = re.sub(r"```.*?```", "", "\n".join(combined), flags=re.DOTALL)
        legacy_spellings = [
            "fuer",
            "Fuer",
            "Fuehrt",
            "zurueck",
            "Buecher",
            "primaere",
            "Grosse",
            "ueber",
            "nuetzlich",
            "Uebersicht",
            "Groessen",
            "Bruecke",
            "draussen",
            "ausfuehren",
        ]
        for spelling in legacy_spellings:
            self.assertNotIn(spelling, text)


class TestCliI18n(unittest.TestCase):
    def run_help(self, lang):
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"
            env["GARDENER_DATA"] = str(Path(tmp) / "data")
            env["GARDENER_HOME"] = str(Path(tmp) / "home")
            env["GARDENER_LANG"] = lang
            result = subprocess.run(
                [sys.executable, str(ROOT / "gardener.py")],
                cwd=ROOT,
                env=env,
                text=True,
                encoding="utf-8",
                capture_output=True,
                check=True,
            )
            return result.stdout

    def test_german_help_uses_real_umlauts(self):
        output = self.run_help("de")
        self.assertIn("Befehle:", output)
        self.assertIn("Einträge", output)
        self.assertIn("Gedächtnis konsolidieren", output)
        self.assertNotIn("Gedaechtnis", output)

    def test_english_help_from_environment(self):
        output = self.run_help("en")
        self.assertIn("Gardener -- LLM-native operating system", output)
        self.assertIn("Commands:", output)
        self.assertIn("Consolidate memory", output)


if __name__ == "__main__":
    unittest.main()
