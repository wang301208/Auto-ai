# Strategy Evolution

The `evolve_strategies/population` folder contains YAML files describing different agent strategies. Each file defines options such as the prompt template, the tools allowed and the order in which the agent uses them. These YAML files can be used to automatically build an agent with `build_agent_from_strategy`.

## Seeding strategies

Use `seed_population.py` to generate an initial set of random strategies. The script writes files to `evolve_strategies/population/generation_0`.

```bash
python seed_population.py -n 20
```

## Evaluating strategies

`evaluate_population.py` loads tasks from `bench_tasks` and evaluates every strategy file in the population directory.

```bash
python evaluate_population.py
```

Each strategy's fitness score is printed so you can select the best configurations.

## Building an agent from a custom strategy

Once you have a YAML strategy, create an agent directly in Python:

```python
from autogpt import build_agent_from_strategy

agent = build_agent_from_strategy("path/to/strategy.yaml")
result = agent.run("Write a short poem about the sea")
print(result)
```

This method applies the YAML settings to the standard configuration and returns an initialized agent ready for use.

## Full evolution loop

The `auto_evolve.py` script runs multiple generations of strategy evolution.
When it finishes, the top-performing YAML configuration is written to
`evolve_strategies/best/best_strategy.yaml` for easy reuse. To maintain backward
compatibility, the same file is also copied to `configs/default_strategy.yaml`:

```bash
python auto_evolve.py -g 10 -p 20 -r 5
```
