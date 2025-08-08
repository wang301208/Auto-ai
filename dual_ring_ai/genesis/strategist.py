"""
策略师代理 (Strategist Agent) - 大脑的大脑

这是一个元认知（Metacognition）代理，专门负责观察、反思和优化整个系统解决问题的"方法论"。
它不参与任何具体任务的执行，而是专注于系统级别的战略优化。
"""

import json
import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict, Counter
import sqlite3
from pathlib import Path

from ..core.event_bus import EventBus, EventTypes, DualRingEvent
from ..meta import (
    MetaSkillRegistry,
    MetaTicketStore,
    MetaTicket,
    ApprovalGate,
    ApprovalRequest,
)

logger = logging.getLogger(__name__)


@dataclass
class StrategicCase:
    """战略案例 - 记录一个完整的任务执行周期"""
    case_id: str
    goal: str
    plan: Dict[str, Any]
    result: str  # "success", "failure", "partial"
    execution_time: float
    api_calls: int
    cost: float
    failure_reason: Optional[str] = None
    skill_sequence: List[str] = None
    created_at: str = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow().isoformat()
        if self.skill_sequence is None:
            self.skill_sequence = []


@dataclass
class StrategicPrinciple:
    """战略原则 - 从案例分析中提炼出的指导方针"""
    principle_id: str
    title: str
    description: str
    category: str  # "planning", "execution", "optimization", "recovery"
    confidence: float  # 0.0 - 1.0
    evidence_count: int
    success_rate: float
    created_at: str = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow().isoformat()


@dataclass
class StrategistConfig:
    """策略师代理配置"""
    analysis_interval: int = 3600  # 分析间隔（秒）
    min_cases_for_analysis: int = 10  # 最少案例数才开始分析
    confidence_threshold: float = 0.7  # 置信度阈值
    max_principles: int = 20  # 最大原则数量
    database_path: str = "strategist_knowledge.db"
    enable_auto_optimization: bool = True
    workspace_path: str = "workspace"
    meta_store_file: str = "meta/meta_skill.json"
    meta_ticket_dir: str = "meta/tickets"
    approval_dir: str = "meta/approvals"


DEFAULT_STRATEGIST_CONFIG = StrategistConfig()


class StrategistAgent:
    """策略师代理 - 元认知大脑"""
    
    def __init__(self, event_bus: EventBus, config: StrategistConfig = DEFAULT_STRATEGIST_CONFIG):
        """初始化策略师代理"""
        self.event_bus = event_bus
        self.config = config
        self.running = False
        self.analysis_thread = None
        
        # 知识库
        self.cases: List[StrategicCase] = []
        self.principles: List[StrategicPrinciple] = []
        
        # 实时统计
        self.stats = {
            "total_cases": 0,
            "success_cases": 0,
            "failure_cases": 0,
            "avg_execution_time": 0.0,
            "avg_cost": 0.0,
            "last_analysis": None
        }
        
        # 初始化数据库
        self._init_database()
        
        # 订阅关键事件
        self._subscribe_to_events()

        # 初始化元技能与审批
        workspace = Path(self.config.workspace_path)
        self.meta_registry = MetaSkillRegistry(workspace / self.config.meta_store_file)
        self.ticket_store = MetaTicketStore(workspace / self.config.meta_ticket_dir)
        self.approval_gate = ApprovalGate(workspace / self.config.approval_dir)
        
        logger.info("Strategist agent initialized")
    
    def _init_database(self):
        """初始化知识库数据库"""
        self.db_path = Path(self.config.database_path)
        self.db_path.parent.mkdir(exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS strategic_cases (
                    case_id TEXT PRIMARY KEY,
                    goal TEXT,
                    plan TEXT,
                    result TEXT,
                    execution_time REAL,
                    api_calls INTEGER,
                    cost REAL,
                    failure_reason TEXT,
                    skill_sequence TEXT,
                    created_at TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS strategic_principles (
                    principle_id TEXT PRIMARY KEY,
                    title TEXT,
                    description TEXT,
                    category TEXT,
                    confidence REAL,
                    evidence_count INTEGER,
                    success_rate REAL,
                    created_at TEXT
                )
            """)
            
            conn.commit()
    
    def _subscribe_to_events(self):
        """订阅关键事件"""
        # 任务开始事件
        self.event_bus.subscribe(EventTypes.TASK_PLANNED, self._on_task_planned)
        
        # 执行完成事件
        self.event_bus.subscribe(EventTypes.EXECUTION_COMPLETED, self._on_execution_completed)
        self.event_bus.subscribe(EventTypes.EXECUTION_FAILED, self._on_execution_failed)
        
        # 创世纪工单事件
        self.event_bus.subscribe(EventTypes.ISSUE_DETECTED, self._on_issue_detected)
        self.event_bus.subscribe(EventTypes.ISSUE_RESOLVED, self._on_issue_resolved)
        
        logger.info("Strategist subscribed to key events")
    
    def start(self):
        """启动策略师代理"""
        if self.running:
            logger.warning("Strategist agent is already running")
            return
        
        self.running = True
        
        # 启动分析线程
        self.analysis_thread = threading.Thread(target=self._analysis_loop, daemon=True)
        self.analysis_thread.start()
        
        # 加载历史数据
        self._load_historical_data()
        
        logger.info("Strategist agent started")
    
    def stop(self):
        """停止策略师代理"""
        self.running = False
        if self.analysis_thread:
            self.analysis_thread.join(timeout=5)
        logger.info("Strategist agent stopped")
    
    def _load_historical_data(self):
        """加载历史数据"""
        with sqlite3.connect(self.db_path) as conn:
            # 加载案例
            cursor = conn.execute("SELECT * FROM strategic_cases ORDER BY created_at DESC LIMIT 1000")
            for row in cursor.fetchall():
                case = StrategicCase(
                    case_id=row[0],
                    goal=row[1],
                    plan=json.loads(row[2]) if row[2] else {},
                    result=row[3],
                    execution_time=row[4],
                    api_calls=row[5],
                    cost=row[6],
                    failure_reason=row[7],
                    skill_sequence=json.loads(row[8]) if row[8] else [],
                    created_at=row[9]
                )
                self.cases.append(case)
            
            # 加载原则
            cursor = conn.execute("SELECT * FROM strategic_principles ORDER BY created_at DESC")
            for row in cursor.fetchall():
                principle = StrategicPrinciple(
                    principle_id=row[0],
                    title=row[1],
                    description=row[2],
                    category=row[3],
                    confidence=row[4],
                    evidence_count=row[5],
                    success_rate=row[6],
                    created_at=row[7]
                )
                self.principles.append(principle)
        
        self._update_stats()
        logger.info(f"Loaded {len(self.cases)} cases and {len(self.principles)} principles")
    
    def _analysis_loop(self):
        """分析循环 - 后台持续运行"""
        while self.running:
            try:
                time.sleep(self.config.analysis_interval)
                
                if len(self.cases) >= self.config.min_cases_for_analysis:
                    logger.info("Starting strategic analysis...")
                    self._perform_strategic_analysis()
                    self._update_executor_prompts()
                    self.stats["last_analysis"] = datetime.utcnow().isoformat()

                # 周期性触发元反思
                self._maybe_trigger_meta_reflection()
                    
            except Exception as e:
                logger.error(f"Error in analysis loop: {e}")

    # ------------------------------------------------------------------
    # Meta reflection
    # ------------------------------------------------------------------
    def _maybe_trigger_meta_reflection(self) -> None:
        """Trigger meta-cognitive reflection and possibly issue a meta-ticket."""
        if len(self.cases) < max(20, self.config.min_cases_for_analysis):
            return

        self.event_bus.publish(
            EventTypes.META_REFLECTION_TRIGGERED,
            {"timestamp": datetime.utcnow().isoformat()},
            "strategist",
        )

        try:
            kpis = self._compute_kpis()
            if self._needs_meta_upgrade(kpis):
                self._issue_meta_ticket(kpis)
        except Exception as exc:
            logger.error("Meta reflection failed: %s", exc)

    def _compute_kpis(self) -> Dict[str, Any]:
        """Compute KPIs for strategist performance."""
        now = datetime.utcnow()
        one_month_ago = now - timedelta(days=30)

        recent = [
            c for c in self.cases if datetime.fromisoformat(c.created_at) >= one_month_ago
        ]
        if not recent:
            return {"recent_cases": 0}

        # First-attempt success rate: success cases with api_calls <= median of successes
        first_attempt_success = sum(1 for c in recent if c.result == "success") / len(recent)

        # Category-level blind spot: categories with success rate < 0.2 and >= 5 attempts
        category_stats: Dict[str, list[bool]] = {}
        for c in recent:
            cat = self._categorize_task(c.goal)
            category_stats.setdefault(cat, []).append(c.result == "success")
        blind_spots = [
            cat
            for cat, outcomes in category_stats.items()
            if len(outcomes) >= 5 and (sum(outcomes) / len(outcomes)) < 0.2
        ]

        return {
            "recent_cases": len(recent),
            "first_attempt_success": first_attempt_success,
            "blind_spots": blind_spots,
        }

    def _needs_meta_upgrade(self, kpis: Dict[str, Any]) -> bool:
        if kpis.get("recent_cases", 0) < 20:
            return False
        if kpis.get("first_attempt_success", 1.0) < 0.5:
            return True
        if kpis.get("blind_spots"):
            return True
        return False

    def _issue_meta_ticket(self, kpis: Dict[str, Any]) -> None:
        current = self.meta_registry.load()
        ticket_id = f"meta_{int(time.time())}"
        title = "Request upgrade of MetaSkill_StrategyEvolution"
        description = (
            "当前战略分析模型在最近周期的关键指标显示瓶颈。"
            f" 首次成功率={kpis.get('first_attempt_success', 0):.2f}，盲点类别={kpis.get('blind_spots', [])}. "
            "请求研究更先进的因果推断、反事实推理或贝叶斯方法，并升级核心逻辑。"
        )

        ticket = MetaTicket(
            ticket_id=ticket_id,
            created_at=datetime.utcnow().isoformat(),
            title=title,
            description=description,
            current_version=current.version,
        )
        path = self.ticket_store.create(ticket)

        # Emit event for the broader system
        self.event_bus.publish(
            EventTypes.META_TICKET_ISSUED,
            {
                "ticket_id": ticket.ticket_id,
                "title": ticket.title,
                "path": str(path),
            },
            "strategist",
        )

        # Request human approval for proposed version bump to v1.1
        proposed_version = "v1.1"
        approval_req = ApprovalRequest(
            ticket_id=ticket.ticket_id,
            meta_current_version=current.version,
            meta_proposed_version=proposed_version,
            created_at=datetime.utcnow().isoformat(),
        )
        self.approval_gate.request(approval_req)

        # Non-blocking check: if already approved, apply immediately
        status = self.approval_gate.check(ticket.ticket_id)
        if status == "approved":
            self._apply_meta_upgrade(ticket.ticket_id, proposed_version)
    
    def _on_task_planned(self, event: DualRingEvent):
        """处理任务计划事件"""
        try:
            payload = event.payload
            case_id = payload.get("plan_id", f"plan_{int(time.time())}")
            
            # 创建新的战略案例
            case = StrategicCase(
                case_id=case_id,
                goal=payload.get("goal", ""),
                plan=payload.get("plan", {}),
                result="pending",
                execution_time=0.0,
                api_calls=0,
                cost=0.0,
                skill_sequence=payload.get("skill_sequence", [])
            )
            
            # 临时存储，等待执行结果
            self._pending_cases = getattr(self, '_pending_cases', {})
            self._pending_cases[case_id] = case
            
        except Exception as e:
            logger.error(f"Error processing task planned event: {e}")
    
    def _on_execution_completed(self, event: DualRingEvent):
        """处理执行完成事件"""
        try:
            payload = event.payload
            case_id = payload.get("plan_id")
            
            if case_id in getattr(self, '_pending_cases', {}):
                case = self._pending_cases[case_id]
                case.result = "success"
                case.execution_time = payload.get("execution_time", 0.0)
                case.api_calls = payload.get("api_calls", 0)
                case.cost = payload.get("cost", 0.0)
                
                self._save_case(case)
                del self._pending_cases[case_id]
                
        except Exception as e:
            logger.error(f"Error processing execution completed event: {e}")
    
    def _on_execution_failed(self, event: DualRingEvent):
        """处理执行失败事件"""
        try:
            payload = event.payload
            case_id = payload.get("plan_id")
            
            if case_id in getattr(self, '_pending_cases', {}):
                case = self._pending_cases[case_id]
                case.result = "failure"
                case.execution_time = payload.get("execution_time", 0.0)
                case.api_calls = payload.get("api_calls", 0)
                case.cost = payload.get("cost", 0.0)
                case.failure_reason = payload.get("failure_reason", "Unknown error")
                
                self._save_case(case)
                del self._pending_cases[case_id]
                
        except Exception as e:
            logger.error(f"Error processing execution failed event: {e}")
    
    def _on_issue_detected(self, event: DualRingEvent):
        """处理问题检测事件"""
        try:
            payload = event.payload
            issue_type = payload.get("issue_type", "unknown")
            
            # 记录工具缺陷相关的失败
            if issue_type in ["tool_defect", "skill_defect", "plugin_defect"]:
                logger.info(f"Tool defect detected: {payload.get('description', 'Unknown')}")
                
        except Exception as e:
            logger.error(f"Error processing issue detected event: {e}")

    def _apply_meta_upgrade(self, ticket_id: str, new_version: str) -> None:
        """Apply approved meta upgrade by loading proposed content stub and persisting.

        In this initial implementation we keep content evolution external; when the
        architect approves, they should place a file named `<ticket_id>.content.md`
        under the approval directory containing the upgraded methodology text.
        """
        try:
            workspace = Path(self.config.workspace_path)
            content_path = workspace / self.config.approval_dir / f"{ticket_id}.content.md"
            if not content_path.exists():
                logger.warning("Approved but no content file found: %s", content_path)
                return
            new_content = content_path.read_text(encoding="utf-8")
            self.meta_registry.apply_upgrade(new_version, new_content)
            self.event_bus.publish(
                EventTypes.META_UPGRADE_APPLIED,
                {"ticket_id": ticket_id, "new_version": new_version},
                "strategist",
            )
        except Exception as exc:
            logger.error("Failed applying meta upgrade: %s", exc)
    
    def _on_issue_resolved(self, event: DualRingEvent):
        """处理问题解决事件"""
        try:
            payload = event.payload
            resolution_method = payload.get("resolution_method", "unknown")
            
            # 记录解决方案的有效性
            logger.info(f"Issue resolved using: {resolution_method}")
            
        except Exception as e:
            logger.error(f"Error processing issue resolved event: {e}")
    
    def _save_case(self, case: StrategicCase):
        """保存战略案例到数据库"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO strategic_cases 
                    (case_id, goal, plan, result, execution_time, api_calls, cost, 
                     failure_reason, skill_sequence, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    case.case_id,
                    case.goal,
                    json.dumps(case.plan),
                    case.result,
                    case.execution_time,
                    case.api_calls,
                    case.cost,
                    case.failure_reason,
                    json.dumps(case.skill_sequence),
                    case.created_at
                ))
                conn.commit()
            
            self.cases.append(case)
            self._update_stats()
            
        except Exception as e:
            logger.error(f"Error saving case: {e}")
    
    def _perform_strategic_analysis(self):
        """执行战略分析"""
        try:
            # 1. 模式识别和聚类分析
            patterns = self._identify_patterns()
            
            # 2. 失败原因分析
            failure_patterns = self._analyze_failures()
            
            # 3. 效率分析
            efficiency_insights = self._analyze_efficiency()
            
            # 4. 提炼新原则
            new_principles = self._extract_principles(patterns, failure_patterns, efficiency_insights)
            
            # 5. 更新现有原则
            self._update_existing_principles()
            
            logger.info(f"Strategic analysis completed. Found {len(new_principles)} new principles")
            
        except Exception as e:
            logger.error(f"Error in strategic analysis: {e}")
    
    def _identify_patterns(self) -> Dict[str, Any]:
        """识别模式"""
        patterns = {
            "skill_combinations": Counter(),
            "failure_patterns": Counter(),
            "success_patterns": Counter(),
            "task_categories": Counter()
        }
        
        for case in self.cases:
            # 分析技能组合
            skill_key = "->".join(case.skill_sequence)
            patterns["skill_combinations"][skill_key] += 1
            
            # 分析任务类别
            task_category = self._categorize_task(case.goal)
            patterns["task_categories"][task_category] += 1
            
            # 分析成功/失败模式
            if case.result == "success":
                patterns["success_patterns"][skill_key] += 1
            else:
                patterns["failure_patterns"][skill_key] += 1
        
        return patterns
    
    def _analyze_failures(self) -> Dict[str, Any]:
        """分析失败原因"""
        failure_analysis = {
            "common_failures": Counter(),
            "failure_by_category": defaultdict(Counter),
            "recovery_patterns": Counter()
        }
        
        failed_cases = [case for case in self.cases if case.result == "failure"]
        
        for case in failed_cases:
            # 分析失败原因
            if case.failure_reason:
                failure_analysis["common_failures"][case.failure_reason] += 1
            
            # 按任务类别分析失败
            task_category = self._categorize_task(case.goal)
            failure_analysis["failure_by_category"][task_category][case.failure_reason or "unknown"] += 1
        
        return failure_analysis
    
    def _analyze_efficiency(self) -> Dict[str, Any]:
        """分析效率"""
        efficiency_analysis = {
            "avg_time_by_category": defaultdict(list),
            "avg_cost_by_category": defaultdict(list),
            "cost_effectiveness": []
        }
        
        for case in self.cases:
            task_category = self._categorize_task(case.goal)
            efficiency_analysis["avg_time_by_category"][task_category].append(case.execution_time)
            efficiency_analysis["avg_cost_by_category"][task_category].append(case.cost)
            
            # 计算成本效益
            if case.execution_time > 0:
                cost_per_second = case.cost / case.execution_time
                efficiency_analysis["cost_effectiveness"].append({
                    "case_id": case.case_id,
                    "category": task_category,
                    "cost_per_second": cost_per_second,
                    "success": case.result == "success"
                })
        
        return efficiency_analysis
    
    def _extract_principles(self, patterns: Dict, failures: Dict, efficiency: Dict) -> List[StrategicPrinciple]:
        """从分析结果中提炼战略原则"""
        new_principles = []
        
        # 1. 基于失败模式的原则
        for failure_reason, count in failures["common_failures"].most_common(5):
            if count >= 3:  # 至少3次相同失败
                principle = StrategicPrinciple(
                    principle_id=f"failure_recovery_{len(new_principles)}",
                    title=f"Failure Recovery: {failure_reason}",
                    description=f"When encountering '{failure_reason}', implement alternative approach or retry with different tools",
                    category="recovery",
                    confidence=min(count / len(self.cases), 1.0),
                    evidence_count=count,
                    success_rate=0.0  # 需要后续跟踪
                )
                new_principles.append(principle)
        
        # 2. 基于技能组合的原则
        for skill_combo, success_count in patterns["success_patterns"].most_common(10):
            total_count = patterns["skill_combinations"][skill_combo]
            success_rate = success_count / total_count if total_count > 0 else 0
            
            if success_rate >= 0.8 and total_count >= 3:  # 高成功率且多次验证
                principle = StrategicPrinciple(
                    principle_id=f"skill_combo_{len(new_principles)}",
                    title=f"Effective Skill Combination: {skill_combo}",
                    description=f"Use skill combination '{skill_combo}' for similar tasks (success rate: {success_rate:.2%})",
                    category="planning",
                    confidence=success_rate,
                    evidence_count=total_count,
                    success_rate=success_rate
                )
                new_principles.append(principle)
        
        # 3. 基于效率的原则
        for category, times in efficiency["avg_time_by_category"].items():
            if len(times) >= 3:
                avg_time = sum(times) / len(times)
                if avg_time > 60:  # 超过1分钟的任务
                    principle = StrategicPrinciple(
                        principle_id=f"efficiency_{len(new_principles)}",
                        title=f"Optimize {category} tasks",
                        description=f"Tasks in category '{category}' take average {avg_time:.1f}s. Consider optimization strategies.",
                        category="optimization",
                        confidence=0.7,
                        evidence_count=len(times),
                        success_rate=0.0
                    )
                    new_principles.append(principle)
        
        return new_principles
    
    def _update_existing_principles(self):
        """更新现有原则的置信度和成功率"""
        for principle in self.principles:
            # 重新评估原则的有效性
            relevant_cases = self._find_relevant_cases(principle)
            if relevant_cases:
                success_count = sum(1 for case in relevant_cases if case.result == "success")
                principle.success_rate = success_count / len(relevant_cases)
                principle.evidence_count = len(relevant_cases)
                
                # 更新置信度
                if principle.evidence_count >= 5:
                    principle.confidence = min(principle.success_rate + 0.2, 1.0)
    
    def _find_relevant_cases(self, principle: StrategicPrinciple) -> List[StrategicCase]:
        """找到与原则相关的案例"""
        relevant_cases = []
        
        for case in self.cases:
            # 根据原则类别和描述匹配相关案例
            if principle.category == "planning" and principle.description in case.goal:
                relevant_cases.append(case)
            elif principle.category == "recovery" and case.failure_reason:
                if principle.description.lower() in case.failure_reason.lower():
                    relevant_cases.append(case)
        
        return relevant_cases
    
    def _categorize_task(self, goal: str) -> str:
        """对任务进行分类"""
        goal_lower = goal.lower()
        
        if any(word in goal_lower for word in ["web", "scrape", "crawl", "download"]):
            return "web_scraping"
        elif any(word in goal_lower for word in ["analyze", "data", "report", "chart"]):
            return "data_analysis"
        elif any(word in goal_lower for word in ["code", "develop", "program", "script"]):
            return "code_development"
        elif any(word in goal_lower for word in ["test", "validate", "verify"]):
            return "testing"
        elif any(word in goal_lower for word in ["file", "read", "write", "process"]):
            return "file_operations"
        else:
            return "general"
    
    def _update_executor_prompts(self):
        """更新执行者的系统提示"""
        if not self.config.enable_auto_optimization:
            return
        
        # 获取高置信度的原则
        high_confidence_principles = [
            p for p in self.principles 
            if p.confidence >= self.config.confidence_threshold
        ]
        
        if high_confidence_principles:
            # 构建优化后的系统提示
            optimized_prompt = self._build_optimized_prompt(high_confidence_principles)
            
            # 发布优化事件
            self.event_bus.publish(
                EventTypes.SYSTEM_OPTIMIZATION,
                {
                    "optimized_prompt": optimized_prompt,
                    "principles_count": len(high_confidence_principles),
                    "confidence_threshold": self.config.confidence_threshold
                },
                "strategist"
            )
            
            logger.info(f"Published system optimization with {len(high_confidence_principles)} principles")
    
    def _build_optimized_prompt(self, principles: List[StrategicPrinciple]) -> str:
        """构建优化后的系统提示"""
        base_prompt = "你是一个AI助手，请为用户的目标制定一个计划。"
        
        if not principles:
            return base_prompt
        
        principles_text = "\n\n在制定任何计划前，必须遵循以下战略原则：\n"
        
        for i, principle in enumerate(principles, 1):
            principles_text += f"{i}. {principle.title}: {principle.description}\n"
        
        return base_prompt + principles_text
    
    def _update_stats(self):
        """更新统计信息"""
        if not self.cases:
            return
        
        total = len(self.cases)
        success = sum(1 for case in self.cases if case.result == "success")
        failure = sum(1 for case in self.cases if case.result == "failure")
        
        avg_time = sum(case.execution_time for case in self.cases) / total
        avg_cost = sum(case.cost for case in self.cases) / total
        
        self.stats.update({
            "total_cases": total,
            "success_cases": success,
            "failure_cases": failure,
            "avg_execution_time": avg_time,
            "avg_cost": avg_cost
        })
    
    def get_knowledge_summary(self) -> Dict[str, Any]:
        """获取知识库摘要"""
        return {
            "stats": self.stats,
            "principles_count": len(self.principles),
            "cases_count": len(self.cases),
            "top_principles": [
                {
                    "title": p.title,
                    "confidence": p.confidence,
                    "success_rate": p.success_rate,
                    "evidence_count": p.evidence_count
                }
                for p in sorted(self.principles, key=lambda x: x.confidence, reverse=True)[:5]
            ],
            "recent_cases": [
                {
                    "goal": case.goal[:100] + "..." if len(case.goal) > 100 else case.goal,
                    "result": case.result,
                    "execution_time": case.execution_time,
                    "created_at": case.created_at
                }
                for case in sorted(self.cases, key=lambda x: x.created_at, reverse=True)[:10]
            ]
        }
    
    def get_strategic_insights(self) -> Dict[str, Any]:
        """获取战略洞察"""
        if len(self.cases) < 5:
            return {"message": "Insufficient data for insights"}
        
        insights = {
            "success_rate": self.stats["success_cases"] / self.stats["total_cases"],
            "avg_execution_time": self.stats["avg_execution_time"],
            "avg_cost": self.stats["avg_cost"],
            "top_failure_reasons": [],
            "efficiency_recommendations": []
        }
        
        # 分析失败原因
        failure_reasons = Counter()
        for case in self.cases:
            if case.result == "failure" and case.failure_reason:
                failure_reasons[case.failure_reason] += 1
        
        insights["top_failure_reasons"] = [
            {"reason": reason, "count": count}
            for reason, count in failure_reasons.most_common(5)
        ]
        
        # 效率建议
        if self.stats["avg_execution_time"] > 60:
            insights["efficiency_recommendations"].append(
                "Consider optimizing long-running tasks"
            )
        
        if self.stats["avg_cost"] > 1.0:
            insights["efficiency_recommendations"].append(
                "Consider cost optimization strategies"
            )
        
        return insights
