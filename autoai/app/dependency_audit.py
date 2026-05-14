"""Dependency audit CLI command — scan, report, and reduce external dependencies."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

import click


CORE_DEPS = {
    "beautifulsoup4": "bs4",
    "colorama": "colorama",
    "openai": "openai",
    "python-dotenv": "dotenv",
    "pyyaml": "yaml",
    "requests": "requests",
    "tiktoken": "tiktoken",
    "click": "click",
    "pydantic": "pydantic",
    "prompt_toolkit": "prompt_toolkit",
}

OPTIONAL_DEPS = {
    "spacy": "spacy",
    "chromadb": "chromadb",
    "redis": "redis",
    "orjson": "orjson",
    "ftfy": "ftfy",
    "inflection": "inflection",
    "distro": "distro",
    "Pillow": "PIL",
    "selenium": "selenium",
    "fastapi": "fastapi",
    "uvicorn": "uvicorn",
    "duckduckgo-search": "duckduckgo_search",
    "gTTS": "gtts",
    "PyPDF2": "PyPDF2",
    "python-docx": "docx",
    "markdown": "markdown",
    "jsonschema": "jsonschema",
    "charset-normalizer": "charset_normalizer",
    "watchdog": "watchdog",
    "pinecone-client": "pinecone",
    "readability-lxml": "readability",
    "pylatexenc": "pylatexenc",
    "webdriver-manager": "webdriver_manager",
    "agent-protocol": "agent_protocol",
    "google-api-python-client": "googleapiclient",
}


def _has_spec(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except (ModuleNotFoundError, ValueError):
        return False


def _count_imports(module_name: str, workspace: Path) -> int:
    count = 0
    for py in workspace.rglob("*.py"):
        if "__pycache__" in str(py):
            continue
        try:
            text = py.read_text(encoding="utf-8", errors="ignore")
            if f"import {module_name}" in text or f"from {module_name}" in text:
                count += 1
        except Exception:
            pass
    return count


def run_audit(
    workspace: Path,
    unused_only: bool = False,
    as_json: bool = False,
) -> list[dict[str, Any]] | None:
    """Execute dependency audit and return/print results."""
    all_deps = {**CORE_DEPS, **OPTIONAL_DEPS}

    results = []
    for pip_name, import_name in all_deps.items():
        installed = _has_spec(import_name)
        imports = _count_imports(import_name, workspace)
        category = "core" if pip_name in CORE_DEPS else "optional"
        results.append({
            "package": pip_name,
            "import_as": import_name,
            "installed": installed,
            "import_count": imports,
            "category": category,
            "status": "unused" if imports == 0 else ("uninstalled" if not installed else "active"),
        })

    if unused_only:
        results = [r for r in results if r["import_count"] == 0]

    if as_json:
        click.echo(json.dumps(results, indent=2))
        return results

    click.echo("=== Dependency Audit Report ===")
    click.echo("")
    for r in sorted(results, key=lambda x: (x["import_count"], x["category"])):
        icon = {"active": "OK", "unused": "UNUSED", "uninstalled": "MISSING"}[r["status"]]
        click.echo(f"  {r['package']:<30s} imports={r['import_count']:>2d}  [{r['category']:<8s}] {icon}")
    click.echo("")
    active = sum(1 for r in results if r["status"] == "active")
    unused = sum(1 for r in results if r["status"] == "unused")
    missing = sum(1 for r in results if r["status"] == "uninstalled")
    click.echo(f"Summary: {active} active, {unused} unused, {missing} missing")

    return results


__all__ = ["run_audit", "CORE_DEPS", "OPTIONAL_DEPS"]
