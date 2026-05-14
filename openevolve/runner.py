from typing import Any, Dict

from autoai import build_agent_from_strategy


def compute_fitness(result: Dict[str, Any] | Any) -> float:
    """Compute fitness score from an agent result.

    The result can be an EvaluationResult dataclass or a plain metrics dict.
    The computed fitness rewards task success and penalizes token usage and
    runtime. Modify this function to reflect the desired evaluation metrics.
    """
    metrics = getattr(result, "metrics", result)
    if not isinstance(metrics, dict):
        return 0.0

    success = float(metrics.get("success", 0.0))
    token_usage = float(metrics.get("token_usage", 0.0))
    runtime = float(metrics.get("runtime", 0.0))

    # Basic weighting: reward success and penalize cost metrics
    return success - 0.01 * token_usage - 0.1 * runtime


def evaluate(strategy_yaml: str, task_suite: list[str]) -> float:
    """Evaluate an agent strategy across a suite of tasks.

    Parameters
    ----------
    strategy_yaml: str
        Path to a YAML file describing the strategy for building the agent.
    task_suite: list[str]
        Collection of tasks that will be passed to the agent's ``run`` method.

    Returns
    -------
    float
        The average fitness across all tasks.
    """
    agent = build_agent_from_strategy(strategy_yaml)
    scores = []
    for task in task_suite:
        result = agent.run(task)
        scores.append(compute_fitness(result))
    return sum(scores) / len(scores) if scores else 0.0
