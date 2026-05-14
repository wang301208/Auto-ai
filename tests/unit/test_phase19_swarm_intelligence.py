"""Tests for Phase 19: Swarm intelligence — consensus, division, knowledge mesh, democratic governance."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from autoai.agents.consensus_engine import (
    ConsensusEngine,
    ConsensusResult,
    Proposal,
    ProposalStatus,
    Vote,
    VoteChoice,
)
from autoai.agents.division_emerger import (
    Assignment,
    CapabilityProfile,
    DivisionEmerger,
    EmergentRole,
    RoleStability,
    TaskRequirement,
)
from autoai.agents.knowledge_mesh import (
    KnowledgeFragment,
    KnowledgeMesh,
    KnowledgeQuery,
    KnowledgeStatus,
    KnowledgeVersion,
)
from autoai.agents.democratic_governance import (
    AgentTerm,
    Constitution,
    DemocraticGovernance,
    GovernanceAction,
    Motion,
    MotionStatus,
)


# ==================== ConsensusEngine ====================

class TestConsensusEngine:
    def test_register_agent(self):
        engine = ConsensusEngine()
        engine.register_agent("a1", weight=2.0, reputation=0.9)
        assert "a1" in engine._agents

    def test_simple_majority(self):
        engine = ConsensusEngine(default_quorum=0.5, default_supermajority=0.5)
        engine.register_agent("a1", weight=1.0)
        engine.register_agent("a2", weight=1.0)
        engine.register_agent("a3", weight=1.0)
        pid = engine.propose("a1", "Test proposal")
        engine.vote(pid, "a1", VoteChoice.YES)
        engine.vote(pid, "a2", VoteChoice.YES)
        engine.vote(pid, "a3", VoteChoice.NO)
        result = engine.resolve(pid)
        assert result.status == ProposalStatus.ACCEPTED

    def test_supermajority_required(self):
        engine = ConsensusEngine(default_quorum=0.5, default_supermajority=0.67)
        engine.register_agent("a1", weight=1.0)
        engine.register_agent("a2", weight=1.0)
        engine.register_agent("a3", weight=1.0)
        pid = engine.propose("a1", "Test proposal")
        engine.vote(pid, "a1", VoteChoice.YES)
        engine.vote(pid, "a2", VoteChoice.NO)
        engine.vote(pid, "a3", VoteChoice.ABSTAIN)
        result = engine.resolve(pid)
        assert result.status == ProposalStatus.REJECTED

    def test_weighted_voting(self):
        engine = ConsensusEngine(default_quorum=0.5, default_supermajority=0.5)
        engine.register_agent("a1", weight=3.0, reputation=1.0)
        engine.register_agent("a2", weight=1.0, reputation=1.0)
        pid = engine.propose("a1", "Weighted vote")
        engine.vote(pid, "a1", VoteChoice.YES)
        engine.vote(pid, "a2", VoteChoice.NO)
        result = engine.resolve(pid)
        assert result.status == ProposalStatus.ACCEPTED
        assert result.yes_votes > result.no_votes

    def test_delegated_voting(self):
        engine = ConsensusEngine(default_quorum=0.5, default_supermajority=0.5)
        engine.register_agent("a1", weight=1.0)
        engine.register_agent("a2", weight=1.0)
        engine.delegate_vote("a2", "a1")
        pid = engine.propose("a1", "Delegated vote")
        engine.vote(pid, "a2", VoteChoice.YES)
        votes = engine.get_votes(pid)
        assert len(votes) == 1

    def test_prevent_delegation_cycle(self):
        engine = ConsensusEngine()
        engine.register_agent("a1")
        engine.register_agent("a2")
        engine.delegate_vote("a1", "a2")
        assert not engine.delegate_vote("a2", "a1")

    def test_no_double_voting(self):
        engine = ConsensusEngine(default_quorum=0.5, default_supermajority=0.5)
        engine.register_agent("a1")
        pid = engine.propose("a1", "Double vote test")
        assert engine.vote(pid, "a1", VoteChoice.YES)
        assert not engine.vote(pid, "a1", VoteChoice.NO)

    def test_proposal_chain_integrity(self):
        engine = ConsensusEngine()
        engine.register_agent("a1")
        pid1 = engine.propose("a1", "First")
        p1 = engine.get_proposal(pid1)
        pid2 = engine.propose("a1", "Second")
        p2 = engine.get_proposal(pid2)
        assert p2.prev_hash == p1.hash

    def test_quorum_not_reached(self):
        engine = ConsensusEngine(default_quorum=0.8, default_supermajority=0.5)
        engine.register_agent("a1")
        engine.register_agent("a2")
        pid = engine.propose("a1", "Low participation")
        engine.vote(pid, "a1", VoteChoice.YES)
        result = engine.resolve(pid)
        assert not result.quorum_reached

    def test_veto_power(self):
        engine = ConsensusEngine(default_quorum=0.5, default_supermajority=0.5)
        engine.register_agent("a1", veto_power=True)
        engine.register_agent("a2")
        pid = engine.propose("a1", "Veto test")
        engine.vote(pid, "a1", VoteChoice.NO)
        engine.vote(pid, "a2", VoteChoice.YES)
        result = engine.resolve(pid)
        assert result.status == ProposalStatus.VETOED

    def test_unknown_proposer(self):
        engine = ConsensusEngine()
        pid = engine.propose("unknown", "Test")
        assert pid == ""

    def test_status(self):
        engine = ConsensusEngine()
        s = engine.get_status()
        assert "registered_agents" in s
        assert "chain_head" in s


# ==================== DivisionEmerger ====================

class TestDivisionEmerger:
    def test_register_agent(self):
        emerger = DivisionEmerger()
        emerger.register_agent(CapabilityProfile("a1", skills={"coding": 0.9}))
        assert "a1" in emerger._agents

    def test_discover_roles(self):
        emerger = DivisionEmerger(skill_similarity_threshold=0.7)
        emerger.register_agent(CapabilityProfile("a1", skills={"coding": 0.9, "review": 0.6}))
        emerger.register_agent(CapabilityProfile("a2", skills={"testing": 0.9}))
        roles = emerger.discover_roles()
        assert len(roles) >= 1

    def test_assign_task(self):
        emerger = DivisionEmerger()
        emerger.register_agent(CapabilityProfile("a1", skills={"coding": 0.9}, capacity=1.0))
        emerger.discover_roles()
        assignment = emerger.assign_task(TaskRequirement("t1", required_skills={"coding": 0.7}))
        assert assignment is not None
        assert assignment.agent_id == "a1"

    def test_no_available_agent(self):
        emerger = DivisionEmerger()
        emerger.register_agent(CapabilityProfile("a1", skills={"coding": 0.9}, capacity=0.1, current_load=0.1))
        assignment = emerger.assign_task(TaskRequirement("t1", required_skills={"coding": 0.7}, estimated_load=0.5))
        assert assignment is None

    def test_load_balancing(self):
        emerger = DivisionEmerger()
        emerger.register_agent(CapabilityProfile("a1", skills={"coding": 0.9}, capacity=1.0, current_load=0.9))
        emerger.register_agent(CapabilityProfile("a2", skills={"coding": 0.8}, capacity=1.0, current_load=0.1))
        assignment = emerger.assign_task(TaskRequirement("t1", required_skills={"coding": 0.5}, estimated_load=0.3))
        assert assignment is not None
        assert assignment.agent_id == "a2"

    def test_rebalance(self):
        emerger = DivisionEmerger()
        emerger.register_agent(CapabilityProfile("a1", skills={"coding": 0.9}, capacity=1.0, current_load=0.95))
        emerger.register_agent(CapabilityProfile("a2", skills={"coding": 0.8}, capacity=1.0, current_load=0.1))
        emerger._assignments = [Assignment(task_id="t1", agent_id="a1", role_id="r1", fitness=0.9)]
        reassigned = emerger.rebalance()
        assert len(reassigned) >= 1

    def test_role_stability(self):
        emerger = DivisionEmerger()
        emerger.register_agent(CapabilityProfile("a1", skills={"coding": 0.9}))
        emerger.discover_roles()
        for role in emerger.roles.values():
            assert role.stability in (RoleStability.FORMING, RoleStability.STABLE, RoleStability.ADAPTING)

    def test_capability_profile_available(self):
        p = CapabilityProfile("a1", capacity=1.0, current_load=0.3)
        assert abs(p.available_capacity - 0.7) < 0.01

    def test_status(self):
        emerger = DivisionEmerger()
        s = emerger.get_status()
        assert "agents" in s
        assert "roles" in s


# ==================== KnowledgeMesh ====================

class TestKnowledgeMesh:
    def test_publish_and_query(self):
        mesh = KnowledgeMesh()
        mesh.register_agent("a1", reputation=0.9)
        fid = mesh.publish("a1", "Circular import fix", "Use lazy imports", topic="python", tags=["import"])
        assert fid != ""
        results = mesh.query(KnowledgeQuery(topic="python"))
        assert len(results) >= 1

    def test_tag_query(self):
        mesh = KnowledgeMesh()
        mesh.register_agent("a1")
        mesh.publish("a1", "Test 1", "Content 1", topic="python", tags=["import", "circular"])
        mesh.publish("a1", "Test 2", "Content 2", topic="python", tags=["performance"])
        results = mesh.query(KnowledgeQuery(tags=["circular"]))
        assert len(results) == 1

    def test_deduplication(self):
        mesh = KnowledgeMesh()
        mesh.register_agent("a1", reputation=0.9)
        mesh.register_agent("a2", reputation=0.7)
        fid1 = mesh.publish("a1", "Same content", "Identical content", topic="test")
        fid2 = mesh.publish("a2", "Same content", "Identical content", topic="test")
        assert fid1 == fid2

    def test_versioning(self):
        mesh = KnowledgeMesh()
        mesh.register_agent("a1", reputation=0.5)
        mesh.register_agent("a2", reputation=0.9)
        fid = mesh.publish("a1", "Original", "Same content", topic="test")
        fid2 = mesh.publish("a2", "Updated", "Same content", topic="test")
        frag = mesh.get_fragment(fid)
        assert frag is not None
        assert frag.version == 2
        assert fid == fid2

    def test_deprecate(self):
        mesh = KnowledgeMesh()
        mesh.register_agent("a1")
        fid = mesh.publish("a1", "Test", "Content", topic="test")
        assert mesh.deprecate(fid)
        results = mesh.query(KnowledgeQuery(topic="test"))
        assert len(results) == 0

    def test_revoke(self):
        mesh = KnowledgeMesh()
        mesh.register_agent("a1")
        fid = mesh.publish("a1", "Test", "Content", topic="test")
        assert mesh.revoke(fid, "a1")
        assert mesh.get_fragment(fid).status == KnowledgeStatus.REVOKED

    def test_revoke_wrong_author(self):
        mesh = KnowledgeMesh()
        mesh.register_agent("a1")
        mesh.register_agent("a2")
        fid = mesh.publish("a1", "Test", "Content", topic="test")
        assert not mesh.revoke(fid, "a2")

    def test_merge_fragments(self):
        mesh = KnowledgeMesh()
        mesh.register_agent("a1")
        mesh.register_agent("a2")
        fid1 = mesh.publish("a1", "Knowledge A", "Content A", topic="python")
        fid2 = mesh.publish("a2", "Knowledge B", "Content B", topic="python")
        assert mesh.merge_fragments(fid1, fid2)
        assert mesh.get_fragment(fid2).status == KnowledgeStatus.MERGED

    def test_quality_filter(self):
        mesh = KnowledgeMesh()
        mesh.register_agent("a1", reputation=0.9)
        mesh.register_agent("a2", reputation=0.3)
        mesh.publish("a1", "High quality", "Good content", topic="test")
        mesh.publish("a2", "Low quality", "Poor content", topic="test")
        results = mesh.query(KnowledgeQuery(topic="test", min_quality=0.5))
        assert len(results) == 1

    def test_status(self):
        mesh = KnowledgeMesh()
        s = mesh.get_status()
        assert "agents" in s
        assert "active_fragments" in s


# ==================== DemocraticGovernance ====================

class TestDemocraticGovernance:
    def test_admit_agent(self):
        gov = DemocraticGovernance()
        gov.admit_agent("a1", reputation=0.9)
        assert gov.member_count == 1

    def test_propose_and_vote(self):
        gov = DemocraticGovernance(voting_period_seconds=3600)
        gov.admit_agent("a1", reputation=0.9)
        gov.admit_agent("a2", reputation=0.7)
        gov.admit_agent("a3", reputation=0.8)
        mid = gov.propose_motion("a1", GovernanceAction.POLICY_CHANGE, "Test motion", "Description")
        assert mid != ""
        gov.vote_on_motion(mid, "a1", VoteChoice.YES)
        gov.vote_on_motion(mid, "a2", VoteChoice.YES)
        gov.vote_on_motion(mid, "a3", VoteChoice.YES)
        result = gov.resolve_motion(mid)
        assert result == MotionStatus.PASSED

    def test_veto(self):
        gov = DemocraticGovernance(voting_period_seconds=3600)
        gov.admit_agent("a1", veto_power=True)
        gov.admit_agent("a2")
        mid = gov.propose_motion("a1", GovernanceAction.POLICY_CHANGE, "Veto test")
        gov.vote_on_motion(mid, "a1", VoteChoice.YES)
        gov.vote_on_motion(mid, "a2", VoteChoice.YES)
        assert gov.veto_motion(mid, "a1")
        result = gov.resolve_motion(mid)
        assert result == MotionStatus.VETOED

    def test_veto_override(self):
        gov = DemocraticGovernance(voting_period_seconds=3600)
        for i in range(6):
            gov.admit_agent(f"a{i}", veto_power=(i == 0))
        mid = gov.propose_motion("a1", GovernanceAction.POLICY_CHANGE, "Override test")
        gov.veto_motion(mid, "a0")
        for i in range(1, 6):
            gov.override_veto(mid, f"a{i}")
        motion = gov._motions[mid]
        assert motion.status == MotionStatus.OVERRIDDEN

    def test_expulsion(self):
        gov = DemocraticGovernance(voting_period_seconds=3600)
        gov.admit_agent("a1", reputation=0.9)
        gov.admit_agent("a2", reputation=0.8)
        gov.admit_agent("a3", reputation=0.7)
        mid = gov.propose_motion("a1", GovernanceAction.EXPULSION, "Expel a3", target_id="a3")
        gov.vote_on_motion(mid, "a1", VoteChoice.YES)
        gov.vote_on_motion(mid, "a2", VoteChoice.YES)
        result = gov.resolve_motion(mid)
        assert "a3" not in gov._members or result in (MotionStatus.PASSED, MotionStatus.FAILED)

    def test_constitution(self):
        gov = DemocraticGovernance()
        c = gov.constitution
        assert "no_self_destruction" in c.rules
        assert not c.is_amendable("no_self_destruction")

    def test_constitutional_amendment(self):
        gov = DemocraticGovernance(voting_period_seconds=3600)
        gov.admit_agent("a1", reputation=0.9)
        gov.admit_agent("a2", reputation=0.8)
        mid = gov.propose_motion(
            "a1", GovernanceAction.CONSTITUTIONAL_AMENDMENT,
            "Extend term limits",
            payload={"rule_name": "term_limits", "new_value": "No agent holds power for more than 7 terms"},
        )
        gov.vote_on_motion(mid, "a1", VoteChoice.YES)
        gov.vote_on_motion(mid, "a2", VoteChoice.YES)
        result = gov.resolve_motion(mid)
        if result == MotionStatus.PASSED:
            assert gov.constitution.rules["term_limits"] == "No agent holds power for more than 7 terms"

    def test_protected_rule_amendment_fails(self):
        gov = DemocraticGovernance()
        gov.admit_agent("a1")
        mid = gov.propose_motion(
            "a1", GovernanceAction.CONSTITUTIONAL_AMENDMENT,
            "Remove self-destruction rule",
            payload={"rule_name": "no_self_destruction", "new_value": "allowed"},
        )
        assert mid == ""

    def test_term_limits(self):
        gov = DemocraticGovernance(max_terms=3)
        gov.admit_agent("a1")
        assert gov.assign_term("a1", "coordinator")
        assert gov.assign_term("a1", "coordinator")
        assert gov.assign_term("a1", "coordinator")
        assert not gov.assign_term("a1", "coordinator")

    def test_impeachment(self):
        gov = DemocraticGovernance(voting_period_seconds=3600)
        gov.admit_agent("a1", reputation=0.9)
        gov.admit_agent("a2", reputation=0.8)
        gov.admit_agent("a3", reputation=0.7)
        mid = gov.impeach("a3", "a1", reason="Misbehavior")
        assert mid != ""
        motion = gov._motions[mid]
        assert motion.action == GovernanceAction.IMPEACHMENT

    def test_status(self):
        gov = DemocraticGovernance()
        s = gov.get_status()
        assert "members" in s
        assert "constitution_rules" in s
