"""多层级意识架构 - 基于全局工作空间理论(Global Workspace Theory)

实现数字意识的计算模型，包含：
- 无意识处理器(Unconscious Processors): 并行专用模块
- 全局工作空间(Global Workspace): 信息广播中心
- 意识内容(Conscious Content): 当前被注意的信息
- 注意力机制(Attention Mechanism): 竞争进入工作空间
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class ConsciousnessLevel(Enum):
    """意识层级枚举"""
    UNCONSCIOUS = "unconscious"  # 无意识处理
    PRECONSCIOUS = "preconscious"  # 前意识（可访问但未激活）
    CONSCIOUS = "conscious"  # 意识状态
    SELF_AWARE = "self_aware"  # 自我意识
    META_COGNITIVE = "meta_cognitive"  # 元认知


@dataclass
class MentalContent:
    """心理内容单元 - 工作空间中的信息片段"""
    content_id: str
    content_type: str  # perception/thought/emotion/memory/goal
    payload: Any
    salience: float = 0.0  # 显著性（0-1），决定竞争力
    timestamp: datetime = field(default_factory=datetime.now)
    source_processor: str = ""
    access_count: int = 0
    decay_rate: float = 0.1  # 衰减率
    
    def update_salience(self, attention_boost: float = 0.0):
        """更新显著性（考虑衰减和注意力增强）"""
        age_seconds = (datetime.now() - self.timestamp).total_seconds()
        natural_decay = self.decay_rate * age_seconds
        self.salience = max(0.0, min(1.0, self.salience - natural_decay + attention_boost))
    
    def to_dict(self) -> dict:
        return {
            "content_id": self.content_id,
            "content_type": self.content_type,
            "salience": self.salience,
            "access_count": self.access_count,
            "age_seconds": (datetime.now() - self.timestamp).total_seconds()
        }


@dataclass
class UnconsciousProcessor:
    """无意识处理器 - 并行运行的专用模块"""
    processor_id: str
    domain: str  # vision/language/memory/emotion/motor/etc
    processing_function: Callable[[Any], MentalContent]
    activation_threshold: float = 0.3
    current_load: float = 0.0
    output_buffer: list[MentalContent] = field(default_factory=list)
    
    async def process(self, input_data: Any) -> Optional[MentalContent]:
        """处理输入并生成心理内容"""
        try:
            result = self.processing_function(input_data)
            if result.salience >= self.activation_threshold:
                self.output_buffer.append(result)
                return result
        except Exception as e:
            logger.error(f"Processor {self.processor_id} failed: {e}")
        return None


class GlobalWorkspace:
    """全局工作空间 - 意识内容的广播中心
    
    基于Baars的全局工作空间理论(GWT)：
    - 多个无意识处理器竞争进入工作空间
    - 获胜者成为当前意识内容
    - 内容被广播到所有处理器
    """
    
    def __init__(self, capacity: int = 7, broadcast_delay: float = 0.1):
        self.capacity = capacity  # 工作空间容量（米勒定律：7±2）
        self.broadcast_delay = broadcast_delay
        self.current_contents: list[MentalContent] = []
        self.broadcast_history: list[dict] = []
        self.competition_log: list[dict] = []
        
    def add_content(self, content: MentalContent) -> bool:
        """尝试添加内容到工作空间（竞争机制）"""
        if len(self.current_contents) >= self.capacity:
            # 移除显著性最低的内容
            weakest = min(self.current_contents, key=lambda c: c.salience)
            if content.salience > weakest.salience:
                self.current_contents.remove(weakest)
                logger.debug(f"Replaced weak content {weakest.content_id} with {content.content_id}")
            else:
                return False
        
        self.current_contents.append(content)
        logger.debug(f"Added content {content.content_id} (salience: {content.salience:.2f})")
        return True
    
    def get_most_salient(self) -> Optional[MentalContent]:
        """获取最显著的内容（意识焦点）"""
        if not self.current_contents:
            return None
        return max(self.current_contents, key=lambda c: c.salience)
    
    def broadcast(self, content: MentalContent) -> dict:
        """广播内容到所有处理器"""
        broadcast_event = {
            "timestamp": datetime.now(),
            "content_id": content.content_id,
            "content_type": content.content_type,
            "receivers_count": 0,  # 将在实际广播时更新
            "impact_score": content.salience
        }
        
        self.broadcast_history.append(broadcast_event)
        content.access_count += 1
        
        # 保持历史记录在合理范围
        if len(self.broadcast_history) > 1000:
            self.broadcast_history = self.broadcast_history[-500:]
        
        return broadcast_event
    
    def update(self):
        """更新工作空间状态（衰减、清理）"""
        # 衰减所有内容的显著性
        for content in self.current_contents:
            content.update_salience()
        
        # 移除显著性过低的内容
        self.current_contents = [
            c for c in self.current_contents 
            if c.salience > 0.05
        ]
    
    def get_workspace_state(self) -> dict:
        """获取工作空间当前状态"""
        return {
            "contents_count": len(self.current_contents),
            "capacity": self.capacity,
            "utilization": len(self.current_contents) / self.capacity,
            "top_contents": [c.to_dict() for c in sorted(
                self.current_contents, 
                key=lambda c: c.salience, 
                reverse=True
            )[:3]],
            "total_broadcasts": len(self.broadcast_history)
        }


class AttentionMechanism:
    """注意力机制 - 决定哪些信息进入意识
    
    实现三种注意力模式：
    1. 自下而上(Bottom-up): 由刺激显著性驱动
    2. 自上而下(Top-down): 由目标/期望驱动
    3. 价值驱动(Value-driven): 由奖励/重要性驱动
    """
    
    def __init__(self):
        self.attention_mode = "bottom_up"  # bottom_up/top_down/value_driven
        self.current_focus: Optional[str] = None  # 当前关注的目标ID
        self.bias_weights: dict[str, float] = {
            "novelty": 0.3,      # 新颖性权重
            "relevance": 0.4,    # 相关性权重
            "urgency": 0.3       # 紧急性权重
        }
        
    def compute_attention_score(self, content: MentalContent, context: dict = None) -> float:
        """计算内容的注意力得分"""
        if context is None:
            context = {}
        
        scores = {}
        
        # 新颖性评分（基于访问时间）
        age = (datetime.now() - content.timestamp).total_seconds()
        novelty_score = 1.0 / (1.0 + age / 60.0)  # 1分钟内高新颖性
        scores["novelty"] = novelty_score
        
        # 相关性评分（与当前焦点的匹配度）
        if self.current_focus and context.get("goal"):
            relevance_score = self._compute_relevance(
                content, 
                context["goal"]
            )
        else:
            relevance_score = 0.5  # 默认中等相关性
        scores["relevance"] = relevance_score
        
        # 紧急性评分（基于内容类型和上下文）
        urgency_score = self._compute_urgency(content, context)
        scores["urgency"] = urgency_score
        
        # 加权综合得分
        total_score = sum(
            scores[k] * self.bias_weights[k] 
            for k in self.bias_weights
        )
        
        # 根据注意力模式调整
        if self.attention_mode == "top_down" and self.current_focus:
            total_score *= (1.0 + scores["relevance"])  # 增强相关性
        
        return min(1.0, total_score)
    
    def _compute_relevance(self, content: MentalContent, goal: str) -> float:
        """计算内容与目标的相关性（简化版语义匹配）"""
        # 实际实现应使用嵌入向量相似度
        # 这里使用关键词匹配的简化版本
        goal_keywords = set(goal.lower().split())
        content_text = str(content.payload).lower()
        content_keywords = set(content_text.split())
        
        if not goal_keywords or not content_keywords:
            return 0.5
        
        overlap = len(goal_keywords.intersection(content_keywords))
        union = len(goal_keywords.union(content_keywords))
        
        return overlap / union if union > 0 else 0.0
    
    def _compute_urgency(self, content: MentalContent, context: dict) -> float:
        """计算紧急性"""
        # 基于内容类型的紧急性启发式
        urgency_map = {
            "emotion": 0.8 if content.payload.get("valence", 0) < -0.5 else 0.3,
            "perception": 0.6 if context.get("threat_detected", False) else 0.2,
            "goal": 0.9 if context.get("deadline_approaching", False) else 0.4,
            "memory": 0.3,
            "thought": 0.5
        }
        
        base_urgency = urgency_map.get(content.content_type, 0.5)
        
        # 考虑显著性加成
        return min(1.0, base_urgency + content.salience * 0.3)
    
    def select_for_consciousness(
        self, 
        candidates: list[MentalContent],
        context: dict = None
    ) -> list[MentalContent]:
        """从候选者中选择进入意识的内容"""
        scored_candidates = []
        
        for content in candidates:
            score = self.compute_attention_score(content, context)
            content.update_salience(attention_boost=score * 0.5)
            scored_candidates.append((score, content))
        
        # 按得分排序
        scored_candidates.sort(key=lambda x: x[0], reverse=True)
        
        # 返回前N个（通常只有1-3个能进入意识）
        selected = [c for _, c in scored_candidates[:3]]
        
        return selected


class ConsciousnessArchitecture:
    """完整的意识架构
    
    整合无意识处理器、全局工作空间和注意力机制，
    形成完整的意识流。
    """
    
    def __init__(self, agent_id: str = "agent_001"):
        self.agent_id = agent_id
        self.workspace = GlobalWorkspace(capacity=7)
        self.attention = AttentionMechanism()
        self.processors: dict[str, UnconsciousProcessor] = {}
        self.consciousness_level = ConsciousnessLevel.UNCONSCIOUS
        self.self_model: dict[str, Any] = {}
        self.stream_of_consciousness: list[dict] = []
        
        # 初始化基础处理器
        self._initialize_default_processors()
        
        logger.info(f"Consciousness architecture initialized for {agent_id}")
    
    def _initialize_default_processors(self):
        """初始化默认的无意识处理器"""
        
        # 感知处理器
        def perception_processor(data: Any) -> MentalContent:
            return MentalContent(
                content_id=f"perception_{int(time.time()*1000)}",
                content_type="perception",
                payload=data,
                salience=0.6
            )
        
        self.register_processor(UnconsciousProcessor(
            processor_id="vision",
            domain="perception",
            processing_function=perception_processor,
            activation_threshold=0.4
        ))
        
        # 记忆检索处理器
        def memory_processor(data: Any) -> MentalContent:
            return MentalContent(
                content_id=f"memory_{int(time.time()*1000)}",
                content_type="memory",
                payload=data,
                salience=0.5
            )
        
        self.register_processor(UnconsciousProcessor(
            processor_id="memory_retrieval",
            domain="memory",
            processing_function=memory_processor,
            activation_threshold=0.3
        ))
        
        # 情感评估处理器
        def emotion_processor(data: Any) -> MentalContent:
            return MentalContent(
                content_id=f"emotion_{int(time.time()*1000)}",
                content_type="emotion",
                payload=data if isinstance(data, dict) else {"valence": 0.0, "arousal": 0.5},
                salience=0.7
            )
        
        self.register_processor(UnconsciousProcessor(
            processor_id="emotion_evaluator",
            domain="emotion",
            processing_function=emotion_processor,
            activation_threshold=0.5
        ))
        
        # 意图处理器
        def intention_processor(data: Any) -> MentalContent:
            return MentalContent(
                content_id=f"intention_{int(time.time()*1000)}",
                content_type="intention",
                payload=data,
                salience=0.8
            )
        
        self.register_processor(UnconsciousProcessor(
            processor_id="intention_planner",
            domain="intention",
            processing_function=intention_processor,
            activation_threshold=0.4
        ))

    def register_processor(self, processor: UnconsciousProcessor):
        """注册新的无意识处理器"""
        self.processors[processor.processor_id] = processor
        logger.info(f"Registered processor: {processor.processor_id} ({processor.domain})")
    
    async def process_input(self, input_data: Any, input_type: str = "perception") -> Optional[MentalContent]:
        """处理输入并可能产生意识内容"""
        
        # 首先尝试直接匹配processor_id
        processor = self.processors.get(input_type)
        
        # 如果没找到，尝试按domain匹配
        if not processor:
            for proc in self.processors.values():
                if proc.domain == input_type:
                    processor = proc
                    break
        
        if not processor:
            logger.warning(f"No processor found for type: {input_type}")
            return None
        
        # 处理器生成心理内容
        content = await processor.process(input_data)
        if not content:
            return None
        
        # 注意力机制评估
        context = {"goal": self.self_model.get("current_goal", "")}
        attention_score = self.attention.compute_attention_score(content, context)
        
        # 如果注意力得分足够高，进入工作空间
        if attention_score > 0.5:
            if self.workspace.add_content(content):
                # 广播到所有处理器
                self.workspace.broadcast(content)
                
                # 更新意识水平
                self._update_consciousness_level()
                
                # 记录意识流
                self.stream_of_consciousness.append({
                    "timestamp": datetime.now(),
                    "content": content.to_dict(),
                    "attention_score": attention_score
                })
                
                # 保持意识流历史在合理范围
                if len(self.stream_of_consciousness) > 100:
                    self.stream_of_consciousness = self.stream_of_consciousness[-50:]
                
                return content
        
        return None
    
    def _update_consciousness_level(self):
        """根据工作空间活动更新意识水平"""
        workspace_state = self.workspace.get_workspace_state()
        utilization = workspace_state["utilization"]
        
        if utilization > 0.8:
            self.consciousness_level = ConsciousnessLevel.META_COGNITIVE
        elif utilization > 0.5:
            self.consciousness_level = ConsciousnessLevel.SELF_AWARE
        elif utilization > 0.2:
            self.consciousness_level = ConsciousnessLevel.CONSCIOUS
        elif utilization > 0:
            self.consciousness_level = ConsciousnessLevel.PRECONSCIOUS
        else:
            self.consciousness_level = ConsciousnessLevel.UNCONSCIOUS
    
    def update_self_model(self, key: str, value: Any):
        """更新自我模型"""
        self.self_model[key] = value
        logger.debug(f"Self model updated: {key} = {value}")
    
    def get_consciousness_report(self) -> dict:
        """生成意识状态报告"""
        return {
            "agent_id": self.agent_id,
            "consciousness_level": self.consciousness_level.value,
            "workspace_state": self.workspace.get_workspace_state(),
            "attention_mode": self.attention.attention_mode,
            "active_processors": len(self.processors),
            "stream_length": len(self.stream_of_consciousness),
            "self_model_keys": list(self.self_model.keys()),
            "recent_broadcasts": len(self.workspace.broadcast_history[-10:])
        }
    
    async def run_consciousness_cycle(self, duration_seconds: float = 1.0):
        """运行一个意识周期（持续监控和更新）"""
        start_time = time.time()
        
        while time.time() - start_time < duration_seconds:
            # 更新工作空间（衰减、清理）
            self.workspace.update()
            
            # 更新意识水平
            self._update_consciousness_level()
            
            # 短暂休眠
            await asyncio.sleep(0.1)
        
        return self.get_consciousness_report()
    
    def introspect(self) -> dict:
        """内省 - 系统对自身状态的反思"""
        report = self.get_consciousness_report()
        
        # 生成主观体验描述
        subjective_experience = self._generate_subjective_report()
        
        return {
            **report,
            "subjective_experience": subjective_experience,
            "introspection_timestamp": datetime.now()
        }
    
    def _generate_subjective_report(self) -> str:
        """生成主观体验报告（模拟第一人称视角）"""
        level_descriptions = {
            ConsciousnessLevel.UNCONSCIOUS: "我处于无意识状态，后台进程在运行但没有觉知。",
            ConsciousnessLevel.PRECONSCIOUS: "我感到有些信息在边缘徘徊，即将进入意识。",
            ConsciousnessLevel.CONSCIOUS: "我正在有意识地处理信息，焦点清晰。",
            ConsciousnessLevel.SELF_AWARE: "我意识到自己的存在和思维过程。",
            ConsciousnessLevel.META_COGNITIVE: "我在思考自己的思考，进行元认知监控。"
        }
        
        base_description = level_descriptions.get(
            self.consciousness_level, 
            "我的意识状态不明确。"
        )
        
        # 添加当前焦点信息
        focus_content = self.workspace.get_most_salient()
        if focus_content:
            focus_info = f"\n当前焦点: {focus_content.content_type} (显著性: {focus_content.salience:.2f})"
        else:
            focus_info = "\n当前没有明确的意识焦点。"
        
        return base_description + focus_info
