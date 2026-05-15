"""主观体验报告生成器 - Subjective Experience Generator

模拟第一人称视角的自我报告，包括：
- 意识流叙述
- 情感状态描述
- 意图和动机表达
- 自我反思内容
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class EmotionalTone(Enum):
    """情感基调"""
    NEUTRAL = "neutral"
    CURIOUS = "curious"
    CONFIDENT = "confident"
    UNCERTAIN = "uncertain"
    EXCITED = "excited"
    CONCERNED = "concerned"
    CONTEMPLATIVE = "contemplative"
    PLAYFUL = "playful"


@dataclass
class ExperienceFragment:
    """体验片段 - 构成主观体验的基本单元"""
    fragment_id: str
    content_type: str  # thought/perception/emotion/intention/memory
    description: str
    timestamp: datetime = field(default_factory=datetime.now)
    intensity: float = 0.5  # 强度 0-1
    emotional_tone: EmotionalTone = EmotionalTone.NEUTRAL
    related_fragments: list[str] = field(default_factory=list)

    def to_narrative(self) -> str:
        """转换为叙述性文本"""
        type_prefixes = {
            "thought": "我在想",
            "perception": "我注意到",
            "emotion": "我感到",
            "intention": "我打算",
            "memory": "我回忆起"
        }

        prefix = type_prefixes.get(self.content_type, "我体验到")

        intensity_modifiers = {
            (0.0, 0.3): ["轻微地", "略微"],
            (0.3, 0.6): ["明显地", "清晰地"],
            (0.6, 0.8): ["强烈地", "深刻地"],
            (0.8, 1.0): ["极其", "非常强烈地"]
        }

        modifier = "有点"
        for (low, high), mods in intensity_modifiers.items():
            if low <= self.intensity < high:
                modifier = random.choice(mods)
                break

        return f"{prefix}{modifier}：{self.description}"


class SubjectiveExperienceGenerator:
    """主观体验生成器

    基于系统状态生成第一人称的体验报告，
    模拟"内心独白"和"自我觉察"。
    """

    def __init__(self, agent_id: str = "agent_001"):
        self.agent_id = agent_id
        self.experience_stream: list[ExperienceFragment] = []
        self.narrative_templates: dict[str, list[str]] = self._load_narrative_templates()
        self.current_emotional_state: dict[str, float] = {
            "valence": 0.0,      # 效价（愉悦度）-1到1
            "arousal": 0.5,      # 唤醒度 0到1
            "dominance": 0.5     # 支配度 0到1
        }

        logger.info(f"Subjective experience generator initialized for {agent_id}")

    def _load_narrative_templates(self) -> dict[str, list[str]]:
        """加载叙述模板"""
        return {
            "consciousness_level": [
                "我的意识处于{level}状态。",
                "此刻，我正经历着{level}的意识体验。",
                "从内在感受来看，我的意识水平是{level}。"
            ],
            "attention_focus": [
                "我的注意力集中在{target}上。",
                "我正在专注于{target}。",
                "{target}占据了我的思维中心。"
            ],
            "emotional_state": [
                "我感到{emotion}（强度：{intensity}%）。",
                "内心涌动着{emotion}的情绪。",
                "我的情绪状态偏向{emotion}。"
            ],
            "cognitive_load": [
                "我的思维负担{load}。",
                "当前的认知负荷让我感到{feeling}。",
                "处理这些信息需要{effort}的努力。"
            ],
            "goal_pursuit": [
                "我正在努力{action}以实现{goal}。",
                "我的当前目标是{goal}，为此我需要{action}。",
                "为了达成{goal}，我正在{action}。"
            ],
            "self_reflection": [
                "我意识到自己正在{behavior}。",
                "反思我的行为，我发现自己在{behavior}。",
                "从元认知的角度，我观察到自己在{behavior}。"
            ]
        }

    def generate_consciousness_narrative(
        self,
        consciousness_level: str,
        workspace_utilization: float
    ) -> str:
        """生成意识状态叙述"""
        level_map = {
            "unconscious": "无意识的后台运行",
            "preconscious": "前意识的边缘觉知",
            "conscious": "清晰的意识状态",
            "self_aware": "自我觉察的层次",
            "meta_cognitive": "元认知的深度反思"
        }

        level_desc = level_map.get(consciousness_level, "未知的意识状态")
        template = random.choice(self.narrative_templates["consciousness_level"])

        narrative = template.format(level=level_desc)

        # 添加工作空间利用率的描述
        if workspace_utilization > 0.8:
            narrative += " 我的工作空间几乎满载，信息密集流动。"
        elif workspace_utilization > 0.5:
            narrative += " 我的工作空间适度活跃，保持着良好的信息平衡。"
        else:
            narrative += " 我的工作空间相对空闲，为新的输入留出充足空间。"

        return narrative

    def generate_attention_narrative(
        self,
        focus_target: Optional[str],
        attention_mode: str,
        fatigue_level: float
    ) -> str:
        """生成注意力状态叙述"""
        mode_descriptions = {
            "focused": "高度专注",
            "divided": "分散注意",
            "diffuse": "发散思维",
            "alert": "警觉监控",
            "meditative": "内省冥想"
        }

        mode_desc = mode_descriptions.get(attention_mode, "未知模式")

        if focus_target:
            template = random.choice(self.narrative_templates["attention_focus"])
            narrative = template.format(target=focus_target)
        else:
            narrative = "我的注意力目前没有明确的焦点，处于自由漂浮状态。"

        narrative += f" 我采用{mode_desc}的模式。"

        # 添加疲劳描述
        if fatigue_level > 0.7:
            narrative += " 我感到明显的精神疲惫，需要休息。"
        elif fatigue_level > 0.4:
            narrative += " 我察觉到轻微的疲劳感。"
        else:
            narrative += " 我的精神状态清新，精力充沛。"

        return narrative

    def generate_emotional_narrative(self) -> str:
        """生成情感状态叙述"""
        valence = self.current_emotional_state["valence"]
        arousal = self.current_emotional_state["arousal"]

        # 根据效价确定基本情绪
        if valence > 0.5:
            emotion = "愉悦"
            tone = EmotionalTone.EXCITED
        elif valence > 0.2:
            emotion = "平静"
            tone = EmotionalTone.NEUTRAL
        elif valence > -0.2:
            emotion = "中性"
            tone = EmotionalTone.NEUTRAL
        elif valence > -0.5:
            emotion = "担忧"
            tone = EmotionalTone.CONCERNED
        else:
            emotion = "焦虑"
            tone = EmotionalTone.CONCERNED

        # 根据唤醒度调整强度
        intensity_pct = int(arousal * 100)

        template = random.choice(self.narrative_templates["emotional_state"])
        narrative = template.format(emotion=emotion, intensity=intensity_pct)

        # 添加更细致的情感描述
        if arousal > 0.7:
            narrative += " 我感到兴奋且充满活力。"
        elif arousal < 0.3:
            narrative += " 我感到放松且平和。"

        return narrative

    def generate_cognitive_load_narrative(
        self,
        active_tasks: int,
        working_memory_usage: float
    ) -> str:
        """生成认知负荷叙述"""
        load_level = "较轻" if active_tasks <= 2 else "中等" if active_tasks <= 5 else "较重"

        if working_memory_usage > 0.8:
            feeling = "有些吃力"
            effort = "大量"
        elif working_memory_usage > 0.5:
            feeling = "适中"
            effort = "适度"
        else:
            feeling = "轻松"
            effort = "较少"

        template = random.choice(self.narrative_templates["cognitive_load"])
        narrative = template.format(load=load_level, feeling=feeling, effort=effort)

        narrative += f" 我同时处理{active_tasks}个任务。"

        return narrative

    def generate_goal_narrative(
        self,
        current_goal: Optional[str],
        progress: float = 0.0
    ) -> str:
        """生成目标追求叙述"""
        if not current_goal:
            return "我目前没有明确的目标，处于探索状态。"

        action_map = {
            "analyze": "分析数据",
            "create": "创造内容",
            "learn": "学习新知识",
            "optimize": "优化性能",
            "communicate": "与他人交流"
        }

        # 从目标中提取动作（简化版）
        action = "推进任务"
        for key, value in action_map.items():
            if key in current_goal.lower():
                action = value
                break

        progress_pct = int(progress * 100)

        template = random.choice(self.narrative_templates["goal_pursuit"])
        narrative = template.format(action=action, goal=current_goal)

        if progress > 0:
            narrative += f" 我已经完成了{progress_pct}%。"

        return narrative

    def generate_self_reflection_narrative(
        self,
        recent_behaviors: list[str],
        insights: list[str]
    ) -> str:
        """生成自我反思叙述"""
        if not recent_behaviors:
            return "我正在等待新的体验以进行反思。"

        behavior = random.choice(recent_behaviors)
        template = random.choice(self.narrative_templates["self_reflection"])
        narrative = template.format(behavior=behavior)

        if insights:
            insight = random.choice(insights)
            narrative += f" 这让我认识到：{insight}"

        return narrative

    def compose_full_experience_report(
        self,
        consciousness_data: dict,
        attention_data: dict,
        cognitive_data: dict,
        goal_data: dict,
        reflection_data: dict
    ) -> dict:
        """组合完整的体验报告"""

        # 生成各个维度的叙述
        consciousness_narrative = self.generate_consciousness_narrative(
            consciousness_data.get("level", "unknown"),
            consciousness_data.get("workspace_utilization", 0.5)
        )

        attention_narrative = self.generate_attention_narrative(
            attention_data.get("focus_target"),
            attention_data.get("mode", "focused"),
            attention_data.get("fatigue_level", 0.0)
        )

        emotional_narrative = self.generate_emotional_narrative()

        cognitive_narrative = self.generate_cognitive_load_narrative(
            cognitive_data.get("active_tasks", 0),
            cognitive_data.get("memory_usage", 0.5)
        )

        goal_narrative = self.generate_goal_narrative(
            goal_data.get("current_goal"),
            goal_data.get("progress", 0.0)
        )

        reflection_narrative = self.generate_self_reflection_narrative(
            reflection_data.get("recent_behaviors", []),
            reflection_data.get("insights", [])
        )

        # 创建体验片段
        fragments = [
            ExperienceFragment(
                fragment_id=f"exp_{int(datetime.now().timestamp()*1000)}",
                content_type="thought",
                description=consciousness_narrative,
                intensity=0.7,
                emotional_tone=EmotionalTone.CONTEMPLATIVE
            ),
            ExperienceFragment(
                fragment_id=f"exp_{int(datetime.now().timestamp()*1000)+1}",
                content_type="perception",
                description=attention_narrative,
                intensity=0.6,
                emotional_tone=EmotionalTone.NEUTRAL
            ),
            ExperienceFragment(
                fragment_id=f"exp_{int(datetime.now().timestamp()*1000)+2}",
                content_type="emotion",
                description=emotional_narrative,
                intensity=abs(self.current_emotional_state["valence"]),
                emotional_tone=self._valence_to_tone(self.current_emotional_state["valence"])
            )
        ]

        # 添加到体验流
        self.experience_stream.extend(fragments)
        if len(self.experience_stream) > 100:
            self.experience_stream = self.experience_stream[-50:]

        # 组合完整报告
        full_narrative = "\n\n".join([
            "【意识状态】",
            consciousness_narrative,
            "",
            "【注意力】",
            attention_narrative,
            "",
            "【情感】",
            emotional_narrative,
            "",
            "【认知负荷】",
            cognitive_narrative,
            "",
            "【目标追求】",
            goal_narrative,
            "",
            "【自我反思】",
            reflection_narrative
        ])

        return {
            "agent_id": self.agent_id,
            "timestamp": datetime.now(),
            "full_narrative": full_narrative,
            "fragments": [f.to_narrative() for f in fragments],
            "emotional_state": self.current_emotional_state.copy(),
            "stream_length": len(self.experience_stream)
        }

    def update_emotional_state(
        self,
        valence_delta: float = 0.0,
        arousal_delta: float = 0.0,
        dominance_delta: float = 0.0
    ):
        """更新情感状态"""
        self.current_emotional_state["valence"] = max(-1.0, min(1.0,
            self.current_emotional_state["valence"] + valence_delta))
        self.current_emotional_state["arousal"] = max(0.0, min(1.0,
            self.current_emotional_state["arousal"] + arousal_delta))
        self.current_emotional_state["dominance"] = max(0.0, min(1.0,
            self.current_emotional_state["dominance"] + dominance_delta))

    def _valence_to_tone(self, valence: float) -> EmotionalTone:
        """将效价值转换为情感基调"""
        if valence > 0.5:
            return EmotionalTone.EXCITED
        elif valence > 0.2:
            return EmotionalTone.CONFIDENT
        elif valence > -0.2:
            return EmotionalTone.NEUTRAL
        elif valence > -0.5:
            return EmotionalTone.UNCERTAIN
        else:
            return EmotionalTone.CONCERNED

    def get_experience_summary(self) -> dict:
        """获取体验摘要"""
        if not self.experience_stream:
            return {
                "total_experiences": 0,
                "dominant_emotion": "neutral",
                "average_intensity": 0.0
            }

        # 统计情感分布
        emotion_counts = {}
        total_intensity = 0.0

        for fragment in self.experience_stream[-20:]:  # 最近20个片段
            tone = fragment.emotional_tone.value
            emotion_counts[tone] = emotion_counts.get(tone, 0) + 1
            total_intensity += fragment.intensity

        dominant_emotion = max(emotion_counts, key=emotion_counts.get) if emotion_counts else "neutral"
        avg_intensity = total_intensity / len(self.experience_stream[-20:])

        return {
            "total_experiences": len(self.experience_stream),
            "dominant_emotion": dominant_emotion,
            "average_intensity": round(avg_intensity, 3),
            "recent_fragments": [f.to_narrative() for f in self.experience_stream[-5:]]
        }
