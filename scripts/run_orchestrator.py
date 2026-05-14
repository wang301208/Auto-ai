"""CLI entry point for running the AutoAI orchestrator."""

import argparse
from pathlib import Path
from typing import Dict

from autoai.orchestrator import AVAILABLE_AGENTS, Orchestrator


def parse_workdirs(pairs: list[str]) -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    for pair in pairs:
        try:
            name, path = pair.split("=", 1)
        except ValueError:  # pragma: no cover - simple argument validation
            raise argparse.ArgumentTypeError("workdir must be in NAME=PATH format")
        mapping[name] = path
    return mapping


def main() -> None:
    parser = argparse.ArgumentParser(description="Run AutoAI orchestrator")
    parser.add_argument(
        "--agents",
        nargs="*",
        default=AVAILABLE_AGENTS,
        choices=AVAILABLE_AGENTS,
        help="Agents to start",
    )
    parser.add_argument(
        "--workdir",
        action="append",
        default=[],
        metavar="AGENT=PATH",
        help="Working directory for an agent",
    )
    parser.add_argument(
        "--db-path",
        default="events.db",
        type=Path,
        help="Path to the event database",
    )
    args = parser.parse_args()

    workdirs = parse_workdirs(args.workdir)
    orchestrator = Orchestrator(
        db_path=args.db_path, agents=args.agents, workdirs=workdirs
    )
    orchestrator.start()


if __name__ == "__main__":
    main()
