"""
双环AI系统 (Dual Ring AI System)

这是一个基于事件驱动的AI代理系统，包含两个主要环路：
1. "创世纪"工厂 - 负责自动开发和维护技能
2. "执行者"驱动 - 负责执行用户任务和技能组合

系统架构：
- 事件总线：基于Redis的发布/订阅系统
- 知识库：插件库和技能库
- 向量数据库：ChromaDB用于语义搜索
- 监控仪表盘：实时可视化系统状态
"""

__version__ = "1.0.0"
__author__ = "Dual Ring AI Team"

_EXPORTS = {
    "EventBus": "dual_ring_ai.core.event_bus",
    "Librarian": "dual_ring_ai.core.librarian",
    "SentryAgent": "dual_ring_ai.genesis.sentry",
    "ArchaeologistAgent": "dual_ring_ai.genesis.archaeologist",
    "TDDDeveloperAgent": "dual_ring_ai.genesis.tdd_developer",
    "QAAgent": "dual_ring_ai.genesis.qa_agent",
    "TaskPlanner": "dual_ring_ai.executor.task_planner",
    "SkillComposer": "dual_ring_ai.executor.skill_composer",
    "ExecutionEngine": "dual_ring_ai.executor.execution_engine",
    "Dashboard": "dual_ring_ai.dashboard.monitor",
}

__all__ = ["__version__", "__author__", *_EXPORTS.keys()]


def __getattr__(name):
    if name not in _EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    import importlib

    module = importlib.import_module(_EXPORTS[name])
    value = getattr(module, name)
    globals()[name] = value
    return value
