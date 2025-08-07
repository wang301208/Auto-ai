"""CLI for interacting with the :class:`LibrarianAgent`."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from types import SimpleNamespace

from autogpt.commands.code_reader import read_and_understand_code
from autogpt.config import Config
from autogpt.skills import LibrarianAgent

logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Interact with the librarian agent")
    sub = parser.add_subparsers(dest="command")

    find_p = sub.add_parser("find", help="Search for skills")
    find_p.add_argument("query", help="Search query")
    find_p.add_argument("--k", type=int, default=3, help="Number of results to return")

    add_p = sub.add_parser("add", help="Add a new skill")
    add_p.add_argument("metadata", help="Path to JSON metadata file")
    add_p.add_argument("code", help="Path to Python file containing the skill")

    read_p = sub.add_parser("read-code", help="Summarize Python files under a path")
    read_p.add_argument("path", help="File or directory to analyze")

    src_p = sub.add_parser(
        "source-path", help="Print the source code path for a plugin"
    )
    src_p.add_argument("plugin_name", help="Name of the plugin")

    audit_p = sub.add_parser(
        "audit-log", help="Display or export denied access attempts"
    )
    audit_p.add_argument(
        "--export",
        help="Path to export audit log in JSON format",
    )

    args = parser.parse_args()
    config = Config()
    agent = LibrarianAgent(config)

    if args.command == "find":
        results = agent.find_skill(args.query, args.k)
        if not results:
            print("No matching skills found")
        else:
            for meta in results:
                print(json.dumps(meta, indent=2))
    elif args.command == "add":
        with Path(args.metadata).open("r", encoding="utf-8") as f:
            metadata = json.load(f)
        try:
            if agent.add_skill(metadata, args.code):
                print("Skill added successfully")
            else:
                print("Failed to add skill")
        except Exception:
            logger.exception("Failed to add skill")
    elif args.command == "source-path":
        path = agent.get_source_code_path(args.plugin_name)
        if path:
            print(path)
        else:
            print("Access denied or plugin not found")
    elif args.command == "read-code":
        dummy_agent = SimpleNamespace(
            config=config, llm=SimpleNamespace(name=config.fast_llm)
        )
        report = read_and_understand_code(args.path, dummy_agent)
        print(report)
    elif args.command == "audit-log":
        from autogpt.telemetry.audit import load_log

        entries = load_log()
        if args.export:
            Path(args.export).write_text(
                json.dumps(entries, indent=2), encoding="utf-8"
            )
            print(f"Audit log exported to {args.export}")
        else:
            if not entries:
                print("Audit log is empty")
            else:
                for entry in entries:
                    print(json.dumps(entry, indent=2))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
