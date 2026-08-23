import gc
import importlib
import json
import os
import shutil
import threading
import time
import unittest
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class SearchGuiTempCase(unittest.TestCase):
    """Temporäre Gardener-Umgebung + GUI-Server auf freiem Port."""

    def setUp(self):
        self.temp = Path(self._make_tempdir())
        os.environ["GARDENER_DATA"] = str(self.temp / "data")
        os.environ["GARDENER_HOME"] = str(self.temp / "home")

        import gardener
        self.gardener = importlib.reload(gardener)
        import search_gui
        self.search_gui = importlib.reload(search_gui)

        self.af = self.gardener.Gardener()
        self.server = self.search_gui.create_server(
            gardener=self.af, host="127.0.0.1", port=0)
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever,
                                       daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        gc.collect()
        for attempt in range(3):
            try:
                shutil.rmtree(self.temp, ignore_errors=False)
                break
            except PermissionError:
                if attempt == 2:
                    raise
                time.sleep(0.1)

    @staticmethod
    def _make_tempdir() -> str:
        import tempfile
        return tempfile.mkdtemp(prefix="gardener-gui-test-")

    def _get(self, path: str):
        """GET gegen den Test-Server. Gibt (status, headers, body bytes)."""
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}")
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status, resp.headers, resp.read()
        except urllib.error.HTTPError as e:
            return e.code, e.headers, e.read()

    def _get_json(self, path: str):
        status, _headers, body = self._get(path)
        return status, json.loads(body.decode("utf-8"))


class TestFindSnippets(SearchGuiTempCase):
    def test_find_with_snippets_marks_match(self):
        self.af.put("beleg-scanner",
                    content="Scannt Belege und Rechnungen automatisch ein.",
                    type="knowledge", tags="steuer,belege")

        results = self.af.find("Rechnungen", with_snippets=True)
        self.assertTrue(results, "FTS-Treffer erwartet")
        self.assertIn(">>>", results[0].get("snippet", ""))
        self.assertIn("Rechnungen", results[0]["snippet"])

    def test_find_without_snippets_unchanged(self):
        self.af.put("beleg-scanner",
                    content="Scannt Belege und Rechnungen automatisch ein.",
                    type="knowledge")

        results = self.af.find("Rechnungen")
        self.assertTrue(results, "FTS-Treffer erwartet")
        self.assertNotIn("snippet", results[0])


class TestSearchGuiHttp(SearchGuiTempCase):
    def setUp(self):
        super().setUp()
        self.af.put("beleg-scanner",
                    content="Scannt Belege und Rechnungen automatisch ein.",
                    type="knowledge", tags="steuer,belege")
        self.af.put("notiz-einkauf", content="Milch und Brot kaufen.",
                    type="memory", tags="privat")

    def test_index_page_served(self):
        status, headers, body = self._get("/")
        self.assertEqual(status, 200)
        self.assertIn("text/html", headers.get("Content-Type", ""))
        html_text = body.decode("utf-8")
        self.assertIn("Gardener Suche", html_text)
        # Keine externen Ressourcen (offline-fähig)
        self.assertNotIn("https://", html_text.replace("w3.org", ""))

    def test_api_search_returns_hits_with_snippet(self):
        status, data = self._get_json("/api/search?q=Rechnungen")
        self.assertEqual(status, 200)
        names = [r["name"] for r in data["results"]]
        self.assertIn("beleg-scanner", names)
        hit = data["results"][names.index("beleg-scanner")]
        self.assertIn(">>>", hit.get("snippet", ""))
        self.assertEqual(hit["source"], "system")  # knowledge -> system-DB

    def test_api_search_type_filter(self):
        status, data = self._get_json("/api/search?q=Brot&type=memory")
        self.assertEqual(status, 200)
        self.assertEqual([r["name"] for r in data["results"]],
                         ["notiz-einkauf"])
        status, data = self._get_json("/api/search?q=Brot&type=tool")
        self.assertEqual(status, 200)
        self.assertEqual(data["results"], [])

    def test_api_search_empty_query(self):
        status, data = self._get_json("/api/search?q=")
        self.assertEqual(status, 200)
        self.assertEqual(data["results"], [])

    def test_api_entry_detail_and_404(self):
        status, data = self._get_json("/api/entry?name=beleg-scanner")
        self.assertEqual(status, 200)
        self.assertEqual(data["name"], "beleg-scanner")
        self.assertIn("Rechnungen", data["content"])

        status, data = self._get_json("/api/entry?name=gibts-nicht")
        self.assertEqual(status, 404)
        self.assertIn("error", data)

    def test_api_entry_with_slash_name(self):
        # Entry-Namen können '/' enthalten (z. B. observed/<pfad>) —
        # darum Query-Param statt Pfadsegment.
        status, data = self._get_json(
            "/api/entry?name=" + urllib.parse.quote("observed/x/y.md"))
        self.assertEqual(status, 404)  # existiert nicht, aber Route greift

    def test_api_status(self):
        status, data = self._get_json("/api/status")
        self.assertEqual(status, 200)
        self.assertIn("user_entries", data)
        self.assertIn("system_entries", data)
        self.assertGreaterEqual(data["user_entries"], 1)
        self.assertGreaterEqual(data["system_entries"], 1)

    def test_unknown_path_is_404(self):
        status, data = self._get_json("/api/nicht-da")
        self.assertEqual(status, 404)
        self.assertIn("error", data)

    def test_server_is_read_only(self):
        # Keine Schreib-Endpunkte: POST wird nicht implementiert (501).
        req = urllib.request.Request(
            f"http://127.0.0.1:{self.port}/api/search", data=b"q=x",
            method="POST")
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(req, timeout=10)
        self.assertEqual(ctx.exception.code, 501)


if __name__ == "__main__":
    unittest.main()
