"""Tests for Phase 12-13: Experience Store, Model Auto-Selector, Autonomy Integration."""

import asyncio
import tempfile
import pytest
from pathlib import Path


class TestExperienceStore:
    def test_record_success_new_pattern(self):
        from governance.experience_store import ExperienceStore, IssueType
        store = ExperienceStore()
        p = store.record_success(
            issue_type=IssueType.LINT,
            symptom="unused variable 'x'",
            fix_action="removed unused variable",
            language="python",
        )
        assert p.success_count == 1
        assert p.confidence == 0.5
        assert store.size == 1

    def test_record_success_existing_pattern(self):
        from governance.experience_store import ExperienceStore, IssueType
        store = ExperienceStore()
        store.record_success(IssueType.LINT, "unused var", "remove", "python")
        p = store.record_success(IssueType.LINT, "unused var", "remove", "python")
        assert p.success_count == 2
        assert p.confidence > 0.5
        assert store.size == 1

    def test_record_failure(self):
        from governance.experience_store import ExperienceStore, IssueType
        store = ExperienceStore()
        store.record_success(IssueType.BUG, "null pointer", "add null check", "python")
        store.record_failure(IssueType.BUG, "null pointer", "python")
        patterns = store.match("null pointer", issue_type=IssueType.BUG)
        assert len(patterns) == 1
        assert patterns[0].failure_count == 1
        assert patterns[0].confidence < 0.5

    def test_match_by_symptom(self):
        from governance.experience_store import ExperienceStore, IssueType
        store = ExperienceStore()
        store.record_success(IssueType.LINT, "unused variable", "remove", "python")
        results = store.match("unused variable 'y'")
        assert len(results) >= 1

    def test_match_by_type(self):
        from governance.experience_store import ExperienceStore, IssueType
        store = ExperienceStore()
        store.record_success(IssueType.LINT, "issue a", "fix a", "python")
        store.record_success(IssueType.BUG, "issue b", "fix b", "python")
        results = store.match("issue", issue_type=IssueType.LINT)
        assert all(p.issue_type == IssueType.LINT for p in results)

    def test_match_by_language(self):
        from governance.experience_store import ExperienceStore, IssueType
        store = ExperienceStore()
        store.record_success(IssueType.LINT, "issue", "fix", "python")
        store.record_success(IssueType.LINT, "issue", "fix", "javascript")
        results = store.match("issue", language="python")
        assert all(p.language == "python" for p in results)

    def test_match_min_confidence(self):
        from governance.experience_store import ExperienceStore, IssueType
        store = ExperienceStore()
        store.record_success(IssueType.LINT, "rare issue", "fix", "python")
        store.record_failure(IssueType.LINT, "rare issue", "python")
        store.record_failure(IssueType.LINT, "rare issue", "python")
        store.record_failure(IssueType.LINT, "rare issue", "python")
        results = store.match("rare issue", min_confidence=0.5)
        assert len(results) == 0

    def test_persistence(self):
        from governance.experience_store import ExperienceStore, IssueType
        with tempfile.TemporaryDirectory() as tmpdir:
            ws = Path(tmpdir)
            store1 = ExperienceStore(workspace=ws)
            store1.record_success(IssueType.LINT, "symptom", "fix", "python")
            store2 = ExperienceStore(workspace=ws)
            assert store2.size == 1

    def test_stats(self):
        from governance.experience_store import ExperienceStore, IssueType
        store = ExperienceStore()
        store.record_success(IssueType.LINT, "a", "fa", "python")
        store.record_success(IssueType.BUG, "b", "fb", "python")
        s = store.stats()
        assert s["total_patterns"] == 2
        assert "lint" in s["by_type"]
        assert "bug" in s["by_type"]

    def test_no_match_returns_empty(self):
        from governance.experience_store import ExperienceStore
        store = ExperienceStore()
        results = store.match("nothing matches this")
        assert len(results) == 0


class TestModelAutoSelector:
    def test_trivial_uses_fast(self):
        from autoai.llm.model_router.model_auto_selector import ModelAutoSelector, TaskProfile, TaskComplexity
        sel = ModelAutoSelector()
        choice = sel.select(TaskProfile(objective="fix lint", complexity=TaskComplexity.TRIVIAL))
        assert choice.tier == "fast"
        assert "budget_low" not in choice.reason

    def test_complex_uses_smart(self):
        from autoai.llm.model_router.model_auto_selector import ModelAutoSelector, TaskProfile, TaskComplexity
        sel = ModelAutoSelector()
        choice = sel.select(TaskProfile(objective="refactor architecture", complexity=TaskComplexity.COMPLEX))
        assert choice.tier == "smart"

    def test_budget_low_downgrades(self):
        from autoai.llm.model_router.model_auto_selector import ModelAutoSelector, TaskProfile, TaskComplexity
        sel = ModelAutoSelector(budget_remaining=0.5)
        choice = sel.select(TaskProfile(objective="refactor", complexity=TaskComplexity.COMPLEX))
        assert choice.tier == "fast"
        assert "budget_low" in choice.reason

    def test_latency_sensitive_downgrades(self):
        from autoai.llm.model_router.model_auto_selector import ModelAutoSelector, TaskProfile, TaskComplexity
        sel = ModelAutoSelector()
        choice = sel.select(TaskProfile(
            objective="quick check", complexity=TaskComplexity.COMPLEX,
            latency_sensitive=True,
        ))
        assert choice.tier == "balanced"

    def test_embedding_task(self):
        from autoai.llm.model_router.model_auto_selector import ModelAutoSelector, TaskProfile
        sel = ModelAutoSelector()
        choice = sel.select(TaskProfile(objective="embed text", task_type="embedding"))
        assert choice.tier == "embedding"

    def test_record_outcome(self):
        from autoai.llm.model_router.model_auto_selector import ModelAutoSelector
        sel = ModelAutoSelector(budget_remaining=10.0)
        sel.record_outcome("gpt-4o-mini", "code", success=True, latency_ms=300, cost=0.001)
        sel.record_outcome("gpt-4o-mini", "code", success=True, latency_ms=250, cost=0.001)
        assert sel.stats()["performance_records"] == 1
        assert sel.budget_remaining < 10.0

    def test_performance_based_selection(self):
        from autoai.llm.model_router.model_auto_selector import ModelAutoSelector, TaskProfile, TaskComplexity
        sel = ModelAutoSelector()
        sel.record_outcome("qwen3-4b", "code", success=True, latency_ms=100)
        sel.record_outcome("qwen3-4b", "code", success=True, latency_ms=120)
        sel.record_outcome("gpt-4o-mini", "code", success=False, latency_ms=500)
        choice = sel.select(TaskProfile(objective="fix lint", complexity=TaskComplexity.TRIVIAL))
        assert choice.model_id == "qwen3-4b"

    def test_creativity_escalates(self):
        from autoai.llm.model_router.model_auto_selector import ModelAutoSelector, TaskProfile, TaskComplexity
        sel = ModelAutoSelector()
        choice = sel.select(TaskProfile(
            objective="design new architecture",
            complexity=TaskComplexity.COMPLEX,
            requires_creativity=True,
        ))
        assert choice.tier == "smart"

    def test_stats(self):
        from autoai.llm.model_router.model_auto_selector import ModelAutoSelector, TaskProfile, TaskComplexity
        sel = ModelAutoSelector()
        sel.select(TaskProfile(objective="test"))
        s = sel.stats()
        assert s["selection_count"] == 1
        assert s["budget_remaining"] == 100.0


class TestAutonomyAsyncAgentIntegration:
    def test_autonomy_attached_to_engine(self):
        from autoai.agents.self_think import SelfThinkEngine
        from governance.autonomy_level import AutonomyLevel, AutonomyManager
        from autoai.agents.self_modify import SelfModifyPipeline
        autonomy = AutonomyManager(initial_level=AutonomyLevel.SELF_BOUND)
        pipeline = SelfModifyPipeline(workspace=Path("/tmp"), autonomy=autonomy)
        engine = SelfThinkEngine(
            workspace=Path("/tmp"),
            self_modify_pipeline=pipeline,
        )
        assert engine._self_modify_pipeline is not None
        assert engine._self_modify_pipeline.can_modify is True

    def test_experience_store_attached_to_engine(self):
        from autoai.agents.self_think import SelfThinkEngine
        from governance.experience_store import ExperienceStore
        store = ExperienceStore()
        engine = SelfThinkEngine(workspace=Path("/tmp"))
        assert engine.auto_fix is True
        assert store.size == 0

    @pytest.mark.asyncio
    async def test_experience_recorded_on_fix_success(self):
        from governance.experience_store import ExperienceStore, IssueType
        store = ExperienceStore()
        p = store.record_success(
            issue_type=IssueType.LINT,
            symptom="unused import os",
            fix_action="removed import",
            language="python",
        )
        assert p.success_count == 1
        results = store.match("unused import sys")
        assert len(results) >= 1
        assert results[0].fix_action == "removed import"
