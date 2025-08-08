"""CLI entry point for running the :class:`Executor` agent."""

from __future__ import annotations

import argparse

from autogpt.agents.executor import Executor
from autogpt.config import Config
from autogpt.event_bus import MessageQueue


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Executor agent")
    parser.add_argument("goal", help="High level goal for the agent")
    args = parser.parse_args()

    config = Config()
    queue = MessageQueue()
    executor = Executor(config=config, message_queue=queue)

    plan = executor.plan(args.goal)
    print("Plan:")
    for i, step in enumerate(plan, start=1):
        print(f"{i}. {step.description}")

    results = executor.execute(plan)
    print("\nResults:")
    for i, res in enumerate(results, start=1):
        print(f"Step {i}: {res}")


if __name__ == "__main__":
    main()
