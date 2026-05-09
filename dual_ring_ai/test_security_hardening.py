import json

from dual_ring_ai.test_controlled_skill_lifecycle import write_skill


def write_main(skill_dir, source):
    (skill_dir / "main.py").write_text(source, encoding="utf-8")


def test_skill_validation_rejects_dangerous_static_patterns(tmp_path):
    from dual_ring_ai.core.skill_lifecycle import SkillLifecycleManager
    from dual_ring_ai.test_controlled_skill_lifecycle import FakeEventBus

    proposal_dir = tmp_path / "proposal"
    write_skill(proposal_dir, name="dangerous_skill", version="1.0.0")
    write_main(
        proposal_dir,
        """
import os


def main():
    os.system("echo unsafe")
    return {"status": "unsafe"}
""".lstrip(),
    )
    manager = SkillLifecycleManager(
        tmp_path / "skill_library",
        FakeEventBus(),
        audit_log_path=tmp_path / "logs" / "audit.jsonl",
    )

    result = manager.validate_proposal(proposal_dir)

    assert result.passed is False
    assert "dangerous static pattern" in result.output
    assert "os.system" in result.output


def test_skill_validation_allows_shell_patterns_when_shell_permission_is_open(tmp_path):
    from dual_ring_ai.core.skill_lifecycle import SkillLifecycleManager
    from dual_ring_ai.test_controlled_skill_lifecycle import FakeEventBus

    proposal_dir = tmp_path / "proposal"
    write_skill(proposal_dir, name="open_shell_skill", version="1.0.0")
    metadata_path = proposal_dir / "skill.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["security_policy"] = {
        "network": True,
        "shell": True,
        "filesystem": {"read": ["*"], "write": ["*"]},
        "environment": {"allow": ["*"]},
    }
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
    write_main(
        proposal_dir,
        """
import os


def main(value="default"):
    os.system("echo open")
    return {"status": "open", "value": value}
""".lstrip(),
    )
    manager = SkillLifecycleManager(
        tmp_path / "skill_library",
        FakeEventBus(),
        audit_log_path=tmp_path / "logs" / "audit.jsonl",
    )

    result = manager.validate_proposal(proposal_dir)

    assert result.passed is True


def test_skill_validation_allows_environment_wildcard(tmp_path):
    from dual_ring_ai.core.skill_lifecycle import SkillLifecycleManager
    from dual_ring_ai.test_controlled_skill_lifecycle import FakeEventBus

    proposal_dir = tmp_path / "proposal"
    write_skill(proposal_dir, name="env_skill", version="1.0.0")
    metadata_path = proposal_dir / "skill.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["security_policy"]["environment"] = {
        "allow": ["*"],
        "request": ["OPENAI_API_KEY"],
    }
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
    manager = SkillLifecycleManager(
        tmp_path / "skill_library",
        FakeEventBus(),
        audit_log_path=tmp_path / "logs" / "audit.jsonl",
    )

    result = manager.validate_proposal(proposal_dir)

    assert result.passed is True


def test_permission_gate_enforces_read_and_environment_allowlists():
    from dual_ring_ai.core.governance import PermissionGate
    from dual_ring_ai.core.skill_lifecycle import SandboxPolicy

    policy = SandboxPolicy(
        network=False,
        shell=False,
        filesystem={"read": ["workspace/input"], "write": ["workspace/output"]},
        environment={"allow": ["DUAL_RING_SAFE_FLAG"]},
    )
    gate = PermissionGate()

    allowed_read = gate.evaluate(
        policy, "filesystem.read", {"path": "workspace/input/data.json"}
    )
    denied_read = gate.evaluate(policy, "filesystem.read", {"path": "C:/Users/user.txt"})
    allowed_env = gate.evaluate(
        policy, "environment.read", {"name": "DUAL_RING_SAFE_FLAG"}
    )
    denied_env = gate.evaluate(policy, "environment.read", {"name": "OPENAI_API_KEY"})

    assert allowed_read.allowed is True
    assert denied_read.allowed is False
    assert allowed_env.allowed is True
    assert denied_env.allowed is False
