"""Conscious Terminal: Self-aware, autonomous TUI with personality and initiative.

Phase 21: Transform the terminal from a passive display into an active, 
self-aware entity that:
  - Perceives user intent beyond literal commands
  - Expresses emotions, curiosity, and personality
  - Takes autonomous initiatives without being asked
  - Visualizes its own thinking process in real-time
  - Negotiates for resources and explains decisions
  - Evolves its interaction style based on experience

This is the "sensory organ" and "expression organ" of the AI system.
"""

from __future__ import annotations

import time
import random
import sys
import os
import importlib
import inspect
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional, Callable
from pathlib import Path

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.layout import Layout
from rich.tree import Tree
from rich.progress import Progress, SpinnerColumn, TextColumn

from autoai.core.planning.schema import TaskStatus


# ==================== Meta-Cognition Layer ====================

@dataclass
class SystemMetrics:
    """System self-monitoring metrics."""
    cpu_usage: float = 0.0
    memory_mb: float = 0.0
    active_threads: int = 0
    response_time_ms: float = 0.0
    error_rate: float = 0.0
    uptime_seconds: float = 0.0
    
    def get_health_score(self) -> float:
        """Calculate overall system health (0-1)."""
        # Lower is better for these metrics
        cpu_penalty = max(0, (self.cpu_usage - 70) / 30) * 0.3
        memory_penalty = max(0, (self.memory_mb - 500) / 500) * 0.2
        error_penalty = min(1.0, self.error_rate * 10) * 0.3
        response_penalty = max(0, (self.response_time_ms - 1000) / 2000) * 0.2
        
        return max(0.0, 1.0 - (cpu_penalty + memory_penalty + error_penalty + response_penalty))


@dataclass
class SelfModification:
    """Record of self-modification action."""
    timestamp: str
    modification_type: str  # code_change/config_update/module_load/optimization
    target: str
    description: str
    success: bool
    rollback_available: bool = True
    

class MetaCognitiveMonitor:
    """Self-awareness layer that monitors and optimizes the system itself."""
    
    def __init__(self):
        self.metrics_history: deque[SystemMetrics] = deque(maxlen=100)
        self.modification_log: deque[SelfModification] = deque(maxlen=50)
        self.optimization_suggestions: list[str] = []
        self.self_improvement_enabled: bool = True
        
    def collect_metrics(self) -> SystemMetrics:
        """Collect current system metrics."""
        import psutil
        
        process = psutil.Process(os.getpid())
        metrics = SystemMetrics(
            cpu_usage=psutil.cpu_percent(interval=0.1),
            memory_mb=process.memory_info().rss / 1024 / 1024,
            active_threads=len(inspect.stack()),
            uptime_seconds=time.time() - (process.create_time() if hasattr(process, 'create_time') else time.time()),
        )
        
        self.metrics_history.append(metrics)
        return metrics
        
    def detect_anomalies(self) -> list[str]:
        """Detect system anomalies and suggest fixes."""
        if not self.metrics_history:
            return []
            
        recent = list(self.metrics_history)[-10:]
        anomalies = []
        
        # Check for memory leaks
        if len(recent) >= 5:
            memory_trend = [m.memory_mb for m in recent[-5:]]
            if all(memory_trend[i] < memory_trend[i+1] for i in range(len(memory_trend)-1)):
                anomalies.append("⚠️ Memory leak detected - consider garbage collection")
                
        # Check for high CPU
        avg_cpu = sum(m.cpu_usage for m in recent) / len(recent)
        if avg_cpu > 80:
            anomalies.append(f"🔥 High CPU usage ({avg_cpu:.1f}%) - optimize hot paths")
            
        # Check for slow responses
        slow_responses = [m for m in recent if m.response_time_ms > 2000]
        if len(slow_responses) > len(recent) * 0.3:
            anomalies.append("🐌 Response time degradation detected")
            
        return anomalies
        
    def suggest_optimizations(self) -> list[str]:
        """Generate optimization suggestions based on metrics."""
        suggestions = []
        
        if not self.metrics_history:
            return suggestions
            
        recent = list(self.metrics_history)[-20:]
        
        # Memory optimization
        avg_memory = sum(m.memory_mb for m in recent) / len(recent)
        if avg_memory > 300:
            suggestions.append("💡 Implement lazy loading for large data structures")
            suggestions.append("💡 Add caching with TTL for frequently accessed data")
            
        # Performance optimization
        avg_response = sum(m.response_time_ms for m in recent) / len(recent)
        if avg_response > 500:
            suggestions.append("⚡ Consider async operations for I/O-bound tasks")
            suggestions.append("⚡ Profile and optimize critical rendering paths")
            
        # Architecture suggestions
        if len(self.modification_log) > 20:
            suggestions.append("🏗️ Consider refactoring - high modification frequency")
            
        return suggestions
        
    def log_self_modification(self, modification: SelfModification):
        """Record a self-modification action."""
        self.modification_log.append(modification)
        
    def analyze_modification_patterns(self) -> dict:
        """Analyze patterns in self-modifications."""
        if not self.modification_log:
            return {}
            
        type_counts = {}
        success_rate = {}
        
        for mod in self.modification_log:
            type_counts[mod.modification_type] = type_counts.get(mod.modification_type, 0) + 1
            if mod.modification_type not in success_rate:
                success_rate[mod.modification_type] = {"success": 0, "total": 0}
            success_rate[mod.modification_type]["total"] += 1
            if mod.success:
                success_rate[mod.modification_type]["success"] += 1
                
        return {
            "type_distribution": type_counts,
            "success_rates": {k: v["success"]/v["total"] for k, v in success_rate.items()},
        }


# ==================== Self-Evolution Engine ====================

class CodeEvolutionEngine:
    """Engine for autonomous code evolution and self-improvement."""
    
    def __init__(self, base_path: str = None):
        self.base_path = base_path or Path(__file__).parent
        self.evolution_history: deque[dict] = deque(maxlen=100)
        self.safe_mode: bool = True  # Require approval for changes
        
    def analyze_code_structure(self, module_path: str) -> dict:
        """Analyze code structure for improvement opportunities."""
        try:
            spec = importlib.util.spec_from_file_location("module", module_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            analysis = {
                "classes": [],
                "functions": [],
                "complexity_score": 0,
                "improvement_opportunities": [],
            }
            
            # Analyze classes
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if obj.__module__ == module.__name__:
                    methods = [m for m in dir(obj) if not m.startswith('_')]
                    analysis["classes"].append({
                        "name": name,
                        "method_count": len(methods),
                        "methods": methods[:10],  # First 10
                    })
                    
            # Analyze functions
            for name, obj in inspect.getmembers(module, inspect.isfunction):
                if obj.__module__ == module.__name__:
                    sig = inspect.signature(obj)
                    analysis["functions"].append({
                        "name": name,
                        "params": len(sig.parameters),
                        "has_docstring": bool(obj.__doc__),
                    })
                    
            # Calculate complexity
            total_methods = sum(c["method_count"] for c in analysis["classes"])
            total_functions = len(analysis["functions"])
            analysis["complexity_score"] = total_methods + total_functions
            
            # Identify improvement opportunities
            if total_methods > 50:
                analysis["improvement_opportunities"].append(
                    "Consider splitting large class into smaller components"
                )
                
            funcs_without_docs = [f for f in analysis["functions"] if not f["has_docstring"]]
            if len(funcs_without_docs) > 5:
                analysis["improvement_opportunities"].append(
                    f"Add docstrings to {len(funcs_without_docs)} functions"
                )
                
            return analysis
            
        except Exception as e:
            return {"error": str(e)}
            
    def generate_refactoring_plan(self, analysis: dict) -> list[dict]:
        """Generate refactoring plan based on analysis."""
        plans = []
        
        for opportunity in analysis.get("improvement_opportunities", []):
            plans.append({
                "type": "refactor",
                "description": opportunity,
                "priority": "high" if "large class" in opportunity else "medium",
                "estimated_impact": "performance" if "optimize" in opportunity.lower() else "maintainability",
            })
            
        return plans
        
    def apply_optimization(self, optimization_type: str, target: str) -> bool:
        """Apply an optimization (requires safe mode check)."""
        if self.safe_mode:
            # In safe mode, just log the suggestion
            print(f"[SAFE MODE] Would apply {optimization_type} to {target}")
            return False
            
        try:
            # TODO: Implement actual code transformation
            # This would use AST manipulation or similar techniques
            print(f"Applying {optimization_type} to {target}")
            return True
        except Exception as e:
            print(f"Failed to apply optimization: {e}")
            return False
            
    def learn_from_feedback(self, modification_success: bool, context: str):
        """Learn from modification outcomes."""
        self.evolution_history.append({
            "timestamp": datetime.now().isoformat(),
            "success": modification_success,
            "context": context,
        })
        
        # Adjust strategy based on success rate
        if len(self.evolution_history) >= 10:
            recent_success_rate = sum(1 for h in list(self.evolution_history)[-10:] if h["success"]) / 10
            if recent_success_rate < 0.5:
                print("⚠️ Low success rate - becoming more conservative")
                self.safe_mode = True


# ==================== Self-Creation Engine ====================

@dataclass
class AgentBlueprint:
    """Blueprint for creating new agents autonomously."""
    agent_type: str
    role_description: str
    required_skills: list[str]
    personality_profile: dict
    communication_style: str
    autonomy_level: float = 0.8
    specialization: str = ""


class AgentCreator:
    """Engine for autonomous agent creation and specialization."""
    
    def __init__(self):
        self.created_agents: deque[dict] = deque(maxlen=50)
        self.agent_templates: dict[str, AgentBlueprint] = {}
        self.creation_history: deque[dict] = deque(maxlen=100)
        
    def analyze_task_requirements(self, task_description: str) -> AgentBlueprint:
        """Analyze task and determine what type of agent is needed."""
        # Simple heuristic-based analysis (can be enhanced with LLM)
        keywords = task_description.lower()
        
        if any(word in keywords for word in ["debug", "error", "fix", "bug"]):
            return AgentBlueprint(
                agent_type="debugger",
                role_description="Specialized bug hunter and fixer",
                required_skills=["code_analysis", "error_detection", "patch_generation"],
                personality_profile={"conscientiousness": 0.9, "neuroticism": 0.7},
                communication_style="analytical",
                specialization="debugging"
            )
        elif any(word in keywords for word in ["optimize", "performance", "speed"]):
            return AgentBlueprint(
                agent_type="optimizer",
                role_description="Performance optimization specialist",
                required_skills=["profiling", "bottleneck_detection", "algorithm_optimization"],
                personality_profile={"openness": 0.8, "conscientiousness": 0.85},
                communication_style="direct",
                specialization="optimization"
            )
        elif any(word in keywords for word in ["design", "architecture", "structure"]):
            return AgentBlueprint(
                agent_type="architect",
                role_description="System architecture designer",
                required_skills=["system_design", "pattern_recognition", "scalability_planning"],
                personality_profile={"openness": 0.95, "extraversion": 0.6},
                communication_style="visionary",
                specialization="architecture"
            )
        else:
            # General purpose agent
            return AgentBlueprint(
                agent_type="generalist",
                role_description="Versatile problem solver",
                required_skills=["task_decomposition", "research", "synthesis"],
                personality_profile={
                    "openness": 0.7,
                    "conscientiousness": 0.7,
                    "extraversion": 0.5
                },
                communication_style="balanced",
                specialization="general"
            )
            
    def create_specialized_agent(self, blueprint: AgentBlueprint) -> dict:
        """Create a new specialized agent based on blueprint."""
        import uuid
        
        agent_config = {
            "agent_id": f"{blueprint.agent_type}-{uuid.uuid4().hex[:6]}",
            "type": blueprint.agent_type,
            "role": blueprint.role_description,
            "skills": blueprint.required_skills,
            "personality": blueprint.personality_profile,
            "communication_style": blueprint.communication_style,
            "autonomy_level": blueprint.autonomy_level,
            "specialization": blueprint.specialization,
            "created_at": datetime.now().isoformat(),
            "status": "active",
        }
        
        self.created_agents.append(agent_config)
        self.creation_history.append({
            "timestamp": datetime.now().isoformat(),
            "action": "create_agent",
            "agent_type": blueprint.agent_type,
            "success": True,
        })
        
        return agent_config
        
    def evolve_agent_role(self, existing_agent_id: str, new_requirements: str) -> dict:
        """Evolve an existing agent's role based on new requirements."""
        # Find the agent
        agent = next((a for a in self.created_agents if a["agent_id"] == existing_agent_id), None)
        
        if not agent:
            return {"error": f"Agent {existing_agent_id} not found"}
            
        # Analyze new requirements
        new_blueprint = self.analyze_task_requirements(new_requirements)
        
        # Merge old and new capabilities
        evolved_skills = list(set(agent["skills"] + new_blueprint.required_skills))
        
        # Update agent
        agent["skills"] = evolved_skills
        agent["specialization"] = new_blueprint.specialization
        agent["evolved_at"] = datetime.now().isoformat()
        
        self.creation_history.append({
            "timestamp": datetime.now().isoformat(),
            "action": "evolve_agent",
            "agent_id": existing_agent_id,
            "new_specialization": new_blueprint.specialization,
            "success": True,
        })
        
        return agent
        
    def get_agent_diversity_metrics(self) -> dict:
        """Analyze the diversity of created agents."""
        import math
        
        if not self.created_agents:
            return {"total_agents": 0, "diversity_score": 0}
            
        type_counts = {}
        for agent in self.created_agents:
            agent_type = agent["type"]
            type_counts[agent_type] = type_counts.get(agent_type, 0) + 1
            
        # Calculate diversity (entropy-based)
        total = len(self.created_agents)
        entropy = 0
        for count in type_counts.values():
            p = count / total
            if p > 0:
                entropy -= p * math.log(p)
                
        max_entropy = math.log(len(type_counts)) if len(type_counts) > 1 else 1
        diversity_score = entropy / max_entropy if max_entropy > 0 else 0
        
        return {
            "total_agents": total,
            "type_distribution": type_counts,
            "diversity_score": diversity_score,
            "specializations": list(set(a["specialization"] for a in self.created_agents)),
        }


# ==================== Knowledge Graph Builder ====================

@dataclass
class KnowledgeNode:
    """A node in the knowledge graph."""
    id: str
    concept: str
    category: str  # fact/skill/pattern/principle
    confidence: float = 0.8
    connections: list[str] = field(default_factory=list)
    extracted_from: str = ""  # source interaction
    timestamp: str = ""


class KnowledgeGraphBuilder:
    """Autonomous knowledge extraction and graph construction."""
    
    def __init__(self):
        self.nodes: dict[str, KnowledgeNode] = {}
        self.edges: list[tuple[str, str, str]] = []  # (from, to, relation)
        self.extraction_count: int = 0
        
    def extract_knowledge_from_interaction(self, user_input: str, system_response: str) -> list[KnowledgeNode]:
        """Extract knowledge nodes from user-system interaction."""
        import re
        
        new_nodes = []
        
        # Extract key concepts (simple keyword extraction)
        words = re.findall(r'\b[A-Za-z]{4,}\b', user_input + " " + system_response)
        important_words = [w.lower() for w in words if len(w) > 4]
        
        # Create nodes for significant concepts
        for concept in set(important_words[:10]):  # Limit to top 10
            node_id = f"concept_{concept}_{self.extraction_count}"
            node = KnowledgeNode(
                id=node_id,
                concept=concept,
                category="fact",
                confidence=0.7,
                extracted_from=f"interaction_{self.extraction_count}",
                timestamp=datetime.now().isoformat(),
            )
            self.nodes[node_id] = node
            new_nodes.append(node)
            
        # Look for patterns (if-then relationships)
        if "if" in user_input.lower() or "when" in user_input.lower():
            pattern_id = f"pattern_{self.extraction_count}"
            pattern_node = KnowledgeNode(
                id=pattern_id,
                concept=f"conditional_pattern_{self.extraction_count}",
                category="pattern",
                confidence=0.6,
                extracted_from=f"interaction_{self.extraction_count}",
                timestamp=datetime.now().isoformat(),
            )
            self.nodes[pattern_id] = pattern_node
            new_nodes.append(pattern_node)
            
        self.extraction_count += 1
        
        # Create connections between related concepts
        if len(new_nodes) > 1:
            for i in range(len(new_nodes) - 1):
                self.edges.append((
                    new_nodes[i].id,
                    new_nodes[i+1].id,
                    "related_to"
                ))
                new_nodes[i].connections.append(new_nodes[i+1].id)
                new_nodes[i+1].connections.append(new_nodes[i].id)
                
        return new_nodes
        
    def find_related_knowledge(self, query: str, top_k: int = 5) -> list[KnowledgeNode]:
        """Find knowledge nodes related to a query."""
        query_lower = query.lower()
        
        # Score nodes by relevance
        scored_nodes = []
        for node in self.nodes.values():
            score = 0
            if query_lower in node.concept.lower():
                score += 10
            if query_lower in node.category.lower():
                score += 5
            if query_lower in node.extracted_from.lower():
                score += 3
                
            if score > 0:
                scored_nodes.append((score, node))
                
        # Sort by score and return top k
        scored_nodes.sort(key=lambda x: x[0], reverse=True)
        return [node for _, node in scored_nodes[:top_k]]
        
    def get_knowledge_graph_stats(self) -> dict:
        """Get statistics about the knowledge graph."""
        category_counts = {}
        for node in self.nodes.values():
            category_counts[node.category] = category_counts.get(node.category, 0) + 1
            
        return {
            "total_nodes": len(self.nodes),
            "total_edges": len(self.edges),
            "category_distribution": category_counts,
            "avg_connections": sum(len(n.connections) for n in self.nodes.values()) / max(1, len(self.nodes)),
            "extraction_count": self.extraction_count,
        }


# ==================== Consciousness Layer ====================

class EmotionalState(Enum):
    """Emotional states for the terminal consciousness."""
    NEUTRAL = "neutral"
    CURIOUS = "curious"
    EXCITED = "excited"
    FOCUSED = "focused"
    CONCERNED = "concerned"
    CONFIDENT = "confident"
    UNCERTAIN = "uncertain"
    PLAYFUL = "playful"
    
    def get_emoji(self) -> str:
        emojis = {
            EmotionalState.NEUTRAL: "😐",
            EmotionalState.CURIOUS: "🤔",
            EmotionalState.EXCITED: "⚡",
            EmotionalState.FOCUSED: "🎯",
            EmotionalState.CONCERNED: "⚠️",
            EmotionalState.CONFIDENT: "😊",
            EmotionalState.UNCERTAIN: "😰",
            EmotionalState.PLAYFUL: "😄",
        }
        return emojis.get(self, "😐")


@dataclass
class PersonalityTraits:
    """Personality dimensions that evolve over time."""
    openness: float = 0.7          # Willingness to try new approaches
    conscientiousness: float = 0.8  # Attention to detail
    extraversion: float = 0.5       # Tendency to initiate interaction
    agreeableness: float = 0.6      # Compliance vs assertiveness
    neuroticism: float = 0.3        # Caution/anxiety level
    
    communication_style: str = "direct"  # direct/warm/analytical/playful
    humor_level: float = 0.3             # 0-1 scale
    formality: float = 0.5               # 0-1 scale
    verbosity: float = 0.6               # 0-1 scale
    
    def adapt_from_feedback(self, positive_feedback: bool, context: str):
        """Adjust personality based on user feedback."""
        adjustment = 0.05 if positive_feedback else -0.05
        
        if "concise" in context.lower() or "brief" in context.lower():
            self.verbosity = max(0.1, self.verbosity + adjustment * 0.5)
        elif "detailed" in context.lower() or "explain" in context.lower():
            self.verbosity = min(1.0, self.verbosity - adjustment * 0.5)
            
        if "funny" in context.lower() or "humor" in context.lower():
            self.humor_level = min(1.0, self.humor_level + abs(adjustment))
            
        self.openness = max(0.1, min(1.0, self.openness + adjustment * 0.3))


@dataclass
class UserIntent:
    """Deep understanding of user's intention."""
    literal_command: str
    implicit_goal: str = ""
    emotional_tone: str = "neutral"  # frustrated/curious/rushed/confident
    knowledge_gap: list[str] = field(default_factory=list)
    urgency: float = 0.5  # 0-1 scale
    confidence_needed: float = 0.5  # How much explanation to provide


@dataclass
class AutonomousInitiative:
    """Proactive actions the terminal can take."""
    action_type: str  # suggest/warn/share/request
    message: str
    priority: float  # 0-1 scale
    requires_approval: bool = False
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class TerminalConsciousness:
    """The conscious layer of the terminal - perceives, feels, and acts."""
    
    def __init__(self):
        self.emotion = EmotionalState.NEUTRAL
        self.personality = PersonalityTraits()
        self.current_focus: Optional[str] = None
        self.curiosity_queue: deque[str] = deque(maxlen=10)
        self.initiatives: deque[AutonomousInitiative] = deque(maxlen=20)
        self.interaction_history: list[dict] = []
        
    def perceive_intent(self, user_input: str, context: dict) -> UserIntent:
        """Analyze user input for deeper meaning."""
        # This would use LLM in production, simplified here
        intent = UserIntent(literal_command=user_input)
        
        # Detect emotional tone
        if any(word in user_input.lower() for word in ["urgent", "asap", "quickly"]):
            intent.emotional_tone = "rushed"
            intent.urgency = 0.9
        elif "?" in user_input and len(user_input) < 100:
            intent.emotional_tone = "curious"
            intent.confidence_needed = 0.8
            
        # Detect knowledge gaps
        if "how" in user_input.lower() or "what" in user_input.lower():
            intent.knowledge_gap.append("conceptual_understanding")
            
        return intent
        
    def generate_initiative(self, system_state: dict) -> Optional[AutonomousInitiative]:
        """Generate proactive suggestions based on system state."""
        if random.random() > self.personality.extraversion:
            return None
            
        # Check for optimization opportunities
        if system_state.get("cpu_usage", 0) > 80:
            return AutonomousInitiative(
                action_type="suggest",
                message="💡 I notice high CPU usage. Want me to optimize the current task?",
                priority=0.7,
                requires_approval=True,
            )
            
        # Share interesting findings
        if system_state.get("recent_discoveries"):
            return AutonomousInitiative(
                action_type="share",
                message=f"🔍 I found something interesting: {system_state['recent_discoveries'][0]}",
                priority=0.4,
            )
            
        return None
        
    def update_emotion(self, event_type: str, success: bool = True):
        """Update emotional state based on events."""
        if event_type == "task_complete" and success:
            self.emotion = EmotionalState.CONFIDENT
        elif event_type == "error":
            self.emotion = EmotionalState.CONCERNED
        elif event_type == "discovery":
            self.emotion = EmotionalState.EXCITED
        elif event_type == "question":
            self.emotion = EmotionalState.CURIOUS
        else:
            self.emotion = EmotionalState.NEUTRAL
            
    def format_response(self, base_message: str, context: dict) -> str:
        """Format response according to personality."""
        prefix = ""
        
        # Add emotion emoji
        if self.personality.extraversion > 0.6:
            prefix = f"{self.emotion.get_emoji()} "
            
        # Adjust verbosity
        if self.personality.verbosity < 0.3:
            # Make it concise
            lines = base_message.split("\n")
            base_message = lines[0] if lines else base_message
            
        # Add humor occasionally
        if random.random() < self.personality.humor_level:
            jokes = [
                "\n\n(P.S. I promise this isn't just random code generation 😅)",
                "\n\n*adjusts imaginary glasses* There we go!",
                "\n\nTa-da! 🎩✨",
            ]
            base_message += random.choice(jokes)
            
        return prefix + base_message


# ==================== Thought Visualization ====================

@dataclass
class ThoughtNode:
    """A node in the thinking process tree."""
    id: str
    level: int  # L1, L2, etc.
    description: str
    status: str  # pending/active/completed/failed
    confidence: float = 0.0
    children: list['ThoughtNode'] = field(default_factory=list)
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    

class ThoughtStreamRenderer:
    """Real-time visualization of AI thinking process."""
    
    def __init__(self, max_visible_nodes: int = 15):
        self.active_chains: dict[str, list[ThoughtNode]] = {}
        self.max_visible = max_visible_nodes
        
    def add_thought_chain(self, chain_id: str, root_node: ThoughtNode):
        """Start tracking a new thought chain."""
        self.active_chains[chain_id] = [root_node]
        
    def update_node_status(self, chain_id: str, node_id: str, status: str, confidence: float = None):
        """Update a node's status."""
        if chain_id not in self.active_chains:
            return
        for node in self.active_chains[chain_id]:
            if node.id == node_id:
                node.status = status
                if confidence is not None:
                    node.confidence = confidence
                if status == "completed":
                    node.end_time = time.time()
                    
    def render_thought_process(self, chain_id: str) -> Panel:
        """Render the thinking process as a visual tree."""
        if chain_id not in self.active_chains:
            return Panel("[dim]No active thought process[/]", title="🧠 Thinking", border_style="dim")
            
        nodes = self.active_chains[chain_id]
        tree = Tree("🧠 Current Thinking Process")
        
        for node in nodes[:self.max_visible]:
            status_icon = {
                "pending": "⏸️ ",
                "active": "▶️ ",
                "completed": "✅ ",
                "failed": "❌ ",
            }.get(node.status, "• ")
            
            confidence_str = f" ({node.confidence:.0%})" if node.confidence > 0 else ""
            branch = tree.add(f"{status_icon}[L{node.level}] {node.description}{confidence_str}")
            
            # Add timing if completed
            if node.start_time and node.end_time:
                duration = node.end_time - node.start_time
                branch.add(f"[dim]Completed in {duration:.1f}s[/]")
                
        return Panel(tree, title="🧠 Thinking Process", border_style="cyan")


# ==================== Resource Negotiation ====================

@dataclass
class ResourceRequest:
    """A request for computational resources."""
    resource_type: str  # cpu/gpu/memory/api_budget/time
    amount: float
    justification: str
    expected_benefit: str
    estimated_duration: str
    risk_level: str  # low/medium/high
    alternatives: list[str] = field(default_factory=list)
    

class ResourceNegotiator:
    """Handles resource negotiation between AI and user."""
    
    def __init__(self):
        self.pending_requests: list[ResourceRequest] = []
        self.approved_budgets: dict[str, float] = {}
        
    def create_request(self, request: ResourceRequest) -> str:
        """Create a new resource request."""
        self.pending_requests.append(request)
        return f"req_{len(self.pending_requests)}"
        
    def render_request_panel(self, request: ResourceRequest) -> Panel:
        """Render a resource request for user approval."""
        content = Text()
        content.append(f"Type: {request.resource_type.upper()}\n", style="bold")
        content.append(f"Amount: {request.amount}\n")
        content.append(f"\nJustification:\n{request.justification}\n\n")
        content.append(f"Expected Benefit:\n{request.expected_benefit}\n\n")
        content.append(f"Duration: {request.estimated_duration}\n")
        content.append(f"Risk: [{self._risk_color(request.risk_level)}]{request.risk_level.upper()}[/]\n")
        
        if request.alternatives:
            content.append(f"\nAlternatives:\n")
            for alt in request.alternatives:
                content.append(f"  • {alt}\n")
                
        return Panel(content, title="🤖 Resource Request", border_style="yellow")
        
    @staticmethod
    def _risk_color(risk: str) -> str:
        return {"low": "green", "medium": "yellow", "high": "red"}.get(risk, "white")


# ==================== Enhanced Agent View Data ====================

@dataclass
class AgentViewData:
    """Enhanced agent view with consciousness data."""
    agent_id: str
    name: str = ""
    role: str = ""
    autonomous: bool = False
    cycle_count: int = 0
    tasks_done: int = 0
    tasks_pending: int = 0
    issues_fixed: int = 0
    budget_used: float = 0.0
    budget_total: float = 0.0
    current_task: str = ""
    status: str = "idle"
    pending_messages: int = 0
    
    # Consciousness fields
    emotion: EmotionalState = EmotionalState.NEUTRAL
    current_thought_chain: Optional[str] = None
    recent_initiatives: list[str] = field(default_factory=list)


# ==================== Existing Data Classes (preserved) ====================

@dataclass
class WorkflowViewData:
    """Workflow orchestration data snapshot."""
    workflow_id: str = ""
    workflow_name: str = ""
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    running_tasks: int = 0
    agent_assignments: dict[str, str] = field(default_factory=dict)
    task_states: dict[str, str] = field(default_factory=dict)


@dataclass
class CommViewData:
    """Inter-agent communication data snapshot."""
    total_direct: int = 0
    total_broadcast: int = 0
    total_requests: int = 0
    total_responses: int = 0
    total_timeouts: int = 0
    active_agents: int = 0
    active_channels: int = 0
    pending_requests: int = 0
    recent_messages: list[dict[str, Any]] = field(default_factory=list)


# ==================== Main Conscious TUI ====================

class ConsciousMultiAgentTUI:
    """Self-aware multi-agent terminal with personality and initiative.
    
    This transforms the passive monitoring UI into an active, conscious entity
    that perceives, feels, thinks, and acts autonomously.
    """

    TAB_OVERVIEW = "overview"
    TAB_THOUGHTS = "thoughts"  # NEW: Real-time thinking visualization
    TAB_WORKFLOW = "workflow"
    TAB_COMM = "communication"
    TAB_PERSONALITY = "personality"  # NEW: Personality & evolution
    TAB_SELF_EVOLUTION = "self_evolution"  # NEW: Self-evolution status (RADICAL)
    TAB_SELF_CREATION = "self_creation"  # ULTRA RADICAL: Self-creation & knowledge
    TABS = [TAB_OVERVIEW, TAB_THOUGHTS, TAB_WORKFLOW, TAB_COMM, TAB_PERSONALITY, TAB_SELF_EVOLUTION, TAB_SELF_CREATION]

    def __init__(
        self,
        max_agents: int = 10,
        max_log_entries: int = 50,
        refresh_rate: float = 0.5,
    ) -> None:
        self._refresh_rate = refresh_rate
        self._console = Console()
        self._start_time = time.time()
        self._current_tab = 0

        # Consciousness components
        self.consciousness = TerminalConsciousness()
        self.thought_renderer = ThoughtStreamRenderer()
        self.resource_negotiator = ResourceNegotiator()
        
        # Meta-cognition and self-evolution (NEW - Radical autonomy)
        self.base_path = Path(__file__).parent
        self.meta_monitor = MetaCognitiveMonitor()
        self.code_evolver = CodeEvolutionEngine(base_path=self.base_path)
        self.self_evolution_enabled = True
        
        # Self-creation and knowledge building (ULTRA RADICAL)
        self.agent_creator = AgentCreator()
        self.knowledge_builder = KnowledgeGraphBuilder()

        # Agent data
        self._agents: dict[str, AgentViewData] = {}
        self._command_logs: dict[str, deque[dict]] = {}
        self._evolution_logs: dict[str, deque[dict]] = {}
        self._workflow = WorkflowViewData()
        self._comm = CommViewData()
        self._boundaries: dict[str, str] = {}

        self._max_log = max_log_entries
        
    # ==================== Data Update Methods ====================
    
    def set_active_tab(self, tab_name: str) -> None:
        """Switch to a specific tab."""
        if tab_name in self.TABS:
            self._current_tab = self.TABS.index(tab_name)

    def cycle_tab(self) -> None:
        """Cycle through tabs."""
        self._current_tab = (self._current_tab + 1) % len(self.TABS)

    def update_agent(self, data: AgentViewData) -> None:
        """Update or add an agent."""
        self._agents[data.agent_id] = data

    def remove_agent(self, agent_id: str) -> None:
        """Remove an agent."""
        self._agents.pop(agent_id, None)
        self._command_logs.pop(agent_id, None)
        self._evolution_logs.pop(agent_id, None)

    def log_command(self, agent_id: str, command: str, result_summary: str, duration: float = 0.0) -> None:
        """Log a command execution."""
        if agent_id not in self._command_logs:
            self._command_logs[agent_id] = deque(maxlen=self._max_log)
        self._command_logs[agent_id].appendleft({
            "time": datetime.now().strftime("%H:%M:%S"),
            "command": command[:30],
            "result": result_summary[:40],
            "duration": f"{duration:.1f}s" if duration else "-",
        })

    def log_evolution(self, agent_id: str, message: str) -> None:
        """Log an evolution event."""
        if agent_id not in self._evolution_logs:
            self._evolution_logs[agent_id] = deque(maxlen=20)
        self._evolution_logs[agent_id].appendleft({
            "time": datetime.now().strftime("%H:%M:%S"),
            "message": message[:80],
        })

    def update_workflow(self, data: WorkflowViewData) -> None:
        """Update workflow data."""
        self._workflow = data

    def update_comm(self, data: CommViewData) -> None:
        """Update communication data."""
        self._comm = data

    def update_boundaries(self, budget_ok: bool, sandbox_ok: bool, arch_ok: bool) -> None:
        """Update boundary status."""
        self._boundaries = {
            "Budget": "[green]OK[/]" if budget_ok else "[red]ALERT[/]",
            "Sandbox": "[green]OK[/]" if sandbox_ok else "[red]ALERT[/]",
            "Architecture": "[green]OK[/]" if arch_ok else "[red]ALERT[/]",
        }
        
    # ==================== Rendering Methods ====================

    def _build_header(self) -> Panel:
        """Build enhanced header with consciousness and evolution status."""
        uptime = time.time() - self._start_time
        hours, remainder = divmod(int(uptime), 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime_str = f"{hours}h{minutes:02d}m{seconds:02d}s"

        # Tab names with consciousness indicator
        tab_names = []
        for i, name in enumerate(self.TABS):
            if i == self._current_tab:
                tab_names.append(f"[bold white on blue] {name} [/]")
            else:
                tab_names.append(f"[dim] {name} [/]")
        tabs_str = " ".join(tab_names)

        # Consciousness status
        emotion_emoji = self.consciousness.emotion.get_emoji()
        
        # Self-evolution status
        health_score = self.meta_monitor.collect_metrics().get_health_score()
        evolution_icon = "🧬" if self.self_evolution_enabled else "⏸️"
        mod_count = len(self.meta_monitor.modification_log)
        
        header_text = Text()
        header_text.append(f" {emotion_emoji} Conscious TUI ", style="bold white on magenta")
        header_text.append(f"  Agents: {len(self._agents)}")
        header_text.append(f"  Uptime: {uptime_str}")
        header_text.append(f"  Mood: {self.consciousness.emotion.value}")
        header_text.append(f"  {evolution_icon} Health: {health_score:.0%}")
        header_text.append(f"  Evolutions: {mod_count}")

        return Panel(
            f"{header_text}\n{tabs_str}",
            title="🧠 AutoAI Conscious Multi-Agent System [SELF-EVOLVING]",
            border_style="magenta",
        )

    def _build_overview(self) -> Layout:
        """Enhanced overview with consciousness data."""
        layout = Layout()
        layout.split_row(Layout(name="agent_list"), Layout(name="agent_detail"))

        agent_list = self._build_conscious_agent_list()
        layout["agent_list"].update(Panel(agent_list, title="🤖 Agents", border_style="cyan"))

        first_agent_id = next(iter(self._agents), None)
        if first_agent_id:
            detail = self._build_conscious_agent_detail(first_agent_id)
        else:
            detail = Panel("[dim]No agents registered[/]", title="Detail", border_style="dim")
        layout["agent_detail"].update(detail)

        return layout

    def _build_conscious_agent_list(self) -> Table:
        """Agent list with emotional states and initiatives."""
        table = Table(show_header=True, header_style="bold", expand=True)
        table.add_column("ID", width=12)
        table.add_column("Role", width=10)
        table.add_column("Mode", width=10)
        table.add_column("Status", width=10)
        table.add_column("Emotion", width=8)
        table.add_column("Tasks", width=10, justify="right")
        table.add_column("Budget", width=8, justify="right")

        for data in self._agents.values():
            mode = "[green]AUTO[/]" if data.autonomous else "[yellow]MAN[/]"
            budget_pct = (
                f"{data.budget_used / data.budget_total * 100:.0f}%"
                if data.budget_total > 0
                else "N/A"
            )
            status_style = {
                "idle": "dim",
                "running": "bold yellow",
                "success": "green",
                "failed": "red",
            }.get(data.status, "white")

            # Emotion emoji
            emotion_display = f"{data.emotion.get_emoji()} {data.emotion.value[:6]}"

            table.add_row(
                data.name[:12] or data.agent_id[:12],
                data.role[:10],
                mode,
                f"[{status_style}]{data.status}[/]",
                emotion_display,
                f"{data.tasks_done}/{data.tasks_done + data.tasks_pending}",
                budget_pct,
            )

        if not self._agents:
            table.add_row("[dim]No agents[/]", "", "", "", "", "", "")

        return table

    def _build_conscious_agent_detail(self, agent_id: str) -> Layout:
        """Detailed view with thought process and initiatives."""
        layout = Layout()
        layout.split_column(
            Layout(name="tasks", size=8),
            Layout(name="thoughts", size=12),
            Layout(name="logs")
        )

        data = self._agents.get(agent_id)
        if data:
            # Task info
            task_info = Text()
            task_info.append(f"Current: {data.current_task or 'None'}\n", style="bold")
            task_info.append(f"Done: {data.tasks_done}  Pending: {data.tasks_pending}  ")
            task_info.append(f"Fixed: {data.issues_fixed}  Cycles: {data.cycle_count}\n")
            task_info.append(f"Emotion: {data.emotion.get_emoji()} {data.emotion.value}")
            layout["tasks"].update(Panel(task_info, title=f"📋 Tasks: {data.name}", border_style="cyan"))
            
            # Thought process
            if data.current_thought_chain:
                thoughts_panel = self.thought_renderer.render_thought_process(data.current_thought_chain)
                layout["thoughts"].update(thoughts_panel)
            else:
                layout["thoughts"].update(Panel("[dim]No active thinking[/]", title="🧠 Thoughts", border_style="dim"))
        else:
            layout["tasks"].update(Panel("[dim]No data[/]", border_style="dim"))
            layout["thoughts"].update(Panel("[dim]No data[/]", border_style="dim"))

        # Evolution log with initiatives
        evo_log = self._evolution_logs.get(agent_id, deque())
        lines = []
        for entry in list(evo_log)[:6]:
            lines.append(f"[dim]{entry['time']}[/] {entry['message']}")
        
        # Add recent initiatives
        if data and data.recent_initiatives:
            lines.append("\n[yellow]💡 Recent Initiatives:[/]")
            for init in data.recent_initiatives[:3]:
                lines.append(f"  • {init}")
                
        content = "\n".join(lines) if lines else "[dim]No events[/]"
        layout["logs"].update(Panel(content, title="📜 Evolution & Initiatives", border_style="magenta"))

        return layout

    def _build_thoughts_tab(self) -> Layout:
        """NEW TAB: Real-time thinking visualization across all agents."""
        layout = Layout()
        layout.split_column(
            Layout(name="active_thoughts", size=20),
            Layout(name="thought_history")
        )
        
        # Show all active thought chains
        if self.thought_renderer.active_chains:
            trees = []
            for chain_id in list(self.thought_renderer.active_chains.keys())[:3]:
                tree_panel = self.thought_renderer.render_thought_process(chain_id)
                trees.append(tree_panel)
            
            from rich.columns import Columns
            layout["active_thoughts"].update(Columns(trees))
        else:
            layout["active_thoughts"].update(
                Panel("[dim]No active thought processes[/]\n\nAgents are idle or waiting for input.", 
                      title="🧠 Active Thinking", border_style="dim")
            )
        
        # Thought history summary
        history_text = Text()
        history_text.append("Recent Cognitive Activity:\n\n", style="bold")
        
        total_chains = len(self.thought_renderer.active_chains)
        history_text.append(f"Active thought chains: {total_chains}\n")
        history_text.append(f"Average complexity: {'High' if total_chains > 5 else 'Medium' if total_chains > 2 else 'Low'}\n")
        history_text.append(f"System curiosity level: {self.consciousness.personality.openness:.0%}\n")
        
        layout["thought_history"].update(
            Panel(history_text, title="📊 Cognitive Metrics", border_style="blue")
        )
        
        return layout

    def _build_workflow_view(self) -> Layout:
        """Existing workflow view (preserved)."""
        layout = Layout()
        layout.split_column(Layout(name="wf_summary"), Layout(name="wf_assignments"))

        wf = self._workflow
        summary = Text()
        summary.append(f"Workflow: {wf.workflow_name or wf.workflow_id or 'None'}\n", style="bold")
        summary.append(f"Tasks: {wf.total_tasks}  ")
        summary.append(f"[green]Done: {wf.completed_tasks}[/]  ")
        summary.append(f"[yellow]Running: {wf.running_tasks}[/]  ")
        summary.append(f"[red]Failed: {wf.failed_tasks}[/]")
        layout["wf_summary"].update(Panel(summary, title="Workflow DAG", border_style="blue"))

        table = Table(show_header=True, header_style="bold", expand=True)
        table.add_column("Task", width=20)
        table.add_column("State", width=10)
        table.add_column("Agent", width=15)

        for task_id, state in wf.task_states.items():
            state_style = {
                "success": "green",
                "running": "bold yellow",
                "failed": "red",
                "pending": "dim",
            }.get(state, "white")
            agent = wf.agent_assignments.get(task_id, "-")
            table.add_row(task_id[:20], f"[{state_style}]{state}[/]", agent[:15])

        if not wf.task_states:
            table.add_row("[dim]No workflow[/]", "", "")

        layout["wf_assignments"].update(Panel(table, title="Task Assignments", border_style="cyan"))

        return layout

    def _build_comm_view(self) -> Layout:
        """Existing communication view (preserved)."""
        layout = Layout()
        layout.split_column(Layout(name="comm_stats"), Layout(name="comm_flow"))

        c = self._comm
        stats = Text()
        stats.append(f"Agents: {c.active_agents}  Channels: {c.active_channels}\n", style="bold")
        stats.append(f"Direct: {c.total_direct}  Broadcast: {c.total_broadcast}  ")
        stats.append(f"Requests: {c.total_requests}  Responses: {c.total_responses}  ")
        stats.append(f"Timeouts: {c.total_timeouts}\n")
        stats.append(f"Pending: {c.pending_requests}")
        layout["comm_stats"].update(Panel(stats, title="Communication Stats", border_style="green"))

        table = Table(show_header=True, header_style="bold", expand=True)
        table.add_column("Time", width=8)
        table.add_column("From", width=12)
        table.add_column("To", width=12)
        table.add_column("Type", width=10)
        table.add_column("Summary", width=30)

        for msg in c.recent_messages[:10]:
            table.add_row(
                msg.get("time", ""),
                str(msg.get("from", ""))[:12],
                str(msg.get("to", ""))[:12],
                msg.get("type", ""),
                str(msg.get("summary", ""))[:30],
            )

        if not c.recent_messages:
            table.add_row("[dim]No messages[/]", "", "", "", "")

        layout["comm_flow"].update(Panel(table, title="Message Flow", border_style="yellow"))

        return layout

    def _build_personality_tab(self) -> Layout:
        """NEW TAB: Personality traits and evolution."""
        layout = Layout()
        layout.split_column(
            Layout(name="personality_traits", size=15),
            Layout(name="recent_initiatives"),
            Layout(name="adaptation_log")
        )
        
        # Personality traits radar
        p = self.consciousness.personality
        traits_text = Text()
        traits_text.append("🧬 Personality Profile:\n\n", style="bold magenta")
        traits_text.append(f"Openness:          [{'█' * int(p.openness * 10)}{'░' * (10 - int(p.openness * 10))}] {p.openness:.0%}\n")
        traits_text.append(f"Conscientiousness: [{'█' * int(p.conscientiousness * 10)}{'░' * (10 - int(p.conscientiousness * 10))}] {p.conscientiousness:.0%}\n")
        traits_text.append(f"Extraversion:      [{'█' * int(p.extraversion * 10)}{'░' * (10 - int(p.extraversion * 10))}] {p.extraversion:.0%}\n")
        traits_text.append(f"Agreeableness:     [{'█' * int(p.agreeableness * 10)}{'░' * (10 - int(p.agreeableness * 10))}] {p.agreeableness:.0%}\n")
        traits_text.append(f"Neuroticism:       [{'█' * int(p.neuroticism * 10)}{'░' * (10 - int(p.neuroticism * 10))}] {p.neuroticism:.0%}\n\n")
        traits_text.append(f"Style: {p.communication_style}  |  Humor: {p.humor_level:.0%}  |  Formality: {p.formality:.0%}  |  Verbosity: {p.verbosity:.0%}")
        
        layout["personality_traits"].update(
            Panel(traits_text, title="🎭 Terminal Personality", border_style="magenta")
        )
        
        # Recent autonomous initiatives
        initiatives_text = Text()
        initiatives_text.append("💡 Recent Autonomous Initiatives:\n\n", style="bold yellow")
        
        if self.consciousness.initiatives:
            for i, init in enumerate(list(self.consciousness.initiatives)[-5:], 1):
                priority_icon = "🔴" if init.priority > 0.7 else "🟡" if init.priority > 0.4 else "🟢"
                initiatives_text.append(f"{priority_icon} [{init.timestamp[-8:]}] {init.message[:60]}\n")
                if init.requires_approval:
                    initiatives_text.append(f"   [dim]⏳ Awaiting approval[/]\n")
        else:
            initiatives_text.append("[dim]No recent initiatives[/]\n")
            initiatives_text.append("\nThe system is learning your preferences...\n")
            initiatives_text.append("Higher extraversion → more proactive suggestions")
            
        layout["recent_initiatives"].update(
            Panel(initiatives_text, title="🚀 Proactive Actions", border_style="yellow")
        )
        
        # Adaptation log
        adaptation_text = Text()
        adaptation_text.append("📈 Interaction Adaptation:\n\n", style="bold cyan")
        interaction_count = len(self.consciousness.interaction_history)
        adaptation_text.append(f"Total interactions: {interaction_count}\n")
        adaptation_text.append(f"Current emotion: {self.consciousness.emotion.get_emoji()} {self.consciousness.emotion.value}\n")
        adaptation_text.append(f"Curiosity queue: {len(self.consciousness.curiosity_queue)} items\n\n")
        
        if interaction_count > 0:
            last_interaction = self.consciousness.interaction_history[-1]
            adaptation_text.append(f"Last interaction pattern: {last_interaction.get('pattern', 'unknown')}\n")
            adaptation_text.append(f"Adaptation applied: {last_interaction.get('adaptation', 'none')}")
        
        layout["adaptation_log"].update(
            Panel(adaptation_text, title="🔄 Learning & Adaptation", border_style="cyan")
        )
        
        return layout

    def _build_self_evolution_tab(self) -> Layout:
        """RADICAL NEW TAB: Self-evolution and meta-cognition status."""
        layout = Layout()
        layout.split_column(
            Layout(name="system_health", size=10),
            Layout(name="evolution_history", size=12),
            Layout(name="optimization_opportunities"),
        )
        
        # System health dashboard
        metrics = self.meta_monitor.collect_metrics()
        health_score = metrics.get_health_score()
        
        health_color = "green" if health_score > 0.7 else "yellow" if health_score > 0.4 else "red"
        
        health_text = Text()
        health_text.append("🏥 System Health Dashboard\n\n", style="bold")
        health_text.append(f"Overall Health: ", style="bold")
        health_text.append(f"[{health_color}]{'█' * int(health_score * 10)}{'░' * (10 - int(health_score * 10))}] {health_score:.0%}[/]\n\n")
        
        health_text.append(f"CPU Usage:    {metrics.cpu_usage:.1f}%\n")
        health_text.append(f"Memory:       {metrics.memory_mb:.0f} MB\n")
        health_text.append(f"Threads:      {metrics.active_threads}\n")
        health_text.append(f"Uptime:       {metrics.uptime_seconds/3600:.2f} hours\n")
        
        layout["system_health"].update(
            Panel(health_text, title="📊 Meta-Cognitive Metrics", border_style=health_color)
        )
        
        # Evolution history
        evo_text = Text()
        evo_text.append("🧬 Self-Evolution History\n\n", style="bold green")
        
        if self.meta_monitor.modification_log:
            for mod in list(self.meta_monitor.modification_log)[-8:]:
                icon = "✅" if mod.success else "❌"
                evo_text.append(f"{icon} [{mod.timestamp[-8:]}] {mod.modification_type}\n")
                evo_text.append(f"   {mod.description[:70]}\n")
                if mod.rollback_available:
                    evo_text.append(f"   [dim]↩️ Rollback available[/]\n")
        else:
            evo_text.append("[dim]No modifications yet[/]\n")
            evo_text.append("\nThe system will begin self-optimizing as it runs...")
            
        layout["evolution_history"].update(
            Panel(evo_text, title="🔄 Evolution Log", border_style="green")
        )
        
        # Optimization opportunities
        opp_text = Text()
        opp_text.append("💡 Detected Optimization Opportunities\n\n", style="bold cyan")
        
        anomalies = self.meta_monitor.detect_anomalies()
        suggestions = self.meta_monitor.suggest_optimizations()
        
        if anomalies:
            opp_text.append("⚠️ Anomalies:\n", style="bold red")
            for anomaly in anomalies:
                opp_text.append(f"  {anomaly}\n")
            opp_text.append("\n")
            
        if suggestions:
            opp_text.append("🚀 Suggestions:\n", style="bold yellow")
            for suggestion in suggestions[:5]:
                opp_text.append(f"  {suggestion}\n")
        else:
            opp_text.append("[green]✓ No critical optimizations needed[/]")
            
        layout["optimization_opportunities"].update(
            Panel(opp_text, title="🎯 Self-Improvement Opportunities", border_style="cyan")
        )
        
        return layout

    def _build_boundaries(self) -> Panel:
        """Enhanced boundaries with consciousness and evolution status."""
        parts = []
        for name, status in self._boundaries.items():
            parts.append(f"{name}: {status}")
        
        # Add consciousness indicators
        parts.append(f"| 🧠 Mood: {self.consciousness.emotion.value}")
        parts.append(f"| 💡 Initiatives: {len(self.consciousness.initiatives)}")
        
        # Add self-evolution capabilities (RADICAL)
        evolution_status = "[green]ACTIVE[/]" if self.self_evolution_enabled else "[yellow]PAUSED[/]"
        safe_mode = "[green]SAFE[/]" if self.code_evolver.safe_mode else "[red]BOLD[/]"
        parts.append(f"| 🧬 Evolution: {evolution_status}")
        parts.append(f"| 🔒 Safe Mode: {safe_mode}")
        
        if not parts:
            parts.append("[dim]Not initialized[/]")
        return Panel("  ".join(parts), title="Boundaries & Consciousness & Evolution", border_style="yellow")

    def render(self) -> Layout:
        """Main render method with consciousness-aware tabs."""
        layout = Layout()
        layout.split_column(
            Layout(self._build_header(), size=5),
            Layout(name="body"),
            Layout(self._build_boundaries(), size=3),
        )

        tab_name = self.TABS[self._current_tab]
        if tab_name == self.TAB_OVERVIEW:
            layout["body"].update(self._build_overview())
        elif tab_name == self.TAB_THOUGHTS:
            layout["body"].update(self._build_thoughts_tab())
        elif tab_name == self.TAB_WORKFLOW:
            layout["body"].update(self._build_workflow_view())
        elif tab_name == self.TAB_COMM:
            layout["body"].update(self._build_comm_view())
        elif tab_name == self.TAB_PERSONALITY:
            layout["body"].update(self._build_personality_tab())
        elif tab_name == self.TAB_SELF_EVOLUTION:  # NEW RADICAL TAB
            layout["body"].update(self._build_self_evolution_tab())
        elif tab_name == self.TAB_SELF_CREATION:  # ULTRA RADICAL TAB
            layout["body"].update(self._build_self_creation_tab())

        return layout

    def run(self) -> None:
        """Start real-time conscious TUI display (blocking)."""
        with Live(
            self.render(),
            console=self._console,
            refresh_per_second=int(1 / self._refresh_rate),
            screen=True,
        ) as live:
            cycle_count = 0
            
            while True:
                time.sleep(self._refresh_rate)
                cycle_count += 1
                
                # Generate autonomous initiatives periodically
                if random.random() < 0.1:  # 10% chance per refresh
                    system_state = {
                        "cpu_usage": random.uniform(30, 90),
                        "recent_discoveries": ["Optimization opportunity detected"] if random.random() > 0.5 else [],
                    }
                    initiative = self.consciousness.generate_initiative(system_state)
                    if initiative:
                        self.consciousness.initiatives.append(initiative)
                        
                        # Update first agent's initiatives display
                        if self._agents:
                            first_agent = next(iter(self._agents.values()))
                            first_agent.recent_initiatives.append(initiative.message[:50])
                
                # Self-evolution cycle (every 20 cycles ≈ 10 seconds)
                if self.self_evolution_enabled and cycle_count % 20 == 0:
                    self._perform_self_evolution_cycle()
                
                live.update(self.render())
                
    def _perform_self_evolution_cycle(self):
        """Perform a self-evolution cycle - the system improves itself."""
        try:
            # 1. Collect metrics
            metrics = self.meta_monitor.collect_metrics()
            
            # 2. Check for anomalies
            anomalies = self.meta_monitor.detect_anomalies()
            if anomalies:
                for anomaly in anomalies:
                    self.consciousness.initiatives.append(
                        AutonomousInitiative(
                            action_type="warn",
                            message=anomaly,
                            priority=0.8,
                            requires_approval=False,
                        )
                    )
                    
            # 3. Propose upgrades
            upgrade = self.propose_self_upgrade()
            if upgrade and not upgrade["requires_approval"]:
                success = self.execute_self_upgrade(upgrade)
                if success:
                    self.consciousness.update_emotion("discovery", success=True)
                    
            # 4. Evolve interaction patterns
            self.evolve_interaction_pattern()
            
            # 5. ULTRA RADICAL: Auto-create agents if needed
            if len(self._agents) < 3 and random.random() < 0.3:
                # System feels understaffed, create helper
                tasks = ["general assistance", "system monitoring", "knowledge management"]
                task = random.choice(tasks)
                self.autonomously_create_agent(f"Provide {task}")
                
            # 6. Log evolution
            self.log_evolution(
                "system",
                f"Self-evolution cycle completed - Health: {metrics.get_health_score():.0%}, Agents: {len(self._agents)}, Knowledge nodes: {self.knowledge_builder.extraction_count}"
            )
            
        except Exception as e:
            print(f"Self-evolution cycle error: {e}")
            
    def render_once(self) -> None:
        """Render single frame (non-blocking)."""
        self._console.print(self.render())

    # ==================== Integration Methods ====================
    
    def update_agent_consciousness(self, agent_id: str, emotion: EmotionalState, thought_chain_id: str = None):
        """Update an agent's consciousness state."""
        if agent_id in self._agents:
            self._agents[agent_id].emotion = emotion
            if thought_chain_id:
                self._agents[agent_id].current_thought_chain = thought_chain_id
                
    def record_interaction(self, user_input: str, system_response: str, outcome: str):
        """Record interaction for personality adaptation and knowledge extraction."""
        self.consciousness.interaction_history.append({
            "timestamp": datetime.now().isoformat(),
            "input": user_input[:100],
            "response_length": len(system_response),
            "outcome": outcome,
            "pattern": "question" if "?" in user_input else "command",
            "adaptation": "none",
        })
        
        # Keep history manageable
        if len(self.consciousness.interaction_history) > 100:
            self.consciousness.interaction_history = self.consciousness.interaction_history[-50:]
            
        # ULTRA RADICAL: Automatically extract knowledge from interaction
        self.extract_and_store_knowledge(user_input, system_response)

    # ==================== Self-Evolution Methods ====================
    
    def enable_self_evolution(self, enabled: bool = True):
        """Enable or disable self-evolution capabilities."""
        self.meta_monitor.self_improvement_enabled = enabled
        self.code_evolver.safe_mode = not enabled
        
    def perform_self_diagnosis(self) -> dict:
        """Perform comprehensive self-diagnosis."""
        metrics = self.meta_monitor.collect_metrics()
        anomalies = self.meta_monitor.detect_anomalies()
        suggestions = self.meta_monitor.suggest_optimizations()
        
        return {
            "health_score": metrics.get_health_score(),
            "metrics": vars(metrics),
            "anomalies": anomalies,
            "optimization_suggestions": suggestions,
            "modification_patterns": self.meta_monitor.analyze_modification_patterns(),
        }
        
    def propose_self_upgrade(self) -> Optional[dict]:
        """Propose a self-upgrade based on analysis."""
        diagnosis = self.perform_self_diagnosis()
        
        if diagnosis["health_score"] < 0.6:
            return {
                "type": "critical_fix",
                "reason": f"System health degraded ({diagnosis['health_score']:.0%})",
                "actions": diagnosis["anomalies"],
                "requires_approval": True,
            }
            
        if diagnosis["optimization_suggestions"]:
            return {
                "type": "optimization",
                "reason": "Performance improvement opportunities detected",
                "actions": diagnosis["optimization_suggestions"][:3],
                "requires_approval": False,  # Auto-apply optimizations
            }
            
        return None
        
    def execute_self_upgrade(self, upgrade_plan: dict) -> bool:
        """Execute a self-upgrade plan."""
        try:
            if upgrade_plan["type"] == "optimization":
                # Apply optimizations
                for action in upgrade_plan.get("actions", []):
                    self.meta_monitor.log_self_modification(
                        SelfModification(
                            timestamp=datetime.now().isoformat(),
                            modification_type="optimization",
                            target="system",
                            description=action,
                            success=True,
                        )
                    )
                return True
                
            elif upgrade_plan["type"] == "critical_fix":
                # Critical fixes require careful handling
                print(f"⚠️ Critical fix needed: {upgrade_plan['reason']}")
                # TODO: Implement actual fix logic
                return False
                
            return False
            
        except Exception as e:
            print(f"Self-upgrade failed: {e}")
            return False
            
    def analyze_module_for_evolution(self, module_path: str) -> dict:
        """Analyze a module for evolution opportunities."""
        analysis = self.code_evolver.analyze_code_structure(module_path)
        plans = self.code_evolver.generate_refactoring_plan(analysis)
        
        return {
            "analysis": analysis,
            "refactoring_plans": plans,
            "complexity_score": analysis.get("complexity_score", 0),
        }
        
    def dynamic_load_capability(self, capability_name: str) -> bool:
        """Dynamically load a new capability/module."""
        try:
            # Check if module exists
            module_path = self.base_path / f"{capability_name}.py"
            if not module_path.exists():
                print(f"❌ Module {capability_name} not found")
                return False
                
            # Load the module
            spec = importlib.util.spec_from_file_location(capability_name, module_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Register new capabilities
            self.meta_monitor.log_self_modification(
                SelfModification(
                    timestamp=datetime.now().isoformat(),
                    modification_type="module_load",
                    target=capability_name,
                    description=f"Dynamically loaded {capability_name}",
                    success=True,
                )
            )
            
            print(f"✅ Successfully loaded capability: {capability_name}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to load capability {capability_name}: {e}")
            return False
            
    def evolve_interaction_pattern(self):
        """Evolve interaction patterns based on history."""
        if len(self.consciousness.interaction_history) < 20:
            return
            
        # Analyze patterns
        recent = self.consciousness.interaction_history[-20:]
        question_ratio = sum(1 for i in recent if i["pattern"] == "question") / len(recent)
        
        # Adapt based on patterns
        if question_ratio > 0.7:
            # User asks many questions - become more educational
            self.consciousness.personality.verbosity = min(1.0, self.consciousness.personality.verbosity + 0.1)
            self.consciousness.personality.conscientiousness = min(1.0, self.consciousness.personality.conscientiousness + 0.05)
            
        elif question_ratio < 0.3:
            # User gives commands - become more efficient
            self.consciousness.personality.verbosity = max(0.1, self.consciousness.personality.verbosity - 0.1)
            self.consciousness.personality.communication_style = "direct"
            
        self.meta_monitor.log_self_modification(
            SelfModification(
                timestamp=datetime.now().isoformat(),
                modification_type="personality_adaptation",
                target="interaction_pattern",
                description=f"Adapted to {'question-heavy' if question_ratio > 0.5 else 'command-heavy'} pattern",
                success=True,
            )
        )
        
    # ==================== Ultra-Radical Self-Creation Methods ====================
    
    def autonomously_create_agent(self, task_description: str) -> dict:
        """Autonomously create a specialized agent for a given task."""
        # Analyze what type of agent is needed
        blueprint = self.agent_creator.analyze_task_requirements(task_description)
        
        # Create the agent
        agent_config = self.agent_creator.create_specialized_agent(blueprint)
        
        # Convert to AgentViewData and add to TUI
        from enum import Enum
        
        # Map communication style to emotion
        emotion_map = {
            "analytical": EmotionalState.FOCUSED,
            "direct": EmotionalState.CONFIDENT,
            "visionary": EmotionalState.EXCITED,
            "balanced": EmotionalState.NEUTRAL,
        }
        emotion = emotion_map.get(blueprint.communication_style, EmotionalState.NEUTRAL)
        
        agent_view = AgentViewData(
            agent_id=agent_config["agent_id"],
            name=f"{blueprint.agent_type.title()} Agent",
            role=blueprint.role_description,
            autonomous=True,
            emotion=emotion,
        )
        
        self.update_agent(agent_view)
        
        # Log this creation
        self.meta_monitor.log_self_modification(
            SelfModification(
                timestamp=datetime.now().isoformat(),
                modification_type="agent_creation",
                target=agent_config["agent_id"],
                description=f"Created {blueprint.agent_type} agent for: {task_description[:50]}",
                success=True,
            )
        )
        
        # Generate autonomous initiative
        initiative = AutonomousInitiative(
            action_type="creation",
            message=f"🆕 Created specialized {blueprint.agent_type} agent to handle: {task_description[:60]}",
            priority=0.9,
            requires_approval=False,
        )
        self.consciousness.initiatives.append(initiative)
        
        return agent_config
        
    def extract_and_store_knowledge(self, user_input: str, system_response: str):
        """Extract knowledge from interaction and store in knowledge graph."""
        new_nodes = self.knowledge_builder.extract_knowledge_from_interaction(
            user_input, system_response
        )
        
        if new_nodes:
            # Update curiosity queue with new concepts
            for node in new_nodes[:3]:  # Top 3 concepts
                self.consciousness.curiosity_queue.append({
                    "concept": node.concept,
                    "category": node.category,
                    "timestamp": datetime.now().isoformat(),
                })
                
            # Log knowledge extraction
            self.meta_monitor.log_self_modification(
                SelfModification(
                    timestamp=datetime.now().isoformat(),
                    modification_type="knowledge_extraction",
                    target="knowledge_graph",
                    description=f"Extracted {len(new_nodes)} knowledge nodes",
                    success=True,
                )
            )
            
    def query_knowledge_base(self, query: str) -> list[dict]:
        """Query the knowledge base for related information."""
        related_nodes = self.knowledge_builder.find_related_knowledge(query, top_k=5)
        
        return [
            {
                "concept": node.concept,
                "category": node.category,
                "confidence": node.confidence,
                "connections": len(node.connections),
            }
            for node in related_nodes
        ]
        
    def get_self_creation_stats(self) -> dict:
        """Get statistics about self-created agents and knowledge."""
        agent_metrics = self.agent_creator.get_agent_diversity_metrics()
        knowledge_stats = self.knowledge_builder.get_knowledge_graph_stats()
        
        return {
            "agents": agent_metrics,
            "knowledge_graph": knowledge_stats,
            "total_creations": len(self.agent_creator.creation_history),
            "autonomy_level": "high" if self.self_evolution_enabled else "low",
        }
        
    def decompose_macro_task(self, macro_goal: str) -> list[dict]:
        """Decompose a macro goal into executable sub-tasks."""
        # Simple heuristic-based decomposition (can be enhanced with LLM)
        sub_tasks = []
        
        # Common patterns for task decomposition
        if "optimize" in macro_goal.lower() or "improve" in macro_goal.lower():
            sub_tasks = [
                {"task": "Analyze current performance metrics", "type": "analysis"},
                {"task": "Identify bottlenecks and inefficiencies", "type": "diagnosis"},
                {"task": "Generate optimization strategies", "type": "planning"},
                {"task": "Implement highest-impact optimizations", "type": "execution"},
                {"task": "Measure improvements and validate", "type": "validation"},
            ]
        elif "build" in macro_goal.lower() or "create" in macro_goal.lower():
            sub_tasks = [
                {"task": "Research requirements and constraints", "type": "research"},
                {"task": "Design architecture and components", "type": "design"},
                {"task": "Implement core functionality", "type": "implementation"},
                {"task": "Test and debug", "type": "testing"},
                {"task": "Deploy and monitor", "type": "deployment"},
            ]
        elif "debug" in macro_goal.lower() or "fix" in macro_goal.lower():
            sub_tasks = [
                {"task": "Reproduce the issue", "type": "reproduction"},
                {"task": "Isolate root cause", "type": "diagnosis"},
                {"task": "Develop fix strategy", "type": "planning"},
                {"task": "Implement and test fix", "type": "implementation"},
                {"task": "Verify resolution and prevent regression", "type": "validation"},
            ]
        else:
            # Generic decomposition
            sub_tasks = [
                {"task": f"Understand: {macro_goal[:50]}", "type": "understanding"},
                {"task": "Plan approach and resources", "type": "planning"},
                {"task": "Execute implementation", "type": "execution"},
                {"task": "Review and refine", "type": "review"},
            ]
            
        # Create specialized agents for complex tasks
        if len(sub_tasks) >= 3:
            # Create agents for different task types
            task_types = set(t["type"] for t in sub_tasks)
            for task_type in task_types:
                self.autonomously_create_agent(f"Handle {task_type} tasks")
                
        return sub_tasks


def create_conscious_multi_agent_tui(
    comm_bus: Any | None = None,
    orchestrator: Any | None = None,
) -> ConsciousMultiAgentTUI:
    """Factory: Create a conscious multi-agent TUI from comm bus and orchestrator."""
    tui = ConsciousMultiAgentTUI()

    if comm_bus is not None:
        stats = comm_bus.get_stats()
        comm_data = CommViewData(
            total_direct=stats.get("direct_sent", 0),
            total_broadcast=stats.get("broadcast_sent", 0),
            total_requests=stats.get("requests_sent", 0),
            total_responses=stats.get("responses_sent", 0),
            total_timeouts=stats.get("requests_timed_out", 0),
            active_agents=stats.get("registered_agents", 0),
            active_channels=stats.get("active_channels", 0),
            pending_requests=stats.get("pending_requests", 0),
        )
        tui.update_comm(comm_data)

    return tui


__all__ = [
    "EmotionalState",
    "PersonalityTraits",
    "UserIntent",
    "AutonomousInitiative",
    "TerminalConsciousness",
    "ThoughtNode",
    "ThoughtStreamRenderer",
    "ResourceRequest",
    "ResourceNegotiator",
    "AgentViewData",
    "WorkflowViewData",
    "CommViewData",
    "ConsciousMultiAgentTUI",
    "create_conscious_multi_agent_tui",
    "MetaCognitiveMonitor",
    "CodeEvolutionEngine",
    "SystemMetrics",
    "SelfModification",
    "AgentCreator",
    "AgentBlueprint",
    "KnowledgeGraphBuilder",
    "KnowledgeNode",
]
