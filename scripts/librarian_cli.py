"""CLI for interacting with the :class:`LibrarianAgent`."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import logging

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

    args = parser.parse_args()
    agent = LibrarianAgent(Config())

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
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
