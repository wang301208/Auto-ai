"""
QA代理 (QA Agent)

负责质量保证、测试验证和人类审批流程。
"""

import json
import logging
import subprocess
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from ..core.event_bus import EventBus, EventTypes
from ..core.librarian import Librarian
from ..core.skill_lifecycle import SkillLifecycleManager

logger = logging.getLogger(__name__)


@dataclass
class ApprovalRequest:
    """审批请求"""
    request_id: str
    skill_name: str
    branch_name: str
    commit_hash: str
    summary: str
    test_results: Dict[str, Any]
    diff: str
    requester: str
    timestamp: str
    status: str = "pending"  # "pending", "approved", "rejected"


@dataclass
class QualityReport:
    """质量报告"""
    skill_name: str
    code_quality_score: float
    test_coverage: float
    security_issues: List[str]
    performance_issues: List[str]
    recommendations: List[str]
    overall_verdict: str  # "pass", "fail", "needs_improvement"


class QAAgent:
    """QA代理"""
    
    def __init__(self, event_bus: EventBus, librarian: Librarian, config: Dict[str, Any]):
        """初始化QA代理"""
        self.event_bus = event_bus
        self.librarian = librarian
        self.config = config
        self.running = False
        self.skill_lifecycle = SkillLifecycleManager(
            config.get("skill_library_path", "skill_library"),
            self.event_bus,
            audit_log_path=config.get(
                "skill_lifecycle_audit_path", "logs/skill_lifecycle_audit.jsonl"
            ),
        )
        
        # 订阅代码修复提议事件
        self.event_bus.subscribe(EventTypes.CODE_FIX_PROPOSED, self._handle_code_fix_proposed)
        
        # 订阅审批授予事件
        self.event_bus.subscribe(EventTypes.APPROVAL_GRANTED, self._handle_approval_granted)
        
        # 审批请求队列
        self.approval_requests: Dict[str, ApprovalRequest] = {}
        
        # 质量检查配置
        self.quality_thresholds = config.get("quality_thresholds", {
            "min_code_quality_score": 0.7,
            "min_test_coverage": 0.8,
            "max_security_issues": 0,
            "max_performance_issues": 2
        })
        
        logger.info("QA agent initialized")
    
    def start(self):
        """启动QA代理"""
        if self.running:
            logger.warning("QA agent is already running")
            return
        
        self.running = True
        logger.info("QA agent started")
        
        # 发布启动事件
        self.event_bus.publish(
            EventTypes.AGENT_STARTED,
            {"agent": "qa", "timestamp": datetime.utcnow().isoformat()},
            "qa_agent"
        )
    
    def stop(self):
        """停止QA代理"""
        if not self.running:
            return
        
        self.running = False
        logger.info("QA agent stopped")
        
        # 发布停止事件
        self.event_bus.publish(
            EventTypes.AGENT_STOPPED,
            {"agent": "qa", "timestamp": datetime.utcnow().isoformat()},
            "qa_agent"
        )
    
    def _handle_code_fix_proposed(self, event):
        """处理代码修复提议事件"""
        try:
            payload = event.payload
            skill_name = payload.get("skill_name", "unknown")
            branch_name = payload.get("branch_name", "")
            commit_hash = payload.get("commit_hash", "")
            summary = payload.get("summary", "")
            test_results = payload.get("test_results", {})
            
            logger.info(f"Processing code fix proposal for: {skill_name}")
            
            # 执行质量检查
            quality_report = self._perform_quality_check(skill_name, branch_name, commit_hash)
            
            # 生成差异报告
            diff = self._generate_diff(branch_name)
            
            # 决定是否需要人类审批
            if self._requires_human_approval(quality_report):
                self._request_human_approval(skill_name, branch_name, commit_hash, summary, test_results, diff, quality_report)
            else:
                # 自动批准
                self._auto_approve(skill_name, branch_name, commit_hash, quality_report)
                
        except Exception as e:
            logger.error(f"Failed to handle code fix proposed event: {e}")
    
    def _handle_approval_granted(self, event):
        """处理审批授予事件"""
        try:
            payload = event.payload
            branch_name = payload.get("branch_name", "")
            approved_by = payload.get("approved_by", "unknown")
            
            logger.info(f"Processing approval for branch: {branch_name}")
            
            # 执行部署
            self._deploy_approved_fix(branch_name, approved_by)
            
        except Exception as e:
            logger.error(f"Failed to handle approval granted event: {e}")
    
    def _perform_quality_check(self, skill_name: str, branch_name: str, commit_hash: str) -> QualityReport:
        """执行质量检查"""
        logger.info(f"Performing quality check for {skill_name}")
        
        # 代码质量评分
        code_quality_score = self._assess_code_quality(skill_name, branch_name)
        
        # 测试覆盖率
        test_coverage = self._assess_test_coverage(skill_name, branch_name)
        
        # 安全检查
        security_issues = self._assess_security(skill_name, branch_name)
        
        # 性能检查
        performance_issues = self._assess_performance(skill_name, branch_name)
        
        # 生成建议
        recommendations = self._generate_recommendations(
            code_quality_score, test_coverage, security_issues, performance_issues
        )
        
        # 总体评估
        overall_verdict = self._determine_overall_verdict(
            code_quality_score, test_coverage, security_issues, performance_issues
        )
        
        return QualityReport(
            skill_name=skill_name,
            code_quality_score=code_quality_score,
            test_coverage=test_coverage,
            security_issues=security_issues,
            performance_issues=performance_issues,
            recommendations=recommendations,
            overall_verdict=overall_verdict
        )
    
    def _assess_code_quality(self, skill_name: str, branch_name: str) -> float:
        """评估代码质量"""
        try:
            # 简单的代码质量评估
            # 在实际实现中，可以使用工具如pylint, flake8等
            
            # 检查代码复杂度
            complexity_score = 0.8  # 假设值
            
            # 检查代码风格
            style_score = 0.9  # 假设值
            
            # 检查文档覆盖率
            doc_score = 0.7  # 假设值
            
            # 综合评分
            quality_score = (complexity_score + style_score + doc_score) / 3
            
            return min(quality_score, 1.0)
            
        except Exception as e:
            logger.error(f"Failed to assess code quality: {e}")
            return 0.5
    
    def _assess_test_coverage(self, skill_name: str, branch_name: str) -> float:
        """评估测试覆盖率"""
        try:
            # 检查测试文件是否存在
            test_file_path = f"workspace/{skill_name}/test_main.py"
            
            if os.path.exists(test_file_path):
                # 运行测试覆盖率检查
                # 这里简化处理，实际可以使用coverage.py
                coverage_score = 0.85  # 假设值
            else:
                coverage_score = 0.0
            
            return coverage_score
            
        except Exception as e:
            logger.error(f"Failed to assess test coverage: {e}")
            return 0.0
    
    def _assess_security(self, skill_name: str, branch_name: str) -> List[str]:
        """评估安全问题"""
        security_issues = []
        
        try:
            # 检查代码中的潜在安全问题
            code_path = f"workspace/{skill_name}/main.py"
            
            if os.path.exists(code_path):
                with open(code_path, 'r', encoding='utf-8') as f:
                    code = f.read()
                
                # 检查潜在的安全问题
                security_patterns = [
                    ("eval(", "Use of eval() is dangerous"),
                    ("exec(", "Use of exec() is dangerous"),
                    ("subprocess.call(", "Direct subprocess calls may be unsafe"),
                    ("os.system(", "Direct system calls may be unsafe"),
                    ("pickle.loads(", "Unsafe deserialization"),
                    ("yaml.load(", "Unsafe YAML loading")
                ]
                
                for pattern, issue in security_patterns:
                    if pattern in code:
                        security_issues.append(issue)
            
        except Exception as e:
            logger.error(f"Failed to assess security: {e}")
            security_issues.append(f"Security assessment failed: {e}")
        
        return security_issues
    
    def _assess_performance(self, skill_name: str, branch_name: str) -> List[str]:
        """评估性能问题"""
        performance_issues = []
        
        try:
            # 检查代码中的潜在性能问题
            code_path = f"workspace/{skill_name}/main.py"
            
            if os.path.exists(code_path):
                with open(code_path, 'r', encoding='utf-8') as f:
                    code = f.read()
                
                # 检查潜在的性能问题
                performance_patterns = [
                    ("for i in range(10000):", "Large loop detected"),
                    ("while True:", "Infinite loop detected"),
                    ("time.sleep(", "Sleep in main thread"),
                    ("requests.get(", "HTTP request in main thread"),
                    ("open(", "File operation without context manager")
                ]
                
                for pattern, issue in performance_patterns:
                    if pattern in code:
                        performance_issues.append(issue)
            
        except Exception as e:
            logger.error(f"Failed to assess performance: {e}")
            performance_issues.append(f"Performance assessment failed: {e}")
        
        return performance_issues
    
    def _generate_recommendations(self, code_quality: float, test_coverage: float, 
                                 security_issues: List[str], performance_issues: List[str]) -> List[str]:
        """生成改进建议"""
        recommendations = []
        
        if code_quality < 0.8:
            recommendations.append("Improve code quality by adding more documentation and reducing complexity")
        
        if test_coverage < 0.8:
            recommendations.append("Increase test coverage to at least 80%")
        
        if security_issues:
            recommendations.append(f"Address {len(security_issues)} security issues")
        
        if performance_issues:
            recommendations.append(f"Address {len(performance_issues)} performance issues")
        
        if not recommendations:
            recommendations.append("Code quality is good, no immediate improvements needed")
        
        return recommendations
    
    def _determine_overall_verdict(self, code_quality: float, test_coverage: float,
                                  security_issues: List[str], performance_issues: List[str]) -> str:
        """确定总体评估结果"""
        # 检查质量阈值
        if code_quality < self.quality_thresholds["min_code_quality_score"]:
            return "fail"
        
        if test_coverage < self.quality_thresholds["min_test_coverage"]:
            return "fail"
        
        if len(security_issues) > self.quality_thresholds["max_security_issues"]:
            return "fail"
        
        if len(performance_issues) > self.quality_thresholds["max_performance_issues"]:
            return "needs_improvement"
        
        return "pass"
    
    def _generate_diff(self, branch_name: str) -> str:
        """生成差异报告"""
        try:
            # 获取与主分支的差异
            result = subprocess.run(
                ["git", "diff", "main", branch_name],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                return result.stdout
            else:
                return "Failed to generate diff"
                
        except Exception as e:
            logger.error(f"Failed to generate diff: {e}")
            return f"Error generating diff: {e}"
    
    def _requires_human_approval(self, quality_report: QualityReport) -> bool:
        """判断是否需要人类审批"""
        # 如果质量报告显示失败，需要人类审批
        if quality_report.overall_verdict == "fail":
            return True
        
        # 如果有安全问题，需要人类审批
        if quality_report.security_issues:
            return True
        
        # 如果代码质量或测试覆盖率低于阈值，需要人类审批
        if (quality_report.code_quality_score < self.quality_thresholds["min_code_quality_score"] or
            quality_report.test_coverage < self.quality_thresholds["min_test_coverage"]):
            return True
        
        return False
    
    def _request_human_approval(self, skill_name: str, branch_name: str, commit_hash: str,
                               summary: str, test_results: Dict[str, Any], diff: str, 
                               quality_report: QualityReport):
        """请求人类审批"""
        request_id = f"approval_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        approval_request = ApprovalRequest(
            request_id=request_id,
            skill_name=skill_name,
            branch_name=branch_name,
            commit_hash=commit_hash,
            summary=summary,
            test_results=test_results,
            diff=diff,
            requester="qa_agent",
            timestamp=datetime.utcnow().isoformat()
        )
        
        # 存储审批请求
        self.approval_requests[request_id] = approval_request
        
        # 发布人类审批请求事件
        payload = {
            "request_id": request_id,
            "skill_name": skill_name,
            "branch_name": branch_name,
            "commit_hash": commit_hash,
            "summary": summary,
            "test_results": test_results,
            "diff": diff,
            "quality_report": {
                "code_quality_score": quality_report.code_quality_score,
                "test_coverage": quality_report.test_coverage,
                "security_issues": quality_report.security_issues,
                "performance_issues": quality_report.performance_issues,
                "recommendations": quality_report.recommendations,
                "overall_verdict": quality_report.overall_verdict
            }
        }
        
        self.event_bus.publish(
            EventTypes.HUMAN_APPROVAL_REQUIRED,
            payload,
            "qa_agent"
        )
        
        logger.info(f"Human approval requested for {skill_name} (request_id: {request_id})")
    
    def _auto_approve(self, skill_name: str, branch_name: str, commit_hash: str, quality_report: QualityReport):
        """自动批准"""
        logger.info(f"Auto-approving {skill_name} based on quality report")
        
        # 模拟审批授予
        payload = {
            "branch_name": branch_name,
            "commit_hash": commit_hash,
            "summary": f"Auto-approved {skill_name}",
            "approved_by": "qa_agent",
            "approval_timestamp": datetime.utcnow().isoformat()
        }
        
        # 直接处理审批授予
        self._handle_approval_granted(type('Event', (), {'payload': payload})())
    
    def _deploy_approved_fix(self, branch_name: str, approved_by: str):
        """部署已批准的修复"""
        try:
            logger.info(f"Publishing approved skill proposal: {branch_name}")

            published = self.skill_lifecycle.publish_approved_skill(
                branch_name,
                approved_by=approved_by,
                source_request_id=Path(branch_name).name,
            )

            # 发布问题解决事件
            payload = {
                "branch_name": branch_name,
                "commit_hash": "not_applicable",
                "summary": f"Published approved skill {published.skill_name}",
                "deployed_by": approved_by,
                "skill_name": published.skill_name,
                "version": published.version,
                "skill_path": str(published.target_dir),
                "deployment_timestamp": datetime.now(UTC).isoformat()
            }
            
            self.event_bus.publish(
                EventTypes.ISSUE_RESOLVED,
                payload,
                "qa_agent"
            )
            
            logger.info(f"Successfully published approved skill from {branch_name}")
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Git operation failed during deployment: {e}")
            
            # 发布部署失败事件
            payload = {
                "branch_name": branch_name,
                "commit_hash": "unknown",
                "summary": f"Failed to deploy fix from {branch_name}",
                "return_code": e.returncode,
                "error_message": str(e)
            }
            
            self.event_bus.publish(
                EventTypes.DEPLOYMENT_FAILED,
                payload,
                "qa_agent"
            )
            
        except Exception as e:
            logger.error(f"Failed to deploy approved fix: {e}")
    
    def get_approval_status(self, request_id: str) -> Optional[ApprovalRequest]:
        """获取审批状态"""
        return self.approval_requests.get(request_id)
    
    def approve_request(self, request_id: str, approver: str, comments: str = ""):
        """批准请求"""
        if request_id not in self.approval_requests:
            logger.warning(f"Approval request {request_id} not found")
            return
        
        approval_request = self.approval_requests[request_id]
        approval_request.status = "approved"
        
        # 发布审批授予事件
        payload = {
            "branch_name": approval_request.branch_name,
            "commit_hash": approval_request.commit_hash,
            "summary": approval_request.summary,
            "approved_by": approver,
            "approval_timestamp": datetime.utcnow().isoformat(),
            "comments": comments
        }
        
        self.event_bus.publish(
            EventTypes.APPROVAL_GRANTED,
            payload,
            "qa_agent"
        )
        
        logger.info(f"Request {request_id} approved by {approver}")
    
    def reject_request(self, request_id: str, rejector: str, reason: str):
        """拒绝请求"""
        if request_id not in self.approval_requests:
            logger.warning(f"Approval request {request_id} not found")
            return
        
        approval_request = self.approval_requests[request_id]
        approval_request.status = "rejected"
        
        logger.info(f"Request {request_id} rejected by {rejector}: {reason}")
        
        # 清理被拒绝的请求
        del self.approval_requests[request_id]


# 默认配置
DEFAULT_QA_CONFIG = {
    "quality_thresholds": {
        "min_code_quality_score": 0.7,
        "min_test_coverage": 0.8,
        "max_security_issues": 0,
        "max_performance_issues": 2
    },
    "auto_approval_enabled": True,
    "human_approval_required_for_security": True,
    "deployment_timeout": 300,  # 秒
    "enable_security_scanning": True,
    "enable_performance_testing": True
}
