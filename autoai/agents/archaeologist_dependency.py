from __future__ import annotations

"""Dependency analysis utilities for the Archaeologist agent."""

import ast
from importlib import metadata
from pathlib import Path
from typing import Any, Dict, Set

import requests


def fetch_release_notes(package: str, version: str | None) -> str | None:
    """获取 释放 notes for ``包`` at ``version`` from PyPI.

    ``version`` may be a not-yet-installed 释放 that should be inspected
    for compatibility. If fetching fails, ``None`` is returned.
    """

    if not version:
        return None
    url = f"https://pypi.org/pypi/{package}/{version}/json"
    try:
        resp = requests.get(url, timeout=5)
        if resp.ok:
            data = resp.json()
            return data.get("info", {}).get("description") or None
    except Exception:
        return None
    return None


def scan_for_usage(source: Path, package: str) -> Set[str]:
    """扫描 ``源`` for imports or API calls related to ``包``.

    Returns a 集合 of fully qualified names used in the file.
    """

    try:
        tree = ast.parse(source.read_text())
    except Exception:
        return set()

    aliases: Dict[str, str] = {}
    usages: Set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] == package:
                    aliases[alias.asname or alias.name] = alias.name
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.module.split(".")[0] == package:
                module = node.module
                for alias in node.names:
                    aliases[alias.asname or alias.name] = f"{module}.{alias.name}"

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute):
                value = func.value
                if isinstance(value, ast.Name) and value.id in aliases:
                    usages.add(f"{aliases[value.id]}.{func.attr}")
            elif isinstance(func, ast.Name) and func.id in aliases:
                usages.add(aliases[func.id])
    return usages


def analyze_dependency(
    package: str, source: Path, new_version: str | None = None
) -> Dict[str, Any]:
    """分析 ``包`` usage within ``源`` and 检查 释放 notes."""

    installed: str | None = None
    try:
        installed = metadata.version(package)
    except Exception:
        pass

    target_version = new_version or installed
    release_notes = fetch_release_notes(package, target_version)
    usages = scan_for_usage(source, package)

    findings: list[str] = []
    if release_notes:
        lowered = release_notes.lower()
        for usage in usages:
            name = usage.split(".")[-1].lower()
            if name in lowered and any(
                kw in lowered for kw in ["deprecated", "removed", "breaking"]
            ):
                findings.append(
                    f"{usage} may be incompatible with {package} {target_version}"
                )
        if not findings and any(
            kw in lowered for kw in ["deprecated", "removed", "breaking"]
        ):
            findings.append(
                f"{package} {target_version} release notes mention potential breaking changes"
            )

    return {
        "dependency": package,
        "version": installed,
        "new_version": new_version,
        "usages": sorted(usages),
        "release_notes": release_notes,
        "findings": findings,
    }
