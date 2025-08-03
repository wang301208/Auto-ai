#!/usr/bin/env python3
from __future__ import annotations

import argparse
import random
import shutil
import time
from pathlib import Path

import yaml

from openevolve.runner import evaluate
from seed_population import STEPS, TOOLS, random_strategy

TASK_DIR = Path("bench_tasks")
POP_DIR = Path("evolve_strategies/population")
CONFIGS_DIR = Path("configs")
DEFAULT_STRATEGY = CONFIGS_DIR / "default_strategy.yaml"
BEST_DIR = Path("evolve_strategies/best")
BEST_STRATEGY = BEST_DIR / "best_strategy.yaml"


def load_tasks() -> list[str]:
    """Load benchmark tasks from text files."""
    return [p.read_text().strip() for p in TASK_DIR.glob("*.txt")]


def mutate_strategy(strategy: dict) -> dict:
    """Return a slightly mutated copy of a strategy."""
    new = strategy.copy()
    if random.random() < 0.3:
        new["think_mode"] = random.choice(["depth_first", "breadth_first"])
    if random.random() < 0.3:
        new["toolset"] = random.sample(TOOLS, random.randint(1, len(TOOLS)))
    if random.random() < 0.3:
        new["step_sequence"] = random.sample(STEPS, random.randint(2, len(STEPS)))
    return new


def evolve_generation(
    gen: int, population: int, retain: int, tasks: list[str]
) -> list[tuple[float, Path]]:
    gen_dir = POP_DIR / f"generation_{gen}"
    next_dir = POP_DIR / f"generation_{gen + 1}"
    next_dir.mkdir(parents=True, exist_ok=True)

    scores: list[tuple[float, Path]] = []
    for yaml_path in gen_dir.glob("*.yaml"):
        start = time.time()
        fitness = evaluate(str(yaml_path), tasks)
        duration = time.time() - start
        scores.append((fitness, yaml_path))
        print(f"{yaml_path.name}: {fitness:.3f} ({duration:.1f}s)")

    scores.sort(reverse=True, key=lambda x: x[0])
    top = scores[:retain]

    for i, (_, path) in enumerate(top):
        data = yaml.safe_load(path.read_text())
        out = next_dir / f"strategy_{i:03d}.yaml"
        with open(out, "w", encoding="utf-8") as f:
            yaml.dump(data, f)

    # Import any incoming strategies before generating new ones
    incoming_dir = POP_DIR / "incoming"
    incoming_dir.mkdir(exist_ok=True)
    incoming_files = sorted(incoming_dir.glob("*.yaml"))
    for i, path in enumerate(incoming_files):
        dest = next_dir / f"incoming_{i:03d}.yaml"
        shutil.move(path, dest)
    # Clear incoming directory to avoid re-importing
    for leftover in incoming_dir.iterdir():
        if leftover.is_file():
            leftover.unlink()
        else:
            shutil.rmtree(leftover)

    while len(list(next_dir.glob("*.yaml"))) < population:
        base = random.choice(top)[1]
        data = yaml.safe_load(base.read_text())
        mutated = mutate_strategy(data)
        out = next_dir / f"strategy_{len(list(next_dir.glob('*.yaml'))):03d}.yaml"
        with open(out, "w", encoding="utf-8") as f:
            yaml.dump(mutated, f)

    return scores


def find_best_strategy(gen: int, tasks: list[str]) -> tuple[Path | None, float]:
    """Evaluate generation `gen` and return the best strategy and its score."""
    gen_dir = POP_DIR / f"generation_{gen}"
    best_path: Path | None = None
    best_score = -float("inf")

    for yaml_path in gen_dir.glob("*.yaml"):
        fitness = evaluate(str(yaml_path), tasks)
        if fitness > best_score:
            best_score = fitness
            best_path = yaml_path

    return best_path, best_score


def main(generations: int, population: int, retain: int) -> None:
    tasks = load_tasks()
    POP_DIR.mkdir(parents=True, exist_ok=True)
    gen0 = POP_DIR / "generation_0"
    gen0.mkdir(exist_ok=True)
    if not any(gen0.glob("*.yaml")):
        for i in range(population):
            data = random_strategy()
            with open(gen0 / f"strategy_{i:03d}.yaml", "w", encoding="utf-8") as f:
                yaml.dump(data, f)

    for g in range(0, generations):
        print(f"\n=== Generation {g} ===")
        evolve_generation(g, population, retain, tasks)

    best_path, score = find_best_strategy(generations, tasks)
    if best_path:
        CONFIGS_DIR.mkdir(exist_ok=True)
        BEST_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copy(best_path, BEST_STRATEGY)
        shutil.copy(best_path, DEFAULT_STRATEGY)
        print(
            f"Best strategy {best_path.name} (score {score:.3f}) -> "
            f"{BEST_STRATEGY} and {DEFAULT_STRATEGY}"
        )
    else:
        print("No strategy found in final generation")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run full strategy evolution loop")
    parser.add_argument(
        "-g", "--generations", type=int, default=10, help="Number of generations"
    )
    parser.add_argument(
        "-p", "--population", type=int, default=20, help="Strategies per generation"
    )
    parser.add_argument(
        "-r",
        "--retain",
        type=int,
        default=5,
        help="Top strategies to keep each generation",
    )
    args = parser.parse_args()
    main(args.generations, args.population, args.retain)
