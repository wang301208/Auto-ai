"""认知循环混入: 为模块批量注入CognitiveLoop认知闭环能力。"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class CognitiveLoopMixin:
    """认知循环混入: 提供observe->assess->decide->act->reflect标准接口。"""

    def _init_cognitive_loop(self, use_cognitive: bool = False) -> None:
        self._use_cognitive = use_cognitive
        self._cog_loop = None
        if use_cognitive:
            self._setup_cognitive_loop()

    def _setup_cognitive_loop(self) -> None:
        try:
            from autoai.autonomy_core.cognitive_loop import CognitiveLoop
            self._cog_loop = CognitiveLoop()
        except Exception as e:
            logger.debug(f"认知循环初始化失败(非致命): {e}")

    def enable_cognitive_loop(self) -> None:
        if not hasattr(self, '_use_cognitive'):
            self._init_cognitive_loop()
        self._use_cognitive = True
        self._setup_cognitive_loop()

    def observe(self, source: str, data: dict[str, Any]) -> Any:
        if self._cog_loop:
            try:
                return self._cog_loop.observe(source, data)
            except Exception:
                pass
        return None

    def assess(self, observation: Any = None) -> Any:
        if self._cog_loop:
            try:
                return self._cog_loop.assess(observation)
            except Exception:
                pass
        return None

    def decide(self, assessment: Any = None, available_actions: list[str] | None = None) -> Any:
        if self._cog_loop:
            try:
                return self._cog_loop.decide(assessment, available_actions)
            except Exception:
                pass
        return None

    def act(self, decision: Any = None) -> Any:
        if self._cog_loop:
            try:
                return self._cog_loop.act(decision)
            except Exception:
                pass
        return None

    def run_cognitive_cycle(self, observations: list[tuple[str, dict, float]]) -> Any:
        if self._cog_loop:
            try:
                return self._cog_loop.run_full_cycle(observations)
            except Exception:
                pass
        return None
