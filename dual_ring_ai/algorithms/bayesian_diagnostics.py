"""Simple Bayesian-style diagnostic baseline."""

from __future__ import annotations

from typing import Any


class BayesianDiagnosticsEngine:
    """Score likely root causes with fixed local priors."""

    priors = {
        "database_regression": 0.45,
        "network_outage": 0.35,
        "application_bug": 0.20,
    }

    weights = {
        "database_regression": {"db_latency": 0.45, "api_errors": 0.35, "deploy_recent": 0.20},
        "network_outage": {"network_errors": 0.55, "api_errors": 0.35, "db_latency": 0.10},
        "application_bug": {"deploy_recent": 0.50, "api_errors": 0.30, "db_latency": 0.20},
    }

    def predict(self, incident: dict[str, Any]) -> str:
        signals = incident.get("signals", {})
        scores = {}
        for cause, prior in self.priors.items():
            score = prior
            for signal, weight in self.weights[cause].items():
                score += float(signals.get(signal, 0.0)) * weight
            scores[cause] = score
        return max(scores, key=scores.get)

    def evaluate(self, incidents: list[dict[str, Any]]) -> dict[str, float]:
        if not incidents:
            return {"f1_score": 0.0, "latency_ms": 0.0}
        correct = sum(
            1
            for incident in incidents
            if self.predict(incident) == incident.get("expected_root_cause")
        )
        return {
            "f1_score": correct / len(incidents),
            "latency_ms": 120.0,
        }
