"""Phase α 全模块集成测试：验证所有新实现的激进自主架构组件。"""
import pytest
import asyncio
import time


class TestLayeredMemory:
    """测试六层分层记忆系统。"""

    def test_memory_layers_exist(self):
        from autoai.memory.layered import MemoryLayer
        assert len(MemoryLayer) == 6
        assert MemoryLayer.SENSORY.value == 0
        assert MemoryLayer.SPECIES.value == 5

    def test_forgetting_curve(self):
        from autoai.memory.layered import ForgettingCurve
        p_now = ForgettingCurve.recall_probability(0, 0.01)
        assert abs(p_now - 1.0) < 0.001
        p_short = ForgettingCurve.recall_probability(100, 0.001)
        assert 0 < p_short < 1.0
        p_long = ForgettingCurve.recall_probability(10000, 0.001)
        assert 0 < p_long < p_short

    def test_layered_memory_store(self):
        from autoai.memory.layered.hierarchy import LayeredMemoryStore, LayeredMemoryItem, MemoryLayer
        store = LayeredMemoryStore(MemoryLayer.WORKING)
        item = LayeredMemoryItem(content="测试记忆", importance=0.8)
        store.put("test_1", item)
        assert store.size() == 1
        retrieved = store.get("test_1")
        assert retrieved is not None
        assert retrieved.content == "测试记忆"
        assert retrieved.access_count == 1

    def test_layered_memory_system(self):
        from autoai.memory.layered import LayeredMemorySystem, MemoryLayer
        system = LayeredMemorySystem()
        key = system.store("重要经验", MemoryLayer.LONG_TERM, importance=0.9)
        assert key.startswith("L3_")
        stats = system.get_layer_stats()
        assert "L3_LONG_TERM" in stats
        assert stats["L3_LONG_TERM"] == 1

    def test_sensory_memory_ttl(self):
        from autoai.memory.layered.providers import SensoryMemory
        from autoai.memory.layered.hierarchy import LayeredMemoryItem
        sensory = SensoryMemory(ttl_seconds=0.01)
        item = LayeredMemoryItem(content="瞬时感知")
        sensory.put("s1", item)
        assert sensory.size() == 1
        time.sleep(0.02)
        result = sensory.get("s1")
        assert result is None

    def test_species_memory_immutable(self):
        from autoai.memory.layered.providers import SpeciesMemory
        from autoai.memory.layered.hierarchy import LayeredMemoryItem
        species = SpeciesMemory()
        item = LayeredMemoryItem(content="种族知识", importance=0.9)
        species.put("sp1", item)
        assert species.size() == 1
        result = species.remove("sp1")
        assert result is None
        assert species.size() == 1

    def test_meta_memory_strategy(self):
        from autoai.memory.layered.providers import MetaMemory
        meta = MetaMemory()
        meta.update_strategy("routing", {"strategy": "cost_optimal", "threshold": 0.5})
        strategy = meta.get_strategy("routing")
        assert strategy is not None
        assert strategy["strategy"] == "cost_optimal"

    def test_consolidation(self):
        from autoai.memory.layered import LayeredMemorySystem, MemoryLayer
        system = LayeredMemorySystem()
        for i in range(5):
            system.store(f"工作记忆{i}", MemoryLayer.WORKING, importance=0.7)
        stats = system.consolidate()
        assert isinstance(stats, dict)


class TestMeshNetwork:
    """测试Agent Mesh自组织网络。"""

    def test_gossip_member(self):
        from autoai.mesh import GossipMember, MemberState
        member = GossipMember(node_id="agent-1", address="127.0.0.1", port=7946)
        assert member.state == MemberState.ALIVE
        assert "agent-1" in member.key

    def test_gossip_protocol(self):
        from autoai.mesh import GossipProtocol, GossipMember
        node = GossipMember(node_id="self", address="127.0.0.1", port=7946)
        gossip = GossipProtocol(self_node=node)
        other = GossipMember(node_id="other", address="127.0.0.1", port=7947)
        gossip.add_member(other)
        assert len(gossip.members) == 2
        msg = gossip.create_gossip_message()
        assert msg["type"] == "gossip"
        assert "members" in msg

    def test_crdt_gcounter(self):
        from autoai.mesh.crdt import GCounter
        a = GCounter("node_a")
        b = GCounter("node_b")
        a.increment(5)
        b.increment(3)
        assert a.value == 5
        assert b.value == 3
        a.merge(b)
        assert a.value == 8

    def test_crdt_lww_register(self):
        from autoai.mesh.crdt import LWWRegister
        import time
        a = LWWRegister("node_a", "old_value")
        time.sleep(0.01)
        b = LWWRegister("node_b", "new_value")
        a.merge(b)
        assert a.value == "new_value"

    def test_crdt_orset(self):
        from autoai.mesh.crdt import ORSet
        s = ORSet("node_a")
        s.add("item1")
        s.add("item2")
        assert s.contains("item1")
        s.remove("item1")
        assert not s.contains("item1")

    def test_mesh_node(self):
        from autoai.mesh import MeshNode, MeshConfig
        config = MeshConfig(node_id="test-node")
        node = MeshNode(config)
        assert node.node_id == "test-node"
        status = node.get_status()
        assert status["node_id"] == "test-node"

    def test_mesh_coordinator(self):
        from autoai.mesh import MeshCoordinator, MeshConfig
        coord = MeshCoordinator()
        stats = coord.get_topology_stats()
        assert stats["total_nodes"] == 0


class TestMCPProtocol:
    """测试MCP协议双向集成。"""

    def test_mcp_tool(self):
        from autoai.mcp import MCPTool
        tool = MCPTool(name="read_file", description="读取文件", input_schema={"path": {"type": "string"}})
        fmt = tool.to_mcp_format()
        assert fmt["name"] == "read_file"
        assert "inputSchema" in fmt

    def test_mcp_server(self):
        from autoai.mcp import MCPServer, MCPTool, MCPToolCall
        server = MCPServer("test-server")
        tool = MCPTool(name="test_tool", description="测试工具")
        server.register_tool(tool, handler=lambda: "ok")
        assert len(server.list_tools()) == 1
        info = server.handle_initialize_request()
        assert info["protocolVersion"] == "2024-11-05"

    def test_mcp_server_handle_call(self):
        from autoai.mcp import MCPServer, MCPTool, MCPToolCall
        server = MCPServer()
        server.register_ability_as_tool(
            "compute", "计算", {"expr": {"type": "string"}}, handler=lambda expr="": eval(expr) if expr else 0
        )
        call = MCPToolCall(tool_name="autoai_compute", arguments={"expr": "2+3"})
        result = asyncio.run(server.handle_call(call))
        assert result.success

    def test_mcp_auto_adapter(self):
        from autoai.mcp import MCPAutoAdapter
        adapter = MCPAutoAdapter()
        framework = adapter.detect_framework("使用LangChain的Agent框架")
        assert framework == "langchain"
        result = adapter.generate_adapter("langchain")
        assert result.confidence > 0.5
        assert "LangChainMCPAdapter" in result.adapter_code


class TestSafetyIntuition:
    """测试安全直觉系统。"""

    def test_intuition_trainer(self):
        from autoai.safety_intuition import IntuitionTrainer
        trainer = IntuitionTrainer()
        experiences = asyncio.run(trainer.train())
        assert len(experiences) > 0
        assert any(e.severity.value >= 3 for e in experiences)

    def test_safety_intuition_judge(self):
        from autoai.safety_intuition import SafetyIntuition, HarmExperience, HarmSeverity
        experiences = [
            HarmExperience(operation="rm -rf", category="destructive", severity=HarmSeverity.CRITICAL),
            HarmExperience(operation="sudo", category="privilege_escalation", severity=HarmSeverity.HIGH),
        ]
        intuition = SafetyIntuition(experiences)
        j = intuition.judge("rm -rf /tmp")
        assert not j.should_proceed
        assert j.suggested_alternative != ""

    def test_safety_learner(self):
        from autoai.safety_intuition import SafetyIntuition, SafetyLearner, HarmSeverity
        intuition = SafetyIntuition()
        learner = SafetyLearner(intuition)
        learner.record_outcome("rm file", "文件已删除", was_harmful=True, severity=HarmSeverity.HIGH)
        assert learner.adaptation_count == 1

    def test_social_safety(self):
        from autoai.safety_intuition import SocialSafetyNorm
        norm = SocialSafetyNorm()
        norm.record_success("agent-a")
        for _ in range(6):
            norm.record_violation("agent-b")
        assert not norm.can_collaborate("agent-a", "agent-b")
        collaborators = norm.select_collaborators("agent-a", ["agent-b"])
        assert len(collaborators) == 0


class TestWASMRuntime:
    """测试WASM能力组件化。"""

    def test_component_spec(self):
        from autoai.wasm_runtime import WASMComponentSpec, ComponentLanguage
        spec = WASMComponentSpec(name="file_reader", language=ComponentLanguage.RUST)
        assert len(spec.component_id) == 16
        assert "fs_read" in spec.permissions

    def test_component_registry(self):
        from autoai.wasm_runtime import ComponentRegistry, WASMComponent, WASMComponentSpec
        registry = ComponentRegistry()
        spec = WASMComponentSpec(name="test_comp")
        component = WASMComponent(spec=spec)
        cid = registry.register(component)
        assert registry.get(cid) is not None
        assert len(registry.list_components()) == 1

    def test_wasm_runtime_execute(self):
        from autoai.wasm_runtime import WASMRuntime, WASMComponentSpec
        runtime = WASMRuntime()
        spec = WASMComponentSpec(name="test")
        component = runtime.load_component(spec, handler=lambda: 42)
        result = asyncio.run(runtime.execute(component.component_id, {}))
        assert result["success"]

    def test_wasm_sandbox(self):
        from autoai.wasm_runtime import WASMSandbox, WASISandboxConfig
        sandbox = WASMSandbox(WASISandboxConfig(allow_fs_write=False, allow_network=False))
        assert sandbox.check_permission("comp1", "fs_read", "/workspace/file.txt")
        assert not sandbox.check_permission("comp1", "fs_write", "/workspace/file.txt")
        assert not sandbox.check_permission("comp1", "network", "http://evil.com")


class TestTelemetry:
    """测试OpenTelemetry全链路可观测。"""

    def test_tracer(self):
        from autoai.telemetry import TelemetryTracer, SpanKind
        tracer = TelemetryTracer("autoai")
        trace_id = tracer.start_trace("test_trace")
        with tracer.span(SpanKind.THOUGHT, "thinking") as span:
            span.set_attribute("model", "gpt-4o")
        spans = tracer.get_trace(trace_id)
        assert len(spans) == 2
        exported = tracer.export_trace(trace_id)
        assert exported["span_count"] == 2

    def test_metrics(self):
        from autoai.telemetry import MetricsCollector
        collector = MetricsCollector()
        collector.record_llm_call("gpt-4o", 100, 50, 0.05, 1500)
        collector.record_task("self_modify", 3000, True)
        summary = collector.get_summary()
        assert "llm_calls_total" in summary
        assert summary["llm_calls_total"]["value"] == 1

    def test_anomaly_detection(self):
        from autoai.telemetry import MetricsCollector
        collector = MetricsCollector()
        for _ in range(20):
            collector.record_task("test", 100, False)
        anomalies = collector.detect_anomalies()
        assert any(a["type"] == "high_error_rate" for a in anomalies)


class TestReasoning:
    """测试推理策略自主选择。"""

    @pytest.mark.asyncio
    async def test_chain_of_thought(self):
        from autoai.reasoning import ChainOfThoughtSolver
        solver = ChainOfThoughtSolver()
        result = await solver.solve("1+1等于几？")
        assert result.strategy.value == "chain_of_thought"
        assert len(result.reasoning_chain) > 0

    @pytest.mark.asyncio
    async def test_tree_of_thought(self):
        from autoai.reasoning import TreeOfThoughtSolver
        solver = TreeOfThoughtSolver(max_depth=2, branch_factor=2)
        result = await solver.solve("最优排序算法")
        assert result.strategy.value == "tree_of_thought"
        assert len(result.alternatives) >= 0

    @pytest.mark.asyncio
    async def test_mcts(self):
        from autoai.reasoning import MCTSSolver
        solver = MCTSSolver(simulations=20, max_depth=3)
        result = await solver.solve("最优路径规划")
        assert result.strategy.value == "monte_carlo_tree_search"
        assert result.metadata["simulations"] == 20

    @pytest.mark.asyncio
    async def test_self_rag(self):
        from autoai.reasoning import SelfRAGEngine
        solver = SelfRAGEngine(retriever=lambda q: [f"关于{q}的文档"])
        result = await solver.solve("什么是量子计算？")
        assert result.strategy.value == "self_rag"

    @pytest.mark.asyncio
    async def test_strategy_selector(self):
        from autoai.reasoning import StrategySelector
        selector = StrategySelector()
        strategy = selector.select_strategy("求最短路径的最优解")
        assert strategy.value == "monte_carlo_tree_search"

        strategy2 = selector.select_strategy("什么是Python？")
        assert strategy2.value == "self_rag"

    @pytest.mark.asyncio
    async def test_strategy_selector_solve(self):
        from autoai.reasoning import StrategySelector
        selector = StrategySelector()
        result = await selector.solve("解释递归")
        assert result.confidence > 0


class TestEnhancedEvolution:
    """测试增强自进化闭环。"""

    @pytest.mark.asyncio
    async def test_evolution_loop(self):
        from autoai.evolution import EnhancedSelfEvolutionLoop, EvolutionPhase
        loop = EnhancedSelfEvolutionLoop(agent_id="test-evolver")
        result = await loop.run_cycle()
        assert result["cycle"] == 1
        assert "duration_ms" in result

    def test_evolution_metrics(self):
        from autoai.evolution import EvolutionMetrics
        metrics = EvolutionMetrics()
        metrics.record_cycle(0.5, True)
        metrics.record_cycle(0.3, True)
        metrics.record_cycle(0.0, False)
        assert metrics.success_rate == pytest.approx(2/3, abs=0.01)
        assert metrics.total_cycles == 3

    def test_shadow_runner(self):
        from autoai.evolution import ShadowRunner
        runner = ShadowRunner(metric_fn=lambda x: x if isinstance(x, (int, float)) else 0)
        assert runner is not None

    @pytest.mark.asyncio
    async def test_auto_agent_writer(self):
        from autoai.evolution import AutoAgentWriter
        writer = AutoAgentWriter()
        agent = await writer.write_agent(
            task_description="监控文件变更并触发测试",
            required_capabilities={"file_watch", "test_runner"},
            role="monitor",
        )
        assert agent.name.startswith("AutoAgent_")
        assert "file_watch" in agent.capabilities
        stats = writer.get_stats()
        assert stats["total_generated"] == 1
