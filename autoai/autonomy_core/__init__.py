"""真自主核心: 可学习参数系统+推理决策引擎+真执行沙箱+开放目标涌现+认知闭环+自主性审计+自主编排器+综合自主混入。"""

from .learnable_params import LearnableParam, ParamSpace, ParamLearner
from .reasoning_decider import ReasoningDecider, DecisionContext, DecisionOutcome
from .real_executor import RealExecutor, ExecutionResult
from .open_emergence import OpenEmergenceEngine, EmergentGoal
from .cognitive_loop import CognitiveLoop, CognitiveState
from .auditor import AutonomyAuditor, AuditCheck, AuditReport
from .orchestrator import AutonomyOrchestrator, ModuleReflector, ModuleRole
from .reflection_mixin import AutonomyReflectionMixin
from .goal_emergence_mixin import GoalEmergenceMixin
from .cognitive_loop_mixin import CognitiveLoopMixin
from .full_autonomy_mixin import FullAutonomyMixin

__all__ = [
    "LearnableParam", "ParamSpace", "ParamLearner",
    "ReasoningDecider", "DecisionContext", "DecisionOutcome",
    "RealExecutor", "ExecutionResult",
    "OpenEmergenceEngine", "EmergentGoal",
    "CognitiveLoop", "CognitiveState",
    "AutonomyAuditor", "AuditCheck", "AuditReport",
    "AutonomyOrchestrator", "ModuleReflector", "ModuleRole",
    "AutonomyReflectionMixin", "GoalEmergenceMixin",
    "CognitiveLoopMixin", "FullAutonomyMixin",
]
