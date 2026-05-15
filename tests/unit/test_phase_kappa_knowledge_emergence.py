"""Phase kappa: 知识涌现测试 - 知识图谱、语义压缩、跨域迁移、信念修正。"""

import time
import pytest
from autoai.knowledge.graph import (
    KnowledgeGraph, KnowledgeNode, KnowledgeEdge,
    NodeType, EdgeType, InferencePath, Conflict,
)
from autoai.knowledge.compressor import (
    SemanticCompressor, ConceptDigest, KnowledgeChunk, CompressionLevel,
)
from autoai.knowledge.transfer import (
    CrossDomainTransfer, DomainBridge, TransferResult, TransferStatus, AnalogyCandidate,
)
from autoai.knowledge.belief import (
    BeliefSystem, Belief, BeliefRevision, BeliefSource, RevisionStrategy, ConditionalBelief,
)


# ======================================================================
# 知识图谱测试
# ======================================================================

class TestKnowledgeGraph:
    def test_add_node(self):
        kg = KnowledgeGraph("test")
        node = kg.add_node("Python", NodeType.CONCEPT, {"type": "language"})
        assert node.label == "Python"
        assert node.node_type == NodeType.CONCEPT
        assert "type" in node.attributes

    def test_add_node_dedup(self):
        kg = KnowledgeGraph("test")
        n1 = kg.add_node("Python", NodeType.CONCEPT)
        n2 = kg.add_node("Python", NodeType.CONCEPT)
        assert n1.node_id == n2.node_id
        assert kg.stats["node_count"] == 1

    def test_add_node_merge_attrs(self):
        kg = KnowledgeGraph("test")
        n1 = kg.add_node("Python", NodeType.CONCEPT, {"version": 3.11})
        n2 = kg.add_node("Python", NodeType.CONCEPT, {"version": 3.12})
        assert n2.attributes["version"] == pytest.approx(3.115, abs=0.01)

    def test_find_node(self):
        kg = KnowledgeGraph("test")
        kg.add_node("Python", NodeType.CONCEPT)
        kg.add_node("Rust", NodeType.CONCEPT)
        found = kg.find_node("Python")
        assert found is not None
        assert found.label == "Python"

    def test_find_node_by_type(self):
        kg = KnowledgeGraph("test")
        kg.add_node("Python", NodeType.CONCEPT)
        kg.add_node("Flask", NodeType.ENTITY)
        found = kg.find_node("Python", NodeType.ENTITY)
        assert found is None
        found = kg.find_node("Python", NodeType.CONCEPT)
        assert found is not None

    def test_add_edge(self):
        kg = KnowledgeGraph("test")
        n1 = kg.add_node("Python", NodeType.CONCEPT)
        n2 = kg.add_node("Programming", NodeType.CONCEPT)
        edge = kg.add_edge(n1.node_id, n2.node_id, EdgeType.IS_A)
        assert edge is not None
        assert edge.edge_type == EdgeType.IS_A

    def test_add_edge_nonexistent(self):
        kg = KnowledgeGraph("test")
        edge = kg.add_edge("nonexistent1", "nonexistent2")
        assert edge is None

    def test_add_edge_self_loop(self):
        kg = KnowledgeGraph("test")
        n = kg.add_node("A", NodeType.CONCEPT)
        edge = kg.add_edge(n.node_id, n.node_id)
        assert edge is None

    def test_add_edge_dedup_with_evidence(self):
        kg = KnowledgeGraph("test")
        n1 = kg.add_node("A", NodeType.CONCEPT)
        n2 = kg.add_node("B", NodeType.CONCEPT)
        e1 = kg.add_edge(n1.node_id, n2.node_id, EdgeType.RELATED, evidence="src1")
        e2 = kg.add_edge(n1.node_id, n2.node_id, EdgeType.RELATED, evidence="src2")
        assert e1.edge_id == e2.edge_id
        assert len(e2.evidence) == 2

    def test_remove_node(self):
        kg = KnowledgeGraph("test")
        n1 = kg.add_node("A", NodeType.CONCEPT)
        n2 = kg.add_node("B", NodeType.CONCEPT)
        kg.add_edge(n1.node_id, n2.node_id)
        assert kg.remove_node(n1.node_id)
        assert kg.stats["node_count"] == 1
        assert kg.stats["edge_count"] == 0

    def test_neighbors(self):
        kg = KnowledgeGraph("test")
        n1 = kg.add_node("A", NodeType.CONCEPT)
        n2 = kg.add_node("B", NodeType.CONCEPT)
        n3 = kg.add_node("C", NodeType.CONCEPT)
        kg.add_edge(n1.node_id, n2.node_id, EdgeType.RELATED)
        kg.add_edge(n1.node_id, n3.node_id, EdgeType.IS_A)
        all_neighbors = kg.neighbors(n1.node_id)
        assert len(all_neighbors) == 2
        related_only = kg.neighbors(n1.node_id, EdgeType.RELATED)
        assert len(related_only) == 1

    def test_find_paths(self):
        kg = KnowledgeGraph("test")
        n1 = kg.add_node("A", NodeType.CONCEPT)
        n2 = kg.add_node("B", NodeType.CONCEPT)
        n3 = kg.add_node("C", NodeType.CONCEPT)
        kg.add_edge(n1.node_id, n2.node_id, EdgeType.RELATED, weight=0.9)
        kg.add_edge(n2.node_id, n3.node_id, EdgeType.RELATED, weight=0.8)
        paths = kg.find_paths(n1.node_id, n3.node_id, max_depth=4)
        assert len(paths) >= 1
        assert paths[0].start_id == n1.node_id
        assert paths[0].end_id == n3.node_id

    def test_auto_link(self):
        kg = KnowledgeGraph("test")
        kg.add_node("Python", NodeType.CONCEPT, {"paradigm": "multi", "typing": "dynamic"})
        kg.add_node("Ruby", NodeType.CONCEPT, {"paradigm": "multi", "typing": "dynamic"})
        linked = kg.auto_link()
        assert linked >= 1

    def test_infer_transitive(self):
        kg = KnowledgeGraph("test")
        animal = kg.add_node("Animal", NodeType.CONCEPT)
        mammal = kg.add_node("Mammal", NodeType.CONCEPT)
        dog = kg.add_node("Dog", NodeType.CONCEPT)
        kg.add_edge(mammal.node_id, animal.node_id, EdgeType.IS_A)
        kg.add_edge(dog.node_id, mammal.node_id, EdgeType.IS_A)
        inferred = kg.infer_transitive()
        assert inferred >= 1
        assert kg.stats["edge_count"] == 3

    def test_detect_conflicts(self):
        kg = KnowledgeGraph("test")
        n1 = kg.add_node("A", NodeType.CONCEPT)
        n2 = kg.add_node("B", NodeType.CONCEPT)
        kg.add_edge(n1.node_id, n2.node_id, EdgeType.CONTRADICTS, weight=0.9, confidence=0.9)
        conflicts = kg.detect_conflicts()
        assert len(conflicts) >= 1

    def test_resolve_conflict(self):
        kg = KnowledgeGraph("test")
        n1 = kg.add_node("A", NodeType.CONCEPT)
        n2 = kg.add_node("B", NodeType.CONCEPT)
        kg.add_edge(n1.node_id, n2.node_id, EdgeType.CONTRADICTS, weight=0.9, confidence=0.9)
        conflicts = kg.detect_conflicts()
        kg.resolve_conflict(conflicts[0], n1.node_id)
        assert conflicts[0].resolution.startswith("winner:")
        assert n2.confidence < 1.0

    def test_prune(self):
        kg = KnowledgeGraph("test")
        n1 = kg.add_node("Important", NodeType.CONCEPT, confidence=1.0)
        n1.access_count = 100
        n1.last_accessed = time.time()
        n2 = kg.add_node("Noise", NodeType.CONCEPT, confidence=0.01)
        pruned = kg.prune(threshold=0.3)
        assert pruned >= 1
        assert kg.get_node(n1.node_id) is not None

    def test_observe_triple(self):
        kg = KnowledgeGraph("test")
        src, edge, tgt = kg.observe_triple(
            "Python", "is_a", "Programming Language",
            subject_type=NodeType.CONCEPT,
            object_type=NodeType.CONCEPT,
            edge_type=EdgeType.IS_A,
        )
        assert src.label == "Python"
        assert tgt.label == "Programming Language"
        assert edge.edge_type == EdgeType.IS_A

    def test_query_related(self):
        kg = KnowledgeGraph("test")
        n1 = kg.add_node("Python", NodeType.CONCEPT)
        n2 = kg.add_node("Flask", NodeType.ENTITY)
        n3 = kg.add_node("Django", NodeType.ENTITY)
        kg.add_edge(n2.node_id, n1.node_id, EdgeType.RELATED)
        kg.add_edge(n3.node_id, n1.node_id, EdgeType.RELATED)
        related = kg.query_related("Python", depth=1)
        assert len(related) >= 3

    def test_node_importance(self):
        kg = KnowledgeGraph("test")
        node = kg.add_node("Test", NodeType.CONCEPT, confidence=1.0)
        node.access_count = 50
        node.last_accessed = time.time()
        assert node.importance > 0.5

    def test_stats(self):
        kg = KnowledgeGraph("test")
        kg.add_node("A", NodeType.CONCEPT)
        kg.add_node("B", NodeType.ENTITY)
        kg.add_node("C", NodeType.EVENT)
        stats = kg.stats
        assert stats["node_count"] == 3
        assert "node_types" in stats
        assert "edge_types" in stats


# ======================================================================
# 语义压缩测试
# ======================================================================

class TestSemanticCompressor:
    def test_compress_chunks_detail(self):
        sc = SemanticCompressor()
        chunks = [
            KnowledgeChunk("c1", "Python is a programming language", {"type": "language"}, tokens=7),
            KnowledgeChunk("c2", "Python supports multiple paradigms", {"type": "language"}, tokens=6),
        ]
        digest = sc.compress_chunks(chunks, CompressionLevel.DETAIL)
        assert digest.abstract != ""
        assert len(digest.source_ids) == 2

    def test_compress_chunks_moderate(self):
        sc = SemanticCompressor()
        chunks = [
            KnowledgeChunk("c1", "Python is great for data science", {"domain": "data"}, tokens=8, domain="data_science"),
            KnowledgeChunk("c2", "R is used for statistics", {"domain": "stats"}, tokens=6, domain="data_science"),
        ]
        digest = sc.compress_chunks(chunks, CompressionLevel.MODERATE)
        assert "data_science" in digest.abstract

    def test_compress_chunks_abstract(self):
        sc = SemanticCompressor()
        chunks = [
            KnowledgeChunk("c1", "Content A", importance=0.8, tokens=5, domain="ml"),
            KnowledgeChunk("c2", "Content B", importance=0.6, tokens=5, domain="ml"),
        ]
        digest = sc.compress_chunks(chunks, CompressionLevel.ABSTRACT)
        assert "n=2" in digest.abstract
        assert "ml" in digest.abstract

    def test_progressive_compress(self):
        sc = SemanticCompressor()
        chunks = [
            KnowledgeChunk("c1", "Deep learning uses neural networks for pattern recognition", tokens=9, domain="ai"),
            KnowledgeChunk("c2", "Neural networks are inspired by biological neurons", tokens=8, domain="ai"),
        ]
        result = sc.progressive_compress(chunks)
        assert CompressionLevel.DETAIL in result
        assert CompressionLevel.MODERATE in result
        assert CompressionLevel.ABSTRACT in result
        assert len(result[CompressionLevel.DETAIL].abstract) >= len(result[CompressionLevel.ABSTRACT].abstract)

    def test_common_attrs_extraction(self):
        sc = SemanticCompressor()
        chunks = [
            KnowledgeChunk("c1", "text", {"speed": 100, "size": 50}, tokens=5),
            KnowledgeChunk("c2", "text", {"speed": 200, "size": 30}, tokens=5),
            KnowledgeChunk("c3", "text", {"speed": 150, "size": 40}, tokens=5),
        ]
        digest = sc.compress_chunks(chunks)
        assert "speed_avg" in digest.key_attributes
        assert digest.key_attributes["speed_avg"] == pytest.approx(150.0)

    def test_decompress_hint(self):
        sc = SemanticCompressor()
        chunks = [KnowledgeChunk("c1", "Python programming language", tokens=3)]
        digest = sc.compress_chunks(chunks)
        hint = sc.decompress_hint(digest)
        assert "Python" in hint or "摘要" in hint

    def test_empty_chunks(self):
        sc = SemanticCompressor()
        digest = sc.compress_chunks([], CompressionLevel.MODERATE)
        assert digest.abstract == ""
        assert len(digest.source_ids) == 0

    def test_chunk_entropy(self):
        chunk = KnowledgeChunk("c1", "aaaa")
        entropy_a = chunk.entropy
        chunk2 = KnowledgeChunk("c2", "abcd")
        entropy_diverse = chunk2.entropy
        assert entropy_diverse > entropy_a

    def test_digest_quality(self):
        digest = ConceptDigest(
            digest_id="test", source_ids=[], abstract="test",
            coverage=0.8, fidelity=0.9,
        )
        assert digest.quality == pytest.approx(0.72)

    def test_stats(self):
        sc = SemanticCompressor()
        chunks = [KnowledgeChunk("c1", "hello world", tokens=5)]
        sc.compress_chunks(chunks)
        stats = sc.stats
        assert stats["compressions_done"] == 1
        assert stats["digests_stored"] == 1


# ======================================================================
# 跨域迁移测试
# ======================================================================

class TestCrossDomainTransfer:
    def test_register_domain(self):
        cdt = CrossDomainTransfer()
        cdt.register_domain("physics", ["force", "mass", "acceleration"], [("force", "acts_on", "mass")])
        assert cdt.stats["domains_registered"] == 1

    def test_discover_bridges(self):
        cdt = CrossDomainTransfer()
        cdt.register_domain(
            "electricity",
            ["voltage", "current", "resistance"],
            [("voltage", "drives", "current"), ("current", "opposed_by", "resistance")],
        )
        cdt.register_domain(
            "fluid",
            ["pressure", "flow", "resistance"],
            [("pressure", "drives", "flow"), ("flow", "opposed_by", "resistance")],
        )
        bridge = cdt.discover_bridges("electricity", "fluid")
        assert bridge is not None
        assert len(bridge.concept_map) > 0

    def test_transfer(self):
        cdt = CrossDomainTransfer()
        cdt.register_domain("physics", ["force", "mass"], [("force", "accelerates", "mass")])
        cdt.register_domain("economics", ["investment", "capital"], [("investment", "grows", "capital")])
        bridge = cdt.discover_bridges("physics", "economics")
        if bridge:
            knowledge = [{"concept": "force", "relation": "accelerates", "value": "F=ma"}]
            result = cdt.transfer(bridge, knowledge)
            assert len(result.transferred_knowledge) > 0

    def test_bridge_validation(self):
        bridge = DomainBridge(
            bridge_id="test",
            source_domain="a",
            target_domain="b",
            structural_similarity=0.7,
            transferability_score=0.6,
        )
        bridge.record_validation(True)
        bridge.record_validation(True)
        bridge.record_validation(True)
        assert bridge.status == TransferStatus.VALIDATED
        assert bridge.success_rate == 1.0

    def test_bridge_rejection(self):
        bridge = DomainBridge(
            bridge_id="test",
            source_domain="a",
            target_domain="b",
            structural_similarity=0.3,
            transferability_score=0.2,
        )
        bridge.record_validation(False)
        bridge.record_validation(False)
        bridge.record_validation(False)
        assert bridge.status == TransferStatus.REJECTED

    def test_abstraction_shared(self):
        cdt = CrossDomainTransfer()
        cdt.register_domain("heat", ["temperature", "conduction"])
        cdt.register_domain("electricity", ["voltage", "conduction"])
        cdt.set_abstraction("temperature", "potential")
        cdt.set_abstraction("voltage", "potential")
        shared = cdt.find_shared_abstractions("heat", "electricity")
        assert "potential" in shared

    def test_transfer_result_quality(self):
        result = TransferResult(
            bridge_id="test",
            transferred_knowledge=[{"a": 1}],
            confidence=0.8,
            domain_utility=0.7,
        )
        assert result.quality == pytest.approx(0.56)
        assert result.is_reliable

    def test_transfer_result_unreliable(self):
        result = TransferResult(
            bridge_id="test",
            confidence=0.3,
            warnings=["无法映射"],
        )
        assert not result.is_reliable

    def test_analogy_candidate_score(self):
        ac = AnalogyCandidate(
            source_concept="voltage",
            target_concept="pressure",
            structural_score=0.8,
            semantic_score=0.3,
            contextual_score=0.5,
        )
        expected = 0.4 * 0.8 + 0.4 * 0.3 + 0.2 * 0.5
        assert ac.overall_score == pytest.approx(expected)

    def test_stats(self):
        cdt = CrossDomainTransfer()
        cdt.register_domain("a", ["x", "y"])
        cdt.register_domain("b", ["u", "v"])
        stats = cdt.stats
        assert stats["domains_registered"] == 2


# ======================================================================
# 信念修正测试
# ======================================================================

class TestBeliefSystem:
    def test_believe(self):
        bs = BeliefSystem("agent1")
        b = bs.believe("sky_is_blue", BeliefSource.PERCEPTION, 0.9)
        assert b.confidence == 0.9
        assert bs.does_believe("sky_is_blue")

    def test_believe_contradiction(self):
        bs = BeliefSystem("agent1")
        bs.believe("warm", BeliefSource.PERCEPTION, 0.7)
        bs.believe("not_warm", BeliefSource.PERCEPTION, 0.9)
        assert bs.does_believe("not_warm")
        assert not bs.does_believe("warm")

    def test_axiom_immutable(self):
        bs = BeliefSystem("agent1")
        bs.add_axiom("identity_law")
        assert not bs.contract("identity_law")
        b = bs.get_belief("identity_law")
        assert b is not None
        assert b.is_axiom

    def test_revise_conservative(self):
        bs = BeliefSystem("agent1")
        bs._revision_strategy = RevisionStrategy.CONSERVATIVE
        bs.believe("price_rising", BeliefSource.PERCEPTION, 0.9)
        new_b = bs.revise("price_rising", 0.3, BeliefSource.INFERENCE)
        assert new_b.confidence < 0.9
        assert new_b.confidence > 0.3

    def test_revise_radical(self):
        bs = BeliefSystem("agent1")
        bs._revision_strategy = RevisionStrategy.RADICAL
        bs.believe("old_fact", BeliefSource.PERCEPTION, 0.9)
        new_b = bs.revise("old_fact", 0.3, BeliefSource.INFERENCE)
        assert new_b.confidence == pytest.approx(0.3)

    def test_revise_prioritized(self):
        bs = BeliefSystem("agent1")
        bs._revision_strategy = RevisionStrategy.PRIORITIZED
        bs.believe("important", BeliefSource.PERCEPTION, 0.9)
        b = bs.get_belief("important")
        if b:
            b.priority = 0.8
        new_b = bs.revise("important", 0.3, BeliefSource.INFERENCE)
        assert new_b.confidence > 0.3

    def test_contract(self):
        bs = BeliefSystem("agent1")
        bs.believe("temp_fact", BeliefSource.DEFAULT, 0.7)
        assert bs.contract("temp_fact")
        assert not bs.does_believe("temp_fact")

    def test_contract_cascading(self):
        bs = BeliefSystem("agent1")
        b1 = bs.believe("premise", BeliefSource.PERCEPTION, 0.9)
        b2 = bs.believe("conclusion", BeliefSource.INFERENCE, 0.8)
        b2.dependencies.append(b1.belief_id)
        bs.contract("premise")
        b2_after = bs.get_belief("conclusion")
        if b2_after:
            assert b2_after.confidence < 0.8

    def test_consistency_check(self):
        bs = BeliefSystem("agent1")
        bs.believe("fast", BeliefSource.PERCEPTION, 0.9)
        bs.believe("not_fast", BeliefSource.INFERENCE, 0.8)
        inconsistencies = bs.check_consistency()
        assert len(inconsistencies) >= 1

    def test_resolve_inconsistency(self):
        bs = BeliefSystem("agent1")
        b1 = bs.believe("reliable_source", BeliefSource.PERCEPTION, 0.9)
        b1.priority = 0.9
        b2 = bs.believe("not_reliable_source", BeliefSource.INFERENCE, 0.6)
        b2.priority = 0.3
        inconsistencies = bs.check_consistency()
        if inconsistencies:
            winner = bs.resolve_inconsistency(inconsistencies[0][0], inconsistencies[0][1])
            assert winner is not None

    def test_deduce(self):
        bs = BeliefSystem("agent1")
        bs.believe("raining", BeliefSource.PERCEPTION, 0.9)
        bs.add_entailment("raining", "wet_ground")
        deduced = bs.deduce()
        assert len(deduced) >= 1
        assert bs.does_believe("wet_ground")

    def test_conditional_belief(self):
        bs = BeliefSystem("agent1")
        cb = bs.add_conditional("take_umbrella", "raining", 0.9)
        assert cb.confidence == 0.9
        results = bs.query_conditional("raining")
        assert len(results) >= 1

    def test_evidence_tracking(self):
        bs = BeliefSystem("agent1")
        b = bs.believe("hypothesis", BeliefSource.DEFAULT, 0.5)
        b.add_evidence(True, 3)
        b.add_evidence(False, 1)
        assert b.evidence_for == 3
        assert b.evidence_against == 1
        assert b.net_evidence == 2
        assert b.confidence == pytest.approx(0.75)

    def test_axiom_blocks_belief(self):
        bs = BeliefSystem("agent1")
        bs.add_axiom("not_impossible")
        result = bs.believe("impossible", BeliefSource.PERCEPTION, 0.9)
        assert not bs.does_believe("impossible")

    def test_stats(self):
        bs = BeliefSystem("agent1")
        bs.add_axiom("axiom1")
        bs.believe("fact1", BeliefSource.PERCEPTION, 0.8)
        bs.believe("fact2", BeliefSource.INFERENCE, 0.6)
        stats = bs.stats
        assert stats["total_beliefs"] == 3
        assert stats["axioms"] == 1
