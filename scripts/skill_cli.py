"""CLI for managing the skill library."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from autogpt.config import Config
from autogpt.skills.library import SkillLibrary


def add_skill(path: str) -> None:
    """Add a new skill from a directory containing ``skill.json`` and ``main.py``."""
    skill_path = Path(path)
    meta_file = skill_path / "skill.json"
    code_file = skill_path / "main.py"
    if not meta_file.exists() or not code_file.exists():
        print("Skill path must contain 'skill.json' and 'main.py'.")
        return

    with meta_file.open("r", encoding="utf-8") as f:
        meta = json.load(f)
    code = code_file.read_text(encoding="utf-8")

    config = Config()
    library = SkillLibrary(config)
    skill = library.add_skill(
        meta["skill_name"],
        meta["version"],
        code,
        meta.get("parameters", {}),
        meta.get("description", ""),
        meta.get("tags", []),
    )
    tag = f"skill-{skill.name}-v{skill.version}"
    try:
        subprocess.run(["git", "tag", tag], check=True)
        print(f"Tagged repository with {tag}")
    except Exception as e:  # pragma: no cover - best effort
        print(f"Warning: failed to create git tag: {e}")
    print(f"Added skill {skill.name} version {skill.version}")


def search_skills(query: str) -> None:
    """Search the library for skills matching ``query``."""
    config = Config()
    library = SkillLibrary(config)
    results = library.search(query)
    if not results:
        print("No matching skills found.")
        return
    for skill in results:
        print(f"{skill.name} {skill.version}: {skill.description}")


def test_skill(name: str) -> int:
    """Run tests for the latest version of ``name``."""
    config = Config()
    library = SkillLibrary(config)
    candidates = [s for s in library.list_skills() if s.name == name]
    if not candidates:
        print(f"No skill named {name} found")
        return 1
    # pick latest version lexicographically
    skill = sorted(candidates, key=lambda s: s.version, reverse=True)[0]
    skill_dir = library.storage_path / f"{skill.name}_{skill.version}"
    test_file = skill_dir / "test_main.py"
    if not test_file.exists():
        print(f"No tests found for {skill.name} {skill.version}")
        return 1
    result = subprocess.run(["pytest", str(test_file)])
    return result.returncode


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage skills in the library")
    sub = parser.add_subparsers(dest="command")

    add_p = sub.add_parser("add", help="Add a skill from a directory")
    add_p.add_argument("path", help="Path to the skill directory")

    search_p = sub.add_parser("search", help="Search for skills")
    search_p.add_argument("query", help="Search query")

    test_p = sub.add_parser("test", help="Run tests for a skill")
    test_p.add_argument("name", help="Name of the skill to test")

    args = parser.parse_args()
    if args.command == "add":
        add_skill(args.path)
    elif args.command == "search":
        search_skills(args.query)
    elif args.command == "test":
        raise SystemExit(test_skill(args.name))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
