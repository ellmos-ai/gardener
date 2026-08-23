# -*- coding: utf-8 -*-
"""Wendet sources.reference.json auf eine Gardener-Instanz an.

Zweck: Ein frisch aufgesetzter Gardener startet sonst leer -- alles Wissen darueber,
welche Ordner und Tabellen durchsuchbar sein sollten, steckt in einer lokalen Config,
die nirgends abgebildet ist. Diese Datei macht das Set uebertragbar.

Grundsaetze:
  * Existenzpruefung. Was auf diesem Host nicht existiert, wird uebersprungen --
    das ist der Normalfall auf einem anderen System, kein Fehler.
  * Additiv. Bereits konfigurierte Quellen werden nie ueberschrieben.
  * Trockenlauf ist Default. Schreiben nur mit --apply.

  python apply_reference_sources.py [--tiers base,system] [--apply]
"""
import argparse, json, os, sys
from pathlib import Path

def source_paths(cfg):
    """Pfade, deren Existenz ueber 'ueberspringen oder anlegen' entscheidet."""
    out = []
    for field in ("path", "db_path"):
        v = cfg.get(field)
        if v:
            out.append(str(v).split("*")[0].rstrip("/\\"))
    return out

def exists(cfg):
    ps = source_paths(cfg)
    if not ps:
        return True  # keine Pfadangabe -> Adapter entscheidet selbst
    return all(Path(os.path.expanduser(p)).exists() for p in ps)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tiers", default="base,system",
                    help="Kommaliste aus base,system,user (Default: base,system)")
    ap.add_argument("--apply", action="store_true", help="wirklich schreiben")
    ap.add_argument("--reference", default="sources.reference.json")
    a = ap.parse_args()

    ref = json.loads(Path(a.reference).read_text(encoding="utf-8"))
    sys.path.insert(0, str(Path(__file__).parent))
    from gardener import Gardener
    g = Gardener()
    have = set(g.observe_source_list())

    add, skip_exist, skip_have = [], [], []
    for tier in [t.strip() for t in a.tiers.split(",") if t.strip()]:
        for sid, cfg in (ref.get("tiers", {}).get(tier) or {}).items():
            if sid in have:
                skip_have.append(sid)
            elif not exists(cfg):
                skip_exist.append(sid)
            else:
                add.append((sid, cfg))

    print(f"bereits konfiguriert : {len(skip_have)}")
    print(f"auf diesem Host nicht vorhanden : {len(skip_exist)}")
    for s in skip_exist:
        print(f"    - {s}")
    print(f"anzulegen : {len(add)}")
    for sid, _ in add:
        print(f"    + {sid}")

    if not a.apply:
        print("\n(Trockenlauf -- mit --apply wirklich anlegen)")
        return 0
    for sid, cfg in add:
        kind = cfg.pop("kind")
        g.observe_source_add(sid, kind, **cfg)
        print(f"  angelegt: {sid}")
    print(f"\n{len(add)} Quellen angelegt. Indexlauf: gardener.py observe-sources")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
