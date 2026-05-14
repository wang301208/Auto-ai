"""模型自动选择：代理自主为每个任务选择最佳模型。"""

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Any

class TaskComplexity(Enum):
    TRIVIAL = 0
    SIMPLE = 1
    MODERATE = 2
    COMPLEX = 3
    CRITICAL = 4

@dataclass
class TaskProfile:
    objective: str
    complexity: TaskComplexity = TaskComplexity.MODERATE
    estimated_tokens: int = 1000
    latency_sensitive: bool = False
    requires_creativity: bool = False
    requires_reasoning: bool = False
    task_type: str = "code"

@dataclass
class ModelChoice:
    model_id: str
    provider: str
    tier: str
    reason: str
    estimated_cost: float = 0.0
    estimated_latency_ms: float = 0.0

@dataclass
class ModelPerformanceRecord:
    model_id: str
    task_type: str
    success_count: int = 0
    failure_count: int = 0
    total_latency_ms: float = 0.0
    total_cost: float = 0.0
    @property
    def success_rate(self) -> float:
        total = self.success_count + self.failure_count
        return self.success_count / total if total > 0 else 0.5
    @property
    def avg_latency_ms(self) -> float:
        return self.total_latency_ms / self.success_count if self.success_count > 0 else 0.0

class ModelAutoSelector:
    def __init__(self, budget_remaining: float = 100.0) -> None:
        self._budget_remaining = budget_remaining
        self._performance: dict[str, ModelPerformanceRecord] = {}
        self._selection_count: int = 0
        self._tier_mapping = {
            TaskComplexity.TRIVIAL: "fast", TaskComplexity.SIMPLE: "fast",
            TaskComplexity.MODERATE: "balanced", TaskComplexity.COMPLEX: "smart",
            TaskComplexity.CRITICAL: "smart",
        }
        self._model_mapping = {
            "fast": [{"model_id": "qwen3-4b", "provider": "ollama"}, {"model_id": "gpt-4o-mini", "provider": "openai"}],
            "balanced": [{"model_id": "qwen3-14b", "provider": "ollama"}, {"model_id": "gpt-4o-mini", "provider": "openai"}],
            "smart": [{"model_id": "gpt-4o", "provider": "openai"}, {"model_id": "qwen3-72b", "provider": "ollama"}],
            "embedding": [{"model_id": "text-embedding-3-small", "provider": "openai"}],
        }
    def select(self, profile: TaskProfile) -> ModelChoice:
        self._selection_count += 1
        if profile.task_type == "embedding":
            c = self._model_mapping["embedding"][0]
            return ModelChoice(model_id=c["model_id"], provider=c["provider"], tier="embedding", reason="embedding_task")
        tier = self._tier_mapping.get(profile.complexity, "balanced")
        if profile.requires_creativity and profile.complexity.value >= TaskComplexity.COMPLEX.value:
            tier = "smart"
        if profile.latency_sensitive and tier == "smart":
            tier = "balanced"
        if self._budget_remaining < 1.0 and tier != "fast":
            tier = "fast"
        candidates = self._model_mapping.get(tier, [])
        best = self._pick_best(candidates, profile.task_type)
        if best is None:
            best = candidates[0] if candidates else {"model_id": "unknown", "provider": "unknown"}
        return ModelChoice(model_id=best["model_id"], provider=best["provider"], tier=tier,
            reason=self._reason(profile, tier),
            estimated_cost=self._cost(best["model_id"], profile.estimated_tokens),
            estimated_latency_ms={"fast":200,"balanced":800,"smart":2000}.get(tier,500))
    def record_outcome(self, model_id: str, task_type: str, success: bool, latency_ms: float = 0.0, cost: float = 0.0) -> None:
        key = f"{model_id}:{task_type}"
        if key not in self._performance:
            self._performance[key] = ModelPerformanceRecord(model_id=model_id, task_type=task_type)
        rec = self._performance[key]
        if success: rec.success_count += 1
        else: rec.failure_count += 1
        rec.total_latency_ms += latency_ms
        rec.total_cost += cost
        self._budget_remaining -= cost
    @property
    def budget_remaining(self) -> float: return self._budget_remaining
    def stats(self) -> dict[str, Any]:
        return {"selection_count": self._selection_count, "budget_remaining": self._budget_remaining, "performance_records": len(self._performance)}
    def _pick_best(self, candidates, task_type):
        if not self._performance: return None
        best_score, best = -1.0, None
        for c in candidates:
            key = f"{c['model_id']}:{task_type}"
            if key in self._performance:
                rec = self._performance[key]
                score = rec.success_rate * 0.7 + (1.0/(1.0+rec.avg_latency_ms/1000.0))*0.3
                if score > best_score: best_score, best = score, c
        return best
    def _cost(self, model_id, tokens):
        rates = {"gpt-4o":0.005,"gpt-4o-mini":0.00015,"qwen3-4b":0.0,"qwen3-14b":0.0,"qwen3-72b":0.0}
        return rates.get(model_id, 0.001)*tokens/1000.0
    def _reason(self, profile, tier):
        parts = [f"complexity={profile.complexity.name.lower()}", f"tier={tier}"]
        if self._budget_remaining < 1.0: parts.append("budget_low")
        if profile.latency_sensitive: parts.append("latency_sensitive")
        if profile.requires_creativity: parts.append("creativity_required")
        return ";".join(parts)

__all__ = ["TaskComplexity", "TaskProfile", "ModelChoice", "ModelAutoSelector"]
