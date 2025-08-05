"""Register newly added skills in the repository.

This script scans the Git history for any ``skill.json`` files that were
added in the current branch compared to the base branch. For each newly
added ``skill.json`` file it invokes ``librarian.add_skill(metadata, code_path)``
so the skill is stored in the local skill library.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from autogpt.skills import LibrarianAgent


def _get_base_ref() -> str:
    """Return the git ref to compare the current branch against."""
    base_branch = os.environ.get("GITHUB_BASE_REF", "master")
    return f"origin/{base_branch}"


def find_new_skill_files(base_ref: str) -> list[Path]:
    """Return paths to ``skill.json`` files added since ``base_ref``."""
    diff_cmd = [
        "git",
        "diff",
        "--name-status",
        f"{base_ref}...HEAD",
        "--",
        "*skill.json",
    ]
    try:
        result = subprocess.run(diff_cmd, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError:
        # Fallback to diffing against the previous commit if the base ref is
        # unavailable (e.g. in a shallow clone)
        fallback_cmd = ["git", "diff", "--name-status", "HEAD^", "--", "*skill.json"]
        result = subprocess.run(
            fallback_cmd, capture_output=True, text=True, check=True
        )

    added: list[Path] = []
    for line in result.stdout.splitlines():
        status, path = line.split("\t", 1)
        if status == "A":
            added.append(Path(path))
    return added


def register_skill(skill_json: Path, librarian: LibrarianAgent) -> None:
    """Register a single skill given its ``skill.json`` file."""
    metadata = json.loads(skill_json.read_text(encoding="utf-8"))
    code_path = skill_json.parent / metadata.get("entry_point", "main.py")
    if librarian.add_skill(metadata, str(code_path)):
        print(f"Registered skill from {skill_json}")
    else:
        print(f"Failed to register skill from {skill_json}")


def main() -> None:
    base_ref = _get_base_ref()
    new_skills = find_new_skill_files(base_ref)
    if not new_skills:
        print("No new skills to register")
        return

    librarian = LibrarianAgent()
    for skill_file in new_skills:
        register_skill(skill_file, librarian)


if __name__ == "__main__":
    main()
