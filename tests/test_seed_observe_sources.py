# -*- coding: utf-8 -*-
"""Tests fuer das Standard-Set an observe-sources beim Seed.

Der interessante Fall ist nicht der eigene Host (dort ist ohnehin alles
konfiguriert), sondern ein fremder: Dort existiert ein Teil der Pfade nicht,
und genau dann darf nichts angelegt und nichts geworfen werden.
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import seed  # noqa: E402


class FakeGardener:
    """Minimalzwilling: nur die zwei Methoden, die _seed_observe_sources nutzt."""

    def __init__(self, existing=None):
        self.sources = dict(existing or {})
        self.added = []

    def observe_source_list(self):
        return dict(self.sources)

    def observe_source_add(self, source_id, kind, **params):
        self.sources[source_id] = {"kind": kind, **params}
        self.added.append(source_id)
        return self.sources[source_id]


def _write_ref(tmp_path, tiers):
    (tmp_path / "sources.reference.json").write_text(
        json.dumps({"schema": "gardener.sources.reference.v1", "tiers": tiers}),
        encoding="utf-8",
    )


@pytest.fixture
def ref_dir(tmp_path, monkeypatch):
    """Laesst _seed_observe_sources die Referenz aus tmp_path lesen."""
    monkeypatch.setattr(seed, "__file__", str(tmp_path / "seed.py"))
    return tmp_path


def test_legt_vorhandene_quelle_an(ref_dir, tmp_path):
    real = tmp_path / "vorhanden"
    real.mkdir()
    _write_ref(ref_dir, {"base": {"da": {"kind": "markdown_dir", "path": str(real)}}})
    g = FakeGardener()
    seed._seed_observe_sources(g)
    assert g.added == ["da"]
    assert g.sources["da"]["kind"] == "markdown_dir"


def test_ueberspringt_fehlende_pfade_ohne_fehler(ref_dir, tmp_path):
    """Der Normalfall auf einem fremden Host -- kein Fehler, kein Eintrag."""
    _write_ref(ref_dir, {"base": {
        "fehlt": {"kind": "markdown_dir", "path": str(tmp_path / "gibt-es-nicht")},
        "fehlt_db": {"kind": "sqlite_table", "db_path": str(tmp_path / "nichts.db"), "table": "t"},
    }})
    g = FakeGardener()
    seed._seed_observe_sources(g)
    assert g.added == []


def test_ueberschreibt_bestehende_konfiguration_nicht(ref_dir, tmp_path):
    real = tmp_path / "vorhanden"
    real.mkdir()
    _write_ref(ref_dir, {"base": {"da": {"kind": "markdown_dir", "path": str(real)}}})
    g = FakeGardener({"da": {"kind": "markdown_dir", "path": "/eigener/pfad"}})
    seed._seed_observe_sources(g)
    assert g.added == []
    assert g.sources["da"]["path"] == "/eigener/pfad"


def test_user_ebene_wird_nicht_automatisch_uebernommen(ref_dir, tmp_path):
    real = tmp_path / "vorhanden"
    real.mkdir()
    _write_ref(ref_dir, {
        "base": {"b": {"kind": "markdown_dir", "path": str(real)}},
        "user": {"u": {"kind": "markdown_dir", "path": str(real)}},
    })
    g = FakeGardener()
    seed._seed_observe_sources(g)
    assert g.added == ["b"], "die user-Ebene ist hostspezifisch und wird von Hand gewaehlt"


def test_fehlende_referenzdatei_bricht_nicht_ab(ref_dir):
    g = FakeGardener()
    seed._seed_observe_sources(g)   # keine sources.reference.json geschrieben
    assert g.added == []


def test_kaputte_referenzdatei_bricht_nicht_ab(ref_dir):
    (ref_dir / "sources.reference.json").write_text("{kein valides json", encoding="utf-8")
    g = FakeGardener()
    seed._seed_observe_sources(g)
    assert g.added == []
