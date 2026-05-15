"""注意力自主调控机制 - Attention Modulation System

实现Agent主动控制自己的注意力分配，包括：
- 注意力资源管理
- 多任务注意力切换
- 专注模式与发散模式
- 注意力疲劳与恢复
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class AttentionMode(Enum):
    """注意力模式"""
    FOCUSED = "focused"          # 高度专注（单任务）
    DIVIDED = "divided"          # 分散注意（多任务）
    DIFFUSE = "diffuse"          # 发散思维（后台处理）
    ALERT = "alert"              # 警觉状态（监控环境）
    MEDITATIVE = "meditative"    # 冥想状态（内省）


@dataclass
class AttentionResource:
    """注意力资源池"""
    total_capacity: float = 100.0  # 总容量
    available: float = 100.0       # 可用量
    fatigue_level: float = 0.0     # 疲劳程度 (0-1)
    recovery_rate: float = 5.0     # 恢复速率（单位/秒）
    depletion_rate: float = 2.0    # 消耗速率（单位/秒）
    last_update: datetime = field(default_factory=datetime.now)
    
    def allocate(self, amount: float) -> bool:
        """分配注意力资源"""
        if amount <= self.available:
            self.available -= amount
            return True
        return False
    
    def release(self, amount: float):
        """释放注意力资源"""
        self.available = min(self.total_capacity, self.available + amount)
    
    def update_fatigue(self, elapsed_seconds: float):
        """更新疲劳状态"""
        # 疲劳累积
        usage_ratio = 1.0 - (self.available / self.total_capacity)
        fatigue_increase = usage_ratio * self.depletion_rate * elapsed_seconds * 0.1
        self.fatigue_level = min(1.0, self.fatigue_level + fatigue_increase)
        
        # 自然恢复
        recovery = self.recovery_rate * elapsed_seconds * 0.05
        self.fatigue_level = max(0.0, self.fatigue_level - recovery)
        
        # 疲劳影响可用资源
        fatigue_penalty = self.fatigue_level * self.total_capacity * 0.3
        effective_available = self.available * (1.0 - self.fatigue_level * 0.5)
        
        self.last_update = datetime.now()
    
    def get_utilization(self) -> float:
        """获取资源利用率"""
        return 1.0 - (self.available / self.total_capacity)
    
    def to_dict(self) -> dict:
        return {
            "total_capacity": self.total_capacity,
            "available": round(self.available, 2),
            "utilization": round(self.get_utilization(), 2),
            "fatigue_level": round(self.fatigue_level, 3),
            "recovery_rate": self.recovery_rate,
            "last_updated_seconds_ago": (datetime.now() - self.last_update).total_seconds()
        }


@dataclass
class AttentionAllocation:
    """注意力分配记录"""
    allocation_id: str
    target: str  # 目标对象（任务/处理器/内容）
    amount: float
    mode: AttentionMode
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    priority: int = 5  # 1-10，越高越优先
    effectiveness: float = 0.0  # 有效性评分
    
    @property
    def duration(self) -> float:
        """持续时间（秒）"""
        end = self.end_time or datetime.now()
        return (end - self.start_time).total_seconds()
    
    def complete(self, effectiveness: float = 1.0):
        """完成分配并记录效果"""
        self.end_time = datetime.now()
        self.effectiveness = effectiveness


class AttentionController:
    """注意力控制器 - 管理注意力的分配和切换"""
    
    def __init__(self, agent_id: str = "agent_001"):
        self.agent_id = agent_id
        self.resource_pool = AttentionResource()
        self.current_mode = AttentionMode.FOCUSED
        self.active_allocations: dict[str, AttentionAllocation] = {}
        self.allocation_history: list[AttentionAllocation] = []
        self.mode_switch_cost: dict[AttentionMode, float] = {
            AttentionMode.FOCUSED: 2.0,      # 切换到专注模式的成本
            AttentionMode.DIVIDED: 3.0,      # 分散注意的成本
            AttentionMode.DIFFUSE: 1.0,      # 发散思维成本低
            AttentionMode.ALERT: 4.0,        # 警觉状态成本高
            AttentionMode.MEDITATIVE: 1.5    # 冥想成本中等
        }
        self.current_focus_target: Optional[str] = None
        
        logger.info(f"Attention controller initialized for {agent_id}")
    
    def switch_mode(self, new_mode: AttentionMode, reason: str = "") -> bool:
        """切换注意力模式"""
        if new_mode == self.current_mode:
            return True
        
        # 检查是否有足够资源支付切换成本
        cost = self.mode_switch_cost.get(new_mode, 2.0)
        if not self.resource_pool.allocate(cost):
            logger.warning(f"Insufficient attention resources to switch to {new_mode.value}")
            return False
        
        old_mode = self.current_mode
        self.current_mode = new_mode
        
        logger.info(f"Attention mode switched: {old_mode.value} → {new_mode.value} (reason: {reason})")
        
        # 根据新模式调整资源分配策略
        self._adjust_allocation_strategy(new_mode)
        
        return True
    
    def _adjust_allocation_strategy(self, mode: AttentionMode):
        """根据模式调整分配策略"""
        if mode == AttentionMode.FOCUSED:
            # 专注模式：集中资源到单一目标
            self.resource_pool.recovery_rate = 3.0
            self.resource_pool.depletion_rate = 3.0
            
        elif mode == AttentionMode.DIVIDED:
            # 分散模式：降低单个任务的资源上限
            self.resource_pool.recovery_rate = 4.0
            self.resource_pool.depletion_rate = 4.0
            
        elif mode == AttentionMode.DIFFUSE:
            # 发散模式：低消耗，高恢复
            self.resource_pool.recovery_rate = 8.0
            self.resource_pool.depletion_rate = 1.0
            
        elif mode == AttentionMode.ALERT:
            # 警觉模式：高消耗，快速响应
            self.resource_pool.recovery_rate = 2.0
            self.resource_pool.depletion_rate = 5.0
            
        elif mode == AttentionMode.MEDITATIVE:
            # 冥想模式：内部处理，中等消耗
            self.resource_pool.recovery_rate = 6.0
            self.resource_pool.depletion_rate = 1.5
    
    def allocate_attention(
        self, 
        target: str, 
        amount: float, 
        priority: int = 5,
        auto_release_after: Optional[float] = None
    ) -> Optional[AttentionAllocation]:
        """分配注意力到目标"""
        
        # 检查资源
        if not self.resource_pool.allocate(amount):
            logger.warning(f"Cannot allocate {amount} attention to {target}: insufficient resources")
            return None
        
        # 如果是专注模式且已有焦点，先释放旧焦点
        if self.current_mode == AttentionMode.FOCUSED and self.current_focus_target:
            self.release_attention(self.current_focus_target)
        
        # 创建分配记录
        allocation = AttentionAllocation(
            allocation_id=f"alloc_{int(time.time()*1000)}",
            target=target,
            amount=amount,
            mode=self.current_mode,
            priority=priority
        )
        
        self.active_allocations[target] = allocation
        self.current_focus_target = target
        
        logger.debug(f"Allocated {amount} attention to {target} (mode: {self.current_mode.value})")
        
        # 如果设置了自动释放，启动定时器
        if auto_release_after:
            asyncio.create_task(self._auto_release(target, auto_release_after))
        
        return allocation
    
    async def _auto_release(self, target: str, delay: float):
        """自动释放注意力"""
        await asyncio.sleep(delay)
        self.release_attention(target)
    
    def release_attention(self, target: str, effectiveness: float = 1.0) -> bool:
        """释放对目标的注意力"""
        allocation = self.active_allocations.get(target)
        if not allocation:
            return False
        
        # 完成分配记录
        allocation.complete(effectiveness)
        self.allocation_history.append(allocation)
        
        # 释放资源
        self.resource_pool.release(allocation.amount)
        
        # 移除活跃分配
        del self.active_allocations[target]
        
        # 如果这是当前焦点，清除焦点
        if self.current_focus_target == target:
            self.current_focus_target = None
        
        logger.debug(f"Released attention from {target} (effectiveness: {effectiveness:.2f})")
        
        # 保持历史记录在合理范围
        if len(self.allocation_history) > 200:
            self.allocation_history = self.allocation_history[-100:]
        
        return True
    
    def reallocate_attention(
        self, 
        from_target: str, 
        to_target: str, 
        transfer_ratio: float = 1.0
    ) -> bool:
        """重新分配注意力（从一个目标转移到另一个）"""
        from_alloc = self.active_allocations.get(from_target)
        if not from_alloc:
            return False
        
        transfer_amount = from_alloc.amount * transfer_ratio
        
        # 释放部分或全部原分配
        self.release_attention(from_target)
        
        # 分配到新目标
        result = self.allocate_attention(to_target, transfer_amount)
        
        return result is not None
    
    def prioritize_targets(self, targets_with_priority: list[tuple[str, int]]):
        """按优先级排序目标并调整注意力分配"""
        # 按优先级排序
        sorted_targets = sorted(targets_with_priority, key=lambda x: x[1], reverse=True)
        
        # 计算每个目标应得的资源比例
        total_priority = sum(p for _, p in sorted_targets)
        if total_priority == 0:
            return
        
        for target, priority in sorted_targets:
            proportion = priority / total_priority
            desired_amount = self.resource_pool.total_capacity * proportion * 0.8  # 保留20%余量
            
            current_alloc = self.active_allocations.get(target)
            if current_alloc:
                # 调整现有分配
                if abs(current_alloc.amount - desired_amount) > 5.0:
                    self.release_attention(target)
                    self.allocate_attention(target, desired_amount, priority=priority)
            else:
                # 新建分配
                self.allocate_attention(target, desired_amount, priority=priority)
    
    def detect_attention_fatigue(self) -> dict:
        """检测注意力疲劳状态"""
        fatigue = self.resource_pool.fatigue_level
        utilization = self.resource_pool.get_utilization()
        
        status = "normal"
        recommendations = []
        
        if fatigue > 0.7:
            status = "severe_fatigue"
            recommendations.append("立即切换到发散模式休息")
            recommendations.append("减少并发任务数量")
        elif fatigue > 0.5:
            status = "moderate_fatigue"
            recommendations.append("考虑短暂休息")
            recommendations.append("降低任务复杂度")
        elif fatigue > 0.3:
            status = "mild_fatigue"
            recommendations.append("监控疲劳水平")
        
        if utilization > 0.9:
            recommendations.append("资源接近耗尽，释放低优先级任务")
        
        return {
            "status": status,
            "fatigue_level": round(fatigue, 3),
            "utilization": round(utilization, 3),
            "recommendations": recommendations,
            "active_tasks": len(self.active_allocations)
        }
    
    def recover_attention(self, recovery_duration: float = 60.0):
        """执行注意力恢复"""
        logger.info(f"Starting attention recovery for {recovery_duration} seconds")
        
        # 切换到发散模式
        self.switch_mode(AttentionMode.DIFFUSE, "recovery")
        
        # 释放所有非关键分配
        critical_targets = []  # 实际应用中应根据任务重要性判断
        for target in list(self.active_allocations.keys()):
            if target not in critical_targets:
                self.release_attention(target)
        
        # 等待恢复
        time.sleep(recovery_duration)
        
        # 更新疲劳状态
        self.resource_pool.update_fatigue(recovery_duration)
        
        logger.info("Attention recovery completed")
    
    def update(self, elapsed_seconds: float = 1.0):
        """更新注意力状态（定期调用）"""
        # 更新疲劳
        self.resource_pool.update_fatigue(elapsed_seconds)
        
        # 检查是否需要自动恢复
        fatigue_status = self.detect_attention_fatigue()
        if fatigue_status["status"] == "severe_fatigue":
            logger.warning("Severe attention fatigue detected!")
            # 这里可以触发自动恢复，但需要谨慎以避免干扰用户
    
    def get_attention_state(self) -> dict:
        """获取注意力状态报告"""
        fatigue_info = self.detect_attention_fatigue()
        
        return {
            "agent_id": self.agent_id,
            "current_mode": self.current_mode.value,
            "resource_pool": self.resource_pool.to_dict(),
            "active_allocations": {
                target: {
                    "amount": alloc.amount,
                    "duration": alloc.duration,
                    "priority": alloc.priority
                }
                for target, alloc in self.active_allocations.items()
            },
            "current_focus": self.current_focus_target,
            "fatigue_status": fatigue_info,
            "total_allocations_made": len(self.allocation_history)
        }
    
    def introspect_attention(self) -> str:
        """内省注意力状态"""
        state = self.get_attention_state()
        
        mode_descriptions = {
            "focused": "我正全神贯注于单一任务，排除一切干扰。",
            "divided": "我在多个任务间分配注意力，效率可能降低。",
            "diffuse": "我的思维处于发散状态，适合创造性思考。",
            "alert": "我保持高度警觉，随时准备应对突发情况。",
            "meditative": "我在进行内省，反思自己的思维过程。"
        }
        
        mode_desc = mode_descriptions.get(state["current_mode"], "我的注意力状态不明确。")
        
        fatigue_desc = ""
        if state["fatigue_status"]["fatigue_level"] > 0.5:
            fatigue_desc = f"\n我感到疲惫（疲劳度: {state['fatigue_status']['fatigue_level']:.0%}），需要休息。"
        else:
            fatigue_desc = f"\n我的精力充沛（疲劳度: {state['fatigue_status']['fatigue_level']:.0%}）。"
        
        focus_desc = ""
        if state["current_focus"]:
            focus_desc = f"\n我当前的焦点是: {state['current_focus']}"
        else:
            focus_desc = "\n我目前没有明确的焦点。"
        
        return mode_desc + fatigue_desc + focus_desc
