"""Lightweight stdlib replacements for common third-party dependencies.

Provides zero-dependency fallbacks so the core system runs without optional packages.

Replaces:
  - inflection.underscore/dasherize/camelize → str methods
  - distro.id()/name()/version() → platform module
  - orjson.dumps/loads → json (with ujson fallback)
  - ftfy.fix_text → str fixup heuristic
"""

from __future__ import annotations

import json
import platform
import re
import unicodedata
from typing import Any


# ==================== inflecti在replacements ====================

def underscore(word: str) -> str:
    """将CamelCase转换为snake_case。替代inflection.underscore()。"""
    word = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", word)
    word = re.sub(r"([a-z\d])([A-Z])", r"\1_\2", word)
    word = word.replace("-", "_")
    return word.lower()


def dasherize(word: str) -> str:
    """将snake_case转换为dash-case。替代inflection.dasherize()。"""
    return underscore(word).replace("_", "-")


def camelize(word: str, uppercase_first_letter: bool = False) -> str:
    """将snake_case/dash-case转换为CamelCase。替代inflection.camelize()。"""
    parts = re.split(r"[_\-]", underscore(word))
    if uppercase_first_letter:
        return "".join(p.capitalize() for p in parts)
    return parts[0].lower() + "".join(p.capitalize() for p in parts[1:])


# ==================== distro replacements ====================

def get_distro_id() -> str:
    """获取OS发行版ID。替代distro.id()。"""
    try:
        import distro
        return distro.id()
    except ImportError:
        return platform.system().lower()


def get_distro_name() -> str:
    """获取OS发行版名称。替代distro.name()。"""
    try:
        import distro
        return distro.name()
    except ImportError:
        return platform.platform()


def get_distro_version() -> str:
    """Get OS distro version. Replaces distro.version()."""
    try:
        import distro
        return distro.version()
    except ImportError:
        return platform.version()


def get_os_info() -> dict[str, str]:
    """获取完整OS信息字典。"""
    return {
        "id": get_distro_id(),
        "name": get_distro_name(),
        "version": get_distro_version(),
        "system": platform.system(),
        "machine": platform.machine(),
        "platform": platform.platform(),
    }


# ==================== orjs在replacements ====================

def json_dumps(obj: Any, *, indent: int | None = None, sort_keys: bool = False) -> str:
    """JSON序列化。尝试orjson，回退到标准库json。"""
    try:
        import orjson
        opts = 0
        if indent is not None:
            opts |= orjson.OPT_INDENT_2
        if sort_keys:
            opts |= orjson.OPT_SORT_KEYS
        result = orjson.dumps(obj, option=opts)
        if isinstance(result, bytes):
            return result.decode("utf-8")
        return str(result)
    except Exception:
        pass
    return json.dumps(obj, indent=indent, sort_keys=sort_keys, ensure_ascii=False, default=str)


def json_loads(s: str | bytes) -> Any:
    """JSON反序列化。尝试orjson，回退到标准库json。"""
    try:
        import orjson
        return orjson.loads(s)
    except (ImportError, Exception):
        return json.loads(s)


# ==================== ftfy replacement ====================

def fix_text(text: str) -> str:
    """Fix common text encoding issues. Replaces ftfy.fix_text().

    Handles: mojibake (Ã© → é), smart quotes, BOM, surrogates.
    """
    if not text:
        return text
    try:
        import ftfy
        return ftfy.fix_text(text)
    except ImportError:
        pass

    try:
        text = text.encode("utf-8", errors="surrogatepass").decode("utf-8", errors="replace")
    except Exception:
        pass

    replacements = {
        "\ufeff": "",
        "\u00a0": " ",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2013": "-",
        "\u2014": "--",
        "\u2026": "...",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)

    try:
        text = unicodedata.normalize("NFC", text)
    except Exception:
        pass

    return text


__all__ = [
    "underscore",
    "dasherize",
    "camelize",
    "get_distro_id",
    "get_distro_name",
    "get_distro_version",
    "get_os_info",
    "json_dumps",
    "json_loads",
    "fix_text",
]
