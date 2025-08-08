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

from .core.event_bus import EventBus
from .core.librarian import Librarian
from .genesis.sentry import SentryAgent
from .genesis.archaeologist import ArchaeologistAgent
from .genesis.tdd_developer import TDDDeveloperAgent
from .genesis.qa_agent import QAAgent
from .executor.task_planner import TaskPlanner
from .executor.skill_composer import SkillComposer
from .executor.execution_engine import ExecutionEngine
from .dashboard.monitor import Dashboard

__all__ = [
    "EventBus",
    "Librarian", 
    "SentryAgent",
    "ArchaeologistAgent",
    "TDDDeveloperAgent",
    "QAAgent",
    "TaskPlanner",
    "SkillComposer",
    "ExecutionEngine",
    "Dashboard"
]
