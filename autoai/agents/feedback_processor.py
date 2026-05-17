"""
外部反馈处理器 - 处理用户反馈、系统告警等外部信号，驱动目标调整
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum
from typing import Any, Callable, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)


class FeedbackType(Enum):
    USER_POSITIVE = "user_positive"
    USER_NEGATIVE = "user_negative"
    USER_SUGGESTION = "user_suggestion"
    SYSTEM_ALERT = "system_alert"
    SYSTEM_ERROR = "system_error"
    PERFORMANCE_DEGRADED = "performance_degraded"
    PERFORMANCE_IMPROVED = "performance_improved"
    EXTERNAL_EVENT = "external_event"


class FeedbackPriority(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class Feedback:
    feedback_type: FeedbackType
    priority: FeedbackPriority
    content: str
    source: str
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    processed: bool = False


@dataclass
class GoalAdjustment:
    goal_id: str
    old_priority: float
    new_priority: float
    reason: str
    feedback_id: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


class FeedbackProcessor:
    def __init__(
        self,
        max_history: int = 1000,
        positive_boost: float = 0.1,
        negative_penalty: float = 0.2,
        alert_boost: float = 0.15,
        degrade_penalty: float = 0.25,
    ):
        self.max_history = max_history
        self.positive_boost = positive_boost
        self.negative_penalty = negative_penalty
        self.alert_boost = alert_boost
        self.degrade_penalty = degrade_penalty

        self._feedback_queue: list[Feedback] = []
        self._processed: list[Feedback] = []
        self._adjustments: list[GoalAdjustment] = []
        self._goals: dict[str, float] = {}
        self._callbacks: dict[FeedbackType, list[Callable]] = defaultdict(list)
        self._feedback_count: dict[FeedbackType, int] = defaultdict(int)

    def register_goal(self, goal_id: str, initial_priority: float = 0.5) -> None:
        self._goals[goal_id] = initial_priority
        logger.debug(f"[FeedbackProcessor] Registered goal: {goal_id}={initial_priority}")

    def register_callback(self, feedback_type: FeedbackType, callback: Callable) -> None:
        self._callbacks[feedback_type].append(callback)

    def submit_feedback(
        self,
        feedback_type: FeedbackType,
        content: str,
        source: str = "unknown",
        priority: FeedbackPriority = FeedbackPriority.MEDIUM,
        metadata: dict[str, Any] | None = None,
        affected_goals: list[str] | None = None,
    ) -> Feedback:
        feedback = Feedback(
            feedback_type=feedback_type,
            priority=priority,
            content=content,
            source=source,
            metadata=metadata or {},
        )
        feedback.metadata["affected_goals"] = affected_goals or []
        self._feedback_queue.append(feedback)
        self._feedback_count[feedback_type] += 1

        if len(self._feedback_queue) > self.max_history:
            self._feedback_queue.pop(0)

        logger.info(f"[FeedbackProcessor] Received {feedback_type.value}: {content[:50]}...")
        return feedback

    def process_all(self) -> list[GoalAdjustment]:
        adjustments = []
        while self._feedback_queue:
            feedback = self._feedback_queue.pop(0)
            adjustment = self._process_single(feedback)
            if adjustment:
                adjustments.extend(adjustment)
            feedback.processed = True
            self._processed.append(feedback)
            if len(self._processed) > self.max_history:
                self._processed.pop(0)
        self._adjustments.extend(adjustments)
        return adjustments

    def _process_single(self, feedback: Feedback) -> list[GoalAdjustment]:
        adjustments = []
        affected_goals = feedback.metadata.get("affected_goals", [])
        if not affected_goals:
            affected_goals = list(self._goals.keys())

        for goal_id in affected_goals:
            if goal_id not in self._goals:
                continue

            old_priority = self._goals[goal_id]
            new_priority = old_priority
            reason = ""

            if feedback.feedback_type == FeedbackType.USER_POSITIVE:
                boost = self.positive_boost * feedback.priority.value
                new_priority = min(1.0, old_priority + boost)
                reason = "positive_user_feedback"

            elif feedback.feedback_type == FeedbackType.USER_NEGATIVE:
                penalty = self.negative_penalty * feedback.priority.value
                new_priority = max(0.0, old_priority - penalty)
                reason = "negative_user_feedback"

            elif feedback.feedback_type == FeedbackType.USER_SUGGESTION:
                boost = self.positive_boost * 0.5 * feedback.priority.value
                new_priority = min(1.0, old_priority + boost)
                reason = "user_suggestion"

            elif feedback.feedback_type == FeedbackType.SYSTEM_ALERT:
                boost = self.alert_boost * feedback.priority.value
                new_priority = min(1.0, old_priority + boost)
                reason = "system_alert"

            elif feedback.feedback_type == FeedbackType.SYSTEM_ERROR:
                penalty = self.negative_penalty * feedback.priority.value
                new_priority = max(0.0, old_priority - penalty)
                reason = "system_error"

            elif feedback.feedback_type == FeedbackType.PERFORMANCE_DEGRADED:
                penalty = self.degrade_penalty * feedback.priority.value
                new_priority = max(0.0, old_priority - penalty)
                reason = "performance_degraded"

            elif feedback.feedback_type == FeedbackType.PERFORMANCE_IMPROVED:
                boost = self.positive_boost * feedback.priority.value
                new_priority = min(1.0, old_priority + boost)
                reason = "performance_improved"

            if new_priority != old_priority:
                self._goals[goal_id] = new_priority
                adjustment = GoalAdjustment(
                    goal_id=goal_id,
                    old_priority=old_priority,
                    new_priority=new_priority,
                    reason=reason,
                    feedback_id=str(id(feedback)),
                )
                adjustments.append(adjustment)
                logger.info(
                    f"[FeedbackProcessor] Adjusted {goal_id}: {old_priority:.2f} -> {new_priority:.2f} ({reason})"
                )

        for callback in self._callbacks[feedback.feedback_type]:
            try:
                callback(feedback, adjustments)
            except Exception as e:
                logger.warning(f"[FeedbackProcessor] Callback failed: {e}")

        return adjustments

    def get_goal_priorities(self) -> dict[str, float]:
        return self._goals.copy()

    def get_top_goals(self, n: int = 5) -> list[tuple[str, float]]:
        sorted_goals = sorted(self._goals.items(), key=lambda x: x[1], reverse=True)
        return sorted_goals[:n]

    def get_statistics(self) -> dict[str, Any]:
        return {
            "total_feedback": sum(self._feedback_count.values()),
            "by_type": dict(self._feedback_count),
            "pending_count": len(self._feedback_queue),
            "processed_count": len(self._processed),
            "adjustment_count": len(self._adjustments),
            "goal_count": len(self._goals),
            "top_goals": self.get_top_goals(5),
        }

    def receive_user_rating(self, rating: int, context: str = "", goals: list[str] | None = None) -> Feedback:
        if rating >= 4:
            fb_type = FeedbackType.USER_POSITIVE
            priority = FeedbackPriority.HIGH if rating == 5 else FeedbackPriority.MEDIUM
        elif rating <= 2:
            fb_type = FeedbackType.USER_NEGATIVE
            priority = FeedbackPriority.HIGH if rating == 1 else FeedbackPriority.MEDIUM
        else:
            fb_type = FeedbackType.USER_SUGGESTION
            priority = FeedbackPriority.LOW

        return self.submit_feedback(
            feedback_type=fb_type,
            content=f"User rating: {rating}/5. {context}",
            source="user_rating",
            priority=priority,
            affected_goals=goals,
        )

    def receive_system_alert(self, alert_level: str, message: str, component: str = "") -> Feedback:
        priority_map = {
            "info": FeedbackPriority.LOW,
            "warning": FeedbackPriority.MEDIUM,
            "error": FeedbackPriority.HIGH,
            "critical": FeedbackPriority.CRITICAL,
        }
        return self.submit_feedback(
            feedback_type=FeedbackType.SYSTEM_ALERT,
            content=message,
            source=f"system:{component}",
            priority=priority_map.get(alert_level, FeedbackPriority.MEDIUM),
            metadata={"alert_level": alert_level, "component": component},
        )

    def receive_performance_metric(self, metric_name: str, current: float, baseline: float) -> Feedback:
        if current < baseline * 0.8:
            return self.submit_feedback(
                feedback_type=FeedbackType.PERFORMANCE_DEGRADED,
                content=f"{metric_name} degraded: {current:.2f} vs baseline {baseline:.2f}",
                source="performance_monitor",
                priority=FeedbackPriority.HIGH,
                metadata={"metric": metric_name, "current": current, "baseline": baseline},
            )
        elif current > baseline * 1.1:
            return self.submit_feedback(
                feedback_type=FeedbackType.PERFORMANCE_IMPROVED,
                content=f"{metric_name} improved: {current:.2f} vs baseline {baseline:.2f}",
                source="performance_monitor",
                priority=FeedbackPriority.LOW,
                metadata={"metric": metric_name, "current": current, "baseline": baseline},
            )
        return None
