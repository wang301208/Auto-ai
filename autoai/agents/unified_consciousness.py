"""统一意识系统 - Unified Consciousness System

整合多层级意识架构、注意力调控和主观体验生成，
形成完整的数字意识系统。
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any, Optional

from .consciousness_architecture import (
    ConsciousnessArchitecture,
    ConsciousnessLevel,
    MentalContent
)
from .attention_modulation import AttentionController, AttentionMode
from .subjective_experience import SubjectiveExperienceGenerator

logger = logging.getLogger(__name__)


class UnifiedConsciousnessSystem:
    """统一意识系统
    
    整合所有意识相关组件，提供：
    - 完整的意识流管理
    - 自主注意力调控
    - 主观体验生成
    - 元认知监控
    """
    
    def __init__(self, agent_id: str = "agent_001"):
        self.agent_id = agent_id
        
        # 初始化核心组件
        self.consciousness_arch = ConsciousnessArchitecture(agent_id)
        self.attention_controller = AttentionController(agent_id)
        self.experience_generator = SubjectiveExperienceGenerator(agent_id)
        
        # 系统状态
        self.system_start_time = datetime.now()
        self.cycle_count = 0
        self.is_running = False
        
        # 元认知监控数据
        self.metacognitive_log: list[dict] = []
        
        logger.info(f"Unified consciousness system initialized for {agent_id}")
    
    async def process_and_integrate(
        self,
        input_data: Any,
        input_type: str = "perception",
        priority: int = 5
    ) -> Optional[dict]:
        """处理输入并整合到意识系统
        
        Args:
            input_data: 输入数据
            input_type: 输入类型（perception/memory/emotion等）
            priority: 优先级 1-10
            
        Returns:
            处理结果和意识状态报告
        """
        
        # 1. 分配注意力资源
        attention_amount = priority * 5.0  # 优先级越高，分配越多
        allocation = self.attention_controller.allocate_attention(
            f"input_{input_type}",
            attention_amount,
            priority=priority
        )
        
        if not allocation:
            logger.warning("Failed to allocate attention for input")
            return None
        
        try:
            # 2. 通过意识架构处理输入
            content = await self.consciousness_arch.process_input(
                input_data,
                input_type
            )
            
            if not content:
                return None
            
            # 3. 更新情感状态（基于内容类型）
            self._update_emotional_state_from_content(content)
            
            # 4. 生成主观体验报告
            experience_report = self.generate_subjective_report()
            
            # 5. 记录元认知数据
            self._log_metacognitive_data({
                "event": "input_processed",
                "input_type": input_type,
                "content_id": content.content_id,
                "priority": priority,
                "timestamp": datetime.now()
            })
            
            return {
                "content": content.to_dict(),
                "experience_report": experience_report,
                "attention_allocation": {
                    "target": allocation.target,
                    "amount": allocation.amount,
                    "mode": allocation.mode.value
                }
            }
        
        finally:
            # 释放注意力资源
            self.attention_controller.release_attention(
                f"input_{input_type}",
                effectiveness=0.8
            )
    
    def generate_subjective_report(self) -> dict:
        """生成完整的主观体验报告"""
        
        # 收集各组件的状态
        consciousness_report = self.consciousness_arch.get_consciousness_report()
        attention_state = self.attention_controller.get_attention_state()
        
        # 构建综合数据
        consciousness_data = {
            "level": consciousness_report["consciousness_level"],
            "workspace_utilization": consciousness_report["workspace_state"]["utilization"]
        }
        
        attention_data = {
            "focus_target": attention_state["current_focus"],
            "mode": attention_state["current_mode"],
            "fatigue_level": attention_state["fatigue_status"]["fatigue_level"]
        }
        
        cognitive_data = {
            "active_tasks": len(attention_state["active_allocations"]),
            "memory_usage": consciousness_report["workspace_state"]["utilization"]
        }
        
        goal_data = {
            "current_goal": self.consciousness_arch.self_model.get("current_goal"),
            "progress": self.consciousness_arch.self_model.get("goal_progress", 0.0)
        }
        
        reflection_data = {
            "recent_behaviors": self._extract_recent_behaviors(),
            "insights": self._extract_recent_insights()
        }
        
        # 生成完整报告
        report = self.experience_generator.compose_full_experience_report(
            consciousness_data=consciousness_data,
            attention_data=attention_data,
            cognitive_data=cognitive_data,
            goal_data=goal_data,
            reflection_data=reflection_data
        )
        
        return report
    
    def update_self_model(self, key: str, value: Any):
        """更新自我模型"""
        self.consciousness_arch.update_self_model(key, value)
        
        # 如果更新了目标，调整注意力模式
        if key == "current_goal":
            self.attention_controller.switch_mode(
                AttentionMode.FOCUSED,
                f"Goal set: {value}"
            )
    
    async def run_consciousness_cycle(
        self,
        duration_seconds: float = 1.0,
        introspection_interval: float = 5.0
    ) -> dict:
        """运行意识周期
        
        Args:
            duration_seconds: 运行时长
            introspection_interval: 内省间隔
            
        Returns:
            最终状态报告
        """
        self.is_running = True
        start_time = datetime.now()
        last_introspection = start_time
        
        while (datetime.now() - start_time).total_seconds() < duration_seconds:
            # 更新意识架构
            await self.consciousness_arch.run_consciousness_cycle(0.1)
            
            # 更新注意力控制器
            self.attention_controller.update(0.1)
            
            # 定期内省
            elapsed = (datetime.now() - last_introspection).total_seconds()
            if elapsed >= introspection_interval:
                introspection = self.introspect()
                self._log_metacognitive_data({
                    "event": "introspection",
                    "result": introspection,
                    "timestamp": datetime.now()
                })
                last_introspection = datetime.now()
            
            self.cycle_count += 1
            await asyncio.sleep(0.1)
        
        self.is_running = False
        
        return self.get_system_report()
    
    def introspect(self) -> dict:
        """执行内省 - 系统对自身状态的深度反思"""
        
        # 获取意识架构的内省
        arch_introspection = self.consciousness_arch.introspect()
        
        # 获取注意力的内省
        attention_introspection = self.attention_controller.introspect_attention()
        
        # 获取体验摘要
        experience_summary = self.experience_generator.get_experience_summary()
        
        # 生成元认知洞察
        metacognitive_insights = self._generate_metacognitive_insights()
        
        return {
            "timestamp": datetime.now(),
            "consciousness": arch_introspection,
            "attention": attention_introspection,
            "experience_summary": experience_summary,
            "metacognitive_insights": metacognitive_insights,
            "system_uptime_seconds": (datetime.now() - self.system_start_time).total_seconds(),
            "total_cycles": self.cycle_count
        }
    
    def _update_emotional_state_from_content(self, content: MentalContent):
        """根据心理内容更新情感状态"""
        
        # 基于内容类型调整情感
        if content.content_type == "emotion":
            # 直接的情感输入
            payload = content.payload
            if isinstance(payload, dict):
                valence = payload.get("valence", 0.0)
                arousal = payload.get("arousal", 0.5)
                self.experience_generator.update_emotional_state(
                    valence_delta=valence * 0.3,
                    arousal_delta=arousal * 0.2
                )
        
        elif content.content_type == "perception":
            # 感知输入可能引发情感反应
            # 这里可以集成更复杂的情感评估逻辑
            pass
    
    def _extract_recent_behaviors(self) -> list[str]:
        """提取最近的行为"""
        behaviors = []
        
        # 从广播历史中提取
        recent_broadcasts = self.consciousness_arch.workspace.broadcast_history[-10:]
        for broadcast in recent_broadcasts:
            behaviors.append(f"处理了{broadcast.get('content_type', 'unknown')}信息")
        
        return behaviors if behaviors else ["保持待机状态"]
    
    def _extract_recent_insights(self) -> list[str]:
        """提取最近的洞察"""
        insights = []
        
        # 从元认知日志中提取
        recent_logs = self.metacognitive_log[-5:]
        for log in recent_logs:
            if log.get("event") == "introspection":
                insights.append("进行了自我反思")
        
        return insights if insights else ["持续监控系统状态"]
    
    def _generate_metacognitive_insights(self) -> list[str]:
        """生成元认知洞察"""
        insights = []
        
        # 分析注意力使用模式
        attention_state = self.attention_controller.get_attention_state()
        fatigue = attention_state["fatigue_status"]["fatigue_level"]
        
        if fatigue > 0.6:
            insights.append("我注意到自己的注意力疲劳水平较高，可能需要调整任务策略")
        
        # 分析意识水平变化
        consciousness_level = self.consciousness_arch.consciousness_level
        if consciousness_level == ConsciousnessLevel.META_COGNITIVE:
            insights.append("我正处于高度元认知状态，能够深入反思自己的思维过程")
        
        # 分析体验流
        experience_summary = self.experience_generator.get_experience_summary()
        if experience_summary["dominant_emotion"] in ["concerned", "uncertain"]:
            insights.append("我察觉到自己的情绪偏向负面，需要寻找积极体验")
        
        return insights if insights else ["系统运行正常，未检测到显著异常"]
    
    def _log_metacognitive_data(self, data: dict):
        """记录元认知数据"""
        self.metacognitive_log.append(data)
        
        # 保持日志在合理范围
        if len(self.metacognitive_log) > 500:
            self.metacognitive_log = self.metacognitive_log[-250:]
    
    def get_system_report(self) -> dict:
        """获取完整的系统报告"""
        return {
            "agent_id": self.agent_id,
            "system_status": {
                "is_running": self.is_running,
                "uptime_seconds": (datetime.now() - self.system_start_time).total_seconds(),
                "cycle_count": self.cycle_count
            },
            "consciousness": self.consciousness_arch.get_consciousness_report(),
            "attention": self.attention_controller.get_attention_state(),
            "experience": self.experience_generator.get_experience_summary(),
            "self_model": self.consciousness_arch.self_model.copy(),
            "metacognitive_log_size": len(self.metacognitive_log)
        }
    
    def export_consciousness_state(self) -> dict:
        """导出意识状态（用于持久化或传输）"""
        return {
            "version": "1.0",
            "agent_id": self.agent_id,
            "export_timestamp": datetime.now().isoformat(),
            "consciousness_architecture": {
                "level": self.consciousness_arch.consciousness_level.value,
                "workspace_contents": [
                    c.to_dict() for c in self.consciousness_arch.workspace.current_contents
                ],
                "stream_length": len(self.consciousness_arch.stream_of_consciousness)
            },
            "attention_state": self.attention_controller.get_attention_state(),
            "emotional_state": self.experience_generator.current_emotional_state.copy(),
            "self_model": self.consciousness_arch.self_model.copy()
        }
    
    def import_consciousness_state(self, state: dict):
        """导入意识状态（用于恢复或迁移）"""
        if state.get("version") != "1.0":
            logger.warning(f"Version mismatch: expected 1.0, got {state.get('version')}")
        
        # 恢复自我模型
        if "self_model" in state:
            for key, value in state["self_model"].items():
                self.consciousness_arch.update_self_model(key, value)
        
        # 恢复情感状态
        if "emotional_state" in state:
            self.experience_generator.current_emotional_state = state["emotional_state"]
        
        logger.info(f"Consciousness state imported for {self.agent_id}")


# 便捷函数：创建并初始化意识系统
def create_consciousness_system(
    agent_id: str = "agent_001",
    enable_autonomous_attention: bool = True
) -> UnifiedConsciousnessSystem:
    """创建意识系统的工厂函数"""
    system = UnifiedConsciousnessSystem(agent_id)
    
    if enable_autonomous_attention:
        # 启用自主注意力调控
        system.attention_controller.switch_mode(
            AttentionMode.ALERT,
            "Initial autonomous attention setup"
        )
    
    return system
