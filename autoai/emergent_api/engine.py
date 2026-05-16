"""自涌现API: API从使用模式中自动涌现，不需要设计。"""

from __future__ import annotations

import time
import hashlib
import logging
from dataclasses import dataclass, field
from typing import Any
from enum import Enum

from autoai.autonomy_core.cognitive_loop import CognitiveLoop
from autoai.autonomy_core.full_autonomy_mixin import FullAutonomyMixin

logger = logging.getLogger(__name__)


class APIStability(Enum):
    EXPERIMENTAL = "experimental"
    STABLE = "stable"
    DEPRECATED = "deprecated"


@dataclass
class APIPattern:
    """API使用模式: 记录Agent如何使用功能。"""
    pattern_id: str
    caller: str
    target_module: str
    target_method: str
    call_count: int = 1
    avg_latency_ms: float = 0.0
    error_rate: float = 0.0
    last_seen: float = field(default_factory=time.time)

    @property
    def is_hot(self) -> bool:
        return self.call_count >= 5

    @property
    def quality(self) -> float:
        if self.call_count == 0:
            return 0.0
        return (1.0 - self.error_rate) * min(1.0, self.call_count / 20.0)


@dataclass
class APISpec:
    """自涌现API规格: 从模式中生成的API。"""
    api_id: str
    endpoint: str
    method: str
    stability: APIStability = APIStability.EXPERIMENTAL
    patterns: list[str] = field(default_factory=list)
    call_count: int = 0
    emergent_at: float = field(default_factory=time.time)
    documentation: str = ""

    @property
    def is_stable(self) -> bool:
        return self.stability == APIStability.STABLE


class EmergentAPIEngine(FullAutonomyMixin):
    """自涌现API引擎: 从使用模式中涌现API。"""

    def __init__(self, use_cognitive_loop: bool = False):
        self._init_full_autonomy()
        self._patterns: dict[str, APIPattern] = {}
        self._apis: dict[str, APISpec] = {}
        self._emergence_threshold: int = 3
        self._total_calls: int = 0
        self._use_cognitive_loop = use_cognitive_loop
        self._cognitive_loop: CognitiveLoop | None = None
        if use_cognitive_loop:
            self._cognitive_loop = CognitiveLoop("emergent_api")

    def enable_cognitive_loop(self) -> None:
        if not self._use_cognitive_loop:
            self._use_cognitive_loop = True
            self._cognitive_loop = CognitiveLoop("emergent_api")

    def record_call(self, caller: str, target_module: str, target_method: str, latency_ms: float = 0.0, error: bool = False) -> APIPattern:
        self._total_calls += 1
        key = f"{caller}:{target_module}.{target_method}"
        if key in self._patterns:
            pat = self._patterns[key]
            pat.call_count += 1
            pat.avg_latency_ms = (pat.avg_latency_ms * (pat.call_count - 1) + latency_ms) / pat.call_count
            if error:
                pat.error_rate = (pat.error_rate * (pat.call_count - 1) + 1) / pat.call_count
            pat.last_seen = time.time()
        else:
            pat = APIPattern(
                pattern_id=f"pat_{len(self._patterns)}",
                caller=caller,
                target_module=target_module,
                target_method=target_method,
                avg_latency_ms=latency_ms,
                error_rate=1.0 if error else 0.0,
            )
            self._patterns[key] = pat
        return pat

    def discover_apis(self) -> list[APISpec]:
        """从使用模式中涌现API。"""
        method_patterns: dict[str, list[APIPattern]] = {}
        for pat in self._patterns.values():
            method_key = f"{pat.target_module}.{pat.target_method}"
            method_patterns.setdefault(method_key, []).append(pat)
        new_apis = []
        for method_key, patterns in method_patterns.items():
            total_calls = sum(p.call_count for p in patterns)
            if total_calls < self._emergence_threshold:
                continue
            if method_key in self._apis:
                api = self._apis[method_key]
                api.call_count = total_calls
                if total_calls >= 20 and api.stability == APIStability.EXPERIMENTAL:
                    api.stability = APIStability.STABLE
                continue
            module, method = method_key.rsplit(".", 1)
            api = APISpec(
                api_id=f"api_{hashlib.sha256(method_key.encode()).hexdigest()[:8]}",
                endpoint=f"/{module.replace('.', '/')}/{method}",
                method=method,
                patterns=[p.pattern_id for p in patterns],
                call_count=total_calls,
                documentation=self._generate_docs(method_key, patterns),
            )
            if total_calls >= 20:
                api.stability = APIStability.STABLE
            self._apis[method_key] = api
            new_apis.append(api)
            logger.info(f"API涌现: {api.endpoint} ({api.stability.value})")
        if self._use_cognitive_loop and self._cognitive_loop and new_apis:
            self._cognitive_loop.observe("api_emergence", {"new_apis": len(new_apis)}, 0.7)
            assessment = self._cognitive_loop.assess()
            self._cognitive_loop.decide(assessment)
        return new_apis

    def _generate_docs(self, method_key: str, patterns: list[APIPattern]) -> str:
        callers = list(set(p.caller for p in patterns))
        total = sum(p.call_count for p in patterns)
        avg_err = sum(p.error_rate * p.call_count for p in patterns) / max(total, 1)
        return f"{method_key}: {total}次调用, {len(callers)}个调用者, 错误率{avg_err:.2%}"

    def get_api(self, endpoint: str) -> APISpec | None:
        for api in self._apis.values():
            if api.endpoint == endpoint:
                return api
        return None

    @property
    def stats(self) -> dict[str, Any]:
        stable = sum(1 for a in self._apis.values() if a.is_stable)
        return {
            "total_patterns": len(self._patterns),
            "total_apis": len(self._apis),
            "stable_apis": stable,
            "experimental_apis": len(self._apis) - stable,
            "total_calls": self._total_calls,
        }
