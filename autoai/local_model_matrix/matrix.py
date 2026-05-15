from __future__ import annotations

import time
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class ModelTier(Enum):
    TINY = "tiny"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    CLOUD = "cloud"


class ModelStatus(Enum):
    AVAILABLE = "available"
    LOADING = "loading"
    READY = "ready"
    BUSY = "busy"
    ERROR = "error"
    UNAVAILABLE = "unavailable"


@dataclass
class ModelSpec:
    """本地模型规格。"""
    model_id: str
    name: str
    tier: ModelTier
    size_billions: float
    provider: str = "ollama"
    endpoint: str = "http://localhost:11434"
    status: ModelStatus = ModelStatus.AVAILABLE
    capabilities: set[str] = field(default_factory=lambda: {"chat"})
    avg_latency_ms: float = 0.0
    avg_quality_score: float = 0.0
    cost_per_1k_tokens: float = 0.0
    is_local: bool = True
    context_window: int = 4096
    last_used: float = 0.0
    use_count: int = 0

    @property
    def is_free(self) -> bool:
        return self.cost_per_1k_tokens == 0.0


@dataclass
class RoutingResult:
    """路由结果。"""
    model: ModelSpec
    reason: str
    estimated_cost: float = 0.0
    estimated_latency_ms: float = 0.0
    escalated: bool = False


class LocalModelMatrix:
    """本地模型矩阵: 从1B到70B+云模型的完整推理基础设施。

    目标: 95%推理零成本、零外部依赖。
    """

    DEFAULT_MATRIX = {
        "tiny": {
            "model_id": "local-tiny",
            "name": "phi3:mini",
            "size_billions": 3.8,
            "endpoint": "http://localhost:11434",
            "avg_latency_ms": 50,
            "avg_quality_score": 0.4,
            "context_window": 4096,
        },
        "small": {
            "model_id": "local-small",
            "name": "llama3.1:8b",
            "size_billions": 8.0,
            "endpoint": "http://localhost:11434",
            "avg_latency_ms": 200,
            "avg_quality_score": 0.6,
            "context_window": 8192,
        },
        "medium": {
            "model_id": "local-medium",
            "name": "qwen2.5:14b",
            "size_billions": 14.0,
            "endpoint": "http://localhost:11434",
            "avg_latency_ms": 500,
            "avg_quality_score": 0.75,
            "context_window": 32768,
        },
        "large": {
            "model_id": "local-large",
            "name": "deepseek-r1:70b",
            "size_billions": 70.0,
            "endpoint": "http://localhost:11434",
            "avg_latency_ms": 2000,
            "avg_quality_score": 0.9,
            "context_window": 32768,
        },
        "cloud": {
            "model_id": "cloud-gpt4o",
            "name": "gpt-4o",
            "size_billions": 0,
            "endpoint": "https://api.openai.com/v1",
            "avg_latency_ms": 1500,
            "avg_quality_score": 0.95,
            "cost_per_1k_tokens": 0.03,
            "is_local": False,
            "context_window": 128000,
        },
    }

    def __init__(self):
        self._models: dict[str, ModelSpec] = {}
        self._load_default_matrix()
        logger.info(f"本地模型矩阵初始化: {len(self._models)}个模型")

    def _load_default_matrix(self) -> None:
        for tier_name, spec_data in self.DEFAULT_MATRIX.items():
            tier = ModelTier(tier_name)
            spec = ModelSpec(
                model_id=spec_data["model_id"],
                name=spec_data["name"],
                tier=tier,
                size_billions=spec_data["size_billions"],
                endpoint=spec_data.get("endpoint", "http://localhost:11434"),
                avg_latency_ms=spec_data.get("avg_latency_ms", 0),
                avg_quality_score=spec_data.get("avg_quality_score", 0),
                cost_per_1k_tokens=spec_data.get("cost_per_1k_tokens", 0.0),
                is_local=spec_data.get("is_local", True),
                context_window=spec_data.get("context_window", 4096),
            )
            self._models[spec.model_id] = spec

    def add_model(self, spec: ModelSpec) -> None:
        self._models[spec.model_id] = spec

    def get_model(self, model_id: str) -> ModelSpec | None:
        return self._models.get(model_id)

    def get_by_tier(self, tier: ModelTier) -> list[ModelSpec]:
        return [m for m in self._models.values() if m.tier == tier]

    def get_local_models(self) -> list[ModelSpec]:
        return [m for m in self._models.values() if m.is_local]

    def get_free_models(self) -> list[ModelSpec]:
        return [m for m in self._models.values() if m.is_free]

    def health_check(self) -> dict[str, ModelStatus]:
        return {mid: m.status for mid, m in self._models.items()}

    def get_matrix_stats(self) -> dict:
        local = [m for m in self._models.values() if m.is_local]
        cloud = [m for m in self._models.values() if not m.is_local]
        free = [m for m in self._models.values() if m.is_free]
        return {
            "total_models": len(self._models),
            "local_models": len(local),
            "cloud_models": len(cloud),
            "free_models": len(free),
            "free_ratio": len(free) / max(1, len(self._models)),
        }


class ZeroCostRouter:
    """零成本路由器: 最大化本地模型使用, 仅关键决策escalate到云端。

    目标: 95%推理零成本。
    """

    def __init__(self, matrix: LocalModelMatrix, escalation_threshold: float = 0.7):
        self.matrix = matrix
        self.escalation_threshold = escalation_threshold
        self._routing_history: list[dict] = []
        self._local_usage_count = 0
        self._cloud_usage_count = 0

    def route(self, task_complexity: float, required_quality: float = 0.8,
              max_latency_ms: float | None = None, task_type: str = "") -> RoutingResult:
        candidates = sorted(
            self.matrix.get_local_models(),
            key=lambda m: m.avg_quality_score, reverse=True,
        )
        best_local = None
        for model in candidates:
            if model.avg_quality_score >= required_quality:
                best_local = model
                break
        if best_local is None:
            best_local = candidates[0] if candidates else None
        if best_local and (best_local.avg_quality_score < self.escalation_threshold or required_quality > 0.9):
            cloud_models = [m for m in self.matrix._models.values() if not m.is_local]
            if cloud_models:
                cloud = max(cloud_models, key=lambda m: m.avg_quality_score)
                self._cloud_usage_count += 1
                self._record_routing(task_type, cloud, "escalated")
                return RoutingResult(
                    model=cloud,
                    reason=f"质量要求{required_quality}超过本地模型能力({best_local.avg_quality_score}), escalate到云端",
                    estimated_cost=cloud.cost_per_1k_tokens,
                    estimated_latency_ms=cloud.avg_latency_ms,
                    escalated=True,
                )
        if best_local:
            self._local_usage_count += 1
            self._record_routing(task_type, best_local, "local")
            return RoutingResult(
                model=best_local,
                reason=f"本地模型满足要求(质量={best_local.avg_quality_score}>=阈值)",
                estimated_cost=0.0,
                estimated_latency_ms=best_local.avg_latency_ms,
            )
        cloud_fallback = next((m for m in self.matrix._models.values() if not m.is_local), None)
        if cloud_fallback:
            self._cloud_usage_count += 1
            return RoutingResult(model=cloud_fallback, reason="无本地模型可用, fallback到云端", escalated=True)
        raise RuntimeError("无可用的推理模型")

    def _record_routing(self, task_type: str, model: ModelSpec, decision: str) -> None:
        self._routing_history.append({
            "task_type": task_type, "model_id": model.model_id,
            "decision": decision, "timestamp": time.time(),
        })

    @property
    def local_ratio(self) -> float:
        total = self._local_usage_count + self._cloud_usage_count
        return self._local_usage_count / total if total > 0 else 0.0

    def get_stats(self) -> dict:
        return {
            "local_usage": self._local_usage_count,
            "cloud_usage": self._cloud_usage_count,
            "local_ratio": self.local_ratio,
            "target_ratio": 0.95,
            "on_target": self.local_ratio >= 0.95,
        }
