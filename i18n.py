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


def _load():
    global _translations
    if _translations_file.exists():
        try:
            with open(_translations_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                _translations = {k: v for k, v in data.items() if not k.startswith('_')}
        except Exception:
            _translations = {}


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
