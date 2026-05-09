"""
监控仪表盘 (Dashboard Monitor)

提供实时可视化界面，监控双环AI系统的运行状态。
"""

import json
import logging
import threading
import time
from datetime import UTC, datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

from ..core.event_bus import EventBus, EventTypes

logger = logging.getLogger(__name__)


@dataclass
class DashboardEvent:
    """仪表盘事件"""
    event_type: str
    source_agent: str
    timestamp: str
    payload: Dict[str, Any]
    severity: str = "info"  # "info", "warning", "error", "success"


@dataclass
class AgentStatus:
    """代理状态"""
    agent_name: str
    status: str  # "running", "stopped", "error"
    last_seen: str
    events_count: int
    error_count: int


class Dashboard:
    """监控仪表盘"""
    
    def __init__(self, event_bus: EventBus, config: Dict[str, Any]):
        """初始化仪表盘"""
        self.event_bus = event_bus
        self.config = config
        self.running = False
        
        # 事件历史
        self.event_history: List[DashboardEvent] = []
        self.max_history_size = config.get("max_history_size", 1000)
        
        # 代理状态
        self.agent_statuses: Dict[str, AgentStatus] = {}
        
        # 统计信息
        self.stats = {
            "total_events": 0,
            "events_by_type": {},
            "events_by_agent": {},
            "errors_count": 0,
            "start_time": datetime.now(UTC).isoformat()
        }
        
        # 订阅所有事件
        self._subscribe_to_events()
        
        logger.info("Dashboard initialized")
    
    def start(self):
        """启动仪表盘"""
        if self.running:
            logger.warning("Dashboard is already running")
            return
        
        self.running = True
        logger.info("Dashboard started")
        
        self._start_console_dashboard()
    
    def stop(self):
        """停止仪表盘"""
        if not self.running:
            return
        
        self.running = False
        logger.info("Dashboard stopped")
    
    def _subscribe_to_events(self):
        """订阅所有事件"""
        event_types = [
            EventTypes.ISSUE_DETECTED,
            EventTypes.DIAGNOSIS_COMPLETE,
            EventTypes.CODE_FIX_PROPOSED,
            EventTypes.HUMAN_APPROVAL_REQUIRED,
            EventTypes.APPROVAL_GRANTED,
            EventTypes.ISSUE_RESOLVED,
            EventTypes.TESTS_FAILED,
            EventTypes.DEPLOYMENT_FAILED,
            EventTypes.SKILL_CREATED,
            EventTypes.SKILL_REQUESTED,
            EventTypes.TASK_PLANNED,
            EventTypes.SKILL_COMPOSED,
            EventTypes.EXECUTION_STARTED,
            EventTypes.EXECUTION_COMPLETED,
            EventTypes.EXECUTION_FAILED,
            EventTypes.SYSTEM_STARTED,
            EventTypes.SYSTEM_STOPPED,
            EventTypes.AGENT_STARTED,
            EventTypes.AGENT_STOPPED
        ]
        
        for event_type in event_types:
            self.event_bus.subscribe(event_type, self._handle_event)
    
    def _handle_event(self, event):
        """处理事件"""
        try:
            # 创建仪表盘事件
            dashboard_event = DashboardEvent(
                event_type=event.event_type,
                source_agent=event.source_agent,
                timestamp=event.timestamp,
                payload=event.payload,
                severity=self._determine_severity(event.event_type)
            )
            
            # 添加到历史记录
            self.event_history.append(dashboard_event)
            
            # 限制历史记录大小
            if len(self.event_history) > self.max_history_size:
                self.event_history.pop(0)
            
            # 更新统计信息
            self._update_stats(dashboard_event)
            
            # 更新代理状态
            self._update_agent_status(dashboard_event)
            
            logger.debug(f"Dashboard received event: {event.event_type} from {event.source_agent}")
            
        except Exception as e:
            logger.error(f"Failed to handle dashboard event: {e}")
    
    def _determine_severity(self, event_type: str) -> str:
        """确定事件严重程度"""
        error_events = [
            EventTypes.EXECUTION_FAILED,
            EventTypes.TESTS_FAILED,
            EventTypes.DEPLOYMENT_FAILED
        ]
        
        warning_events = [
            EventTypes.HUMAN_APPROVAL_REQUIRED,
            EventTypes.SKILL_REQUESTED
        ]
        
        success_events = [
            EventTypes.EXECUTION_COMPLETED,
            EventTypes.ISSUE_RESOLVED,
            EventTypes.SKILL_CREATED,
            EventTypes.APPROVAL_GRANTED
        ]
        
        if event_type in error_events:
            return "error"
        elif event_type in warning_events:
            return "warning"
        elif event_type in success_events:
            return "success"
        else:
            return "info"
    
    def _update_stats(self, event: DashboardEvent):
        """更新统计信息"""
        self.stats["total_events"] += 1
        
        # 按事件类型统计
        event_type = event.event_type
        if event_type not in self.stats["events_by_type"]:
            self.stats["events_by_type"][event_type] = 0
        self.stats["events_by_type"][event_type] += 1
        
        # 按代理统计
        agent = event.source_agent
        if agent not in self.stats["events_by_agent"]:
            self.stats["events_by_agent"][agent] = 0
        self.stats["events_by_agent"][agent] += 1
        
        # 错误统计
        if event.severity == "error":
            self.stats["errors_count"] += 1
    
    def _update_agent_status(self, event: DashboardEvent):
        """更新代理状态"""
        agent_name = event.source_agent
        
        if agent_name not in self.agent_statuses:
            self.agent_statuses[agent_name] = AgentStatus(
                agent_name=agent_name,
                status="running",
                last_seen=event.timestamp,
                events_count=0,
                error_count=0
            )
        
        agent_status = self.agent_statuses[agent_name]
        agent_status.last_seen = event.timestamp
        agent_status.events_count += 1
        
        if event.severity == "error":
            agent_status.error_count += 1
    
    def _start_console_dashboard(self):
        """启动控制台仪表盘"""
        def run_console_dashboard():
            while self.running:
                self._print_console_dashboard()
                time.sleep(5)  # 每5秒更新一次
        
        thread = threading.Thread(target=run_console_dashboard, daemon=True)
        thread.start()
    
    def _print_console_dashboard(self):
        """打印控制台仪表盘"""
        print("\n" + "="*80)
        print("🤖 双环AI系统监控仪表盘")
        print("="*80)
        
        # 系统统计
        print(f"\n📊 系统统计:")
        print(f"   总事件数: {self.stats['total_events']}")
        print(f"   错误数: {self.stats['errors_count']}")
        print(f"   运行时间: {self._calculate_uptime()}")
        
        # 代理状态
        print(f"\n🤖 代理状态:")
        for agent_name, status in self.agent_statuses.items():
            status_icon = "🟢" if status.status == "running" else "🔴"
            print(f"   {status_icon} {agent_name}: {status.status} (事件: {status.events_count}, 错误: {status.error_count})")
        
        # 最近事件
        print(f"\n📝 最近事件:")
        recent_events = self.event_history[-5:] if self.event_history else []
        for event in reversed(recent_events):
            severity_icon = {
                "info": "ℹ️",
                "warning": "⚠️",
                "error": "❌",
                "success": "✅"
            }.get(event.severity, "ℹ️")
            
            print(f"   {severity_icon} {event.timestamp} - {event.event_type} (来自: {event.source_agent})")
        
        print("="*80)
    
    def _calculate_uptime(self) -> str:
        """计算运行时间"""
        try:
            start_time = datetime.fromisoformat(self.stats["start_time"])
            uptime = datetime.now(UTC) - start_time
            
            hours = int(uptime.total_seconds() // 3600)
            minutes = int((uptime.total_seconds() % 3600) // 60)
            seconds = int(uptime.total_seconds() % 60)
            
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        except:
            return "未知"
    
    def get_event_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """获取事件历史"""
        events = self.event_history
        if limit:
            events = events[-limit:]
        
        return [asdict(event) for event in events]
    
    def get_agent_statuses(self) -> Dict[str, Dict[str, Any]]:
        """获取代理状态"""
        return {name: asdict(status) for name, status in self.agent_statuses.items()}
    
    def get_system_stats(self) -> Dict[str, Any]:
        """获取系统统计"""
        return self.stats.copy()
    
    def clear_history(self):
        """清空历史记录"""
        self.event_history.clear()
        logger.info("Dashboard history cleared")


# 默认配置
DEFAULT_DASHBOARD_CONFIG = {
    "max_history_size": 1000,
    "update_interval": 5,  # 秒
    "enable_console": True,
    "enable_websocket": False,
    "websocket_port": 8765
}
