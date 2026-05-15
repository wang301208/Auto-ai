"""Phase epsilon: 涌现能力测试 - 目标涌现/自我意识/因果推理/进化压力/工具创造"""
from __future__ import annotations

import time
import pytest

from autoai.goal_emergence import GoalEmergenceEngine, EmergentGoal, GoalOrigin, DesireSystem, DesireType
from autoai.self_awareness import SelfAwarenessLoop, CognitiveLoad, CapabilityBoundary, KnowledgeGap, AwarenessSnapshot
from autoai.causal_reasoning import CausalGraph, CausalNode, CausalEdge, CausalReasoner, InterventionResult
from autoai.evolution_pressure import EvolutionPressure, FitnessEvaluator, AgentGenome, FitnessReport, NicheSpec
from autoai.tool_creation import ToolCreator, ToolSpec, CreatedTool, ToolRegistry


# === 目标涌现 ===

class TestGoalEmergence:
    def test_emergent_goal_creation(self):
        goal = EmergentGoal(description="探索新API", origin=GoalOrigin.CURIOSITY)
        assert goal._id != ""
        assert goal.state.value == "dormant"

    def test_goal_lifecycle(self):
        goal = EmergentGoal(description="优化性能", origin=GoalOrigin.EFFICIENCY, priority=0.7)
        goal.activate()
        assert goal.state.value == "active"
        goal.start_pursuing()
        assert goal.state.value == "pursuing"
        goal.mark_achieved()
        assert goal.state.value == "achieved"
        assert goal.progress == 1.0

    def test_goal_abandon(self):
        goal = EmergentGoal(description="不现实的目标", origin=GoalOrigin.CURIOSITY)
        goal.abandon("资源不足")
        assert goal.state.value == "abandoned"
        assert len(goal.evidence) > 0

    def test_engine_observe_and_emerge(self):
        engine = GoalEmergenceEngine(agent_id="test")
        for _ in range(5):
            engine.observe_outcome("api_call", success=False)
        goals = engine.emerge_goals()
        assert len(goals) >= 1
        assert goals[0].origin == GoalOrigin.ROBUSTNESS

    def test_unexplored_goal(self):
        engine = GoalEmergenceEngine(agent_id="test")
        engine.observe_unexplored("quantum_computing")
        goals = engine.emerge_goals()
        assert len(goals) >= 1
        assert goals[0].origin == GoalOrigin.CURIOSITY

    def test_performance_goal(self):
        engine = GoalEmergenceEngine(agent_id="test")
        for _ in range(3):
            engine.observe_outcome("heavy_compute", success=True, duration_ms=3000)
        goals = engine.emerge_goals()
        perf_goals = [g for g in goals if g.origin == GoalOrigin.EFFICIENCY]
        assert len(perf_goals) >= 1

    def test_prioritize(self):
        engine = GoalEmergenceEngine(agent_id="test")
        for _ in range(5):
            engine.observe_outcome("fail_op", success=False)
        engine.emerge_goals()
        for g in engine.get_all_goals():
            g.activate()
        ranked = engine.prioritize()
        assert len(ranked) >= 1

    def test_update_progress(self):
        engine = GoalEmergenceEngine(agent_id="test")
        for _ in range(5):
            engine.observe_outcome("op", success=False)
        goals = engine.emerge_goals()
        if goals:
            engine.update_progress(goals[0]._id, 0.5)
            assert goals[0].progress == 0.5
            engine.update_progress(goals[0]._id, 1.0)
            assert goals[0].state.value == "achieved"

    def test_no_duplicate_goals(self):
        engine = GoalEmergenceEngine(agent_id="test")
        for _ in range(5):
            engine.observe_outcome("same_op", success=False)
        g1 = engine.emerge_goals()
        g2 = engine.emerge_goals()
        assert len(g1) >= 1
        assert len(g2) == 0 or all(g._id not in {x._id for x in g1} for g in g2)


class TestDesireSystem:
    def test_desires_initialized(self):
        ds = DesireSystem()
        assert len(ds.get_urgent_desires()) > 0

    def test_satisfy_and_frustrate(self):
        ds = DesireSystem()
        ds.frustrate(DesireType.CURIOSITY)
        d = ds.get_desire(DesireType.CURIOSITY)
        assert d.frustration_count == 1
        ds.satisfy(DesireType.CURIOSITY)
        assert d.satisfaction_count == 1

    def test_motivation_vector(self):
        ds = DesireSystem()
        mv = ds.get_motivation_vector()
        assert "curiosity" in mv
        assert "safety" in mv

    def test_adjust_strength(self):
        ds = DesireSystem()
        ds.adjust_strength(DesireType.AUTONOMY, 0.3)
        d = ds.get_desire(DesireType.AUTONOMY)
        assert d.strength > 0.6


# === 自我意识 ===

class TestSelfAwareness:
    def test_cognitive_load_levels(self):
        low = CognitiveLoad(active_tasks=1)
        assert low.level.value == "low"
        high = CognitiveLoad(active_tasks=10, context_window_usage=0.95, memory_pressure=0.9)
        assert high.level.value in ("high", "critical")

    def test_needs_relief(self):
        load = CognitiveLoad(active_tasks=10, memory_pressure=0.9, context_window_usage=0.9, pending_decisions=5)
        assert load.needs_relief

    def test_capability_boundary(self):
        cap = CapabilityBoundary(capability="code_gen", confidence=0.7, evidence_count=5)
        assert cap.is_within_boundary
        assert not cap.needs_learning

    def test_knowledge_gap_critical(self):
        gap = KnowledgeGap(domain="rust", relevance=0.9, depth=0.1)
        assert gap.is_critical
        assert gap.priority > 0.7

    def test_awareness_snapshot(self):
        snap = AwarenessSnapshot(
            cognitive_load=CognitiveLoad(),
            capabilities=[CapabilityBoundary(capability="test", confidence=0.8)],
            knowledge_gaps=[KnowledgeGap(domain="x", relevance=0.5, depth=0.3)],
        )
        assert 0.0 <= snap.overall_self_awareness <= 1.0

    def test_loop_reflect(self):
        loop = SelfAwarenessLoop(agent_id="test")
        loop.update_load(active_tasks=3)
        snap = loop.reflect()
        assert snap.cognitive_load.active_tasks == 3

    def test_capability_testing(self):
        loop = SelfAwarenessLoop(agent_id="test")
        loop.register_capability("search", confidence=0.5)
        loop.test_capability("search", success=True)
        loop.test_capability("search", success=True)
        cap = loop._capabilities["search"]
        assert cap.confidence > 0.5

    def test_suggest_relief(self):
        loop = SelfAwarenessLoop(agent_id="test")
        loop.update_load(active_tasks=10, context_usage=0.95, memory_pressure=0.9, pending_decisions=5)
        suggestions = loop.suggest_relief()
        assert len(suggestions) >= 1

    def test_learning_plan(self):
        loop = SelfAwarenessLoop(agent_id="test")
        loop.discover_gap("wasm", relevance=0.9, depth=0.1)
        plan = loop.get_learning_plan()
        assert len(plan) >= 1


# === 因果推理 ===

class TestCausalReasoning:
    def test_dag_no_cycle(self):
        g = CausalGraph()
        g.add_edge("X", "Y")
        g.add_edge("Y", "Z")
        assert len(g.edges) == 2

    def test_cycle_rejected(self):
        g = CausalGraph()
        g.add_edge("X", "Y")
        result = g.add_edge("Y", "X")
        assert result.strength == 0
        assert len(g.edges) == 1

    def test_confounders(self):
        g = CausalGraph()
        g.add_edge("Z", "X")
        g.add_edge("Z", "Y")
        g.add_edge("X", "Y")
        confounders = g.get_confounders("X", "Y")
        assert "Z" in confounders

    def test_do_intervention(self):
        g = CausalGraph()
        g.add_edge("X", "Y")
        reasoner = CausalReasoner(g)
        result = reasoner.do_intervention("X", value=1)
        assert result.intervention == "do(X=1)"

    def test_effect_estimation(self):
        g = CausalGraph()
        g.add_edge("X", "Y", strength=0.7)
        reasoner = CausalReasoner(g)
        est = reasoner.estimate_effect("X", "Y")
        assert est["estimated_effect"] == 0.7

    def test_counterfactual(self):
        g = CausalGraph()
        reasoner = CausalReasoner(g)
        cf = reasoner.counterfactual("X", actual_value=1, counterfactual_value=0, effect="Y")
        assert "question" in cf
        assert cf["requires_abduction"]

    def test_ancestors(self):
        g = CausalGraph()
        g.add_edge("A", "B")
        g.add_edge("B", "C")
        assert "A" in g.get_ancestors("C")


# === 进化压力 ===

class TestEvolutionPressure:
    def test_genome_mutate(self):
        genome = AgentGenome(agent_id="g1", strategy_params={"lr": 0.5, "temp": 0.7})
        child = genome.mutate(rate=1.0)
        assert child.generation == 1
        assert child.parent_ids == ["g1"]

    def test_genome_crossover(self):
        a = AgentGenome(agent_id="a", strategy_params={"x": 0.3, "y": 0.7})
        b = AgentGenome(agent_id="b", strategy_params={"x": 0.9, "y": 0.1})
        child = AgentGenome.crossover(a, b)
        assert child.generation == 1
        assert len(child.parent_ids) == 2

    def test_fitness_evaluator(self):
        ev = FitnessEvaluator()
        ev.record("a1", "efficiency", 0.8)
        ev.record("a1", "robustness", 0.7)
        report = ev.evaluate("a1")
        assert report.overall > 0.0

    def test_niche_compatibility(self):
        niche = NicheSpec(name="fast_agent", required_dimensions={"efficiency": 0.7})
        compat = niche.compatibility({"efficiency": 0.8})
        assert compat >= 0.9

    def test_evolution_select(self):
        evo = EvolutionPressure(selection_threshold=0.2)
        genome = AgentGenome(agent_id="a1", strategy_params={"x": 0.5})
        evo.register_genome(genome)
        evo.record_fitness("a1", "efficiency", 0.7)
        evo.record_fitness("a1", "robustness", 0.6)
        results = evo.select()
        assert "a1" in results

    def test_evolution_evolve(self):
        evo = EvolutionPressure()
        for i in range(3):
            genome = AgentGenome(agent_id=f"a{i}", strategy_params={"x": 0.5})
            evo.register_genome(genome)
            evo.record_fitness(f"a{i}", "efficiency", 0.6)
        offspring = evo.evolve()
        assert len(offspring) >= 3

    def test_fitness_report_viable(self):
        report = FitnessReport(agent_id="t", scores={"efficiency": 0.5}, overall=0.5)
        assert report.is_viable

    def test_adapted_fitness(self):
        genome = AgentGenome(agent_id="t", fitness_history=[0.3, 0.5, 0.7, 0.8])
        assert genome.adapted_fitness > 0.5


# === 工具创造 ===

class TestToolCreation:
    def test_tool_spec(self):
        spec = ToolSpec(name="my_tool", description="测试工具", parameters={"x": "int"})
        assert spec.risk_level == "low"

    def test_created_tool_lifecycle(self):
        spec = ToolSpec(name="calc", description="计算")
        tool = CreatedTool(spec=spec, implementation="def calc(x): return x*2")
        assert tool.status.value == "draft"
        assert not tool.is_usable

    def test_tool_registry(self):
        registry = ToolRegistry()
        spec = ToolSpec(name="hello", description="打招呼")
        tool = CreatedTool(spec=spec, implementation="def hello(): return 'hi'", status=CreatedTool.__dataclass_fields__['status'].default)
        tool.status = __import__("autoai.tool_creation.creator", fromlist=["ToolStatus"]).ToolStatus.TESTED
        registry.register(tool)
        assert registry.count == 1

    def test_analyze_gap(self):
        creator = ToolCreator(agent_id="test")
        specs = creator.analyze_gap(["process_csv", "validate_json"])
        assert len(specs) == 2

    def test_design_tool(self):
        creator = ToolCreator(agent_id="test")
        spec = ToolSpec(name="auto_process", description="处理", parameters={"input_data": "str"})
        tool = creator.design_tool(spec, "file_processor")
        assert tool.status.value == "draft"
        assert "def auto_process" in tool.implementation

    def test_test_tool(self):
        creator = ToolCreator(agent_id="test")
        spec = ToolSpec(name="simple_func", description="简单", parameters={})
        impl = "def simple_func(): return 42"
        tool = CreatedTool(spec=spec, implementation=impl)
        tool = creator.test_tool(tool, test_inputs=[{}])
        assert tool.status.value in ("tested", "rejected")

    def test_create_from_need(self):
        creator = ToolCreator(agent_id="test")
        tool = creator.create_from_need("process_data", "data_transform")
        assert tool is not None

    def test_creator_stats(self):
        creator = ToolCreator(agent_id="test")
        assert "created_count" in creator.stats
        assert "templates" in creator.stats
