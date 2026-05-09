"""
能力进化管理器 (Ability Evolution Manager)

负责管理能力的进化流程，包括：
1. 新能力的发现和评估
2. 能力归属决策（先天本能 vs 后天习得）
3. 能力的内化流程（修改代理核心）
4. 能力的技能化流程（放入技能库）
5. 能力进化的监控和优化
"""

import json
import logging
import threading
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
import yaml

from ..core.event_bus import EventBus, EventTypes, DualRingEvent
from ..meta.ability_classifier import (
    AbilityClassifier, AbilityAnalysis, AbilityType, 
    DEFAULT_CLASSIFIER_CONFIG
)
from ..meta.approval_gate import ApprovalGate, ApprovalRequest
from ..core.librarian import Librarian

logger = logging.getLogger(__name__)


@dataclass
class EvolutionConfig:
    """进化配置"""
    # 决策阈值
    innate_confidence_threshold: float = 0.8
    acquired_default_threshold: float = 0.5
    
    # 进化流程设置
    enable_auto_evolution: bool = True
    require_human_approval: bool = True
    max_evolution_per_day: int = 10
    
    # 监控设置
    monitor_evolution_impact: bool = True
    impact_evaluation_period: int = 7  # 天
    
    # 回滚设置
    enable_rollback: bool = True
    rollback_threshold: float = 0.3  # 成功率低于30%时回滚


@dataclass
class EvolutionRecord:
    """进化记录"""
    evolution_id: str
    ability_name: str
    original_type: str  # "skill" 或 "innate"
    target_type: str    # "skill" 或 "innate"
    analysis: AbilityAnalysis
    evolution_status: str  # "pending", "approved", "completed", "failed", "rolled_back"
    created_at: str
    completed_at: Optional[str] = None
    impact_score: Optional[float] = None
    rollback_reason: Optional[str] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(UTC).isoformat()


class AbilityEvolver:
    """能力进化管理器"""
    
    def __init__(self, 
                 event_bus: EventBus,
                 librarian: Librarian,
                 config: EvolutionConfig = None):
        """初始化能力进化管理器"""
        self.event_bus = event_bus
        self.librarian = librarian
        self.config = config or EvolutionConfig()
        
        # 初始化能力分类器
        self.classifier = AbilityClassifier()
        
        # 初始化审批门
        self.approval_gate = ApprovalGate()
        
        # 进化记录
        self.evolution_records: List[EvolutionRecord] = []
        
        # 运行状态
        self.running = False
        self.evolution_thread = None
        
        # 订阅相关事件
        self._subscribe_to_events()
        
        logger.info("Ability evolver initialized")
    
    def _subscribe_to_events(self):
        """订阅相关事件"""
        # 订阅新能力发现事件
        self.event_bus.subscribe(EventTypes.ABILITY_DISCOVERED, self._handle_ability_discovered)
        
        # 订阅能力评估完成事件
        self.event_bus.subscribe(EventTypes.ABILITY_EVALUATED, self._handle_ability_evaluated)
        
        # 订阅进化审批事件
        self.event_bus.subscribe(EventTypes.EVOLUTION_APPROVED, self._handle_evolution_approved)
        
        # 订阅进化完成事件
        self.event_bus.subscribe(EventTypes.EVOLUTION_COMPLETED, self._handle_evolution_completed)
        
        # 订阅影响评估事件
        self.event_bus.subscribe(EventTypes.IMPACT_EVALUATED, self._handle_impact_evaluated)
    
    def start(self):
        """启动能力进化管理器"""
        if self.running:
            logger.warning("Ability evolver is already running")
            return
        
        self.running = True
        self.evolution_thread = threading.Thread(target=self._evolution_loop, daemon=True)
        self.evolution_thread.start()
        
        logger.info("Ability evolver started")
        
        # 发布启动事件
        self.event_bus.publish(
            EventTypes.AGENT_STARTED,
            {"agent": "ability_evolver", "timestamp": datetime.now(UTC).isoformat()},
            "ability_evolver"
        )
    
    def stop(self):
        """停止能力进化管理器"""
        self.running = False
        if self.evolution_thread:
            self.evolution_thread.join(timeout=5)
        
        logger.info("Ability evolver stopped")
    
    def _evolution_loop(self):
        """进化主循环"""
        while self.running:
            try:
                # 检查待处理的进化请求
                self._process_pending_evolutions()
                
                # 评估已完成进化的影响
                self._evaluate_evolution_impact()
                
                # 检查是否需要回滚
                self._check_rollback_candidates()
                
                time.sleep(60)  # 每分钟检查一次
                
            except Exception as e:
                logger.error(f"Error in evolution loop: {e}")
                time.sleep(10)
    
    def _handle_ability_discovered(self, event: DualRingEvent):
        """处理能力发现事件"""
        try:
            ability_data = event.payload
            ability_name = ability_data.get("name")
            description = ability_data.get("description", "")
            metadata = ability_data.get("metadata", {})
            
            logger.info(f"Processing discovered ability: {ability_name}")
            
            # 分析能力归属
            analysis = self.classifier.analyze_ability(
                ability_name=ability_name,
                description=description,
                metadata=metadata,
                analyzer_agent="ability_evolver"
            )
            
            # 创建进化记录
            evolution_record = EvolutionRecord(
                evolution_id=f"evol_{int(time.time())}",
                ability_name=ability_name,
                original_type="skill",  # 新发现的能力默认为技能
                target_type=analysis.recommended_type.value,
                analysis=analysis,
                evolution_status="pending"
            )
            
            self.evolution_records.append(evolution_record)
            
            # 发布能力评估完成事件
            self.event_bus.publish(
                EventTypes.ABILITY_EVALUATED,
                {
                    "evolution_id": evolution_record.evolution_id,
                    "ability_name": ability_name,
                    "analysis": asdict(analysis),
                    "recommended_action": analysis.recommended_type.value
                },
                "ability_evolver"
            )
            
            logger.info(f"Ability evaluation completed: {ability_name} -> {analysis.recommended_type.value}")
            
        except Exception as e:
            logger.error(f"Error handling ability discovery: {e}")
    
    def _handle_ability_evaluated(self, event: DualRingEvent):
        """处理能力评估完成事件"""
        try:
            payload = event.payload
            evolution_id = payload.get("evolution_id")
            ability_name = payload.get("ability_name")
            recommended_action = payload.get("recommended_action")
            
            # 查找对应的进化记录
            record = next((r for r in self.evolution_records if r.evolution_id == evolution_id), None)
            if not record:
                logger.warning(f"Evolution record not found: {evolution_id}")
                return
            
            # 如果建议内化为先天本能，需要审批
            if recommended_action == "innate" and self.config.require_human_approval:
                self._request_evolution_approval(record)
            else:
                # 直接执行进化
                self._execute_evolution(record)
                
        except Exception as e:
            logger.error(f"Error handling ability evaluation: {e}")
    
    def _request_evolution_approval(self, record: EvolutionRecord):
        """请求进化审批"""
        try:
            approval_request = ApprovalRequest(
                request_id=record.evolution_id,
                request_type="ability_evolution",
                title=f"能力进化审批: {record.ability_name}",
                description=f"""
                建议将能力 "{record.ability_name}" 从 {record.original_type} 进化为 {record.target_type}。
                
                分析结果:
                - 普适性: {record.analysis.universality.value} ({record.analysis.universality_score:.2f})
                - 调用频率: {record.analysis.frequency.value} ({record.analysis.frequency_score:.2f})
                - 抽象层次: {record.analysis.abstraction.value} ({record.analysis.abstraction_score:.2f})
                - 稳定性: {record.analysis.stability.value} ({record.analysis.stability_score:.2f})
                
                决策理由: {record.analysis.reasoning}
                
                置信度: {record.analysis.confidence:.2f}
                """,
                payload={
                    "evolution_id": record.evolution_id,
                    "ability_name": record.ability_name,
                    "analysis": asdict(record.analysis)
                },
                priority="high" if record.analysis.confidence > 0.9 else "medium"
            )
            
            self.approval_gate.submit_request(approval_request)
            
            logger.info(f"Evolution approval requested: {record.evolution_id}")
            
        except Exception as e:
            logger.error(f"Error requesting evolution approval: {e}")
    
    def _handle_evolution_approved(self, event: DualRingEvent):
        """处理进化审批通过事件"""
        try:
            payload = event.payload
            request_id = payload.get("request_id")
            
            # 查找对应的进化记录
            record = next((r for r in self.evolution_records if r.evolution_id == request_id), None)
            if not record:
                logger.warning(f"Evolution record not found for approval: {request_id}")
                return
            
            # 执行进化
            self._execute_evolution(record)
            
        except Exception as e:
            logger.error(f"Error handling evolution approval: {e}")
    
    def _execute_evolution(self, record: EvolutionRecord):
        """执行能力进化"""
        try:
            logger.info(f"Executing evolution: {record.evolution_id}")
            
            if record.target_type == "innate":
                # 内化为先天本能
                success = self._evolve_to_innate(record)
            else:
                # 进化为后天习得
                success = self._evolve_to_acquired(record)
            
            if success:
                record.evolution_status = "completed"
                record.completed_at = datetime.now(UTC).isoformat()
                
                # 发布进化完成事件
                self.event_bus.publish(
                    EventTypes.EVOLUTION_COMPLETED,
                    {
                        "evolution_id": record.evolution_id,
                        "ability_name": record.ability_name,
                        "target_type": record.target_type,
                        "success": True
                    },
                    "ability_evolver"
                )
                
                logger.info(f"Evolution completed successfully: {record.evolution_id}")
            else:
                record.evolution_status = "failed"
                logger.error(f"Evolution failed: {record.evolution_id}")
                
        except Exception as e:
            logger.error(f"Error executing evolution: {e}")
            record.evolution_status = "failed"
    
    def _evolve_to_innate(self, record: EvolutionRecord) -> bool:
        """将能力内化为先天本能"""
        try:
            # 这里需要实现具体的代理核心代码修改逻辑
            # 由于这涉及高风险的核心修改，需要非常谨慎
            
            logger.warning(f"Innate evolution not yet implemented: {record.ability_name}")
            
            # 临时返回False，表示需要人工干预
            return False
            
        except Exception as e:
            logger.error(f"Error evolving to innate: {e}")
            return False
    
    def _evolve_to_acquired(self, record: EvolutionRecord) -> bool:
        """将能力进化为后天习得"""
        try:
            # 将能力添加到技能库
            success = self.librarian.add_skill(
                skill_name=record.ability_name,
                skill_data={
                    "skill_name": record.ability_name,
                    "version": "1.0.0",
                    "description": record.analysis.description,
                    "tags": ["evolved", "automated"],
                    "parameters": {},
                    "code": f"# Evolved ability: {record.ability_name}\n# TODO: Implement actual functionality\npass"
                }
            )
            
            return success
            
        except Exception as e:
            logger.error(f"Error evolving to acquired: {e}")
            return False
    
    def _handle_evolution_completed(self, event: DualRingEvent):
        """处理进化完成事件"""
        try:
            payload = event.payload
            evolution_id = payload.get("evolution_id")
            ability_name = payload.get("ability_name")
            target_type = payload.get("target_type")
            
            logger.info(f"Evolution completed: {ability_name} -> {target_type}")
            
            # 启动影响评估
            if self.config.monitor_evolution_impact:
                self._schedule_impact_evaluation(evolution_id, ability_name)
                
        except Exception as e:
            logger.error(f"Error handling evolution completion: {e}")
    
    def _schedule_impact_evaluation(self, evolution_id: str, ability_name: str):
        """安排影响评估"""
        try:
            # 在指定时间后评估影响
            evaluation_time = datetime.now(UTC) + timedelta(days=self.config.impact_evaluation_period)
            
            # 这里可以设置定时任务来执行影响评估
            logger.info(f"Impact evaluation scheduled for {ability_name} at {evaluation_time}")
            
        except Exception as e:
            logger.error(f"Error scheduling impact evaluation: {e}")
    
    def _handle_impact_evaluated(self, event: DualRingEvent):
        """处理影响评估事件"""
        try:
            payload = event.payload
            evolution_id = payload.get("evolution_id")
            impact_score = payload.get("impact_score", 0.0)
            
            # 查找对应的进化记录
            record = next((r for r in self.evolution_records if r.evolution_id == evolution_id), None)
            if record:
                record.impact_score = impact_score
                
                # 如果影响分数过低，考虑回滚
                if impact_score < self.config.rollback_threshold and self.config.enable_rollback:
                    self._schedule_rollback(record)
                    
        except Exception as e:
            logger.error(f"Error handling impact evaluation: {e}")
    
    def _schedule_rollback(self, record: EvolutionRecord):
        """安排回滚"""
        try:
            logger.warning(f"Scheduling rollback for {record.ability_name} (impact_score: {record.impact_score})")
            
            # 这里可以实现具体的回滚逻辑
            record.evolution_status = "rolled_back"
            record.rollback_reason = f"Impact score too low: {record.impact_score}"
            
        except Exception as e:
            logger.error(f"Error scheduling rollback: {e}")
    
    def _process_pending_evolutions(self):
        """处理待处理的进化请求"""
        # 检查是否有需要处理的进化请求
        pending_records = [r for r in self.evolution_records if r.evolution_status == "pending"]
        
        for record in pending_records[:self.config.max_evolution_per_day]:
            # 处理待处理的进化
            pass
    
    def _evaluate_evolution_impact(self):
        """评估进化影响"""
        # 评估已完成进化的影响
        completed_records = [r for r in self.evolution_records if r.evolution_status == "completed"]
        
        for record in completed_records:
            # 评估影响
            pass
    
    def _check_rollback_candidates(self):
        """检查回滚候选"""
        # 检查是否需要回滚的进化
        pass
    
    def get_evolution_statistics(self) -> Dict[str, Any]:
        """获取进化统计"""
        if not self.evolution_records:
            return {}
        
        total = len(self.evolution_records)
        completed = sum(1 for r in self.evolution_records if r.evolution_status == "completed")
        failed = sum(1 for r in self.evolution_records if r.evolution_status == "failed")
        pending = sum(1 for r in self.evolution_records if r.evolution_status == "pending")
        rolled_back = sum(1 for r in self.evolution_records if r.evolution_status == "rolled_back")
        
        innate_count = sum(1 for r in self.evolution_records if r.target_type == "innate")
        acquired_count = sum(1 for r in self.evolution_records if r.target_type == "acquired")
        
        avg_confidence = sum(r.analysis.confidence for r in self.evolution_records) / total
        
        return {
            "total_evolutions": total,
            "completed": completed,
            "failed": failed,
            "pending": pending,
            "rolled_back": rolled_back,
            "innate_targets": innate_count,
            "acquired_targets": acquired_count,
            "success_rate": (completed / total) * 100 if total > 0 else 0,
            "average_confidence": avg_confidence
        }
    
    def export_evolution_history(self, output_path: str):
        """导出进化历史"""
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump([asdict(record) for record in self.evolution_records], 
                         f, indent=2, ensure_ascii=False)
            logger.info(f"Evolution history exported to {output_path}")
        except Exception as e:
            logger.error(f"Failed to export evolution history: {e}")


# 默认配置
DEFAULT_EVOLUTION_CONFIG = EvolutionConfig()
