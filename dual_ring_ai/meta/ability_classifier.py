"""
能力归属决策框架 (Ability Classification Framework)

基于四大决策原则，帮助系统决定新能力应该：
1. 内化为"先天本能" (Innate Ability) - 修改代理核心代码
2. 掌握为"后天习得" (Acquired Skill) - 放入技能库

四大决策原则：
1. 普适性 (Universality)
2. 调用频率与开销 (Frequency & Overhead)  
3. 抽象层次 (Level of Abstraction)
4. 稳定与风险 (Stability & Risk)
"""

import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import yaml

logger = logging.getLogger(__name__)


class AbilityType(Enum):
    """能力类型枚举"""
    INNATE = "innate"      # 先天本能
    ACQUIRED = "acquired"  # 后天习得


class UniversalityLevel(Enum):
    """普适性级别"""
    UNIVERSAL = "universal"        # 所有任务都需要
    COMMON = "common"              # 大部分任务需要
    DOMAIN_SPECIFIC = "domain_specific"  # 特定领域
    TASK_SPECIFIC = "task_specific"      # 特定任务


class FrequencyLevel(Enum):
    """调用频率级别"""
    EVERY_STEP = "every_step"      # 每个思考步骤
    HIGH_FREQUENCY = "high_frequency"  # 高频调用
    MEDIUM_FREQUENCY = "medium_frequency"  # 中等频率
    LOW_FREQUENCY = "low_frequency"        # 低频调用


class AbstractionLevel(Enum):
    """抽象层次级别"""
    METACOGNITIVE = "metacognitive"  # 元认知、战略规划
    REASONING = "reasoning"           # 推理、决策
    FUNCTIONAL = "functional"         # 功能性操作
    CONCRETE = "concrete"            # 具体动作


class StabilityLevel(Enum):
    """稳定性级别"""
    PROVEN_STABLE = "proven_stable"    # 经过验证的稳定
    EXPERIMENTAL = "experimental"      # 实验性
    EVOLVING = "evolving"             # 持续演化
    UNSTABLE = "unstable"             # 不稳定


@dataclass
class AbilityAnalysis:
    """能力分析结果"""
    ability_name: str
    description: str
    universality: UniversalityLevel
    frequency: FrequencyLevel
    abstraction: AbstractionLevel
    stability: StabilityLevel
    
    # 决策分数 (0-1)
    universality_score: float
    frequency_score: float
    abstraction_score: float
    stability_score: float
    
    # 综合决策
    recommended_type: AbilityType
    confidence: float
    reasoning: str
    
    # 元数据
    analyzed_at: str = None
    analyzer_agent: str = None
    
    def __post_init__(self):
        if self.analyzed_at is None:
            self.analyzed_at = datetime.utcnow().isoformat()


@dataclass
class DecisionThresholds:
    """决策阈值配置"""
    # 普适性阈值
    universal_threshold: float = 0.8
    common_threshold: float = 0.6
    
    # 频率阈值
    every_step_threshold: float = 0.9
    high_frequency_threshold: float = 0.7
    
    # 抽象层次阈值
    metacognitive_threshold: float = 0.8
    reasoning_threshold: float = 0.6
    
    # 稳定性阈值
    proven_stable_threshold: float = 0.9
    
    # 综合决策阈值
    innate_confidence_threshold: float = 0.8
    acquired_default_threshold: float = 0.5


class AbilityClassifier:
    """能力分类器"""
    
    def __init__(self, config_path: Optional[str] = None):
        """初始化能力分类器"""
        self.thresholds = self._load_thresholds(config_path)
        self.analysis_history: List[AbilityAnalysis] = []
        
        logger.info("Ability classifier initialized")
    
    def _load_thresholds(self, config_path: Optional[str]) -> DecisionThresholds:
        """加载决策阈值配置"""
        if config_path and Path(config_path).exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = yaml.safe_load(f)
                return DecisionThresholds(**config_data.get("thresholds", {}))
            except Exception as e:
                logger.error(f"Failed to load thresholds from {config_path}: {e}")
        
        return DecisionThresholds()
    
    def analyze_ability(self, 
                       ability_name: str,
                       description: str,
                       metadata: Dict[str, Any],
                       analyzer_agent: str = "system") -> AbilityAnalysis:
        """
        分析能力并做出归属决策
        
        Args:
            ability_name: 能力名称
            description: 能力描述
            metadata: 能力元数据
            analyzer_agent: 分析代理名称
            
        Returns:
            AbilityAnalysis: 分析结果
        """
        logger.info(f"Analyzing ability: {ability_name}")
        
        # 原则一：普适性分析
        universality, universality_score = self._analyze_universality(description, metadata)
        
        # 原则二：调用频率与开销分析
        frequency, frequency_score = self._analyze_frequency(description, metadata)
        
        # 原则三：抽象层次分析
        abstraction, abstraction_score = self._analyze_abstraction(description, metadata)
        
        # 原则四：稳定性分析
        stability, stability_score = self._analyze_stability(description, metadata)
        
        # 综合决策
        recommended_type, confidence, reasoning = self._make_decision(
            universality_score, frequency_score, abstraction_score, stability_score
        )
        
        analysis = AbilityAnalysis(
            ability_name=ability_name,
            description=description,
            universality=universality,
            frequency=frequency,
            abstraction=abstraction,
            stability=stability,
            universality_score=universality_score,
            frequency_score=frequency_score,
            abstraction_score=abstraction_score,
            stability_score=stability_score,
            recommended_type=recommended_type,
            confidence=confidence,
            reasoning=reasoning,
            analyzer_agent=analyzer_agent
        )
        
        self.analysis_history.append(analysis)
        logger.info(f"Analysis complete: {ability_name} -> {recommended_type.value} (confidence: {confidence:.2f})")
        
        return analysis
    
    def _analyze_universality(self, description: str, metadata: Dict[str, Any]) -> Tuple[UniversalityLevel, float]:
        """分析普适性"""
        # 关键词匹配
        universal_keywords = [
            "memory", "planning", "reasoning", "decision", "thinking",
            "optimization", "efficiency", "cost", "budget", "resource"
        ]
        
        domain_keywords = [
            "web", "scrape", "api", "database", "file", "email",
            "chart", "report", "analysis", "test", "validate"
        ]
        
        task_keywords = [
            "specific", "custom", "unique", "particular", "specialized"
        ]
        
        description_lower = description.lower()
        
        # 计算匹配分数
        universal_matches = sum(1 for keyword in universal_keywords if keyword in description_lower)
        domain_matches = sum(1 for keyword in domain_keywords if keyword in description_lower)
        task_matches = sum(1 for keyword in task_keywords if keyword in description_lower)
        
        total_keywords = len(universal_keywords) + len(domain_keywords) + len(task_keywords)
        
        if universal_matches > 0:
            score = universal_matches / total_keywords
            if score >= self.thresholds.universal_threshold:
                return UniversalityLevel.UNIVERSAL, score
            elif score >= self.thresholds.common_threshold:
                return UniversalityLevel.COMMON, score
            else:
                return UniversalityLevel.DOMAIN_SPECIFIC, score
        elif domain_matches > 0:
            score = domain_matches / total_keywords
            return UniversalityLevel.DOMAIN_SPECIFIC, score
        else:
            return UniversalityLevel.TASK_SPECIFIC, 0.1
    
    def _analyze_frequency(self, description: str, metadata: Dict[str, Any]) -> Tuple[FrequencyLevel, float]:
        """分析调用频率"""
        # 关键词匹配
        every_step_keywords = [
            "every", "each", "step", "cycle", "iteration", "loop",
            "continuous", "ongoing", "persistent", "always"
        ]
        
        high_freq_keywords = [
            "frequent", "often", "repeated", "multiple", "batch",
            "stream", "real-time", "live", "monitor"
        ]
        
        medium_freq_keywords = [
            "periodic", "scheduled", "regular", "routine", "daily"
        ]
        
        description_lower = description.lower()
        
        # 计算匹配分数
        every_step_matches = sum(1 for keyword in every_step_keywords if keyword in description_lower)
        high_freq_matches = sum(1 for keyword in high_freq_keywords if keyword in description_lower)
        medium_freq_matches = sum(1 for keyword in medium_freq_keywords if keyword in description_lower)
        
        if every_step_matches > 0:
            score = min(1.0, every_step_matches / len(every_step_keywords))
            if score >= self.thresholds.every_step_threshold:
                return FrequencyLevel.EVERY_STEP, score
            else:
                return FrequencyLevel.HIGH_FREQUENCY, score
        elif high_freq_matches > 0:
            score = min(1.0, high_freq_matches / len(high_freq_keywords))
            return FrequencyLevel.HIGH_FREQUENCY, score
        elif medium_freq_matches > 0:
            score = min(1.0, medium_freq_matches / len(medium_freq_keywords))
            return FrequencyLevel.MEDIUM_FREQUENCY, score
        else:
            return FrequencyLevel.LOW_FREQUENCY, 0.1
    
    def _analyze_abstraction(self, description: str, metadata: Dict[str, Any]) -> Tuple[AbstractionLevel, float]:
        """分析抽象层次"""
        # 关键词匹配
        metacognitive_keywords = [
            "strategy", "planning", "optimization", "efficiency", "methodology",
            "approach", "framework", "principle", "heuristic", "meta"
        ]
        
        reasoning_keywords = [
            "reasoning", "logic", "decision", "analysis", "evaluation",
            "assessment", "judgment", "inference", "deduction"
        ]
        
        functional_keywords = [
            "process", "transform", "convert", "generate", "create",
            "build", "construct", "assemble", "compose"
        ]
        
        concrete_keywords = [
            "read", "write", "send", "receive", "download", "upload",
            "copy", "move", "delete", "execute", "run"
        ]
        
        description_lower = description.lower()
        
        # 计算匹配分数
        metacognitive_matches = sum(1 for keyword in metacognitive_keywords if keyword in description_lower)
        reasoning_matches = sum(1 for keyword in reasoning_keywords if keyword in description_lower)
        functional_matches = sum(1 for keyword in functional_keywords if keyword in description_lower)
        concrete_matches = sum(1 for keyword in concrete_keywords if keyword in description_lower)
        
        if metacognitive_matches > 0:
            score = min(1.0, metacognitive_matches / len(metacognitive_keywords))
            if score >= self.thresholds.metacognitive_threshold:
                return AbstractionLevel.METACOGNITIVE, score
            else:
                return AbstractionLevel.REASONING, score
        elif reasoning_matches > 0:
            score = min(1.0, reasoning_matches / len(reasoning_keywords))
            return AbstractionLevel.REASONING, score
        elif functional_matches > 0:
            score = min(1.0, functional_matches / len(functional_keywords))
            return AbstractionLevel.FUNCTIONAL, score
        else:
            return AbstractionLevel.CONCRETE, 0.1
    
    def _analyze_stability(self, description: str, metadata: Dict[str, Any]) -> Tuple[StabilityLevel, float]:
        """分析稳定性"""
        # 从元数据中获取稳定性信息
        version = metadata.get("version", "1.0.0")
        maturity = metadata.get("maturity", "experimental")
        test_coverage = metadata.get("test_coverage", 0.0)
        usage_count = metadata.get("usage_count", 0)
        
        # 版本号分析
        version_parts = version.split(".")
        major_version = int(version_parts[0]) if version_parts else 0
        
        # 成熟度分析
        maturity_scores = {
            "experimental": 0.2,
            "alpha": 0.4,
            "beta": 0.6,
            "stable": 0.8,
            "production": 0.9
        }
        
        maturity_score = maturity_scores.get(maturity.lower(), 0.2)
        
        # 综合稳定性评分
        version_score = min(1.0, major_version / 5.0)  # 主版本号越高越稳定
        test_score = test_coverage / 100.0  # 测试覆盖率
        usage_score = min(1.0, usage_count / 1000.0)  # 使用次数
        
        stability_score = (version_score + maturity_score + test_score + usage_score) / 4.0
        
        if stability_score >= self.thresholds.proven_stable_threshold:
            return StabilityLevel.PROVEN_STABLE, stability_score
        elif stability_score >= 0.6:
            return StabilityLevel.EVOLVING, stability_score
        elif stability_score >= 0.3:
            return StabilityLevel.EXPERIMENTAL, stability_score
        else:
            return StabilityLevel.UNSTABLE, stability_score
    
    def _make_decision(self, 
                      universality_score: float,
                      frequency_score: float,
                      abstraction_score: float,
                      stability_score: float) -> Tuple[AbilityType, float, str]:
        """综合决策"""
        # 计算各原则的权重分数
        innate_scores = []
        reasoning_parts = []
        
        # 普适性：高普适性倾向于内化
        if universality_score >= self.thresholds.universal_threshold:
            innate_scores.append(universality_score)
            reasoning_parts.append(f"高度普适({universality_score:.2f})")
        elif universality_score >= self.thresholds.common_threshold:
            innate_scores.append(universality_score * 0.7)
            reasoning_parts.append(f"较为普适({universality_score:.2f})")
        else:
            innate_scores.append(0.0)
            reasoning_parts.append(f"领域特定({universality_score:.2f})")
        
        # 频率：高频调用倾向于内化
        if frequency_score >= self.thresholds.every_step_threshold:
            innate_scores.append(frequency_score)
            reasoning_parts.append(f"每步调用({frequency_score:.2f})")
        elif frequency_score >= self.thresholds.high_frequency_threshold:
            innate_scores.append(frequency_score * 0.8)
            reasoning_parts.append(f"高频调用({frequency_score:.2f})")
        else:
            innate_scores.append(0.0)
            reasoning_parts.append(f"低频调用({frequency_score:.2f})")
        
        # 抽象层次：元认知和推理倾向于内化
        if abstraction_score >= self.thresholds.metacognitive_threshold:
            innate_scores.append(abstraction_score)
            reasoning_parts.append(f"元认知层次({abstraction_score:.2f})")
        elif abstraction_score >= self.thresholds.reasoning_threshold:
            innate_scores.append(abstraction_score * 0.6)
            reasoning_parts.append(f"推理层次({abstraction_score:.2f})")
        else:
            innate_scores.append(0.0)
            reasoning_parts.append(f"功能层次({abstraction_score:.2f})")
        
        # 稳定性：高稳定性倾向于内化
        if stability_score >= self.thresholds.proven_stable_threshold:
            innate_scores.append(stability_score)
            reasoning_parts.append(f"高度稳定({stability_score:.2f})")
        else:
            innate_scores.append(0.0)
            reasoning_parts.append(f"稳定性不足({stability_score:.2f})")
        
        # 计算综合分数
        if innate_scores:
            innate_confidence = sum(innate_scores) / len(innate_scores)
        else:
            innate_confidence = 0.0
        
        # 决策逻辑
        if innate_confidence >= self.thresholds.innate_confidence_threshold:
            decision = AbilityType.INNATE
            confidence = innate_confidence
            reasoning = f"建议内化为先天本能。理由：{', '.join(reasoning_parts)}"
        else:
            decision = AbilityType.ACQUIRED
            confidence = max(self.thresholds.acquired_default_threshold, 1.0 - innate_confidence)
            reasoning = f"建议掌握为后天习得。理由：{', '.join(reasoning_parts)}"
        
        return decision, confidence, reasoning
    
    def get_analysis_history(self) -> List[AbilityAnalysis]:
        """获取分析历史"""
        return self.analysis_history
    
    def export_analysis(self, output_path: str):
        """导出分析结果"""
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump([asdict(analysis) for analysis in self.analysis_history], 
                         f, indent=2, ensure_ascii=False)
            logger.info(f"Analysis exported to {output_path}")
        except Exception as e:
            logger.error(f"Failed to export analysis: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取分析统计"""
        if not self.analysis_history:
            return {}
        
        total = len(self.analysis_history)
        innate_count = sum(1 for a in self.analysis_history if a.recommended_type == AbilityType.INNATE)
        acquired_count = total - innate_count
        
        avg_confidence = sum(a.confidence for a in self.analysis_history) / total
        
        return {
            "total_analyses": total,
            "innate_recommendations": innate_count,
            "acquired_recommendations": acquired_count,
            "innate_percentage": (innate_count / total) * 100,
            "average_confidence": avg_confidence
        }


# 默认配置
DEFAULT_CLASSIFIER_CONFIG = {
    "thresholds": {
        "universal_threshold": 0.8,
        "common_threshold": 0.6,
        "every_step_threshold": 0.9,
        "high_frequency_threshold": 0.7,
        "metacognitive_threshold": 0.8,
        "reasoning_threshold": 0.6,
        "proven_stable_threshold": 0.9,
        "innate_confidence_threshold": 0.8,
        "acquired_default_threshold": 0.5
    }
}
