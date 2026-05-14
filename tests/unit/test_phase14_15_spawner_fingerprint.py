"""Tests for Phase 14-15: AutonomousSpawner + ProjectFingerprint."""

import tempfile
import pytest
from pathlib import Path


class TestAutonomousSpawner:
    def test_cannot_spawn_below_l4(self):
        from autoai.agents.autonomous_spawner import AutonomousSpawner
        from governance.autonomy_level import AutonomyLevel, AutonomyManager
        autonomy = AutonomyManager(initial_level=AutonomyLevel.SELF_BOUND)
        spawner = AutonomousSpawner(autonomy=autonomy)
        assert spawner.can_spawn is False
        result = spawner.evaluate_and_spawn([], set())
        assert result is None

    def test_can_spawn_at_l4(self):
        from autoai.agents.autonomous_spawner import AutonomousSpawner
        from governance.autonomy_level import AutonomyLevel, AutonomyManager
        autonomy = AutonomyManager(initial_level=AutonomyLevel.SELF_SPAWN)
        spawner = AutonomousSpawner(autonomy=autonomy)
        assert spawner.can_spawn is True

    def test_spawn_on_overload(self):
        from autoai.agents.autonomous_spawner import AutonomousSpawner, SpawnReason
        from governance.autonomy_level import AutonomyLevel, AutonomyManager
        autonomy = AutonomyManager(initial_level=AutonomyLevel.SELF_SPAWN)
        spawner = AutonomousSpawner(autonomy=autonomy, overload_threshold=5)
        tasks = [{"type": "bug"} for _ in range(20)]
        child_id = spawner.evaluate_and_spawn(tasks, {"primary"})
        assert child_id is not None
        assert spawner.child_count == 1
        assert spawner.children[child_id].reason in (SpawnReason.OVERLOADED, SpawnReason.MISSING_ROLE)

    def test_spawn_missing_role(self):
        from autoai.agents.autonomous_spawner import AutonomousSpawner, SpawnReason
        from governance.autonomy_level import AutonomyLevel, AutonomyManager
        autonomy = AutonomyManager(initial_level=AutonomyLevel.SELF_SPAWN)
        spawner = AutonomousSpawner(autonomy=autonomy, overload_threshold=5)
        tasks = [{"type": "security"} for _ in range(10)]
        child_id = spawner.evaluate_and_spawn(tasks, {"primary"})
        assert child_id is not None
        assert spawner.children[child_id].role == "security"

    def test_no_spawn_below_threshold(self):
        from autoai.agents.autonomous_spawner import AutonomousSpawner
        from governance.autonomy_level import AutonomyLevel, AutonomyManager
        autonomy = AutonomyManager(initial_level=AutonomyLevel.SELF_SPAWN)
        spawner = AutonomousSpawner(autonomy=autonomy, overload_threshold=50)
        tasks = [{"type": "code"} for _ in range(3)]
        result = spawner.evaluate_and_spawn(tasks, {"primary", "fixer"})
        assert result is None

    def test_max_children_limit(self):
        from autoai.agents.autonomous_spawner import AutonomousSpawner
        from governance.autonomy_level import AutonomyLevel, AutonomyManager
        autonomy = AutonomyManager(initial_level=AutonomyLevel.SELF_SPAWN)
        spawner = AutonomousSpawner(autonomy=autonomy, max_children=2, overload_threshold=1)
        tasks = [{"type": "bug"} for _ in range(20)]
        c1 = spawner.evaluate_and_spawn(tasks, {"primary"})
        c2 = spawner.evaluate_and_spawn(tasks, {"primary"})
        c3 = spawner.evaluate_and_spawn(tasks, {"primary"})
        assert c1 is not None
        assert c2 is not None
        assert c3 is None
        assert spawner.child_count == 2

    def test_destroy_idle_child(self):
        from autoai.agents.autonomous_spawner import AutonomousSpawner
        from governance.autonomy_level import AutonomyLevel, AutonomyManager
        autonomy = AutonomyManager(initial_level=AutonomyLevel.SELF_SPAWN)
        spawner = AutonomousSpawner(autonomy=autonomy, overload_threshold=1, idle_timeout_seconds=10)
        tasks = [{"type": "bug"} for _ in range(20)]
        child_id = spawner.evaluate_and_spawn(tasks, {"primary"})
        assert child_id is not None
        destroyed = spawner.evaluate_and_destroy(child_id, child_idle_seconds=15, child_tasks_remaining=0)
        assert destroyed is True
        assert spawner.child_count == 0

    def test_destroy_not_idle(self):
        from autoai.agents.autonomous_spawner import AutonomousSpawner
        from governance.autonomy_level import AutonomyLevel, AutonomyManager
        autonomy = AutonomyManager(initial_level=AutonomyLevel.SELF_SPAWN)
        spawner = AutonomousSpawner(autonomy=autonomy, overload_threshold=1, idle_timeout_seconds=300)
        tasks = [{"type": "bug"} for _ in range(20)]
        child_id = spawner.evaluate_and_spawn(tasks, {"primary"})
        destroyed = spawner.evaluate_and_destroy(child_id, child_idle_seconds=5, child_tasks_remaining=3)
        assert destroyed is False

    def test_consolidate(self):
        from autoai.agents.autonomous_spawner import AutonomousSpawner
        from governance.autonomy_level import AutonomyLevel, AutonomyManager
        autonomy = AutonomyManager(initial_level=AutonomyLevel.SELF_SPAWN)
        spawner = AutonomousSpawner(autonomy=autonomy, overload_threshold=1)
        tasks = [{"type": "bug"} for _ in range(20)]
        spawner.evaluate_and_spawn(tasks, {"primary"})
        spawner.evaluate_and_spawn(tasks, {"primary"})
        assert spawner.child_count == 2
        count = spawner.consolidate()
        assert count == 2
        assert spawner.child_count == 0

    def test_record_child_progress(self):
        from autoai.agents.autonomous_spawner import AutonomousSpawner
        from governance.autonomy_level import AutonomyLevel, AutonomyManager
        autonomy = AutonomyManager(initial_level=AutonomyLevel.SELF_SPAWN)
        spawner = AutonomousSpawner(autonomy=autonomy, overload_threshold=1)
        tasks = [{"type": "bug"} for _ in range(20)]
        child_id = spawner.evaluate_and_spawn(tasks, {"primary"})
        spawner.record_child_progress(child_id, tasks_completed=5, tasks_assigned=3)
        assert spawner.children[child_id].tasks_completed == 5
        assert spawner.children[child_id].tasks_assigned == 3

    def test_stats(self):
        from autoai.agents.autonomous_spawner import AutonomousSpawner
        from governance.autonomy_level import AutonomyLevel, AutonomyManager
        autonomy = AutonomyManager(initial_level=AutonomyLevel.SELF_SPAWN)
        spawner = AutonomousSpawner(autonomy=autonomy)
        s = spawner.stats()
        assert s["can_spawn"] is True
        assert s["child_count"] == 0


class TestProjectFingerprint:
    def test_extract_from_directory(self):
        from governance.project_fingerprint import ProjectFingerprint
        with tempfile.TemporaryDirectory() as tmpdir:
            ws = Path(tmpdir)
            (ws / "main.py").write_text("print('hello')\n")
            (ws / "test_main.py").write_text("def test_x(): pass\n")
            (ws / "requirements.txt").write_text("flask\nrequests\n")
            fp = ProjectFingerprint.extract(ws, "test-project")
            assert fp.project_name == "test-project"
            assert "python" in fp.languages
            assert fp.file_count >= 3
            assert fp.test_file_count >= 1
            assert fp.dependency_count >= 2

    def test_similarity_same_project(self):
        from governance.project_fingerprint import ProjectFingerprint
        fp = ProjectFingerprint(
            project_name="a",
            languages={"python": 1.0},
            frameworks=["flask"],
            file_count=100,
            test_ratio=0.3,
            complexity_score=5.0,
        )
        assert fp.similarity(fp) > 0.95

    def test_similarity_different_languages(self):
        from governance.project_fingerprint import ProjectFingerprint
        fp1 = ProjectFingerprint(project_name="a", languages={"python": 1.0})
        fp2 = ProjectFingerprint(project_name="b", languages={"java": 1.0})
        assert fp1.similarity(fp2) < 0.7

    def test_similarity_similar_projects(self):
        from governance.project_fingerprint import ProjectFingerprint
        fp1 = ProjectFingerprint(
            project_name="a", languages={"python": 0.9, "javascript": 0.1},
            frameworks=["flask"], file_count=200, test_ratio=0.3,
            complexity_score=5.0, has_ci=True, has_docker=True,
        )
        fp2 = ProjectFingerprint(
            project_name="b", languages={"python": 0.85, "javascript": 0.15},
            frameworks=["flask"], file_count=180, test_ratio=0.35,
            complexity_score=4.8, has_ci=True, has_docker=True,
        )
        sim = fp1.similarity(fp2)
        assert sim > 0.7

    def test_to_dict_roundtrip(self):
        from governance.project_fingerprint import ProjectFingerprint
        fp = ProjectFingerprint(
            project_name="test", languages={"python": 1.0},
            frameworks=["flask"], file_count=50, total_lines=1000,
            test_file_count=10, has_ci=True, has_docker=False,
            dependency_count=5, complexity_score=3.0,
        )
        d = fp.to_dict()
        fp2 = ProjectFingerprint.from_dict(d)
        assert fp2.project_name == "test"
        assert fp2.languages == {"python": 1.0}
        assert fp2.has_ci is True

    def test_project_registry(self):
        from governance.project_fingerprint import ProjectFingerprint, ProjectRegistry
        with tempfile.TemporaryDirectory() as tmpdir:
            reg = ProjectRegistry(store_path=Path(tmpdir) / "registry.json")
            fp1 = ProjectFingerprint(project_name="a", languages={"python": 1.0}, frameworks=["flask"])
            fp2 = ProjectFingerprint(project_name="b", languages={"python": 0.9, "javascript": 0.1}, frameworks=["flask"])
            reg.register(fp1)
            reg.register(fp2)
            assert reg.size == 2
            similar = fp1.find_similar if hasattr(fp1, 'find_similar') else None
            results = reg.find_similar(fp1, min_similarity=0.3)
            assert len(results) >= 1

    def test_registry_persistence(self):
        from governance.project_fingerprint import ProjectFingerprint, ProjectRegistry
        with tempfile.TemporaryDirectory() as tmpdir:
            sp = Path(tmpdir) / "registry.json"
            reg1 = ProjectRegistry(store_path=sp)
            reg1.register(ProjectFingerprint(project_name="x", languages={"python": 1.0}))
            reg2 = ProjectRegistry(store_path=sp)
            assert reg2.size == 1

    def test_detect_docker_and_ci(self):
        from governance.project_fingerprint import ProjectFingerprint
        with tempfile.TemporaryDirectory() as tmpdir:
            ws = Path(tmpdir)
            (ws / "main.py").write_text("x=1")
            (ws / "Dockerfile").write_text("FROM python:3.12")
            ci_dir = ws / ".github" / "workflows"
            ci_dir.mkdir(parents=True)
            (ci_dir / "ci.yml").write_text("name: CI")
            fp = ProjectFingerprint.extract(ws, "docker-project")
            assert fp.has_docker is True
            assert fp.has_ci is True
