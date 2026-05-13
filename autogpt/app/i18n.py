import json
import os
from pathlib import Path

_available_locales: dict[str, Path] = {}
_translations: dict[str, str] = {}
_current_locale: str = "en"

_LOCALE_DIR = Path(__file__).parent

for _f in _LOCALE_DIR.glob("*.json"):
    _locale_name = _f.stem
    _available_locales[_locale_name] = _f


def _load_locale(locale_name: str) -> None:
    global _translations, _current_locale
    locale_file = _available_locales.get(locale_name)
    if locale_file is None:
        _translations = {}
        _current_locale = "en"
        return
    try:
        with locale_file.open(encoding="utf-8") as f:
            _translations = json.load(f)
        _current_locale = locale_name
    except Exception:
        _translations = {}
        _current_locale = "en"


def init_locale(locale_name: str | None = None) -> None:
    if locale_name is None:
        locale_name = os.environ.get("AUTOGPT_LANG", "")
    if not locale_name:
        try:
            from autogpt.config import Config
            locale_name = Config().language if hasattr(Config(), "language") else "zh"
        except Exception:
            locale_name = "zh"
    if locale_name == "en":
        global _translations, _current_locale
        _translations = {}
        _current_locale = "en"
        return
    if locale_name not in _available_locales:
        for key in _available_locales:
            if key.startswith(locale_name):
                locale_name = key
                break
        else:
            locale_name = "zh"
    _load_locale(locale_name)


def get_current_locale() -> str:
    return _current_locale


def get_available_locales() -> list[str]:
    return sorted(_available_locales.keys())


def _(text: str) -> str:
    return _translations.get(text, text)


init_locale()
