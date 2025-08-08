"""
执行引擎 (Execution Engine)

负责执行技能组合，处理能力缺口，并管理执行流程。
"""

import json
import logging
import subprocess
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

from ..core.event_bus import EventBus, EventTypes
from ..core.librarian import Librarian

logger = logging.getLogger(__name__)


@dataclass
class ExecutionStep:
    """执行步骤"""
    step_id: str
    subtask_id: str
    skill_name: str
    parameters: Dict[str, Any]
    status: str  # "pending", "running", "completed", "failed"
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@dataclass
class ExecutionPlan:
    """执行计划"""
    plan_id: str
    goal: str
    steps: List[ExecutionStep]
    status: str  # "planning", "executing", "completed", "failed", "paused"
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    total_steps: int = 0
    completed_steps: int = 0
    failed_steps: int = 0


class ExecutionEngine:
    """执行引擎"""
    
    def __init__(self, event_bus: EventBus, librarian: Librarian, config: Dict[str, Any]):
        """初始化执行引擎"""
        self.event_bus = event_bus
        self.librarian = librarian
        self.config = config
        self.running = False
        
        # 订阅技能组合完成事件
        self.event_bus.subscribe(EventTypes.SKILL_COMPOSED, self._handle_skill_composed)
        
        # 订阅技能创建完成事件
        self.event_bus.subscribe(EventTypes.SKILL_CREATED, self._handle_skill_created)
        
        # 执行计划缓存
        self.execution_plans: Dict[str, ExecutionPlan] = {}
        
        # 等待技能的执行步骤
        self.pending_executions: Dict[str, Dict[str, Any]] = {}
        
        # 执行配置
        self.execution_timeout = config.get("execution_timeout", 300)  # 秒
        self.max_retries = config.get("max_retries", 3)
        self.enable_parallel_execution = config.get("enable_parallel_execution", False)
        
        logger.info("Execution engine initialized")
    
    def start(self):
        """启动执行引擎"""
        if self.running:
            logger.warning("Execution engine is already running")
            return
        
        self.running = True
        logger.info("Execution engine started")
        
        # 发布启动事件
        self.event_bus.publish(
            EventTypes.AGENT_STARTED,
            {"agent": "execution_engine", "timestamp": datetime.utcnow().isoformat()},
            "execution_engine_agent"
        )
    
    def stop(self):
        """停止执行引擎"""
        if not self.running:
            return
        
        self.running = False
        logger.info("Execution engine stopped")
        
        # 发布停止事件
        self.event_bus.publish(
            EventTypes.AGENT_STOPPED,
            {"agent": "execution_engine", "timestamp": datetime.utcnow().isoformat()},
            "execution_engine_agent"
        )
    
    def _handle_skill_composed(self, event):
        """处理技能组合完成事件"""
        try:
            payload = event.payload
            plan_id = payload.get("plan_id", "")
            subtask_id = payload.get("subtask_id", "")
            best_composition = payload.get("best_composition")
            requires_new_skill = payload.get("requires_new_skill", False)
            
            logger.info(f"Processing skill composition for subtask: {subtask_id}")
            
            if requires_new_skill:
                # 等待新技能创建
                self._wait_for_skill_creation(subtask_id, payload)
            elif best_composition:
                # 执行技能
                self._execute_skill(subtask_id, best_composition, plan_id)
            else:
                logger.warning(f"No suitable skill found for subtask: {subtask_id}")
                
        except Exception as e:
            logger.error(f"Failed to handle skill composed event: {e}")
    
    def _handle_skill_created(self, event):
        """处理技能创建完成事件"""
        try:
            payload = event.payload
            skill_name = payload.get("skill_name", "")
            
            logger.info(f"New skill created: {skill_name}")
            
            # 检查是否有等待此技能的执行步骤
            self._check_pending_executions(skill_name)
            
        except Exception as e:
            logger.error(f"Failed to handle skill created event: {e}")
    
    def _wait_for_skill_creation(self, subtask_id: str, composition_data: Dict[str, Any]):
        """等待技能创建"""
        # 缓存等待的执行步骤
        self.pending_executions[subtask_id] = {
            "composition_data": composition_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Waiting for skill creation for subtask: {subtask_id}")
    
    def _check_pending_executions(self, skill_name: str):
        """检查等待的执行步骤"""
        executions_to_remove = []
        
        for subtask_id, execution_data in self.pending_executions.items():
            composition_data = execution_data["composition_data"]
            best_composition = composition_data.get("best_composition")
            
            if best_composition and skill_name.lower() in best_composition.get("skill_name", "").lower():
                # 找到匹配的技能，执行它
                plan_id = composition_data.get("plan_id", "auto")
                self._execute_skill(subtask_id, best_composition, plan_id)
                executions_to_remove.append(subtask_id)
        
        # 清理已处理的执行步骤
        for subtask_id in executions_to_remove:
            del self.pending_executions[subtask_id]
    
    def _execute_skill(self, subtask_id: str, composition: Dict[str, Any], plan_id: str):
        """执行技能"""
        skill_name = composition.get("skill_name", "")
        parameters = composition.get("parameters", {})
        confidence = composition.get("confidence", 0.0)
        
        logger.info(f"Executing skill: {skill_name} for subtask: {subtask_id}")
        
        # 创建执行步骤
        step_id = f"step_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        execution_step = ExecutionStep(
            step_id=step_id,
            subtask_id=subtask_id,
            skill_name=skill_name,
            parameters=parameters,
            status="running",
            start_time=datetime.utcnow().isoformat()
        )
        
        # 获取或创建执行计划
        if plan_id not in self.execution_plans:
            self.execution_plans[plan_id] = ExecutionPlan(
                plan_id=plan_id,
                goal="Auto-generated plan",
                steps=[],
                status="executing",
                created_at=datetime.utcnow().isoformat(),
                started_at=datetime.utcnow().isoformat()
            )
        
        execution_plan = self.execution_plans[plan_id]
        execution_plan.steps.append(execution_step)
        execution_plan.total_steps += 1
        
        # 发布执行开始事件
        self._publish_execution_started(plan_id, step_id, subtask_id, skill_name, parameters)
        
        try:
            # 执行技能
            result = self._run_skill(skill_name, parameters)
            
            # 更新执行步骤
            execution_step.status = "completed"
            execution_step.end_time = datetime.utcnow().isoformat()
            execution_step.result = result
            
            execution_plan.completed_steps += 1
            
            # 发布执行完成事件
            self._publish_execution_completed(plan_id, step_id, subtask_id, skill_name, result)
            
            logger.info(f"Successfully executed skill: {skill_name}")
            
        except Exception as e:
            # 处理执行失败
            execution_step.status = "failed"
            execution_step.end_time = datetime.utcnow().isoformat()
            execution_step.error = str(e)
            
            execution_plan.failed_steps += 1
            
            # 发布执行失败事件
            self._publish_execution_failed(plan_id, step_id, subtask_id, skill_name, str(e))
            
            logger.error(f"Failed to execute skill {skill_name}: {e}")
    
    def _run_skill(self, skill_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """运行技能"""
        try:
            # 获取技能路径
            skill_path = self.librarian.get_source_code_path(skill_name, "skill")
            
            if not skill_path:
                raise Exception(f"Skill path not found for: {skill_name}")
            
            # 构建技能执行路径
            skill_dir = Path(skill_path)
            main_file = skill_dir / "main.py"
            
            if not main_file.exists():
                raise Exception(f"Main file not found for skill: {skill_name}")
            
            # 准备参数
            param_str = " ".join([f"--{k} {v}" for k, v in parameters.items()])
            
            # 执行技能
            cmd = f"python {main_file} {param_str}"
            
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=self.execution_timeout,
                cwd=str(skill_dir)
            )
            
            if result.returncode == 0:
                # 尝试解析JSON输出
                try:
                    output = json.loads(result.stdout.strip())
                except json.JSONDecodeError:
                    # 如果不是JSON，使用原始输出
                    output = {
                        "status": "success",
                        "output": result.stdout.strip(),
                        "skill_name": skill_name
                    }
                
                return output
            else:
                raise Exception(f"Skill execution failed: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            raise Exception(f"Skill execution timed out after {self.execution_timeout} seconds")
        except Exception as e:
            raise Exception(f"Failed to run skill {skill_name}: {e}")
    
    def _publish_execution_started(self, plan_id: str, step_id: str, subtask_id: str, 
                                  skill_name: str, parameters: Dict[str, Any]):
        """发布执行开始事件"""
        payload = {
            "plan_id": plan_id,
            "step_id": step_id,
            "subtask_id": subtask_id,
            "skill_name": skill_name,
            "parameters": parameters,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        self.event_bus.publish(
            EventTypes.EXECUTION_STARTED,
            payload,
            "execution_engine_agent"
        )
    
    def _publish_execution_completed(self, plan_id: str, step_id: str, subtask_id: str, 
                                   skill_name: str, result: Dict[str, Any]):
        """发布执行完成事件"""
        payload = {
            "plan_id": plan_id,
            "step_id": step_id,
            "subtask_id": subtask_id,
            "skill_name": skill_name,
            "result": result,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        self.event_bus.publish(
            EventTypes.EXECUTION_COMPLETED,
            payload,
            "execution_engine_agent"
        )
    
    def _publish_execution_failed(self, plan_id: str, step_id: str, subtask_id: str, 
                                 skill_name: str, error: str):
        """发布执行失败事件"""
        payload = {
            "plan_id": plan_id,
            "step_id": step_id,
            "subtask_id": subtask_id,
            "skill_name": skill_name,
            "error": error,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        self.event_bus.publish(
            EventTypes.EXECUTION_FAILED,
            payload,
            "execution_engine_agent"
        )
    
    def execute_plan(self, plan_id: str, goal: str, steps: List[Dict[str, Any]]) -> ExecutionPlan:
        """执行计划"""
        logger.info(f"Executing plan: {plan_id} with {len(steps)} steps")
        
        # 创建执行计划
        execution_steps = []
        for i, step_data in enumerate(steps):
            step = ExecutionStep(
                step_id=f"step_{i+1}",
                subtask_id=step_data.get("subtask_id", f"subtask_{i+1}"),
                skill_name=step_data.get("skill_name", ""),
                parameters=step_data.get("parameters", {}),
                status="pending"
            )
            execution_steps.append(step)
        
        execution_plan = ExecutionPlan(
            plan_id=plan_id,
            goal=goal,
            steps=execution_steps,
            status="executing",
            created_at=datetime.utcnow().isoformat(),
            started_at=datetime.utcnow().isoformat(),
            total_steps=len(execution_steps)
        )
        
        # 缓存执行计划
        self.execution_plans[plan_id] = execution_plan
        
        # 按顺序执行步骤
        for step in execution_steps:
            if step.status == "pending":
                self._execute_step(step, plan_id)
        
        return execution_plan
    
    def _execute_step(self, step: ExecutionStep, plan_id: str):
        """执行单个步骤"""
        logger.info(f"Executing step: {step.step_id} - {step.skill_name}")
        
        # 更新步骤状态
        step.status = "running"
        step.start_time = datetime.utcnow().isoformat()
        
        try:
            # 执行技能
            result = self._run_skill(step.skill_name, step.parameters)
            
            # 更新步骤状态
            step.status = "completed"
            step.end_time = datetime.utcnow().isoformat()
            step.result = result
            
            # 更新计划状态
            execution_plan = self.execution_plans[plan_id]
            execution_plan.completed_steps += 1
            
            # 检查是否所有步骤都完成了
            if execution_plan.completed_steps == execution_plan.total_steps:
                execution_plan.status = "completed"
                execution_plan.completed_at = datetime.utcnow().isoformat()
            
            logger.info(f"Successfully executed step: {step.step_id}")
            
        except Exception as e:
            # 处理执行失败
            step.status = "failed"
            step.end_time = datetime.utcnow().isoformat()
            step.error = str(e)
            
            # 更新计划状态
            execution_plan = self.execution_plans[plan_id]
            execution_plan.failed_steps += 1
            execution_plan.status = "failed"
            
            logger.error(f"Failed to execute step {step.step_id}: {e}")
    
    def get_execution_plan(self, plan_id: str) -> Optional[ExecutionPlan]:
        """获取执行计划"""
        return self.execution_plans.get(plan_id)
    
    def pause_execution(self, plan_id: str):
        """暂停执行"""
        if plan_id in self.execution_plans:
            execution_plan = self.execution_plans[plan_id]
            execution_plan.status = "paused"
            logger.info(f"Execution plan {plan_id} paused")
    
    def resume_execution(self, plan_id: str):
        """恢复执行"""
        if plan_id in self.execution_plans:
            execution_plan = self.execution_plans[plan_id]
            execution_plan.status = "executing"
            
            # 继续执行未完成的步骤
            for step in execution_plan.steps:
                if step.status == "pending":
                    self._execute_step(step, plan_id)
            
            logger.info(f"Execution plan {plan_id} resumed")
    
    def cancel_execution(self, plan_id: str):
        """取消执行"""
        if plan_id in self.execution_plans:
            execution_plan = self.execution_plans[plan_id]
            execution_plan.status = "failed"
            logger.info(f"Execution plan {plan_id} cancelled")
    
    def get_execution_status(self, plan_id: str) -> Optional[Dict[str, Any]]:
        """获取执行状态"""
        if plan_id not in self.execution_plans:
            return None
        
        execution_plan = self.execution_plans[plan_id]
        
        return {
            "plan_id": execution_plan.plan_id,
            "goal": execution_plan.goal,
            "status": execution_plan.status,
            "total_steps": execution_plan.total_steps,
            "completed_steps": execution_plan.completed_steps,
            "failed_steps": execution_plan.failed_steps,
            "progress": execution_plan.completed_steps / execution_plan.total_steps if execution_plan.total_steps > 0 else 0,
            "created_at": execution_plan.created_at,
            "started_at": execution_plan.started_at,
            "completed_at": execution_plan.completed_at
        }


# 默认配置
DEFAULT_EXECUTION_ENGINE_CONFIG = {
    "execution_timeout": 300,  # 秒
    "max_retries": 3,
    "enable_parallel_execution": False,
    "max_concurrent_executions": 5,
    "enable_execution_logging": True,
    "enable_performance_monitoring": True
}
