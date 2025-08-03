import json
from pathlib import Path

# Load Chinese translations
_translations = {}
_locale_file = Path(__file__).with_name("zh_CN.json")
if _locale_file.exists():
    try:
        with _locale_file.open(encoding="utf-8") as f:
            _translations = json.load(f)
    except Exception:
        _translations = {}

def _(text: str) -> str:
    """Simple translation lookup. Falls back to original text."""
    return _translations.get(text, text)
