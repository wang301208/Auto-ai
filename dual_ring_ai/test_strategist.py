"""
策略师代理测试脚本

演示策略师代理的元认知功能和系统优化能力。
"""

import json
import time
import logging
from datetime import datetime
from pathlib import Path

from core.event_bus import EventBus, EventTypes
from genesis.strategist import StrategistAgent, DEFAULT_STRATEGIST_CONFIG
from dashboard.strategist_monitor import StrategistMonitor

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def create_mock_cases():
    """创建模拟的战略案例"""
    cases = [
        {
            "case_id": "case_001",
            "goal": "Scrape data from website example.com",
            "plan": {"skills": ["web_scraper", "data_processor"]},
            "result": "success",
            "execution_time": 45.2,
            "api_calls": 3,
            "cost": 0.15,
            "skill_sequence": ["web_scraper", "data_processor"]
        },
        {
            "case_id": "case_002", 
            "goal": "Analyze sales data and generate report",
            "plan": {"skills": ["data_analyzer", "report_generator"]},
            "result": "success",
            "execution_time": 120.5,
            "api_calls": 5,
            "cost": 0.35,
            "skill_sequence": ["data_analyzer", "report_generator"]
        },
        {
            "case_id": "case_003",
            "goal": "Scrape data from website blocked.com",
            "plan": {"skills": ["web_scraper"]},
            "result": "failure",
            "execution_time": 30.0,
            "api_calls": 2,
            "cost": 0.10,
            "failure_reason": "Access blocked by website",
            "skill_sequence": ["web_scraper"]
        },
        {
            "case_id": "case_004",
            "goal": "Process large dataset for machine learning",
            "plan": {"skills": ["data_processor", "ml_trainer"]},
            "result": "success",
            "execution_time": 300.0,
            "api_calls": 8,
            "cost": 0.80,
            "skill_sequence": ["data_processor", "ml_trainer"]
        },
        {
            "case_id": "case_005",
            "goal": "Scrape data from website example2.com",
            "plan": {"skills": ["web_scraper"]},
            "result": "failure",
            "execution_time": 25.0,
            "api_calls": 1,
            "cost": 0.05,
            "failure_reason": "Access blocked by website",
            "skill_sequence": ["web_scraper"]
        },
        {
            "case_id": "case_006",
            "goal": "Generate code for API integration",
            "plan": {"skills": ["code_generator", "api_tester"]},
            "result": "success",
            "execution_time": 180.0,
            "api_calls": 6,
            "cost": 0.45,
            "skill_sequence": ["code_generator", "api_tester"]
        },
        {
            "case_id": "case_007",
            "goal": "Scrape data from website example3.com",
            "plan": {"skills": ["web_scraper", "browser_simulator"]},
            "result": "success",
            "execution_time": 60.0,
            "api_calls": 4,
            "cost": 0.20,
            "skill_sequence": ["web_scraper", "browser_simulator"]
        },
        {
            "case_id": "case_008",
            "goal": "Analyze customer feedback data",
            "plan": {"skills": ["data_analyzer", "sentiment_analyzer"]},
            "result": "success",
            "execution_time": 90.0,
            "api_calls": 4,
            "cost": 0.25,
            "skill_sequence": ["data_analyzer", "sentiment_analyzer"]
        },
        {
            "case_id": "case_009",
            "goal": "Scrape data from website blocked2.com",
            "plan": {"skills": ["web_scraper"]},
            "result": "failure",
            "execution_time": 20.0,
            "api_calls": 1,
            "cost": 0.05,
            "failure_reason": "Access blocked by website",
            "skill_sequence": ["web_scraper"]
        },
        {
            "case_id": "case_010",
            "goal": "Create automated test suite",
            "plan": {"skills": ["test_generator", "test_runner"]},
            "result": "success",
            "execution_time": 150.0,
            "api_calls": 5,
            "cost": 0.30,
            "skill_sequence": ["test_generator", "test_runner"]
        }
    ]
    return cases


def simulate_task_execution(event_bus: EventBus, cases):
    """模拟任务执行，发布相关事件"""
    logger.info("开始模拟任务执行...")
    
    for case in cases:
        # 发布任务计划事件
        event_bus.publish(
            EventTypes.TASK_PLANNED,
            {
                "plan_id": case["case_id"],
                "goal": case["goal"],
                "plan": case["plan"],
                "skill_sequence": case["skill_sequence"]
            },
            "test_simulator"
        )
        
        # 等待一小段时间
        time.sleep(0.1)
        
        # 发布执行结果事件
        if case["result"] == "success":
            event_bus.publish(
                EventTypes.EXECUTION_COMPLETED,
                {
                    "plan_id": case["case_id"],
                    "execution_time": case["execution_time"],
                    "api_calls": case["api_calls"],
                    "cost": case["cost"]
                },
                "test_simulator"
            )
        else:
            event_bus.publish(
                EventTypes.EXECUTION_FAILED,
                {
                    "plan_id": case["case_id"],
                    "execution_time": case["execution_time"],
                    "api_calls": case["api_calls"],
                    "cost": case["cost"],
                    "failure_reason": case["failure_reason"]
                },
                "test_simulator"
            )
        
        time.sleep(0.1)
    
    logger.info("任务执行模拟完成")


def test_strategist_analysis():
    """测试策略师分析功能"""
    logger.info("=== 策略师代理测试 ===")
    
    # 初始化事件总线
    event_bus = EventBus()
    if not event_bus.connect():
        logger.error("无法连接到事件总线")
        return
    
    # 初始化策略师代理
    config = DEFAULT_STRATEGIST_CONFIG
    config.analysis_interval = 5  # 缩短分析间隔用于测试
    config.min_cases_for_analysis = 5  # 降低最小案例数
    
    strategist = StrategistAgent(event_bus, config)
    strategist.start()
    
    # 初始化监控组件
    monitor = StrategistMonitor(event_bus, strategist)
    monitor.start_monitoring()
    
    # 创建模拟案例
    mock_cases = create_mock_cases()
    
    # 模拟任务执行
    simulate_task_execution(event_bus, mock_cases)
    
    # 等待分析完成
    logger.info("等待策略师分析...")
    time.sleep(10)
    
    # 获取分析结果
    logger.info("\n=== 策略师分析结果 ===")
    
    # 获取知识库摘要
    knowledge_summary = strategist.get_knowledge_summary()
    print(f"总案例数: {knowledge_summary['cases_count']}")
    print(f"总原则数: {knowledge_summary['principles_count']}")
    print(f"成功率: {knowledge_summary['stats']['success_cases']}/{knowledge_summary['stats']['total_cases']}")
    
    # 获取战略洞察
    insights = strategist.get_strategic_insights()
    print(f"\n成功率: {insights.get('success_rate', 0):.2%}")
    print(f"平均执行时间: {insights.get('avg_execution_time', 0):.1f}秒")
    print(f"平均成本: ${insights.get('avg_cost', 0):.3f}")
    
    # 显示失败原因
    if insights.get('top_failure_reasons'):
        print("\n主要失败原因:")
        for reason in insights['top_failure_reasons']:
            print(f"  - {reason['reason']}: {reason['count']}次")
    
    # 显示效率建议
    if insights.get('efficiency_recommendations'):
        print("\n效率建议:")
        for rec in insights['efficiency_recommendations']:
            print(f"  - {rec}")
    
    # 获取仪表板数据
    dashboard = monitor.get_strategic_dashboard()
    print(f"\n=== 战略仪表板 ===")
    print(f"分析状态: {dashboard['optimization']['status']}")
    print(f"自动优化: {'启用' if dashboard['optimization']['auto_optimization_enabled'] else '禁用'}")
    
    # 显示原则分类
    if dashboard['principles']['categories']:
        print("\n原则分类:")
        for category, count in dashboard['principles']['categories'].items():
            print(f"  - {category}: {count}个")
    
    # 显示置信度分布
    if dashboard['principles']['confidence_distribution']:
        print("\n置信度分布:")
        dist = dashboard['principles']['confidence_distribution']
        print(f"  - 高置信度 (0.8-1.0): {dist['high']}个")
        print(f"  - 中置信度 (0.5-0.8): {dist['medium']}个")
        print(f"  - 低置信度 (0.0-0.5): {dist['low']}个")
    
    # 获取性能报告
    report = monitor.get_performance_report()
    print(f"\n=== 性能报告 ===")
    print(f"总结: {report['summary']}")
    
    if report['recommendations']:
        print("\n改进建议:")
        for rec in report['recommendations']:
            print(f"  - {rec}")
    
    # 导出知识库
    export_path = "strategist_knowledge_export.json"
    if monitor.export_knowledge_base(export_path):
        print(f"\n知识库已导出到: {export_path}")
    
    # 停止代理
    strategist.stop()
    monitor.stop_monitoring()
    event_bus.disconnect()
    
    logger.info("策略师代理测试完成")


def test_principle_extraction():
    """测试原则提取功能"""
    logger.info("=== 原则提取测试 ===")
    
    # 初始化事件总线
    event_bus = EventBus()
    if not event_bus.connect():
        logger.error("无法连接到事件总线")
        return
    
    # 初始化策略师代理
    config = DEFAULT_STRATEGIST_CONFIG
    config.analysis_interval = 3
    config.min_cases_for_analysis = 3
    
    strategist = StrategistAgent(event_bus, config)
    strategist.start()
    
    # 创建更多模拟案例来测试原则提取
    additional_cases = [
        {
            "case_id": "case_011",
            "goal": "Scrape data from website example4.com",
            "plan": {"skills": ["web_scraper", "browser_simulator"]},
            "result": "success",
            "execution_time": 55.0,
            "api_calls": 3,
            "cost": 0.18,
            "skill_sequence": ["web_scraper", "browser_simulator"]
        },
        {
            "case_id": "case_012",
            "goal": "Scrape data from website example5.com",
            "plan": {"skills": ["web_scraper", "browser_simulator"]},
            "result": "success",
            "execution_time": 65.0,
            "api_calls": 4,
            "cost": 0.22,
            "skill_sequence": ["web_scraper", "browser_simulator"]
        },
        {
            "case_id": "case_013",
            "goal": "Scrape data from website blocked3.com",
            "plan": {"skills": ["web_scraper"]},
            "result": "failure",
            "execution_time": 15.0,
            "api_calls": 1,
            "cost": 0.05,
            "failure_reason": "Access blocked by website",
            "skill_sequence": ["web_scraper"]
        }
    ]
    
    # 模拟执行
    simulate_task_execution(event_bus, additional_cases)
    
    # 等待分析
    time.sleep(8)
    
    # 检查提取的原则
    knowledge_summary = strategist.get_knowledge_summary()
    print(f"\n提取的原则:")
    for principle in knowledge_summary['top_principles']:
        print(f"  - {principle['title']}")
        print(f"    置信度: {principle['confidence']:.2f}")
        print(f"    成功率: {principle['success_rate']:.2%}")
        print(f"    证据数: {principle['evidence_count']}")
        print()
    
    strategist.stop()
    event_bus.disconnect()


if __name__ == "__main__":
    # 运行测试
    test_strategist_analysis()
    print("\n" + "="*50 + "\n")
    test_principle_extraction()
