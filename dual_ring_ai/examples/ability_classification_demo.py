"""
能力归属决策框架演示脚本

展示如何使用四大决策原则来评估新能力应该内化为"先天本能"还是掌握为"后天习得"。
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any

from ..meta.ability_classifier import (
    AbilityClassifier, AbilityAnalysis, AbilityType,
    UniversalityLevel, FrequencyLevel, AbstractionLevel, StabilityLevel
)

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def create_sample_abilities() -> Dict[str, Dict[str, Any]]:
    """创建示例能力数据"""
    return {
        "memory_optimizer": {
            "name": "memory_optimizer",
            "description": "Optimize memory usage and reduce token costs by compressing and summarizing long-term memory",
            "metadata": {
                "version": "2.1.0",
                "maturity": "stable",
                "test_coverage": 95.0,
                "usage_count": 1500,
                "category": "core_optimization"
            }
        },
        "web_scraper": {
            "name": "web_scraper",
            "description": "Scrape data from websites using various methods including Selenium and requests",
            "metadata": {
                "version": "1.0.0",
                "maturity": "experimental",
                "test_coverage": 60.0,
                "usage_count": 200,
                "category": "data_collection"
            }
        },
        "strategic_planner": {
            "name": "strategic_planner",
            "description": "Analyze task patterns and develop strategic planning methodologies for complex problem solving",
            "metadata": {
                "version": "3.0.0",
                "maturity": "production",
                "test_coverage": 98.0,
                "usage_count": 3000,
                "category": "metacognition"
            }
        },
        "email_sender": {
            "name": "email_sender",
            "description": "Send emails with attachments and formatted content using SMTP",
            "metadata": {
                "version": "1.2.0",
                "maturity": "beta",
                "test_coverage": 80.0,
                "usage_count": 500,
                "category": "communication"
            }
        },
        "reasoning_engine": {
            "name": "reasoning_engine",
            "description": "Advanced logical reasoning and decision-making engine that processes every thinking step",
            "metadata": {
                "version": "4.0.0",
                "maturity": "production",
                "test_coverage": 99.0,
                "usage_count": 5000,
                "category": "core_reasoning"
            }
        },
        "file_processor": {
            "name": "file_processor",
            "description": "Process and transform files between different formats like CSV, JSON, XML",
            "metadata": {
                "version": "1.5.0",
                "maturity": "stable",
                "test_coverage": 85.0,
                "usage_count": 800,
                "category": "data_processing"
            }
        },
        "cost_analyzer": {
            "name": "cost_analyzer",
            "description": "Monitor and analyze API usage costs to optimize budget allocation across all operations",
            "metadata": {
                "version": "2.0.0",
                "maturity": "stable",
                "test_coverage": 90.0,
                "usage_count": 1200,
                "category": "resource_management"
            }
        },
        "task_decomposer": {
            "name": "task_decomposer",
            "description": "Break down complex tasks into manageable subtasks using hierarchical planning",
            "metadata": {
                "version": "2.3.0",
                "maturity": "production",
                "test_coverage": 92.0,
                "usage_count": 2500,
                "category": "planning"
            }
        }
    }


def analyze_abilities(classifier: AbilityClassifier, abilities: Dict[str, Dict[str, Any]]) -> Dict[str, AbilityAnalysis]:
    """分析所有能力"""
    results = {}
    
    logger.info("开始分析能力归属...")
    logger.info("=" * 80)
    
    for ability_id, ability_data in abilities.items():
        logger.info(f"\n分析能力: {ability_data['name']}")
        logger.info(f"描述: {ability_data['description']}")
        
        analysis = classifier.analyze_ability(
            ability_name=ability_data['name'],
            description=ability_data['description'],
            metadata=ability_data['metadata'],
            analyzer_agent="demo"
        )
        
        results[ability_id] = analysis
        
        # 打印分析结果
        print_analysis_result(analysis)
    
    return results


def print_analysis_result(analysis: AbilityAnalysis):
    """打印分析结果"""
    print(f"\n{'='*60}")
    print(f"能力名称: {analysis.ability_name}")
    print(f"建议类型: {analysis.recommended_type.value}")
    print(f"置信度: {analysis.confidence:.2f}")
    print(f"\n四大原则分析:")
    print(f"  普适性: {analysis.universality.value} ({analysis.universality_score:.2f})")
    print(f"  调用频率: {analysis.frequency.value} ({analysis.frequency_score:.2f})")
    print(f"  抽象层次: {analysis.abstraction.value} ({analysis.abstraction_score:.2f})")
    print(f"  稳定性: {analysis.stability.value} ({analysis.stability_score:.2f})")
    print(f"\n决策理由: {analysis.reasoning}")
    print(f"{'='*60}")


def print_summary_statistics(classifier: AbilityClassifier, results: Dict[str, AbilityAnalysis]):
    """打印统计摘要"""
    stats = classifier.get_statistics()
    
    print(f"\n{'='*80}")
    print("能力归属决策统计摘要")
    print(f"{'='*80}")
    print(f"总分析数: {stats['total_analyses']}")
    print(f"建议内化: {stats['innate_recommendations']} ({stats['innate_percentage']:.1f}%)")
    print(f"建议技能化: {stats['acquired_recommendations']}")
    print(f"平均置信度: {stats['average_confidence']:.2f}")
    
    # 按类型分组显示
    innate_abilities = [name for name, result in results.items() if result.recommended_type == AbilityType.INNATE]
    acquired_abilities = [name for name, result in results.items() if result.recommended_type == AbilityType.ACQUIRED]
    
    print(f"\n建议内化为先天本能的能力:")
    for ability in innate_abilities:
        result = results[ability]
        print(f"  - {result.ability_name} (置信度: {result.confidence:.2f})")
    
    print(f"\n建议掌握为后天习得的能力:")
    for ability in acquired_abilities:
        result = results[ability]
        print(f"  - {result.ability_name} (置信度: {result.confidence:.2f})")


def demonstrate_decision_principles():
    """演示四大决策原则"""
    print(f"\n{'='*80}")
    print("四大决策原则详解")
    print(f"{'='*80}")
    
    principles = {
        "普适性 (Universality)": {
            "description": "这个新能力是否是所有或绝大多数任务在底层都需要用到的基础能力？",
            "innate_criteria": "高度普适，所有任务都需要",
            "acquired_criteria": "领域相关，特定场景使用",
            "example": "内存优化器 vs 网页抓取器"
        },
        "调用频率与开销 (Frequency & Overhead)": {
            "description": "在一个典型的任务流程中，这个能力被调用的频率有多高？",
            "innate_criteria": "每个思考步骤都调用，高频调用",
            "acquired_criteria": "任务流程中只调用几次",
            "example": "推理引擎 vs 邮件发送器"
        },
        "抽象层次 (Level of Abstraction)": {
            "description": "这个新能力是改变了代理'如何做事'还是'如何思考'？",
            "innate_criteria": "元认知、战略规划、学习方法论",
            "acquired_criteria": "具体的功能性动作",
            "example": "战略规划器 vs 文件处理器"
        },
        "稳定与风险 (Stability & Risk)": {
            "description": "这个新能力是否已经完全成熟、稳定？",
            "innate_criteria": "经过千锤百炼、绝对稳定可靠",
            "acquired_criteria": "实验性、需要频繁迭代",
            "example": "生产级推理引擎 vs 实验性网页抓取器"
        }
    }
    
    for principle, details in principles.items():
        print(f"\n{principle}")
        print(f"  描述: {details['description']}")
        print(f"  内化条件: {details['innate_criteria']}")
        print(f"  技能化条件: {details['acquired_criteria']}")
        print(f"  示例: {details['example']}")


def run_demo():
    """运行演示"""
    print("能力归属决策框架演示")
    print("=" * 80)
    print("基于四大决策原则，帮助系统决定新能力应该内化为'先天本能'还是掌握为'后天习得'")
    print("=" * 80)
    
    # 创建能力分类器
    classifier = AbilityClassifier()
    
    # 创建示例能力
    abilities = create_sample_abilities()
    
    # 演示决策原则
    demonstrate_decision_principles()
    
    # 分析能力
    results = analyze_abilities(classifier, abilities)
    
    # 打印统计摘要
    print_summary_statistics(classifier, results)
    
    # 导出分析结果
    output_path = "ability_analysis_results.json"
    classifier.export_analysis(output_path)
    print(f"\n分析结果已导出到: {output_path}")
    
    # 显示决策框架的优势
    print(f"\n{'='*80}")
    print("决策框架的优势")
    print(f"{'='*80}")
    print("1. 客观性: 基于明确的四大原则，避免主观判断")
    print("2. 可解释性: 每个决策都有详细的分析理由")
    print("3. 可配置性: 阈值可以根据系统需求调整")
    print("4. 安全性: 高风险的内化操作需要人工审批")
    print("5. 可监控性: 可以跟踪决策效果和影响")
    print("6. 可回滚性: 支持对失败进化的回滚机制")


if __name__ == "__main__":
    run_demo()
