"""
考古学家代理 (Archaeologist Agent)

负责诊断问题，分析根本原因，并制定解决方案。
"""

import json
import logging
import re
from datetime import UTC, datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

from ..core.event_bus import EventBus, EventTypes
from ..core.librarian import Librarian

logger = logging.getLogger(__name__)


@dataclass
class DiagnosisResult:
    """诊断结果"""
    issue_type: str
    root_cause: str
    recommended_solutions: List[Dict[str, Any]]
    confidence: float
    priority: str  # "high", "medium", "low"
    estimated_effort: str  # "small", "medium", "large"
    dependencies: List[str]
    metadata: Dict[str, Any]


class ArchaeologistAgent:
    """考古学家代理"""
    
    def __init__(self, event_bus: EventBus, librarian: Librarian, config: Dict[str, Any]):
        """初始化考古学家代理"""
        self.event_bus = event_bus
        self.librarian = librarian
        self.config = config
        self.running = False
        
        # 订阅问题检测事件
        self.event_bus.subscribe(EventTypes.ISSUE_DETECTED, self._handle_issue_detected)
        
        logger.info("Archaeologist agent initialized")
    
    def start(self):
        """启动考古学家代理"""
        if self.running:
            logger.warning("Archaeologist agent is already running")
            return
        
        self.running = True
        logger.info("Archaeologist agent started")
        
        # 发布启动事件
        self.event_bus.publish(
            EventTypes.AGENT_STARTED,
            {"agent": "archaeologist", "timestamp": datetime.now(UTC).isoformat()},
            "archaeologist_agent"
        )
    
    def stop(self):
        """停止考古学家代理"""
        if not self.running:
            return
        
        self.running = False
        logger.info("Archaeologist agent stopped")
        
        # 发布停止事件
        self.event_bus.publish(
            EventTypes.AGENT_STOPPED,
            {"agent": "archaeologist", "timestamp": datetime.now(UTC).isoformat()},
            "archaeologist_agent"
        )
    
    def _handle_issue_detected(self, event):
        """处理问题检测事件"""
        try:
            payload = event.payload
            issue_type = payload.get("issue_type", "unknown")
            
            logger.info(f"Processing issue: {issue_type}")
            
            # 执行诊断
            diagnosis = self._diagnose_issue(payload)
            
            if diagnosis:
                # 发布诊断完成事件
                self._publish_diagnosis_complete(diagnosis, payload)
            else:
                logger.warning(f"Could not diagnose issue: {issue_type}")
                
        except Exception as e:
            logger.error(f"Failed to handle issue detected event: {e}")
    
    def _diagnose_issue(self, issue_payload: Dict[str, Any]) -> Optional[DiagnosisResult]:
        """诊断问题"""
        issue_type = issue_payload.get("issue_type", "unknown")
        
        # 根据问题类型选择诊断策略
        if issue_type == "log_error":
            return self._diagnose_log_error(issue_payload)
        elif issue_type == "api_error":
            return self._diagnose_api_error(issue_payload)
        elif issue_type == "dependency_update":
            return self._diagnose_dependency_update(issue_payload)
        elif issue_type == "skill_requested":
            return self._diagnose_skill_request(issue_payload)
        else:
            return self._diagnose_generic_issue(issue_payload)
    
    def _diagnose_log_error(self, issue_payload: Dict[str, Any]) -> Optional[DiagnosisResult]:
        """诊断日志错误"""
        error_log = issue_payload.get("error_log", "")
        plugin = issue_payload.get("plugin", "unknown")
        
        # 分析错误模式
        patterns = {
            "connection_error": r"(connection|timeout|refused|network)",
            "permission_error": r"(permission|access|denied|forbidden)",
            "resource_error": r"(memory|disk|space|quota)",
            "dependency_error": r"(import|module|package|dependency)",
            "configuration_error": r"(config|setting|parameter|invalid)"
        }
        
        root_cause = "unknown"
        for pattern_name, pattern in patterns.items():
            if re.search(pattern, error_log.lower()):
                root_cause = pattern_name
                break
        
        # 查找相关技能
        relevant_skills = self.librarian.find_skill(root_cause, top_k=3)
        
        # 查找相关插件
        relevant_plugins = self.librarian.find_plugin(root_cause, top_k=3)
        
        # 构建解决方案
        solutions = []
        
        # 添加技能解决方案
        for skill_result in relevant_skills:
            if skill_result.confidence > 0.5:
                solutions.append({
                    "type": "skill",
                    "name": skill_result.item.name,
                    "description": skill_result.item.description,
                    "confidence": skill_result.confidence,
                    "parameters": skill_result.item.parameters
                })
        
        # 添加插件解决方案
        for plugin_result in relevant_plugins:
            if plugin_result.confidence > 0.5:
                solutions.append({
                    "type": "plugin",
                    "name": plugin_result.item.name,
                    "description": plugin_result.item.description,
                    "confidence": plugin_result.confidence,
                    "inputs": plugin_result.item.inputs,
                    "outputs": plugin_result.item.outputs
                })
        
        # 如果没有找到合适的解决方案，创建新技能请求
        if not solutions:
            solutions.append({
                "type": "new_skill",
                "name": f"fix_{root_cause}_error",
                "description": f"Fix {root_cause} errors",
                "parameters": {
                    "error_type": {"type": "string", "required": True},
                    "error_message": {"type": "string", "required": True},
                    "context": {"type": "string", "required": False}
                }
            })
        
        return DiagnosisResult(
            issue_type=issue_payload.get("issue_type", "log_error"),
            root_cause=root_cause,
            recommended_solutions=solutions,
            confidence=0.7 if solutions else 0.3,
            priority="high" if "error" in error_log.lower() else "medium",
            estimated_effort="small" if len(solutions) > 0 else "medium",
            dependencies=[s["name"] for s in solutions if s["type"] in ["skill", "plugin"]],
            metadata={
                "error_log": error_log,
                "plugin": plugin,
                "timestamp": datetime.now(UTC).isoformat()
            }
        )
    
    def _diagnose_api_error(self, issue_payload: Dict[str, Any]) -> Optional[DiagnosisResult]:
        """诊断API错误"""
        url = issue_payload.get("metadata", {}).get("url", "")
        status_code = issue_payload.get("metadata", {}).get("actual_status")
        
        # 根据状态码确定问题类型
        if status_code == 404:
            root_cause = "endpoint_not_found"
        elif status_code == 500:
            root_cause = "server_error"
        elif status_code == 401:
            root_cause = "authentication_error"
        elif status_code == 403:
            root_cause = "authorization_error"
        else:
            root_cause = "api_error"
        
        # 查找相关技能
        relevant_skills = self.librarian.find_skill(f"api {root_cause}", top_k=3)
        
        solutions = []
        for skill_result in relevant_skills:
            if skill_result.confidence > 0.4:
                solutions.append({
                    "type": "skill",
                    "name": skill_result.item.name,
                    "description": skill_result.item.description,
                    "confidence": skill_result.confidence,
                    "parameters": skill_result.item.parameters
                })
        
        return DiagnosisResult(
            issue_type="api_error",
            root_cause=root_cause,
            recommended_solutions=solutions,
            confidence=0.8,
            priority="high",
            estimated_effort="small",
            dependencies=[s["name"] for s in solutions],
            metadata={
                "url": url,
                "status_code": status_code,
                "timestamp": datetime.now(UTC).isoformat()
            }
        )
    
    def _diagnose_dependency_update(self, issue_payload: Dict[str, Any]) -> Optional[DiagnosisResult]:
        """诊断依赖更新"""
        metadata = issue_payload.get("metadata", {})
        repo = metadata.get("repo", "")
        current_version = metadata.get("current_version", "")
        latest_version = metadata.get("latest_version", "")
        
        # 查找更新技能
        relevant_skills = self.librarian.find_skill("dependency update", top_k=3)
        
        solutions = []
        for skill_result in relevant_skills:
            if skill_result.confidence > 0.4:
                solutions.append({
                    "type": "skill",
                    "name": skill_result.item.name,
                    "description": skill_result.item.description,
                    "confidence": skill_result.confidence,
                    "parameters": skill_result.item.parameters
                })
        
        return DiagnosisResult(
            issue_type="dependency_update",
            root_cause="outdated_dependency",
            recommended_solutions=solutions,
            confidence=0.9,
            priority="medium",
            estimated_effort="medium",
            dependencies=[s["name"] for s in solutions],
            metadata={
                "repo": repo,
                "current_version": current_version,
                "latest_version": latest_version,
                "timestamp": datetime.now(UTC).isoformat()
            }
        )
    
    def _diagnose_skill_request(self, issue_payload: Dict[str, Any]) -> Optional[DiagnosisResult]:
        """诊断技能请求"""
        skill_name = issue_payload.get("skill_name", "")
        context = issue_payload.get("context", {})
        
        # 分析技能需求
        description = context.get("description", "")
        parameters = context.get("parameters", {})
        
        # 查找类似技能
        relevant_skills = self.librarian.find_skill(skill_name, top_k=3)
        
        solutions = []
        
        # 如果找到类似技能，建议使用现有技能
        for skill_result in relevant_skills:
            if skill_result.confidence > 0.6:
                solutions.append({
                    "type": "existing_skill",
                    "name": skill_result.item.name,
                    "description": skill_result.item.description,
                    "confidence": skill_result.confidence,
                    "parameters": skill_result.item.parameters
                })
        
        # 如果没有找到合适的现有技能，创建新技能
        if not solutions:
            solutions.append({
                "type": "new_skill",
                "name": skill_name,
                "description": description,
                "parameters": parameters,
                "code_template": self._generate_skill_template(skill_name, description, parameters)
            })
        
        return DiagnosisResult(
            issue_type="skill_request",
            root_cause="missing_skill",
            recommended_solutions=solutions,
            confidence=0.8,
            priority="medium",
            estimated_effort="medium" if solutions[0]["type"] == "new_skill" else "small",
            dependencies=[],
            metadata={
                "requested_skill": skill_name,
                "context": context,
                "timestamp": datetime.now(UTC).isoformat()
            }
        )
    
    def _diagnose_generic_issue(self, issue_payload: Dict[str, Any]) -> Optional[DiagnosisResult]:
        """诊断通用问题"""
        issue_type = issue_payload.get("issue_type", "unknown")
        description = issue_payload.get("description", "")
        
        # 查找相关技能
        relevant_skills = self.librarian.find_skill(description, top_k=3)
        
        solutions = []
        for skill_result in relevant_skills:
            if skill_result.confidence > 0.3:
                solutions.append({
                    "type": "skill",
                    "name": skill_result.item.name,
                    "description": skill_result.item.description,
                    "confidence": skill_result.confidence,
                    "parameters": skill_result.item.parameters
                })
        
        return DiagnosisResult(
            issue_type=issue_type,
            root_cause="unknown",
            recommended_solutions=solutions,
            confidence=0.5,
            priority="medium",
            estimated_effort="medium",
            dependencies=[s["name"] for s in solutions],
            metadata={
                "description": description,
                "timestamp": datetime.now(UTC).isoformat()
            }
        )
    
    def _generate_skill_template(self, skill_name: str, description: str, parameters: Dict[str, Any]) -> str:
        """生成技能代码模板"""
        param_str = ""
        for param_name, param_info in parameters.items():
            param_type = param_info.get("type", "str")
            required = param_info.get("required", False)
            default = param_info.get("default", "")
            
            if required:
                param_str += f"    {param_name}: {param_type},\n"
            else:
                param_str += f"    {param_name}: {param_type} = {default},\n"
        
        template = f'''"""
{description}
"""

def main({param_str.rstrip(',\n')}):
    """
    Main function for {skill_name}
    """
    # TODO: Implement the skill logic
    result = {{"status": "success", "message": "Skill {skill_name} executed"}}
    return result

if __name__ == "__main__":
    # Test the skill
    result = main()
    print(result)
'''
        return template
    
    def _publish_diagnosis_complete(self, diagnosis: DiagnosisResult, original_issue: Dict[str, Any]):
        """发布诊断完成事件"""
        payload = {
            "issue_type": diagnosis.issue_type,
            "root_cause": diagnosis.root_cause,
            "recommended_solutions": diagnosis.recommended_solutions,
            "confidence": diagnosis.confidence,
            "priority": diagnosis.priority,
            "estimated_effort": diagnosis.estimated_effort,
            "dependencies": diagnosis.dependencies,
            "metadata": diagnosis.metadata,
            "original_issue": original_issue
        }
        
        self.event_bus.publish(
            EventTypes.DIAGNOSIS_COMPLETE,
            payload,
            "archaeologist_agent"
        )
        
        logger.info(f"Diagnosis completed for {diagnosis.issue_type} with confidence {diagnosis.confidence}")


# 默认配置
DEFAULT_ARCHAEOLOGIST_CONFIG = {
    "diagnosis_timeout": 30,  # 秒
    "min_confidence_threshold": 0.3,
    "max_solutions_per_diagnosis": 5,
    "enable_llm_analysis": False,  # 是否使用LLM进行深度分析
    "llm_provider": "openai",  # LLM提供商
    "llm_model": "gpt-4"  # LLM模型
}
