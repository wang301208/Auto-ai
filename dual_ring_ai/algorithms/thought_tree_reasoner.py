"""Deterministic tree-of-thought style option scorer."""

from __future__ import annotations


class ThoughtTreeReasoner:
    """Score candidate actions by progress, evidence, and risk terms."""

    positive_terms = {
        "change": 2.0,
        "inspect": 1.5,
        "source": 1.2,
        "credibility": 1.2,
        "reduce": 1.0,
        "verify": 1.0,
    }
    negative_terms = {
        "same": 1.5,
        "ignore": 2.0,
        "failure": 0.8,
    }

    def __init__(self, branch_limit: int = 3) -> None:
        self.branch_limit = branch_limit

    def solve(self, goal: str, options: list[str]) -> dict:
        scored = []
        for option in options[: self.branch_limit]:
            text = f"{goal} {option}".lower()
            score = sum(
                weight for term, weight in self.positive_terms.items() if term in text
            )
            score -= sum(
                weight for term, weight in self.negative_terms.items() if term in option.lower()
            )
            scored.append({"option": option, "score": score})
        selected = max(scored, key=lambda item: item["score"])
        return {
            "goal": goal,
            "branches": scored,
            "selected_option": selected["option"],
            "score": selected["score"],
        }
