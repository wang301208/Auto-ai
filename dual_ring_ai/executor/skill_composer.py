"""
技能组合器 (Skill Composer)

负责为子任务找到合适的技能并组合参数。
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

from ..core.event_bus import EventBus, EventTypes
from ..core.librarian import Librarian

logger = logging.getLogger(__name__)


@dataclass
class SkillComposition:
    """技能组合"""
    subtask_id: str
    skill_name: str
    confidence: float
    parameters: Dict[str, Any]
    alternatives: List[Dict[str, Any]]
    composition_strategy: str


@dataclass
class CompositionResult:
    """组合结果"""
    subtask_id: str
    compositions: List[SkillComposition]
    best_composition: Optional[SkillComposition]
    confidence: float
    requires_new_skill: bool


class SkillComposer:
    """技能组合器"""
    
    def __init__(self, event_bus: EventBus, librarian: Librarian, config: Dict[str, Any]):
        """初始化技能组合器"""
        self.event_bus = event_bus
        self.librarian = librarian
        self.config = config
        self.running = False
        
        # 订阅任务规划完成事件
        self.event_bus.subscribe(EventTypes.TASK_PLANNED, self._handle_task_planned)
        
        # 订阅技能创建完成事件
        self.event_bus.subscribe(EventTypes.SKILL_CREATED, self._handle_skill_created)
        
        # 组合策略
        self.composition_strategies = config.get("composition_strategies", {
            "exact_match": True,
            "semantic_similarity": True,
            "parameter_mapping": True,
            "skill_chaining": True
        })
        
        # 置信度阈值
        self.confidence_threshold = config.get("confidence_threshold", 0.7)
        
        # 等待技能请求的缓存
        self.pending_skill_requests: Dict[str, Dict[str, Any]] = {}
        
        logger.info("Skill composer initialized")
    
    def start(self):
        """启动技能组合器"""
        if self.running:
            logger.warning("Skill composer is already running")
            return
        
        self.running = True
        logger.info("Skill composer started")
        
        # 发布启动事件
        self.event_bus.publish(
            EventTypes.AGENT_STARTED,
            {"agent": "skill_composer", "timestamp": datetime.utcnow().isoformat()},
            "skill_composer_agent"
        )
    
    def stop(self):
        """停止技能组合器"""
        if not self.running:
            return
        
        self.running = False
        logger.info("Skill composer stopped")
        
        # 发布停止事件
        self.event_bus.publish(
            EventTypes.AGENT_STOPPED,
            {"agent": "skill_composer", "timestamp": datetime.utcnow().isoformat()},
            "skill_composer_agent"
        )
    
    def _handle_task_planned(self, event):
        """处理任务规划完成事件"""
        try:
            payload = event.payload
            plan_id = payload.get("plan_id", "")
            subtasks = payload.get("subtasks", [])
            
            logger.info(f"Processing task plan: {plan_id} with {len(subtasks)} subtasks")
            
            # 为每个子任务组合技能
            for subtask in subtasks:
                self._compose_skills_for_subtask(subtask, plan_id)
                
        except Exception as e:
            logger.error(f"Failed to handle task planned event: {e}")
    
    def _handle_skill_created(self, event):
        """处理技能创建完成事件"""
        try:
            payload = event.payload
            skill_name = payload.get("skill_name", "")
            
            logger.info(f"New skill created: {skill_name}")
            
            # 检查是否有等待此技能的请求
            self._check_pending_requests(skill_name)
            
        except Exception as e:
            logger.error(f"Failed to handle skill created event: {e}")
    
    def _compose_skills_for_subtask(self, subtask: Dict[str, Any], plan_id: str):
        """为子任务组合技能"""
        subtask_id = subtask.get("id", "")
        subtask_name = subtask.get("name", "")
        subtask_description = subtask.get("description", "")
        subtask_parameters = subtask.get("parameters", {})
        
        logger.info(f"Composing skills for subtask: {subtask_name}")
        
        # 查找合适的技能
        skill_results = self.librarian.find_skill(subtask_description, top_k=5)
        
        # 生成组合结果
        composition_result = self._generate_composition_result(
            subtask_id, subtask_name, subtask_description, subtask_parameters, skill_results
        )
        
        # 发布技能组合完成事件
        self._publish_skill_composed(plan_id, subtask_id, composition_result)
        
        # 如果需要新技能，发布技能请求
        if composition_result.requires_new_skill:
            self._request_new_skill(subtask_id, subtask_name, subtask_description, subtask_parameters)
    
    def _generate_composition_result(self, subtask_id: str, subtask_name: str, 
                                   subtask_description: str, subtask_parameters: Dict[str, Any],
                                   skill_results: List) -> CompositionResult:
        """生成组合结果"""
        compositions = []
        
        for skill_result in skill_results:
            skill = skill_result.item
            confidence = skill_result.confidence
            
            # 参数映射
            mapped_parameters = self._map_parameters(subtask_parameters, skill.parameters)
            
            composition = SkillComposition(
                subtask_id=subtask_id,
                skill_name=skill.name,
                confidence=confidence,
                parameters=mapped_parameters,
                alternatives=[],
                composition_strategy="semantic_similarity"
            )
            
            compositions.append(composition)
        
        # 选择最佳组合
        best_composition = None
        if compositions:
            best_composition = max(compositions, key=lambda x: x.confidence)
        
        # 检查是否需要新技能
        requires_new_skill = (
            not compositions or 
            (best_composition and best_composition.confidence < self.confidence_threshold)
        )
        
        return CompositionResult(
            subtask_id=subtask_id,
            compositions=compositions,
            best_composition=best_composition,
            confidence=best_composition.confidence if best_composition else 0.0,
            requires_new_skill=requires_new_skill
        )
    
    def _map_parameters(self, subtask_parameters: Dict[str, Any], skill_parameters: Dict[str, Any]) -> Dict[str, Any]:
        """映射参数"""
        mapped_parameters = {}
        
        for param_name, param_info in skill_parameters.items():
            param_type = param_info.get("type", "str")
            required = param_info.get("required", False)
            default = param_info.get("default", "")
            
            # 尝试从子任务参数中找到匹配的参数
            if param_name in subtask_parameters:
                mapped_parameters[param_name] = subtask_parameters[param_name]
            elif param_name.lower() in {k.lower(): v for k, v in subtask_parameters.items()}:
                # 不区分大小写的匹配
                for k, v in subtask_parameters.items():
                    if k.lower() == param_name.lower():
                        mapped_parameters[param_name] = v
                        break
            elif not required and default:
                # 使用默认值
                mapped_parameters[param_name] = default
            elif required:
                # 必需参数但没有找到匹配，使用占位符
                if param_type == "str":
                    mapped_parameters[param_name] = f"<{param_name}>"
                elif param_type == "int":
                    mapped_parameters[param_name] = 0
                elif param_type == "float":
                    mapped_parameters[param_name] = 0.0
                elif param_type == "bool":
                    mapped_parameters[param_name] = False
                else:
                    mapped_parameters[param_name] = None
        
        return mapped_parameters
    
    def _request_new_skill(self, subtask_id: str, subtask_name: str, 
                          subtask_description: str, subtask_parameters: Dict[str, Any]):
        """请求新技能"""
        request_id = f"skill_request_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        # 缓存请求
        self.pending_skill_requests[request_id] = {
            "subtask_id": subtask_id,
            "subtask_name": subtask_name,
            "subtask_description": subtask_description,
            "subtask_parameters": subtask_parameters,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # 发布技能请求事件
        payload = {
            "skill_name": f"skill_{subtask_name.lower().replace(' ', '_')}",
            "request_id": request_id,
            "parameters": subtask_parameters,
            "requester": "skill_composer_agent",
            "context": {
                "subtask_id": subtask_id,
                "subtask_name": subtask_name,
                "subtask_description": subtask_description,
                "description": f"Skill to handle {subtask_name}: {subtask_description}",
                "parameters": self._convert_parameters_to_schema(subtask_parameters)
            }
        }
        
        self.event_bus.publish(
            EventTypes.SKILL_REQUESTED,
            payload,
            "skill_composer_agent"
        )
        
        logger.info(f"Requested new skill for subtask: {subtask_name} (request_id: {request_id})")
    
    def _convert_parameters_to_schema(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """将参数转换为技能参数模式"""
        schema = {}
        
        for param_name, param_value in parameters.items():
            param_type = type(param_value).__name__
            
            # 转换为技能参数模式
            if param_type == "str":
                schema[param_name] = {
                    "type": "string",
                    "required": True,
                    "description": f"Parameter {param_name}"
                }
            elif param_type == "int":
                schema[param_name] = {
                    "type": "integer",
                    "required": True,
                    "description": f"Parameter {param_name}"
                }
            elif param_type == "float":
                schema[param_name] = {
                    "type": "number",
                    "required": True,
                    "description": f"Parameter {param_name}"
                }
            elif param_type == "bool":
                schema[param_name] = {
                    "type": "boolean",
                    "required": True,
                    "description": f"Parameter {param_name}"
                }
            else:
                schema[param_name] = {
                    "type": "string",
                    "required": True,
                    "description": f"Parameter {param_name}"
                }
        
        return schema
    
    def _check_pending_requests(self, skill_name: str):
        """检查等待的请求"""
        requests_to_remove = []
        
        for request_id, request_data in self.pending_skill_requests.items():
            requested_skill_name = request_data.get("subtask_name", "").lower().replace(" ", "_")
            
            if requested_skill_name in skill_name.lower():
                # 找到匹配的技能，重新组合
                subtask_id = request_data["subtask_id"]
                subtask_name = request_data["subtask_name"]
                subtask_description = request_data["subtask_description"]
                subtask_parameters = request_data["subtask_parameters"]
                
                logger.info(f"Found matching skill for request {request_id}: {skill_name}")
                
                # 重新组合技能
                skill_results = self.librarian.find_skill(skill_name, top_k=1)
                if skill_results:
                    composition_result = self._generate_composition_result(
                        subtask_id, subtask_name, subtask_description, subtask_parameters, skill_results
                    )
                    
                    # 发布技能组合完成事件
                    self._publish_skill_composed("auto", subtask_id, composition_result)
                
                requests_to_remove.append(request_id)
        
        # 清理已处理的请求
        for request_id in requests_to_remove:
            del self.pending_skill_requests[request_id]
    
    def _publish_skill_composed(self, plan_id: str, subtask_id: str, composition_result: CompositionResult):
        """发布技能组合完成事件"""
        payload = {
            "plan_id": plan_id,
            "subtask_id": subtask_id,
            "compositions": [
                {
                    "skill_name": comp.skill_name,
                    "confidence": comp.confidence,
                    "parameters": comp.parameters,
                    "composition_strategy": comp.composition_strategy
                }
                for comp in composition_result.compositions
            ],
            "best_composition": {
                "skill_name": composition_result.best_composition.skill_name,
                "confidence": composition_result.best_composition.confidence,
                "parameters": composition_result.best_composition.parameters,
                "composition_strategy": composition_result.best_composition.composition_strategy
            } if composition_result.best_composition else None,
            "confidence": composition_result.confidence,
            "requires_new_skill": composition_result.requires_new_skill
        }
        
        self.event_bus.publish(
            EventTypes.SKILL_COMPOSED,
            payload,
            "skill_composer_agent"
        )
        
        logger.info(f"Skill composition completed for subtask {subtask_id}")
    
    def compose(self, subtask: str, parameters: Optional[Dict[str, Any]] = None) -> CompositionResult:
        """手动组合技能"""
        parameters = parameters or {}
        
        # 查找技能
        skill_results = self.librarian.find_skill(subtask, top_k=5)
        
        # 生成组合结果
        composition_result = self._generate_composition_result(
            "manual", "Manual Task", subtask, parameters, skill_results
        )
        
        return composition_result
    
    def get_composition_strategies(self) -> Dict[str, bool]:
        """获取组合策略"""
        return self.composition_strategies
    
    def set_confidence_threshold(self, threshold: float):
        """设置置信度阈值"""
        self.confidence_threshold = max(0.0, min(1.0, threshold))
        logger.info(f"Confidence threshold set to: {self.confidence_threshold}")


# 默认配置
DEFAULT_SKILL_COMPOSER_CONFIG = {
    "composition_strategies": {
        "exact_match": True,
        "semantic_similarity": True,
        "parameter_mapping": True,
        "skill_chaining": True
    },
    "confidence_threshold": 0.7,
    "max_alternatives_per_subtask": 3,
    "enable_llm_composition": False,
    "llm_provider": "openai",
    "llm_model": "gpt-4"
}
