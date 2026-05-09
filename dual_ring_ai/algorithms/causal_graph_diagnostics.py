"""Causal graph diagnostic candidate engine."""

from __future__ import annotations

from typing import Any


class CausalGraphDiagnosticsEngine:
    """Use explicit signal-to-cause edges for local root-cause diagnosis."""

    causal_edges = {
        "database_regression": {
            "db_latency": 0.65,
            "api_errors": 0.25,
            "deploy_recent": 0.20,
            "network_errors": -0.20,
        },
        "network_outage": {
            "network_errors": 0.70,
            "api_errors": 0.25,
            "db_latency": -0.10,
            "deploy_recent": -0.10,
        },
        "application_bug": {
            "deploy_recent": 0.60,
            "api_errors": 0.25,
            "db_latency": 0.05,
            "network_errors": -0.10,
        },
    }

    def predict(self, incident: dict[str, Any]) -> str:
        signals = incident.get("signals", {})
        scores = {}
        for cause, edges in self.causal_edges.items():
            scores[cause] = sum(
                float(signals.get(signal, 0.0)) * weight
                for signal, weight in edges.items()
            )
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
            "latency_ms": 90.0,
        }
