"""
事件总线核心模块

基于Redis的发布/订阅系统，为双环AI系统提供事件驱动通信。
"""

import json
import logging
from typing import Any, Callable, Dict, Optional
from dataclasses import dataclass
from datetime import datetime

# 导入现有的event_bus实现
from autogpt.event_bus import connect, publish, subscribe
from autogpt.event_bus.message_types import EventMessage

logger = logging.getLogger(__name__)


@dataclass
class DualRingEvent:
    """双环AI系统的事件消息"""
    event_type: str
    payload: Dict[str, Any]
    source_agent: str
    timestamp: str
    correlation_id: Optional[str] = None


class EventBus:
    """双环AI系统的事件总线封装"""
    
    def __init__(self, redis_host: str = "localhost", redis_port: int = 6379, redis_db: int = 0):
        """初始化事件总线"""
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.redis_db = redis_db
        self._subscribers: Dict[str, list[Callable]] = {}
        self._connected = False
        
    def connect(self) -> bool:
        """连接到Redis"""
        try:
            connect(host=self.redis_host, port=self.redis_port, db=self.redis_db)
            self._connected = True
            logger.info(f"Connected to Redis at {self.redis_host}:{self.redis_port}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self._connected = False
            return False
    
    def publish(self, event_type: str, payload: Dict[str, Any], source_agent: str, 
                correlation_id: Optional[str] = None) -> None:
        """发布事件"""
        if not self._connected:
            logger.warning("Event bus not connected, skipping publish")
            return
            
        event = DualRingEvent(
            event_type=event_type,
            payload=payload,
            source_agent=source_agent,
            timestamp=datetime.utcnow().isoformat(),
            correlation_id=correlation_id
        )
        
        # 使用现有的publish函数
        publish(event_type, {
            "event_type": event.event_type,
            "payload": event.payload,
            "source_agent": event.source_agent,
            "timestamp": event.timestamp,
            "correlation_id": event.correlation_id
        })
        
        logger.info(f"Published event {event_type} from {source_agent}")
    
    def subscribe(self, event_type: str, handler: Callable[[DualRingEvent], None]) -> None:
        """订阅事件"""
        if not self._connected:
            logger.warning("Event bus not connected, skipping subscribe")
            return
            
        def wrapped_handler(event_message: EventMessage):
            """包装处理器以适配现有的事件消息格式"""
            dual_ring_event = DualRingEvent(
                event_type=event_message.event_type,
                payload=event_message.payload if isinstance(event_message.payload, dict) else {},
                source_agent=event_message.source_agent or "unknown",
                timestamp=event_message.timestamp
            )
            handler(dual_ring_event)
        
        # 使用现有的subscribe函数
        subscribe(event_type, wrapped_handler)
        
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)
        
        logger.info(f"Subscribed to event {event_type}")
    
    def is_connected(self) -> bool:
        """检查连接状态"""
        return self._connected


# 预定义的事件类型
class EventTypes:
    """双环AI系统的事件类型常量"""
    
    # 创世纪工厂事件
    ISSUE_DETECTED = "ISSUE_DETECTED"
    DIAGNOSIS_COMPLETE = "DIAGNOSIS_COMPLETE"
    CODE_FIX_PROPOSED = "CODE_FIX_PROPOSED"
    HUMAN_APPROVAL_REQUIRED = "HUMAN_APPROVAL_REQUIRED"
    APPROVAL_GRANTED = "APPROVAL_GRANTED"
    ISSUE_RESOLVED = "ISSUE_RESOLVED"
    TESTS_FAILED = "TESTS_FAILED"
    DEPLOYMENT_FAILED = "DEPLOYMENT_FAILED"
    
    # 执行者事件
    SKILL_CREATED = "SKILL_CREATED"
    SKILL_REQUESTED = "SKILL_REQUESTED"
    TASK_PLANNED = "TASK_PLANNED"
    SKILL_COMPOSED = "SKILL_COMPOSED"
    EXECUTION_STARTED = "EXECUTION_STARTED"
    EXECUTION_COMPLETED = "EXECUTION_COMPLETED"
    EXECUTION_FAILED = "EXECUTION_FAILED"
    
    # 系统事件
    SYSTEM_STARTED = "SYSTEM_STARTED"
    SYSTEM_STOPPED = "SYSTEM_STOPPED"
    AGENT_STARTED = "AGENT_STARTED"
    AGENT_STOPPED = "AGENT_STOPPED"
    
    # 策略师事件
    SYSTEM_OPTIMIZATION = "SYSTEM_OPTIMIZATION"
    STRATEGIC_ANALYSIS_COMPLETED = "STRATEGIC_ANALYSIS_COMPLETED"
    PRINCIPLE_EXTRACTED = "PRINCIPLE_EXTRACTED"
    KNOWLEDGE_UPDATED = "KNOWLEDGE_UPDATED"

    # 元级别（Meta）事件
    META_REFLECTION_TRIGGERED = "META_REFLECTION_TRIGGERED"
    META_TICKET_ISSUED = "META_TICKET_ISSUED"
    META_UPGRADE_APPLIED = "META_UPGRADE_APPLIED"