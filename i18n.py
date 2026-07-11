import json
import os
from pathlib import Path
from typing import Dict, List

SUPPORTED_LANGUAGES = ['de', 'en', 'es', 'zh', 'ja', 'ru']
DEFAULT_LANGUAGE = 'de'
FALLBACK_CHAIN = ['en', 'de']

_current_lang: str = os.environ.get("GARDENER_LANG", DEFAULT_LANGUAGE).lower()
if _current_lang not in SUPPORTED_LANGUAGES:
    _current_lang = DEFAULT_LANGUAGE
_translations: Dict[str, Dict[str, str]] = {}
_translations_file: Path = Path(__file__).parent / "locales" / "translations.json"
_BUILTIN_TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "help.title": {
        "de": "Gardener -- LLM-natives Betriebssystem",
        "en": "Gardener -- LLM-native operating system",
    },
    "help.commands": {"de": "Befehle:", "en": "Commands:"},
    "help.home": {"de": "Home", "en": "Home"},
    "help.data": {"de": "Daten", "en": "Data"},
    "help.system_db": {"de": "System-DB", "en": "System DB"},
    "help.user_db": {"de": "User-DB", "en": "User DB"},
    "help.entries": {"de": "Einträge", "en": "entries"},
    "help.heap": {"de": "Halde", "en": "Heap"},
    "help.files": {"de": "Dateien", "en": "files"},
    "cmd.find": {"de": "Suche", "en": "Search"},
    "cmd.get": {"de": "Eintrag lesen", "en": "Read entry"},
    "cmd.put": {"de": "Eintrag schreiben", "en": "Write entry"},
    "cmd.run": {"de": "Tool ausführen", "en": "Run tool"},
    "cmd.absorb": {
        "de": "Datei absorbieren (Transporter IN)",
        "en": "Absorb file (transporter in)",
    },
    "cmd.materialize": {
        "de": "Eintrag als Datei (Transporter OUT)",
        "en": "Materialize entry as file (transporter out)",
    },
    "cmd.sync": {
        "de": "Absorber leeren + Ordner beobachten",
        "en": "Empty absorber + observe folders",
    },
    "cmd.observe": {
        "de": "Ordner scannen (nur beobachten)",
        "en": "Scan folders (observe only)",
    },
    "cmd.memo": {
        "de": "Notiz ins Arbeitsgedächtnis",
        "en": "Store note in working memory",
    },
    "cmd.lesson": {
        "de": "Lektion speichern (Best Practice)",
        "en": "Store lesson (best practice)",
    },
    "cmd.recall": {
        "de": "Erinnern (sucht in Memory/Lessons/Sessions)",
        "en": "Recall (searches memory, lessons, sessions)",
    },
    "cmd.consolidate": {
        "de": "Gedächtnis konsolidieren (Decay/Forget)",
        "en": "Consolidate memory (decay/forget)",
    },
    "cmd.session_end": {
        "de": "Session-Bericht speichern",
        "en": "Store session report",
    },
    "cmd.tasks": {
        "de": "Tasks auflisten (open/doing/done)",
        "en": "List tasks (open/doing/done)",
    },
    "cmd.task": {"de": "Task erstellen", "en": "Create task"},
    "cmd.done": {
        "de": "Task als erledigt markieren",
        "en": "Mark task done",
    },
    "cmd.list": {"de": "Alle Einträge auflisten", "en": "List all entries"},
    "cmd.delete": {"de": "Eintrag löschen", "en": "Delete entry"},
    "cmd.status": {"de": "System-Status", "en": "System status"},
}


def _builtin_translations() -> Dict[str, Dict[str, str]]:
    return {key: value.copy() for key, value in _BUILTIN_TRANSLATIONS.items()}


def _load():
    global _translations
    if _translations_file.exists():
        try:
            with open(_translations_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                _translations = {k: v for k, v in data.items() if not k.startswith('_')}
                if _translations:
                    return
        except Exception:
            pass
    _translations = _builtin_translations()


def t(key: str, **kwargs) -> str:
    """Translate a key with fallback: current language -> en -> de -> key."""
    if not _translations:
        _load()

    entry = _translations.get(key)
    if entry:
        value = entry.get(_current_lang)
        if value:
                return _format(value, kwargs)
        for fb in FALLBACK_CHAIN:
            value = entry.get(fb)
            if value:
                return _format(value, kwargs)
    return key


def _format(value: str, kwargs: Dict[str, str]) -> str:
    if not kwargs:
        return value
    try:
        return value.format(**kwargs)
    except (KeyError, IndexError, ValueError):
        return value


def set_language(lang: str) -> None:
    global _current_lang
    lang = lang.lower()
    if lang in SUPPORTED_LANGUAGES:
        _current_lang = lang


def get_language() -> str:
    return _current_lang


def get_supported_languages() -> List[str]:
    return list(SUPPORTED_LANGUAGES)
