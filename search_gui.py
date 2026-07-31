# -*- coding: utf-8 -*-
"""
Gardener Such-GUI -- schlanke Weboberfläche für menschliche Nutzer
===================================================================

Startet einen lokalen, read-only Webserver (reine Standardbibliothek,
keine externen Dependencies) und zeigt eine Suchseite über dem
FTS5-Suchkern von Gardener (find() mit Snippets, get(), status()).

    python search_gui.py [--port 8765] [--no-browser]
    gardener gui [--port 8765] [--no-browser]

Sicherheit/Privacy (SYSTEM-MANIFEST §3.1): Bind standardmäßig auf
127.0.0.1 (kein LAN-Zugriff), ausschließlich GET-Endpunkte, keinerlei
Schreibzugriffe auf gardener.db/user.db. Die Seite lädt keine externen
Ressourcen (offline-fähig).

Muster: BACH unified_search (Treffer-Snippets mit '>>>'/'<<<'-Markern,
die im Browser als <mark> hervorgehoben werden).
"""

import json
import os
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Optional
from urllib.parse import parse_qs, urlparse

from gardener import Gardener

DEFAULT_PORT = int(os.environ.get("GARDENER_GUI_PORT", "8765"))
DEFAULT_HOST = "127.0.0.1"

# Bekannte Typen für den Filter (frei erweiterbar; alles andere bleibt
# über "alle Typen" erreichbar).
KNOWN_TYPES = [
    "knowledge", "tool", "task", "memory", "lesson", "session",
    "observed", "document", "config", "export",
]

INDEX_HTML = """<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Gardener Suche</title>
<style>
  :root { --bg:#f6f7f9; --card:#ffffff; --ink:#1c1e21; --ink-faint:#6a737d;
          --accent:#2e7d4f; --border:#d8dce1; }
  * { box-sizing: border-box; }
  body { margin:0; font-family: "Segoe UI", system-ui, sans-serif;
         background:var(--bg); color:var(--ink); }
  header { background:var(--card); border-bottom:1px solid var(--border);
           padding:12px 20px; display:flex; align-items:baseline; gap:14px; }
  header h1 { font-size:18px; margin:0; color:var(--accent); }
  header .stats { font-size:12px; color:var(--ink-faint); }
  main { max-width:980px; margin:20px auto; padding:0 16px; }
  .searchbar { display:flex; gap:8px; flex-wrap:wrap; margin-bottom:16px; }
  .searchbar input[type=text] { flex:1 1 320px; padding:10px 12px;
        font-size:15px; border:1px solid var(--border); border-radius:8px; }
  .searchbar select, .searchbar button { padding:10px 12px; font-size:14px;
        border:1px solid var(--border); border-radius:8px; background:var(--card); }
  .searchbar button { background:var(--accent); color:#fff; cursor:pointer;
        border-color:var(--accent); }
  .hit { background:var(--card); border:1px solid var(--border);
         border-radius:8px; padding:10px 14px; margin-bottom:8px; cursor:pointer; }
  .hit:hover { border-color:var(--accent); }
  .hit .title { font-weight:600; }
  .badge { display:inline-block; font-size:11px; padding:1px 7px;
           border-radius:10px; margin-right:6px; background:#e8eef5;
           color:#37475a; }
  .badge.src-user { background:#e3f1e7; color:#2e7d4f; }
  .badge.src-system { background:#fdeeda; color:#9a6a1a; }
  .snippet { font-size:13px; color:var(--ink-faint); margin-top:4px; }
  .snippet mark { background:#fff1a8; padding:0 1px; }
  .meta-line { font-size:11px; color:var(--ink-faint); margin-top:4px; }
  #detail { background:var(--card); border:1px solid var(--border);
            border-radius:8px; padding:14px 18px; margin-top:16px; display:none; }
  #detail h2 { font-size:16px; margin:0 0 8px; }
  #detail pre { white-space:pre-wrap; word-break:break-word; font-size:13px;
        background:var(--bg); padding:10px; border-radius:6px; max-height:50vh;
        overflow:auto; }
  .empty { color:var(--ink-faint); font-size:14px; padding:12px 4px; }
</style>
</head>
<body>
<header>
  <h1>Gardener Suche</h1>
  <span class="stats" id="stats">lade Status …</span>
</header>
<main>
  <div class="searchbar">
    <input type="text" id="q" placeholder="Suchbegriff …" autocomplete="off" autofocus>
    <select id="type"><option value="">alle Typen</option></select>
    <select id="limit">
      <option value="10">10</option>
      <option value="20" selected>20</option>
      <option value="50">50</option>
    </select>
    <button id="go">Suchen</button>
  </div>
  <div id="results"></div>
  <div id="detail"></div>
</main>
<script>
const TYPES = __TYPES_JSON__;

function esc(s) {
  return String(s == null ? "" : s)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
function renderSnippet(s) {
  // Erst escapen, dann die FTS-Marker in <mark> umwandeln.
  return esc(s)
    .replace(/&gt;&gt;&gt;/g, "<mark>")
    .replace(/&lt;&lt;&lt;/g, "</mark>");
}

const typeSel = document.getElementById("type");
for (const t of TYPES) {
  const o = document.createElement("option");
  o.value = t; o.textContent = t;
  typeSel.appendChild(o);
}

async function loadStatus() {
  try {
    const r = await fetch("/api/status");
    const s = await r.json();
    document.getElementById("stats").textContent =
      "User-DB: " + s.user_entries + " · System-DB: " + s.system_entries + " Einträge";
  } catch (e) {
    document.getElementById("stats").textContent = "";
  }
}

async function search() {
  const q = document.getElementById("q").value.trim();
  const params = new URLSearchParams({ q: q,
    limit: document.getElementById("limit").value });
  const ty = typeSel.value;
  if (ty) params.set("type", ty);
  const box = document.getElementById("results");
  box.innerHTML = '<div class="empty">suche …</div>';
  document.getElementById("detail").style.display = "none";
  const r = await fetch("/api/search?" + params.toString());
  const data = await r.json();
  const hits = data.results || [];
  if (!hits.length) {
    box.innerHTML = '<div class="empty">Keine Ergebnisse.</div>';
    return;
  }
  box.innerHTML = "";
  for (const h of hits) {
    const div = document.createElement("div");
    div.className = "hit";
    div.innerHTML =
      '<span class="badge">' + esc(h.type) + '</span>' +
      '<span class="badge src-' + esc(h.source || "user") + '">' + esc(h.source || "?") + '</span>' +
      '<span class="title">' + esc(h.name) + '</span>' +
      (h.snippet ? '<div class="snippet">' + renderSnippet(h.snippet) + '</div>' : '') +
      '<div class="meta-line">' + esc(h.updated || "") +
        (h.tags ? ' · ' + esc(h.tags) : '') + '</div>';
    div.onclick = () => showDetail(h.name);
    box.appendChild(div);
  }
}

async function showDetail(name) {
  const r = await fetch("/api/entry?name=" + encodeURIComponent(name));
  const e = await r.json();
  const d = document.getElementById("detail");
  if (e.error) { d.style.display = "none"; return; }
  d.innerHTML =
    '<h2>' + esc(e.name) + '</h2>' +
    '<div><span class="badge">' + esc(e.type) + '</span>' +
    '<span class="badge src-' + esc(e.source || "user") + '">' + esc(e.source || "?") + '</span>' +
    '<span class="meta-line">Tags: ' + esc(e.tags || "–") +
    ' · updated: ' + esc(e.updated || "") + '</span></div>' +
    '<pre>' + esc(e.content || "") + '</pre>';
  d.style.display = "block";
  d.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

document.getElementById("go").onclick = search;
document.getElementById("q").addEventListener("keydown", (ev) => {
  if (ev.key === "Enter") search();
});
loadStatus();
</script>
</body>
</html>
"""


def _json_bytes(payload) -> bytes:
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


class SearchGuiHandler(BaseHTTPRequestHandler):
    """Read-only HTTP-Handler für die Gardener Such-GUI."""

    server_version = "GardenerSearchGUI/1.0"

    @property
    def gardener(self) -> Gardener:
        return self.server.gardener  # type: ignore[attr-defined]

    # -- Hilfen --------------------------------------------------------

    def _send(self, body: bytes, status: int = 200,
              content_type: str = "application/json; charset=utf-8") -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, payload, status: int = 200) -> None:
        self._send(_json_bytes(payload), status=status)

    def log_message(self, format, *args):  # noqa: A002 - stdlib-Signatur
        pass  # still: keine Access-Logs auf stderr

    # -- Routing (nur GET, read-only) ----------------------------------

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        params = parse_qs(parsed.query)

        if path == "/":
            body = INDEX_HTML.replace(
                "__TYPES_JSON__", json.dumps(KNOWN_TYPES)
            ).encode("utf-8")
            self._send(body, content_type="text/html; charset=utf-8")
            return

        if path == "/api/search":
            query = (params.get("q", [""])[0] or "").strip()
            type_filter = (params.get("type", [""])[0] or "").strip() or None
            try:
                limit = int(params.get("limit", ["20"])[0])
                limit = max(1, min(limit, 100))
            except ValueError:
                limit = 20
            if not query:
                self._send_json({"results": [], "query": query})
                return
            results = self.gardener.find(query, type=type_filter,
                                         limit=limit, with_snippets=True)
            self._send_json({"results": results, "query": query})
            return

        if path == "/api/entry":
            name = (params.get("name", [""])[0] or "").strip()
            if not name:
                self._send_json({"error": "name fehlt"}, status=400)
                return
            entry = self.gardener.get(name)
            if entry is None:
                self._send_json({"error": f"nicht gefunden: {name}"}, status=404)
                return
            self._send_json(entry)
            return

        if path == "/api/status":
            self._send_json(self.gardener.status())
            return

        self._send_json({"error": f"unbekannter Pfad: {path}"}, status=404)


def create_server(gardener: Optional[Gardener] = None,
                  host: str = DEFAULT_HOST,
                  port: int = DEFAULT_PORT) -> ThreadingHTTPServer:
    """Baut den GUI-Server (ohne ihn zu starten).

    Args:
        gardener: vorhandene Gardener-Instanz (Tests); None = Standard-DBs
        host: Bind-Adresse (Default 127.0.0.1 -- kein LAN-Zugriff)
        port: Port; 0 = freier Port (für Tests)
    """
    server = ThreadingHTTPServer((host, port), SearchGuiHandler)
    server.gardener = gardener or Gardener()  # type: ignore[attr-defined]
    server.daemon_threads = True
    return server


def run(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT,
        open_browser: bool = True,
        gardener: Optional[Gardener] = None) -> None:
    """Startet die Such-GUI (blockierend, Strg+C zum Beenden)."""
    server = create_server(gardener=gardener, host=host, port=port)
    url = f"http://{host}:{server.server_address[1]}/"
    print(f"  Gardener Such-GUI läuft: {url}")
    print("  Read-only, nur lokal (127.0.0.1). Beenden mit Strg+C.")
    if open_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  GUI beendet.")
    finally:
        server.server_close()


def main(argv=None) -> None:
    """Direkteinstieg: python search_gui.py [--port N] [--no-browser]."""
    import sys
    args = list(sys.argv[1:] if argv is None else argv)
    port = DEFAULT_PORT
    open_browser = True
    i = 0
    while i < len(args):
        if args[i] == "--port" and i + 1 < len(args):
            port = int(args[i + 1])
            i += 2
        elif args[i] == "--no-browser":
            open_browser = False
            i += 1
        else:
            print(f"Unbekannte Option: {args[i]}")
            print("Nutzung: python search_gui.py [--port N] [--no-browser]")
            return
    run(port=port, open_browser=open_browser)


if __name__ == "__main__":
    main()
