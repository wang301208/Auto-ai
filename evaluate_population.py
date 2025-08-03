from pathlib import Path
import time
from openevolve.runner import evaluate

TASK_DIR = Path("bench_tasks")
STRATEGY_DIR = Path("evolve_strategies/population/generation_0")

tasks = [p.read_text().strip() for p in TASK_DIR.glob("*.txt")]


def main() -> None:
    for yaml_path in STRATEGY_DIR.glob("*.yaml"):
        start = time.time()
        fitness = evaluate(str(yaml_path), tasks)
        duration = time.time() - start
        print(f"{yaml_path.name}: {fitness:.3f} ({duration:.1f}s)")


if __name__ == "__main__":
    main()
