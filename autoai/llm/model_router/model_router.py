"""模型路由器：从任务特征到提供者+模型选择的智能路由。"""

from __future__ import annotations

import enum
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .base_provider import BaseProvider, ChatMessage, ChatResponse, EmbeddingResponse, ProviderStatus
from .model_registry import ModelRegistry
from .model_spec import ModelCapability, ModelSpec, ModelTier

logger = logging.getLogger(__name__)


class RoutingStrategy(enum.Enum):
    COST_OPTIMAL = "cost_optimal"
    PERFORMANCE_OPTIMAL = "performance_optimal"
    LOCAL_FIRST = "local_first"
    CLOUD_FIRST = "cloud_first"
    MANUAL = "manual"


@dataclass
class RoutingPolicy:
    strategy: RoutingStrategy = RoutingStrategy.COST_OPTIMAL
    budget_limit_per_request: float = 0.1
    daily_budget_limit: float = 10.0
    prefer_local: bool = False
    allow_degradation: bool = True
    max_degradation_depth: int = 3
    require_capabilities: ModelCapability = ModelCapability.CHAT
    blocked_providers: set[str] = field(default_factory=set)
    forced_model: str | None = None
    _daily_spent: float = field(default=0.0, init=False)
    _daily_reset_date: str = field(default="", init=False)

    def check_budget(self, estimated_cost: float) -> bool:
        self._check_daily_reset()
        if estimated_cost > self.budget_limit_per_request:
            return False
        if self._daily_spent + estimated_cost > self.daily_budget_limit:
            return False
        return True

    def record_spend(self, cost: float) -> None:
        self._check_daily_reset()
        self._daily_spent += cost

    @property
    def daily_remaining(self) -> float:
        self._check_daily_reset()
        return max(0, self.daily_budget_limit - self._daily_spent)

    def _check_daily_reset(self) -> None:
        today = datetime.now(timezone.utc).date().isoformat()
        if today != self._daily_reset_date:
            self._daily_spent = 0.0
            self._daily_reset_date = today


@dataclass
class RoutingDecision:
    model_id: str
    provider_name: str
    tier: ModelTier
    estimated_cost: float = 0.0
    degradation_path: list[str] = field(default_factory=list)
    reason: str = ""


class ModelRouter:
    """Intelligent model router.

        Routing pipeline:
          1. If policy.forced_model is set, use that directly
          2. Resolve candidate models by tier/capability
          3. 过滤 by budget, availability, blocked providers
          4. Apply strategy to rank candidates
          5. If top candidate unavailable, follow degradation chain
          6. Return RoutingDecision with provider+model
"""

    def __init__(
        self,
        registry: ModelRegistry,
        policy: RoutingPolicy | None = None,
    ) -> None:
        self._registry = registry
        self._policy = policy or RoutingPolicy()

    @property
    def registry(self) -> ModelRegistry:
        return self._registry

    @property
    def policy(self) -> RoutingPolicy:
        return self._policy

    def route(
        self,
        task_tier: ModelTier = ModelTier.BALANCED,
        required_capabilities: ModelCapability = ModelCapability.CHAT,
        estimated_tokens: int = 1000,
        preferred_provider: str | None = None,
        task_type: str | None = None,
    ) -> RoutingDecision | None:
        if self._policy.forced_model:
            spec = self._registry.get_model(self._policy.forced_model)
            if spec and self._is_available(spec):
                return RoutingDecision(
                    model_id=spec.model_id,
                    provider_name=spec.provider_name,
                    tier=spec.tier,
                    estimated_cost=self._estimate_cost(spec, estimated_tokens),
                    reason="forced_model",
                )

        candidates = self._get_candidates(task_tier, required_capabilities, preferred_provider)
        if not candidates:
            broader_tier = self._broaden_tier(task_tier)
            if broader_tier != task_tier:
                candidates = self._get_candidates(broader_tier, required_capabilities, preferred_provider)
        if not candidates:
            candidates = self._get_candidates(ModelTier.BALANCED, required_capabilities, preferred_provider)

        if not candidates:
            logger.warning("No candidate 模型 found for tier=%s, caps=%s", task_tier, required_capabilities)
            return None

        candidates = self._filter_by_budget(candidates, estimated_tokens)
        candidates = self._filter_by_availability(candidates)
        candidates = self._filter_blocked(candidates)

        if not candidates and self._policy.allow_degradation:
            return self._route_with_degradation(task_tier, required_capabilities, estimated_tokens)

        if not candidates:
            return None

        ranked = self._rank_by_strategy(candidates, estimated_tokens)
        best = ranked[0]
        cost = self._estimate_cost(best, estimated_tokens)

        return RoutingDecision(
            model_id=best.model_id,
            provider_name=best.provider_name,
            tier=best.tier,
            estimated_cost=cost,
            reason=f"strategy={self._policy.strategy.value}",
        )

    async def execute_chat(
        self,
        messages: list[ChatMessage],
        decision: RoutingDecision,
        temperature: float = 0.0,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> ChatResponse:
        provider = self._registry.get_provider(decision.provider_name)
        if not provider:
            raise ValueError(f"Provider '{decision.provider_name}' not registered")

        try:
            response = await provider.chat(
                messages=messages,
                model=decision.model_id,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            )
            self._policy.record_spend(response.total_cost)
            provider.health.record_success(0)
            return response
        except Exception as e:
            provider.health.record_failure()
            if self._policy.allow_degradation:
                fallback = self._get_fallback(decision)
                if fallback:
                    logger.info("回退到%s/%s", fallback.provider_name, fallback.model_id)
                    return await self.execute_chat(messages, fallback, temperature, max_tokens, **kwargs)
            raise

    async def execute_embed(
        self,
        text: str,
        model_id: str | None = None,
        **kwargs: Any,
    ) -> EmbeddingResponse:
        if model_id is None:
            embed_models = self._registry.list_models(tier="embedding")
            if not embed_models:
                raise ValueError("没有注册嵌入模型")
            model_id = embed_models[0].model_id

        spec = self._registry.get_model(model_id)
        if not spec:
            raise ValueError(f"Model '{model_id}' not found in registry")

        provider = self._registry.get_provider(spec.provider_name)
        if not provider:
            raise ValueError(f"Provider '{spec.provider_name}' not registered")

        return await provider.embed(text=text, model=model_id, **kwargs)

    def _get_candidates(
        self,
        tier: ModelTier,
        capabilities: ModelCapability,
        preferred_provider: str | None = None,
    ) -> list[ModelSpec]:
        models = self._registry.list_models(tier=tier.value)
        models = [m for m in models if m.has_capability(capabilities)]
        if preferred_provider:
            preferred = [m for m in models if m.provider_name == preferred_provider]
            if preferred:
                return preferred
        return models

    def _filter_by_budget(self, models: list[ModelSpec], tokens: int) -> list[ModelSpec]:
        result = []
        for m in models:
            cost = self._estimate_cost(m, tokens)
            if self._policy.check_budget(cost):
                result.append(m)
        return result if result else models

    def _filter_by_availability(self, models: list[ModelSpec]) -> list[ModelSpec]:
        available = []
        for m in models:
            provider = self._registry.get_provider(m.provider_name)
            if provider and provider.is_available:
                available.append(m)
            elif not provider and not m.is_local:
                available.append(m)
        return available if available else models

    def _filter_blocked(self, models: list[ModelSpec]) -> list[ModelSpec]:
        if not self._policy.blocked_providers:
            return models
        return [m for m in models if m.provider_name not in self._policy.blocked_providers]

    def _rank_by_strategy(self, models: list[ModelSpec], tokens: int) -> list[ModelSpec]:
        if self._policy.strategy == RoutingStrategy.COST_OPTIMAL:
            return sorted(models, key=lambda m: self._estimate_cost(m, tokens))
        elif self._policy.strategy == RoutingStrategy.PERFORMANCE_OPTIMAL:
            return sorted(models, key=lambda m: -m.max_context_tokens)
        elif self._policy.strategy == RoutingStrategy.LOCAL_FIRST:
            return sorted(models, key=lambda m: (0 if m.is_local else 1, self._estimate_cost(m, tokens)))
        elif self._policy.strategy == RoutingStrategy.CLOUD_FIRST:
            return sorted(models, key=lambda m: (1 if m.is_local else 0, self._estimate_cost(m, tokens)))
        return models

    def _route_with_degradation(
        self,
        tier: ModelTier,
        capabilities: ModelCapability,
        tokens: int,
    ) -> RoutingDecision | None:
        all_models = self._registry.list_models()
        all_models = [m for m in all_models if m.has_capability(capabilities)]
        if not all_models:
            return None

        for model in all_models:
            chain = self._registry.get_fallback_chain(model.model_id)
            for mid in chain[:self._policy.max_degradation_depth]:
                spec = self._registry.get_model(mid)
                if spec and self._is_available(spec):
                    cost = self._estimate_cost(spec, tokens)
                    return RoutingDecision(
                        model_id=spec.model_id,
                        provider_name=spec.provider_name,
                        tier=spec.tier,
                        estimated_cost=cost,
                        degradation_path=chain,
                        reason="degradation_fallback",
                    )
        return None

    def _get_fallback(self, decision: RoutingDecision) -> RoutingDecision | None:
        chain = self._registry.get_fallback_chain(decision.model_id)
        for mid in chain[1:]:
            spec = self._registry.get_model(mid)
            if spec and self._is_available(spec):
                return RoutingDecision(
                    model_id=spec.model_id,
                    provider_name=spec.provider_name,
                    tier=spec.tier,
                    reason="runtime_fallback",
                )
        return None

    def _is_available(self, spec: ModelSpec) -> bool:
        provider = self._registry.get_provider(spec.provider_name)
        if provider:
            return provider.is_available
        return True

    def _estimate_cost(self, spec: ModelSpec, tokens: int) -> float:
        input_cost = (tokens / 1000) * spec.prompt_token_cost_per_1k
        output_cost = (tokens / 2000) * spec.completion_token_cost_per_1k
        return input_cost + output_cost

    @staticmethod
    def _broaden_tier(tier: ModelTier) -> ModelTier:
        tier_map = {
            ModelTier.FAST: ModelTier.BALANCED,
            ModelTier.BALANCED: ModelTier.SMART,
            ModelTier.SMART: ModelTier.BALANCED,
            ModelTier.EMBEDDING: ModelTier.EMBEDDING,
        }
        return tier_map.get(tier, ModelTier.BALANCED)


__all__ = [
    "RoutingStrategy",
    "RoutingPolicy",
    "RoutingDecision",
    "ModelRouter",
]
