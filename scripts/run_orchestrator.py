"""CLI entry point for running the AutoGPT orchestrator."""

from autogpt.orchestrator import Orchestrator


def main() -> None:
    orchestrator = Orchestrator()
    orchestrator.start()


if __name__ == "__main__":
    main()
