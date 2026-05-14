from __future__ import annotations

import argparse
from pathlib import Path

from autoai.orchestrator_blueprint import BlueprintOrchestrator


def main() -> None:
    parser = argparse.ArgumentParser(description="Run blueprint-based orchestrator")
    parser.add_argument("--charter-url", required=False, default=str((Path.cwd() / "organizational_charter").resolve()))
    parser.add_argument("--events-db", required=False, default="events.db")
    parser.add_argument("--poll", type=float, default=60.0)
    args = parser.parse_args()

    orch = BlueprintOrchestrator(
        charter_git_url=args.charter_url,
        local_path=".autoai_charter",
        events_db=args.events_db,
        poll_interval_sec=args.poll,
    )
    orch.start()


if __name__ == "__main__":
    main()


