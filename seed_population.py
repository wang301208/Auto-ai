import argparse
import random
from pathlib import Path
import yaml

STRATEGY_DIR = Path("evolve_strategies/population/generation_0")
STRATEGY_DIR.mkdir(parents=True, exist_ok=True)

TOOLS = ["web_browser", "file_writer", "terminal", "debugger"]
STEPS = ["plan", "search", "reflect", "execute"]


def random_strategy() -> dict:
    return {
        "think_mode": random.choice(["depth_first", "breadth_first"]),
        "prompt_template": "SYSTEM: You are AutoAI.\nUSER: ${task}",
        "toolset": random.sample(TOOLS, random.randint(1, len(TOOLS))),
        "step_sequence": random.sample(STEPS, random.randint(2, len(STEPS))),
    }


def main(count: int) -> None:
    for i in range(count):
        data = random_strategy()
        path = STRATEGY_DIR / f"strategy_{i:03d}.yaml"
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(data, f)
        print(f"Wrote {path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed initial strategy population")
    parser.add_argument("-n", "--num", type=int, default=20, help="Number of strategies")
    args = parser.parse_args()
    main(args.num)
