"""Tests for Phase 16-17: CI Auto-Builder + Model Auto-Trainer."""

import tempfile
import pytest
from pathlib import Path


class TestCIAutoBuilder:
    def test_diagnose_no_ci(self):
        from autoai.agents.ci_auto_builder import CIAutoBuilder
        with tempfile.TemporaryDirectory() as tmpdir:
            builder = CIAutoBuilder(workspace=Path(tmpdir))
            diag = builder.diagnose()
            assert diag.has_ci is False
            assert diag.platform is None

    def test_diagnose_with_github_actions(self):
        from autoai.agents.ci_auto_builder import CIAutoBuilder
        with tempfile.TemporaryDirectory() as tmpdir:
            ws = Path(tmpdir)
            wf = ws / ".github" / "workflows"
            wf.mkdir(parents=True)
            (wf / "ci.yml").write_text("name: CI\non: push\n")
            builder = CIAutoBuilder(workspace=ws)
            diag = builder.diagnose()
            assert diag.has_ci is True
            assert diag.platform.value == "github_actions"

    def test_auto_create_github_actions(self):
        from autoai.agents.ci_auto_builder import CIAutoBuilder, CIOperation
        from governance.autonomy_level import AutonomyLevel, AutonomyManager
        with tempfile.TemporaryDirectory() as tmpdir:
            ws = Path(tmpdir)
            autonomy = AutonomyManager(initial_level=AutonomyLevel.SELF_BOUND)
            builder = CIAutoBuilder(workspace=ws, autonomy=autonomy)
            actions = builder.auto_create_ci()
            assert len(actions) == 1
            assert actions[0].operation == CIOperation.CREATE
            assert (ws / ".github" / "workflows" / "ci.yml").is_file()

    def test_auto_create_gitlab_ci(self):
        from autoai.agents.ci_auto_builder import CIAutoBuilder, CIPlatform
        from governance.autonomy_level import AutonomyLevel, AutonomyManager
        with tempfile.TemporaryDirectory() as tmpdir:
            ws = Path(tmpdir)
            autonomy = AutonomyManager(initial_level=AutonomyLevel.SELF_BOUND)
            builder = CIAutoBuilder(workspace=ws, autonomy=autonomy)
            actions = builder.auto_create_ci(platform=CIPlatform.GITLAB_CI)
            assert len(actions) == 1
            assert (ws / ".gitlab-ci.yml").is_file()

    def test_auto_create_makefile(self):
        from autoai.agents.ci_auto_builder import CIAutoBuilder, CIPlatform
        from governance.autonomy_level import AutonomyLevel, AutonomyManager
        with tempfile.TemporaryDirectory() as tmpdir:
            ws = Path(tmpdir)
            autonomy = AutonomyManager(initial_level=AutonomyLevel.SELF_BOUND)
            builder = CIAutoBuilder(workspace=ws, autonomy=autonomy)
            actions = builder.auto_create_ci(platform=CIPlatform.MAKEFILE)
            assert len(actions) == 1
            assert (ws / "Makefile").is_file()

    def test_cannot_modify_below_l2(self):
        from autoai.agents.ci_auto_builder import CIAutoBuilder
        from governance.autonomy_level import AutonomyLevel, AutonomyManager
        with tempfile.TemporaryDirectory() as tmpdir:
            autonomy = AutonomyManager(initial_level=AutonomyLevel.MANUAL)
            builder = CIAutoBuilder(workspace=Path(tmpdir), autonomy=autonomy)
            assert builder.can_modify is False
            actions = builder.auto_create_ci()
            assert len(actions) == 0

    def test_no_duplicate_create(self):
        from autoai.agents.ci_auto_builder import CIAutoBuilder
        from governance.autonomy_level import AutonomyLevel, AutonomyManager
        with tempfile.TemporaryDirectory() as tmpdir:
            ws = Path(tmpdir)
            autonomy = AutonomyManager(initial_level=AutonomyLevel.SELF_BOUND)
            builder = CIAutoBuilder(workspace=ws, autonomy=autonomy)
            builder.auto_create_ci()
            actions2 = builder.auto_create_ci()
            assert len(actions2) == 0

    def test_auto_extend_ci(self):
        from autoai.agents.ci_auto_builder import CIAutoBuilder
        from governance.autonomy_level import AutonomyLevel, AutonomyManager
        with tempfile.TemporaryDirectory() as tmpdir:
            ws = Path(tmpdir)
            autonomy = AutonomyManager(initial_level=AutonomyLevel.SELF_BOUND)
            builder = CIAutoBuilder(workspace=ws, autonomy=autonomy)
            builder.auto_create_ci()
            action = builder.auto_extend_ci(
                "security_scan",
                "      - run: pip install bandit\n      - run: bandit -r autoai/\n",
            )
            assert action is not None
            assert "security_scan" in (ws / ".github" / "workflows" / "ci.yml").read_text()

    def test_stats(self):
        from autoai.agents.ci_auto_builder import CIAutoBuilder
        from governance.autonomy_level import AutonomyLevel, AutonomyManager
        with tempfile.TemporaryDirectory() as tmpdir:
            autonomy = AutonomyManager(initial_level=AutonomyLevel.SELF_BOUND)
            builder = CIAutoBuilder(workspace=Path(tmpdir), autonomy=autonomy)
            builder.auto_create_ci()
            s = builder.stats()
            assert s["creates"] == 1
            assert s["can_modify"] is True


class TestModelAutoTrainer:
    def test_cannot_train_below_l3(self):
        from autoai.llm.model_router.model_auto_trainer import ModelAutoTrainer, TrainingStatus
        from governance.autonomy_level import AutonomyLevel, AutonomyManager
        autonomy = AutonomyManager(initial_level=AutonomyLevel.SELF_BOUND)
        trainer = ModelAutoTrainer(workspace=Path("/tmp"), autonomy=autonomy)
        assert trainer.can_train is False
        record = trainer.auto_train_cycle()
        assert record.status == TrainingStatus.FAILED
        assert "autonomy" in record.error

    def test_can_train_at_l3(self):
        from autoai.llm.model_router.model_auto_trainer import ModelAutoTrainer
        from governance.autonomy_level import AutonomyLevel, AutonomyManager
        autonomy = AutonomyManager(initial_level=AutonomyLevel.SELF_REWRITE)
        trainer = ModelAutoTrainer(workspace=Path("/tmp"), autonomy=autonomy)
        assert trainer.can_train is True

    def test_insufficient_data_fails(self):
        from autoai.llm.model_router.model_auto_trainer import ModelAutoTrainer, TrainingStatus
        from governance.autonomy_level import AutonomyLevel, AutonomyManager
        autonomy = AutonomyManager(initial_level=AutonomyLevel.SELF_REWRITE)
        trainer = ModelAutoTrainer(workspace=Path("/tmp"), autonomy=autonomy)
        record = trainer.auto_train_cycle()
        assert record.status == TrainingStatus.FAILED
        assert "insufficient_data" in record.error

    def test_prepare_sft_data_from_store(self):
        from autoai.llm.model_router.model_auto_trainer import ModelAutoTrainer
        from governance.experience_store import ExperienceStore, IssueType
        from governance.autonomy_level import AutonomyLevel, AutonomyManager
        store = ExperienceStore()
        store.record_success(IssueType.LINT, "unused var x", "remove x", "python")
        store.record_success(IssueType.LINT, "unused var x", "remove x", "python")
        store.record_success(IssueType.BUG, "null ptr", "add null check", "python")
        store.record_success(IssueType.BUG, "null ptr", "add null check", "python")
        autonomy = AutonomyManager(initial_level=AutonomyLevel.SELF_REWRITE)
        trainer = ModelAutoTrainer(workspace=Path("/tmp"), autonomy=autonomy, experience_store=store)
        data = trainer.prepare_sft_data()
        assert len(data) == 2
        assert "unused var" in data[0].prompt or "null ptr" in data[0].prompt

    def test_save_sft_dataset(self):
        from autoai.llm.model_router.model_auto_trainer import ModelAutoTrainer, SFTDataPoint
        with tempfile.TemporaryDirectory() as tmpdir:
            trainer = ModelAutoTrainer(workspace=Path(tmpdir))
            data = [
                SFTDataPoint(prompt="fix bug", completion="add check", quality_score=0.9),
                SFTDataPoint(prompt="fix lint", completion="remove unused", quality_score=0.8),
            ]
            path = trainer.save_sft_dataset(data)
            assert path.exists()
            content = path.read_text()
            assert "fix bug" in content
            assert "add check" in content

    def test_training_config_defaults(self):
        from autoai.llm.model_router.model_auto_trainer import TrainingConfig
        config = TrainingConfig()
        assert config.lora_rank == 8
        assert config.num_epochs == 3
        assert config.min_data_points == 50

    def test_stats(self):
        from autoai.llm.model_router.model_auto_trainer import ModelAutoTrainer
        from governance.autonomy_level import AutonomyLevel, AutonomyManager
        autonomy = AutonomyManager(initial_level=AutonomyLevel.SELF_REWRITE)
        trainer = ModelAutoTrainer(workspace=Path("/tmp"), autonomy=autonomy)
        trainer.auto_train_cycle()
        s = trainer.stats()
        assert s["total_cycles"] == 1
        assert s["can_train"] is True
