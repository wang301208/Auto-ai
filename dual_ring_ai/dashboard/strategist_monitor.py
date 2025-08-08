"""
策略师监控组件

提供策略师代理的实时监控和可视化界面。
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import asdict

from ..core.event_bus import EventBus, EventTypes
from ..genesis.strategist import StrategistAgent

logger = logging.getLogger(__name__)


class StrategistMonitor:
    """策略师监控组件"""
    
    def __init__(self, event_bus: EventBus, strategist: StrategistAgent):
        """初始化策略师监控"""
        self.event_bus = event_bus
        self.strategist = strategist
        self.monitoring = False
        
        # 监控数据
        self.monitor_data = {
            "last_update": None,
            "analysis_status": "idle",
            "principles_count": 0,
            "cases_count": 0,
            "success_rate": 0.0,
            "avg_execution_time": 0.0,
            "avg_cost": 0.0,
            "recent_insights": [],
            "top_principles": [],
            "failure_trends": [],
            "efficiency_metrics": {}
        }
        
        # 订阅策略师事件
        self._subscribe_to_events()
        
        logger.info("Strategist monitor initialized")
    
    def _subscribe_to_events(self):
        """订阅策略师相关事件"""
        self.event_bus.subscribe(EventTypes.STRATEGIC_ANALYSIS_COMPLETED, self._on_analysis_completed)
        self.event_bus.subscribe(EventTypes.PRINCIPLE_EXTRACTED, self._on_principle_extracted)
        self.event_bus.subscribe(EventTypes.KNOWLEDGE_UPDATED, self._on_knowledge_updated)
        self.event_bus.subscribe(EventTypes.SYSTEM_OPTIMIZATION, self._on_system_optimization)
        
        logger.info("Strategist monitor subscribed to events")
    
    def start_monitoring(self):
        """开始监控"""
        self.monitoring = True
        self._update_monitor_data()
        logger.info("Strategist monitoring started")
    
    def stop_monitoring(self):
        """停止监控"""
        self.monitoring = False
        logger.info("Strategist monitoring stopped")
    
    def _on_analysis_completed(self, event):
        """处理分析完成事件"""
        try:
            payload = event.payload
            self.monitor_data["analysis_status"] = "completed"
            self.monitor_data["last_update"] = datetime.utcnow().isoformat()
            
            # 更新分析结果
            if "new_principles_count" in payload:
                self.monitor_data["principles_count"] += payload["new_principles_count"]
            
            if "insights" in payload:
                self.monitor_data["recent_insights"].append({
                    "timestamp": datetime.utcnow().isoformat(),
                    "insights": payload["insights"]
                })
                # 保持最近10个洞察
                self.monitor_data["recent_insights"] = self.monitor_data["recent_insights"][-10:]
            
            logger.info("Analysis completed, monitor data updated")
            
        except Exception as e:
            logger.error(f"Error processing analysis completed event: {e}")
    
    def _on_principle_extracted(self, event):
        """处理原则提取事件"""
        try:
            payload = event.payload
            principle = payload.get("principle", {})
            
            self.monitor_data["top_principles"].append({
                "title": principle.get("title", ""),
                "confidence": principle.get("confidence", 0.0),
                "category": principle.get("category", ""),
                "extracted_at": datetime.utcnow().isoformat()
            })
            
            # 保持最近20个原则
            self.monitor_data["top_principles"] = self.monitor_data["top_principles"][-20:]
            
            logger.info(f"New principle extracted: {principle.get('title', 'Unknown')}")
            
        except Exception as e:
            logger.error(f"Error processing principle extracted event: {e}")
    
    def _on_knowledge_updated(self, event):
        """处理知识库更新事件"""
        try:
            payload = event.payload
            self.monitor_data["cases_count"] = payload.get("total_cases", 0)
            self.monitor_data["principles_count"] = payload.get("total_principles", 0)
            self.monitor_data["last_update"] = datetime.utcnow().isoformat()
            
            logger.info("Knowledge base updated")
            
        except Exception as e:
            logger.error(f"Error processing knowledge updated event: {e}")
    
    def _on_system_optimization(self, event):
        """处理系统优化事件"""
        try:
            payload = event.payload
            self.monitor_data["analysis_status"] = "optimizing"
            
            # 记录优化信息
            optimization_info = {
                "timestamp": datetime.utcnow().isoformat(),
                "principles_count": payload.get("principles_count", 0),
                "confidence_threshold": payload.get("confidence_threshold", 0.0)
            }
            
            if "recent_optimizations" not in self.monitor_data:
                self.monitor_data["recent_optimizations"] = []
            
            self.monitor_data["recent_optimizations"].append(optimization_info)
            self.monitor_data["recent_optimizations"] = self.monitor_data["recent_optimizations"][-5:]
            
            logger.info(f"System optimization applied with {payload.get('principles_count', 0)} principles")
            
        except Exception as e:
            logger.error(f"Error processing system optimization event: {e}")
    
    def _update_monitor_data(self):
        """更新监控数据"""
        try:
            # 获取策略师知识库摘要
            knowledge_summary = self.strategist.get_knowledge_summary()
            
            # 获取战略洞察
            strategic_insights = self.strategist.get_strategic_insights()
            
            # 更新监控数据
            self.monitor_data.update({
                "last_update": datetime.utcnow().isoformat(),
                "principles_count": knowledge_summary.get("principles_count", 0),
                "cases_count": knowledge_summary.get("cases_count", 0),
                "success_rate": strategic_insights.get("success_rate", 0.0),
                "avg_execution_time": strategic_insights.get("avg_execution_time", 0.0),
                "avg_cost": strategic_insights.get("avg_cost", 0.0),
                "top_principles": knowledge_summary.get("top_principles", []),
                "failure_trends": strategic_insights.get("top_failure_reasons", []),
                "efficiency_metrics": {
                    "avg_time": strategic_insights.get("avg_execution_time", 0.0),
                    "avg_cost": strategic_insights.get("avg_cost", 0.0),
                    "recommendations": strategic_insights.get("efficiency_recommendations", [])
                }
            })
            
        except Exception as e:
            logger.error(f"Error updating monitor data: {e}")
    
    def get_monitor_data(self) -> Dict[str, Any]:
        """获取监控数据"""
        self._update_monitor_data()
        return self.monitor_data
    
    def get_strategic_dashboard(self) -> Dict[str, Any]:
        """获取战略仪表板数据"""
        try:
            # 获取基础监控数据
            monitor_data = self.get_monitor_data()
            
            # 构建仪表板数据
            dashboard = {
                "overview": {
                    "total_cases": monitor_data["cases_count"],
                    "total_principles": monitor_data["principles_count"],
                    "success_rate": f"{monitor_data['success_rate']:.2%}",
                    "avg_execution_time": f"{monitor_data['avg_execution_time']:.1f}s",
                    "avg_cost": f"${monitor_data['avg_cost']:.3f}",
                    "last_analysis": monitor_data.get("last_update", "Never")
                },
                "principles": {
                    "top_principles": monitor_data["top_principles"],
                    "categories": self._get_principle_categories(),
                    "confidence_distribution": self._get_confidence_distribution()
                },
                "performance": {
                    "failure_trends": monitor_data["failure_trends"],
                    "efficiency_metrics": monitor_data["efficiency_metrics"],
                    "recent_insights": monitor_data["recent_insights"]
                },
                "optimization": {
                    "status": monitor_data["analysis_status"],
                    "recent_optimizations": monitor_data.get("recent_optimizations", []),
                    "auto_optimization_enabled": self.strategist.config.enable_auto_optimization
                }
            }
            
            return dashboard
            
        except Exception as e:
            logger.error(f"Error generating strategic dashboard: {e}")
            return {"error": str(e)}
    
    def _get_principle_categories(self) -> Dict[str, int]:
        """获取原则分类统计"""
        categories = {}
        for principle in self.strategist.principles:
            category = principle.category
            categories[category] = categories.get(category, 0) + 1
        return categories
    
    def _get_confidence_distribution(self) -> Dict[str, int]:
        """获取置信度分布"""
        distribution = {
            "high": 0,    # 0.8-1.0
            "medium": 0,  # 0.5-0.8
            "low": 0      # 0.0-0.5
        }
        
        for principle in self.strategist.principles:
            confidence = principle.confidence
            if confidence >= 0.8:
                distribution["high"] += 1
            elif confidence >= 0.5:
                distribution["medium"] += 1
            else:
                distribution["low"] += 1
        
        return distribution
    
    def get_performance_report(self) -> Dict[str, Any]:
        """获取性能报告"""
        try:
            insights = self.strategist.get_strategic_insights()
            
            report = {
                "summary": {
                    "total_cases": self.strategist.stats["total_cases"],
                    "success_rate": f"{insights.get('success_rate', 0):.2%}",
                    "avg_execution_time": f"{insights.get('avg_execution_time', 0):.1f}s",
                    "avg_cost": f"${insights.get('avg_cost', 0):.3f}"
                },
                "trends": {
                    "failure_reasons": insights.get("top_failure_reasons", []),
                    "efficiency_recommendations": insights.get("efficiency_recommendations", [])
                },
                "recommendations": self._generate_recommendations(insights)
            }
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating performance report: {e}")
            return {"error": str(e)}
    
    def _generate_recommendations(self, insights: Dict[str, Any]) -> List[str]:
        """生成改进建议"""
        recommendations = []
        
        # 基于成功率的建议
        success_rate = insights.get("success_rate", 0)
        if success_rate < 0.7:
            recommendations.append("Success rate is below 70%. Consider reviewing failure patterns and improving error handling.")
        
        # 基于执行时间的建议
        avg_time = insights.get("avg_execution_time", 0)
        if avg_time > 60:
            recommendations.append(f"Average execution time is {avg_time:.1f}s. Consider optimizing long-running tasks.")
        
        # 基于成本的建议
        avg_cost = insights.get("avg_cost", 0)
        if avg_cost > 1.0:
            recommendations.append(f"Average cost is ${avg_cost:.3f}. Consider cost optimization strategies.")
        
        # 基于失败原因的建议
        failure_reasons = insights.get("top_failure_reasons", [])
        if failure_reasons:
            top_reason = failure_reasons[0]
            recommendations.append(f"Most common failure: '{top_reason['reason']}' ({top_reason['count']} times). Consider implementing specific recovery strategies.")
        
        return recommendations
    
    def export_knowledge_base(self, file_path: str) -> bool:
        """导出知识库"""
        try:
            export_data = {
                "export_timestamp": datetime.utcnow().isoformat(),
                "strategist_config": asdict(self.strategist.config),
                "knowledge_summary": self.strategist.get_knowledge_summary(),
                "strategic_insights": self.strategist.get_strategic_insights(),
                "monitor_data": self.monitor_data
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Knowledge base exported to {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error exporting knowledge base: {e}")
            return False
