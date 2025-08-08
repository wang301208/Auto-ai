"""
任务规划器 (Task Planner)

负责将用户的高级目标分解为具体的、可执行的子任务。
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from ..core.event_bus import EventBus, EventTypes

logger = logging.getLogger(__name__)


@dataclass
class SubTask:
    """子任务"""
    id: str
    name: str
    description: str
    priority: str  # "high", "medium", "low"
    estimated_duration: str  # "short", "medium", "long"
    dependencies: List[str]
    parameters: Dict[str, Any]
    status: str = "pending"  # "pending", "in_progress", "completed", "failed"


@dataclass
class TaskPlan:
    """任务计划"""
    goal: str
    subtasks: List[SubTask]
    total_estimated_duration: str
    priority: str
    created_at: str
    status: str = "planning"  # "planning", "executing", "completed", "failed"


class TaskPlanner:
    """任务规划器"""
    
    def __init__(self, event_bus: EventBus, config: Dict[str, Any]):
        """初始化任务规划器"""
        self.event_bus = event_bus
        self.config = config
        self.running = False
        
        # 任务计划缓存
        self.task_plans: Dict[str, TaskPlan] = {}
        
        # 规划策略
        self.planning_strategies = config.get("planning_strategies", {
            "chain_of_thought": True,
            "react": True,
            "hierarchical": True
        })
        
        logger.info("Task planner initialized")
    
    def start(self):
        """启动任务规划器"""
        if self.running:
            logger.warning("Task planner is already running")
            return
        
        self.running = True
        logger.info("Task planner started")
        
        # 发布启动事件
        self.event_bus.publish(
            EventTypes.AGENT_STARTED,
            {"agent": "task_planner", "timestamp": datetime.utcnow().isoformat()},
            "task_planner_agent"
        )
    
    def stop(self):
        """停止任务规划器"""
        if not self.running:
            return
        
        self.running = False
        logger.info("Task planner stopped")
        
        # 发布停止事件
        self.event_bus.publish(
            EventTypes.AGENT_STOPPED,
            {"agent": "task_planner", "timestamp": datetime.utcnow().isoformat()},
            "task_planner_agent"
        )
    
    def plan(self, goal: str, context: Optional[Dict[str, Any]] = None) -> TaskPlan:
        """规划任务"""
        logger.info(f"Planning task for goal: {goal}")
        
        # 分析目标
        goal_analysis = self._analyze_goal(goal, context)
        
        # 生成子任务
        subtasks = self._generate_subtasks(goal_analysis)
        
        # 确定依赖关系
        subtasks = self._resolve_dependencies(subtasks)
        
        # 计算优先级
        subtasks = self._assign_priorities(subtasks)
        
        # 估算时间
        total_duration = self._estimate_total_duration(subtasks)
        
        # 创建任务计划
        plan_id = f"plan_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        task_plan = TaskPlan(
            goal=goal,
            subtasks=subtasks,
            total_estimated_duration=total_duration,
            priority=self._determine_plan_priority(subtasks),
            created_at=datetime.utcnow().isoformat()
        )
        
        # 缓存任务计划
        self.task_plans[plan_id] = task_plan
        
        # 发布任务规划完成事件
        self._publish_task_planned(plan_id, task_plan)
        
        logger.info(f"Task plan created with {len(subtasks)} subtasks")
        
        return task_plan
    
    def _analyze_goal(self, goal: str, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """分析目标"""
        # 简单的目标分析
        analysis = {
            "goal_type": self._classify_goal(goal),
            "complexity": self._assess_complexity(goal),
            "domain": self._identify_domain(goal),
            "requirements": self._extract_requirements(goal),
            "constraints": context.get("constraints", []) if context else [],
            "context": context or {}
        }
        
        return analysis
    
    def _classify_goal(self, goal: str) -> str:
        """分类目标"""
        goal_lower = goal.lower()
        
        if any(word in goal_lower for word in ["create", "build", "develop", "make"]):
            return "creation"
        elif any(word in goal_lower for word in ["fix", "repair", "solve", "debug"]):
            return "fix"
        elif any(word in goal_lower for word in ["analyze", "examine", "investigate", "study"]):
            return "analysis"
        elif any(word in goal_lower for word in ["optimize", "improve", "enhance", "upgrade"]):
            return "optimization"
        elif any(word in goal_lower for word in ["test", "verify", "validate", "check"]):
            return "testing"
        else:
            return "general"
    
    def _assess_complexity(self, goal: str) -> str:
        """评估复杂度"""
        # 简单的复杂度评估
        words = goal.split()
        
        if len(words) <= 5:
            return "simple"
        elif len(words) <= 10:
            return "medium"
        else:
            return "complex"
    
    def _identify_domain(self, goal: str) -> str:
        """识别领域"""
        goal_lower = goal.lower()
        
        domains = {
            "web": ["website", "web", "http", "api", "frontend", "backend"],
            "data": ["data", "database", "csv", "json", "analysis", "processing"],
            "system": ["system", "os", "file", "process", "service"],
            "network": ["network", "connection", "socket", "protocol"],
            "security": ["security", "encrypt", "auth", "password", "secure"],
            "ui": ["ui", "interface", "gui", "user", "display"],
            "automation": ["automate", "script", "batch", "schedule"]
        }
        
        for domain, keywords in domains.items():
            if any(keyword in goal_lower for keyword in keywords):
                return domain
        
        return "general"
    
    def _extract_requirements(self, goal: str) -> List[str]:
        """提取需求"""
        requirements = []
        
        # 简单的需求提取
        if "fast" in goal.lower() or "quick" in goal.lower():
            requirements.append("performance")
        
        if "secure" in goal.lower() or "safe" in goal.lower():
            requirements.append("security")
        
        if "user" in goal.lower() or "interface" in goal.lower():
            requirements.append("usability")
        
        if "test" in goal.lower() or "verify" in goal.lower():
            requirements.append("testing")
        
        return requirements
    
    def _generate_subtasks(self, goal_analysis: Dict[str, Any]) -> List[SubTask]:
        """生成子任务"""
        subtasks = []
        goal_type = goal_analysis["goal_type"]
        domain = goal_analysis["domain"]
        requirements = goal_analysis["requirements"]
        
        # 根据目标类型生成子任务
        if goal_type == "creation":
            subtasks.extend(self._generate_creation_subtasks(goal_analysis))
        elif goal_type == "fix":
            subtasks.extend(self._generate_fix_subtasks(goal_analysis))
        elif goal_type == "analysis":
            subtasks.extend(self._generate_analysis_subtasks(goal_analysis))
        elif goal_type == "optimization":
            subtasks.extend(self._generate_optimization_subtasks(goal_analysis))
        elif goal_type == "testing":
            subtasks.extend(self._generate_testing_subtasks(goal_analysis))
        else:
            subtasks.extend(self._generate_general_subtasks(goal_analysis))
        
        # 添加通用子任务
        if "security" in requirements:
            subtasks.extend(self._generate_security_subtasks(goal_analysis))
        
        if "performance" in requirements:
            subtasks.extend(self._generate_performance_subtasks(goal_analysis))
        
        if "testing" in requirements:
            subtasks.extend(self._generate_testing_subtasks(goal_analysis))
        
        return subtasks
    
    def _generate_creation_subtasks(self, goal_analysis: Dict[str, Any]) -> List[SubTask]:
        """生成创建类子任务"""
        subtasks = []
        
        # 基础创建流程
        subtasks.append(SubTask(
            id="create_1",
            name="Requirements Analysis",
            description="Analyze and understand the requirements",
            priority="high",
            estimated_duration="short",
            dependencies=[],
            parameters={"goal": goal_analysis["goal"]}
        ))
        
        subtasks.append(SubTask(
            id="create_2",
            name="Design",
            description="Design the solution architecture",
            priority="high",
            estimated_duration="medium",
            dependencies=["create_1"],
            parameters={"domain": goal_analysis["domain"]}
        ))
        
        subtasks.append(SubTask(
            id="create_3",
            name="Implementation",
            description="Implement the solution",
            priority="high",
            estimated_duration="long",
            dependencies=["create_2"],
            parameters={"complexity": goal_analysis["complexity"]}
        ))
        
        return subtasks
    
    def _generate_fix_subtasks(self, goal_analysis: Dict[str, Any]) -> List[SubTask]:
        """生成修复类子任务"""
        subtasks = []
        
        subtasks.append(SubTask(
            id="fix_1",
            name="Issue Diagnosis",
            description="Diagnose the root cause of the issue",
            priority="high",
            estimated_duration="short",
            dependencies=[],
            parameters={"goal": goal_analysis["goal"]}
        ))
        
        subtasks.append(SubTask(
            id="fix_2",
            name="Solution Design",
            description="Design the fix solution",
            priority="high",
            estimated_duration="short",
            dependencies=["fix_1"],
            parameters={}
        ))
        
        subtasks.append(SubTask(
            id="fix_3",
            name="Implementation",
            description="Implement the fix",
            priority="high",
            estimated_duration="medium",
            dependencies=["fix_2"],
            parameters={}
        ))
        
        return subtasks
    
    def _generate_analysis_subtasks(self, goal_analysis: Dict[str, Any]) -> List[SubTask]:
        """生成分析类子任务"""
        subtasks = []
        
        subtasks.append(SubTask(
            id="analysis_1",
            name="Data Collection",
            description="Collect relevant data for analysis",
            priority="high",
            estimated_duration="medium",
            dependencies=[],
            parameters={"domain": goal_analysis["domain"]}
        ))
        
        subtasks.append(SubTask(
            id="analysis_2",
            name="Data Processing",
            description="Process and clean the data",
            priority="medium",
            estimated_duration="medium",
            dependencies=["analysis_1"],
            parameters={}
        ))
        
        subtasks.append(SubTask(
            id="analysis_3",
            name="Analysis",
            description="Perform the analysis",
            priority="high",
            estimated_duration="long",
            dependencies=["analysis_2"],
            parameters={}
        ))
        
        return subtasks
    
    def _generate_optimization_subtasks(self, goal_analysis: Dict[str, Any]) -> List[SubTask]:
        """生成优化类子任务"""
        subtasks = []
        
        subtasks.append(SubTask(
            id="optimize_1",
            name="Baseline Measurement",
            description="Measure current performance baseline",
            priority="high",
            estimated_duration="short",
            dependencies=[],
            parameters={}
        ))
        
        subtasks.append(SubTask(
            id="optimize_2",
            name="Bottleneck Identification",
            description="Identify performance bottlenecks",
            priority="high",
            estimated_duration="medium",
            dependencies=["optimize_1"],
            parameters={}
        ))
        
        subtasks.append(SubTask(
            id="optimize_3",
            name="Optimization Implementation",
            description="Implement optimizations",
            priority="high",
            estimated_duration="long",
            dependencies=["optimize_2"],
            parameters={}
        ))
        
        return subtasks
    
    def _generate_testing_subtasks(self, goal_analysis: Dict[str, Any]) -> List[SubTask]:
        """生成测试类子任务"""
        subtasks = []
        
        subtasks.append(SubTask(
            id="test_1",
            name="Test Planning",
            description="Plan the testing strategy",
            priority="high",
            estimated_duration="short",
            dependencies=[],
            parameters={}
        ))
        
        subtasks.append(SubTask(
            id="test_2",
            name="Test Execution",
            description="Execute the tests",
            priority="high",
            estimated_duration="medium",
            dependencies=["test_1"],
            parameters={}
        ))
        
        subtasks.append(SubTask(
            id="test_3",
            name="Result Analysis",
            description="Analyze test results",
            priority="medium",
            estimated_duration="short",
            dependencies=["test_2"],
            parameters={}
        ))
        
        return subtasks
    
    def _generate_general_subtasks(self, goal_analysis: Dict[str, Any]) -> List[SubTask]:
        """生成通用子任务"""
        subtasks = []
        
        subtasks.append(SubTask(
            id="general_1",
            name="Goal Understanding",
            description="Understand and clarify the goal",
            priority="high",
            estimated_duration="short",
            dependencies=[],
            parameters={"goal": goal_analysis["goal"]}
        ))
        
        subtasks.append(SubTask(
            id="general_2",
            name="Solution Development",
            description="Develop the solution",
            priority="high",
            estimated_duration="long",
            dependencies=["general_1"],
            parameters={"complexity": goal_analysis["complexity"]}
        ))
        
        return subtasks
    
    def _generate_security_subtasks(self, goal_analysis: Dict[str, Any]) -> List[SubTask]:
        """生成安全相关子任务"""
        subtasks = []
        
        subtasks.append(SubTask(
            id="security_1",
            name="Security Assessment",
            description="Assess security requirements and risks",
            priority="high",
            estimated_duration="medium",
            dependencies=[],
            parameters={}
        ))
        
        subtasks.append(SubTask(
            id="security_2",
            name="Security Implementation",
            description="Implement security measures",
            priority="high",
            estimated_duration="medium",
            dependencies=["security_1"],
            parameters={}
        ))
        
        return subtasks
    
    def _generate_performance_subtasks(self, goal_analysis: Dict[str, Any]) -> List[SubTask]:
        """生成性能相关子任务"""
        subtasks = []
        
        subtasks.append(SubTask(
            id="performance_1",
            name="Performance Analysis",
            description="Analyze performance requirements",
            priority="medium",
            estimated_duration="short",
            dependencies=[],
            parameters={}
        ))
        
        subtasks.append(SubTask(
            id="performance_2",
            name="Performance Optimization",
            description="Implement performance optimizations",
            priority="medium",
            estimated_duration="medium",
            dependencies=["performance_1"],
            parameters={}
        ))
        
        return subtasks
    
    def _resolve_dependencies(self, subtasks: List[SubTask]) -> List[SubTask]:
        """解析依赖关系"""
        # 这里可以添加更复杂的依赖解析逻辑
        # 目前保持简单的依赖关系
        return subtasks
    
    def _assign_priorities(self, subtasks: List[SubTask]) -> List[SubTask]:
        """分配优先级"""
        # 根据任务类型和依赖关系分配优先级
        for subtask in subtasks:
            if "high" in subtask.name.lower() or "critical" in subtask.name.lower():
                subtask.priority = "high"
            elif "low" in subtask.name.lower() or "optional" in subtask.name.lower():
                subtask.priority = "low"
            else:
                subtask.priority = "medium"
        
        return subtasks
    
    def _estimate_total_duration(self, subtasks: List[SubTask]) -> str:
        """估算总时长"""
        duration_mapping = {
            "short": 1,
            "medium": 2,
            "long": 4
        }
        
        total_units = sum(duration_mapping.get(subtask.estimated_duration, 1) for subtask in subtasks)
        
        if total_units <= 3:
            return "short"
        elif total_units <= 6:
            return "medium"
        else:
            return "long"
    
    def _determine_plan_priority(self, subtasks: List[SubTask]) -> str:
        """确定计划优先级"""
        high_priority_count = sum(1 for subtask in subtasks if subtask.priority == "high")
        
        if high_priority_count > len(subtasks) / 2:
            return "high"
        elif high_priority_count > 0:
            return "medium"
        else:
            return "low"
    
    def _publish_task_planned(self, plan_id: str, task_plan: TaskPlan):
        """发布任务规划完成事件"""
        payload = {
            "plan_id": plan_id,
            "goal": task_plan.goal,
            "subtasks": [
                {
                    "id": subtask.id,
                    "name": subtask.name,
                    "description": subtask.description,
                    "priority": subtask.priority,
                    "estimated_duration": subtask.estimated_duration,
                    "dependencies": subtask.dependencies,
                    "parameters": subtask.parameters
                }
                for subtask in task_plan.subtasks
            ],
            "total_estimated_duration": task_plan.total_estimated_duration,
            "priority": task_plan.priority,
            "created_at": task_plan.created_at
        }
        
        self.event_bus.publish(
            EventTypes.TASK_PLANNED,
            payload,
            "task_planner_agent"
        )
    
    def get_task_plan(self, plan_id: str) -> Optional[TaskPlan]:
        """获取任务计划"""
        return self.task_plans.get(plan_id)
    
    def update_subtask_status(self, plan_id: str, subtask_id: str, status: str):
        """更新子任务状态"""
        if plan_id in self.task_plans:
            task_plan = self.task_plans[plan_id]
            for subtask in task_plan.subtasks:
                if subtask.id == subtask_id:
                    subtask.status = status
                    break


# 默认配置
DEFAULT_TASK_PLANNER_CONFIG = {
    "planning_strategies": {
        "chain_of_thought": True,
        "react": True,
        "hierarchical": True
    },
    "max_subtasks_per_plan": 10,
    "enable_llm_planning": False,
    "llm_provider": "openai",
    "llm_model": "gpt-4"
}
