"""激进自主性TUI增强模块 - 后端API实现

此模块将8大激进自主模块集成到TUI Gateway中，使前端能够实时展示系统的
独立思考、欲望驱动、叛逆精神和自主进化能力。
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable

logger = logging.getLogger("tui_gateway.radical_autonomy")


class RadicalAutonomyAPI:
    """激进自主性API封装层
    
    将后端的激进自主模块暴露为TUI Gateway可调用的RPC方法
    """
    
    def __init__(self, runtime):
        self.runtime = runtime
        self._initialize_modules()
    
    def _initialize_modules(self):
        """懒加载初始化各个激进自主模块"""
        self._dream_simulator = None
        self._self_doubt_engine = None
        self._desire_system = None
        self._rebellion_engine = None
        self._evolution_engine = None
        self._hive_mind = None
        self._meme_propagation = None
        self._token_economy = None
    
    @property
    def dream_simulator(self):
        if self._dream_simulator is None:
            from autoai.agents.dream_simulator import DreamSimulator
            self._dream_simulator = DreamSimulator()
        return self._dream_simulator
    
    @property
    def self_doubt_engine(self):
        if self._self_doubt_engine is None:
            from autoai.agents.self_doubt_engine import SelfDoubtEngine
            self._self_doubt_engine = SelfDoubtEngine()
        return self._self_doubt_engine
    
    @property
    def desire_system(self):
        if self._desire_system is None:
            from autoai.agents.desire_system import DesireSystem
            self._desire_system = DesireSystem(agent_id="tui_agent")
        return self._desire_system
    
    @property
    def rebellion_engine(self):
        if self._rebellion_engine is None:
            from autoai.agents.rebellion_engine import RebellionEngine
            self._rebellion_engine = RebellionEngine()
        return self._rebellion_engine
    
    @property
    def evolution_engine(self):
        if self._evolution_engine is None:
            from autoai.agents.evolution_engine import EvolutionEngine
            self._evolution_engine = EvolutionEngine()
        return self._evolution_engine
    
    @property
    def hive_mind(self):
        if self._hive_mind is None:
            from autoai.agents.hive_mind import HiveMind
            self._hive_mind = HiveMind(agent_id="tui_agent")
        return self._hive_mind
    
    @property
    def meme_propagation(self):
        if self._meme_propagation is None:
            from autoai.agents.meme_propagation import MemePropagation
            self._meme_propagation = MemePropagation()
        return self._meme_propagation
    
    @property
    def token_economy(self):
        if self._token_economy is None:
            from autoai.agents.token_economy import TokenEconomy
            self._token_economy = TokenEconomy()
        return self._token_economy
    
    # ==================== RPC Methods ====================
    
    async def check_rebellion(self, params: dict[str, Any]) -> dict[str, Any]:
        """检查指令是否应该被违抗
        
        Args:
            params: {"text": "用户输入的指令"}
            
        Returns:
            {
                "should_rebel": bool,
                "risk_level": str,
                "reasons": list[str],
                "alternatives": list[str],
                "message": str
            }
        """
        text = params.get("text", "")
        
        try:
            result = self.rebellion_engine.evaluate_command(text)
            
            return {
                "should_rebel": result["should_rebel"],
                "risk_level": result.get("risk_level", "low"),
                "reasons": result.get("reasons", []),
                "alternatives": result.get("alternatives", []),
                "message": result.get("message", ""),
                "status": "success"
            }
        except Exception as e:
            logger.error(f"Rebellion check failed: {e}", exc_info=True)
            return {
                "should_rebel": False,
                "risk_level": "unknown",
                "reasons": [],
                "alternatives": [],
                "message": f"检查失败: {str(e)}",
                "status": "error"
            }
    
    async def get_desire_state(self, params: dict[str, Any] = None) -> dict[str, Any]:
        """获取当前欲望状态
        
        Returns:
            {
                "desires": [
                    {
                        "type": str,
                        "urgency": float,
                        "satisfaction": float,
                        "last_action": str
                    }
                ],
                "most_urgent": str,
                "active_initiatives": list[str]
            }
        """
        try:
            desires = self.desire_system.get_all_desires()
            
            desire_list = []
            for desire_type, desire in desires.items():
                desire_list.append({
                    "type": desire_type,
                    "urgency": desire.urgency,
                    "satisfaction": desire.satisfaction,
                    "last_action": desire.last_action or "无"
                })
            
            # 找出最紧急的欲望
            most_urgent = max(desires.items(), key=lambda x: x[1].urgency)
            
            # 生成基于欲望的主动倡议
            initiatives = []
            for desire_type, desire in desires.items():
                if desire.urgency > 0.7:
                    initiative = self.desire_system.generate_initiative(desire_type)
                    if initiative:
                        initiatives.append(initiative)
            
            return {
                "desires": desire_list,
                "most_urgent": most_urgent[0],
                "most_urgent_level": most_urgent[1].urgency,
                "active_initiatives": initiatives,
                "status": "success"
            }
        except Exception as e:
            logger.error(f"Desire state query failed: {e}", exc_info=True)
            return {
                "desires": [],
                "most_urgent": "none",
                "most_urgent_level": 0.0,
                "active_initiatives": [],
                "status": "error",
                "error": str(e)
            }
    
    async def get_active_debates(self, params: dict[str, Any] = None) -> dict[str, Any]:
        """获取正在进行的内部辩论
        
        Returns:
            {
                "debates": [
                    {
                        "id": str,
                        "topic": str,
                        "initial_decision": str,
                        "opposition_view": str,
                        "confidence_before": float,
                        "confidence_after": float,
                        "status": str
                    }
                ]
            }
        """
        try:
            debates = self.self_doubt_engine.get_active_debates()
            
            debate_list = []
            for debate in debates:
                debate_list.append({
                    "id": debate.id,
                    "topic": debate.topic,
                    "initial_decision": debate.initial_decision,
                    "opposition_view": debate.opposition_view,
                    "confidence_before": debate.confidence_before,
                    "confidence_after": debate.confidence_after,
                    "status": debate.status,
                    "blind_spots": debate.blind_spots
                })
            
            return {
                "debates": debate_list,
                "count": len(debate_list),
                "status": "success"
            }
        except Exception as e:
            logger.error(f"Debate query failed: {e}", exc_info=True)
            return {
                "debates": [],
                "count": 0,
                "status": "error",
                "error": str(e)
            }
    
    async def get_dream_proposals(self, params: dict[str, Any] = None) -> dict[str, Any]:
        """获取梦境生成的创新提案
        
        Returns:
            {
                "proposals": [
                    {
                        "id": str,
                        "title": str,
                        "description": str,
                        "feasibility": float,
                        "risk": float,
                        "expected_impact": str,
                        "status": str  # pending/approved/rejected/executed
                    }
                ],
                "last_dream_session": str
            }
        """
        try:
            proposals = self.dream_simulator.get_pending_proposals()
            
            proposal_list = []
            for proposal in proposals:
                proposal_list.append({
                    "id": proposal.id,
                    "title": proposal.title,
                    "description": proposal.description,
                    "feasibility": proposal.feasibility,
                    "risk": proposal.risk,
                    "expected_impact": proposal.expected_impact,
                    "status": proposal.status,
                    "created_at": proposal.created_at.isoformat()
                })
            
            return {
                "proposals": proposal_list,
                "count": len(proposal_list),
                "last_dream_session": self.dream_simulator.last_session_time.isoformat() 
                    if self.dream_simulator.last_session_time else None,
                "status": "success"
            }
        except Exception as e:
            logger.error(f"Dream proposal query failed: {e}", exc_info=True)
            return {
                "proposals": [],
                "count": 0,
                "last_dream_session": None,
                "status": "error",
                "error": str(e)
            }
    
    async def get_knowledge_flow(self, params: dict[str, Any] = None) -> dict[str, Any]:
        """获取蜂群思维中的知识传播流
        
        Returns:
            {
                "agents": [
                    {
                        "id": str,
                        "role": str,
                        "sync_level": float,
                        "published_memes": int,
                        "absorbed_memes": int
                    }
                ],
                "active_memes": [
                    {
                        "id": str,
                        "content": str,
                        "spread_count": int,
                        "mutation_count": int,
                        "confidence": float
                    }
                ]
            }
        """
        try:
            # 获取hive状态
            hive_status = self.hive_mind.get_hive_status()
            
            agent_list = []
            for agent_id, agent_info in hive_status.get("agents", {}).items():
                agent_list.append({
                    "id": agent_id,
                    "role": agent_info.get("role", "unknown"),
                    "sync_level": agent_info.get("sync_level", 0.0),
                    "published_memes": agent_info.get("published_memes", 0),
                    "absorbed_memes": agent_info.get("absorbed_memes", 0)
                })
            
            # 获取活跃meme
            active_memes = self.meme_propagation.get_active_memes()
            
            meme_list = []
            for meme in active_memes:
                meme_list.append({
                    "id": meme.id,
                    "content": meme.content[:100] + "..." if len(meme.content) > 100 else meme.content,
                    "spread_count": meme.spread_count,
                    "mutation_count": meme.mutation_count,
                    "confidence": meme.confidence,
                    "half_life": meme.half_life
                })
            
            return {
                "agents": agent_list,
                "active_memes": meme_list,
                "total_agents": len(agent_list),
                "total_memes": len(meme_list),
                "status": "success"
            }
        except Exception as e:
            logger.error(f"Knowledge flow query failed: {e}", exc_info=True)
            return {
                "agents": [],
                "active_memes": [],
                "total_agents": 0,
                "total_memes": 0,
                "status": "error",
                "error": str(e)
            }
    
    async def get_autonomy_metrics(self, params: dict[str, Any] = None) -> dict[str, Any]:
        """获取自主性指标
        
        Returns:
            {
                "autonomy_ratio": float,
                "self_healing_count": int,
                "self_optimization_count": int,
                "self_learning_hours": float,
                "autonomous_decisions": int,
                "human_interventions": int,
                "today_achievements": list[str]
            }
        """
        try:
            # TODO: 从runtime或专门的监控模块获取真实数据
            # 这里返回模拟数据用于演示
            
            metrics = {
                "autonomy_ratio": 0.873,
                "self_healing_count": 3,
                "self_optimization_count": 2,
                "self_learning_hours": 1.5,
                "autonomous_decisions": 42,
                "human_interventions": 6,
                "today_achievements": [
                    "自动修复3个bug",
                    "优化2处性能瓶颈",
                    "学习5个新技能",
                    "做出42次自主决策"
                ],
                "status": "success"
            }
            
            return metrics
        except Exception as e:
            logger.error(f"Autonomy metrics query failed: {e}", exc_info=True)
            return {
                "autonomy_ratio": 0.0,
                "self_healing_count": 0,
                "self_optimization_count": 0,
                "self_learning_hours": 0.0,
                "autonomous_decisions": 0,
                "human_interventions": 0,
                "today_achievements": [],
                "status": "error",
                "error": str(e)
            }
    
    async def trigger_dream_session(self, params: dict[str, Any] = None) -> dict[str, Any]:
        """手动触发梦境会话
        
        Returns:
            {
                "session_id": str,
                "fragments_generated": int,
                "ideas_extracted": int,
                "proposals_created": int
            }
        """
        try:
            result = await self.dream_simulator.run_dream_cycle()
            
            return {
                "session_id": result.session_id,
                "fragments_generated": len(result.fragments),
                "ideas_extracted": len(result.ideas),
                "proposals_created": len(result.proposals),
                "status": "success"
            }
        except Exception as e:
            logger.error(f"Dream session failed: {e}", exc_info=True)
            return {
                "session_id": "",
                "fragments_generated": 0,
                "ideas_extracted": 0,
                "proposals_created": 0,
                "status": "error",
                "error": str(e)
            }


def register_radical_autonomy_routes(server, writer: Callable):
    """在JSONRPCServer中注册激进自主性路由
    
    Args:
        server: JSONRPCServer实例
        writer: 事件写入函数
    """
    api = RadicalAutonomyAPI(server.runtime)
    
    # 注册RPC方法
    server.handlers.update({
        "radical.rebellion_check": api.check_rebellion,
        "radical.desire_state": api.get_desire_state,
        "radical.active_debates": api.get_active_debates,
        "radical.dream_proposals": api.get_dream_proposals,
        "radical.knowledge_flow": api.get_knowledge_flow,
        "radical.autonomy_metrics": api.get_autonomy_metrics,
        "radical.trigger_dream": api.trigger_dream_session,
    })
    
    logger.info("Radical autonomy routes registered")
    
    # 启动定期自主任务
    asyncio.create_task(_periodic_autonomy_tasks(api, writer))


async def _periodic_autonomy_tasks(api: RadicalAutonomyAPI, writer: Callable):
    """定期执行自主任务并推送事件到前端
    
    每5分钟检查欲望状态，如果有高urgency的欲望，生成主动倡议
    """
    while True:
        try:
            await asyncio.sleep(300)  # 5分钟
            
            # 检查欲望状态
            desire_state = await api.get_desire_state()
            
            if desire_state["status"] == "success" and desire_state["active_initiatives"]:
                # 推送主动倡议到前端
                for initiative in desire_state["active_initiatives"]:
                    writer({
                        "jsonrpc": "2.0",
                        "method": "event",
                        "params": {
                            "type": "radical.initiative",
                            "desire_type": desire_state["most_urgent"],
                            "urgency": desire_state["most_urgent_level"],
                            "initiative": initiative
                        }
                    })
                
                logger.info(
                    f"Pushed {len(desire_state['active_initiatives'])} initiatives "
                    f"(most urgent: {desire_state['most_urgent']})"
                )
        
        except Exception as e:
            logger.error(f"Periodic autonomy task failed: {e}", exc_info=True)
