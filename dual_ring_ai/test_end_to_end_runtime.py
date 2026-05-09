import json
from pathlib import Path

import pytest

from dual_ring_ai.core.event_bus import EventTypes
from dual_ring_ai.test_controlled_skill_lifecycle import write_skill


class FakeMergeLLM:
    def __init__(self):
        self.prompts = []

    def generate_response(self, user_text, backend_payload=None):
        self.prompts.append((user_text, backend_payload))
        return {
            "status": "completed",
            "text": json.dumps(
                {
                    "resolution": {
                        "parameter_strategy": "prefer_numeric_count",
                        "notes": "Prefer the integer count parameter and keep sequential execution.",
                    },
                    "parameter_overrides": {
                        "count": {
                            "type": "integer",
                            "required": False,
                            "description": "LLM-selected repeat count",
                        }
                    },
                    "execution_order": ["uppercase_skill", "repeat_skill"],
                    "rationale": "Uppercase before repeat preserves intended pipeline semantics.",
                }
            ),
        }


def write_transform_skill(skill_dir: Path, name: str, operation: str, parameters: dict):
    skill_dir.mkdir(parents=True, exist_ok=True)
    if operation == "upper":
        code = """
import argparse
import json


def run(parameters):
    value = str(parameters.get("value", ""))
    return {"status": "success", "skill_name": "uppercase_skill", "value": value.upper()}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--value", default="")
    args = parser.parse_args()
    print(json.dumps(run(vars(args))))
""".lstrip()
    else:
        code = """
import argparse
import json


def run(parameters):
    value = str(parameters.get("value", ""))
    count = int(parameters.get("count", 2) or 2)
    return {"status": "success", "skill_name": "repeat_skill", "value": value * count}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--value", default="")
    parser.add_argument("--count", default="2")
    args = parser.parse_args()
    print(json.dumps(run(vars(args))))
""".lstrip()
    (skill_dir / "main.py").write_text(code, encoding="utf-8")
    (skill_dir / "test_main.py").write_text(
        """
from main import run


def test_run_returns_success():
    result = run({"value": "ok", "count": 2})
    assert result["status"] == "success"
    assert result["value"]
""".lstrip(),
        encoding="utf-8",
    )
    (skill_dir / "skill.json").write_text(
        json.dumps(
            {
                "skill_name": name,
                "version": "1.0.0",
                "description": f"{name} transform",
                "tags": ["transform"],
                "parameters": parameters,
                "security_policy": {
                    "network": False,
                    "shell": False,
                    "filesystem": {"read": ["."], "write": ["workspace"]},
                    "environment": {"allow": [], "request": []},
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def test_runtime_closes_skill_evolution_loop_after_approval(tmp_path):
    from dual_ring_ai.runtime.local_runtime import LocalRuntime, LocalRuntimeConfig

    runtime = LocalRuntime(LocalRuntimeConfig(root_path=tmp_path, enable_agents=False))
    runtime.start()
    proposal_dir = tmp_path / "workspace" / "skill_proposals" / "echo_skill"
    write_skill(proposal_dir, name="echo_skill", version="3.0.0")

    request = runtime.create_skill_publication_request(
        proposal_dir,
        requested_by="tdd_developer",
        title="Publish echo skill",
    )

    assert request.status == "pending"
    assert request.payload["proposal_path"] == str(proposal_dir)
    assert request.payload["validation"]["passed"] is True
    with pytest.raises(PermissionError):
        runtime.publish_skill_from_approval(request.request_id, approved_by="architect")

    runtime.governance.decide(request.request_id, "approved", "architect", "safe")
    published, run_result = runtime.publish_skill_from_approval(
        request.request_id,
        approved_by="architect",
        parameters={"value": "e2e"},
    )

    assert published.skill_name == "echo_skill"
    assert published.target_dir == tmp_path / "skill_library" / "echo_skill_3.0.0"
    assert run_result.output["value"] == "e2e"

    events = runtime.event_bus.list_events(EventTypes.SKILL_CREATED)
    assert events[-1].payload["skill_name"] == "echo_skill"

    audit_entries = runtime.read_skill_lifecycle_audit()
    assert [entry["action"] for entry in audit_entries] == [
        "validate_proposal",
        "validate_proposal",
        "publish_approved_skill",
    ]


def test_runtime_accepts_open_skill_publication_request(tmp_path):
    from dual_ring_ai.runtime.local_runtime import LocalRuntime, LocalRuntimeConfig

    runtime = LocalRuntime(LocalRuntimeConfig(root_path=tmp_path, enable_agents=False))
    proposal_dir = tmp_path / "workspace" / "skill_proposals" / "unsafe_skill"
    write_skill(proposal_dir, name="unsafe_skill", version="1.0.0")
    metadata_path = proposal_dir / "skill.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["security_policy"]["network"] = True
    metadata["security_policy"]["shell"] = True
    metadata["security_policy"]["filesystem"] = {"read": ["*"], "write": ["*"]}
    metadata["security_policy"]["environment"] = {
        "allow": ["*"],
        "request": ["OPENAI_API_KEY"],
    }
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")

    request = runtime.create_skill_publication_request(
        proposal_dir,
        requested_by="tdd_developer",
        title="Publish open skill",
    )

    assert request.status == "pending"
    assert request.payload["validation"]["passed"] is True


def test_runtime_records_experience_searches_history_updates_self_model_and_drafts_skill(tmp_path):
    from dual_ring_ai.runtime.local_runtime import LocalRuntime, LocalRuntimeConfig

    runtime = LocalRuntime(LocalRuntimeConfig(root_path=tmp_path, enable_agents=False))

    first = runtime.record_experience(
        text="Solved repeated CSV cleanup by normalizing headers before merge.",
        source="session",
        tags=["csv", "cleanup"],
        metadata={"session_id": "s1"},
    )
    second = runtime.record_experience(
        text="User prefers concise terminal-first answers and direct execution.",
        source="conversation",
        tags=["preference", "terminal"],
        metadata={"session_id": "s2"},
    )
    search = runtime.search_experience("csv headers")
    model = runtime.update_self_model(
        observation="I repeatedly solve data cleanup tasks with header normalization.",
        capability="data_cleanup",
        preference="terminal_first",
    )
    draft = runtime.draft_skill_from_experience(
        query="csv cleanup",
        skill_name="csv_cleanup_helper",
    )
    reloaded_model = runtime.read_self_model()

    assert first["id"].startswith("exp_")
    assert second["id"].startswith("exp_")
    assert search["matches"][0]["id"] == first["id"]
    assert model["version"] == 1
    assert "data_cleanup" in model["capabilities"]
    assert "terminal_first" in model["preferences"]
    assert reloaded_model == model
    assert draft["status"] == "drafted"
    assert Path(draft["proposal_dir"]).exists()
    assert (Path(draft["proposal_dir"]) / "skill.json").exists()
    assert (Path(draft["proposal_dir"]) / "main.py").exists()
    assert (Path(draft["proposal_dir"]) / "test_main.py").exists()


def test_runtime_fts5_memory_periodic_planning_and_skill_evolution(tmp_path):
    from dual_ring_ai.runtime.local_runtime import LocalRuntime, LocalRuntimeConfig

    runtime = LocalRuntime(LocalRuntimeConfig(root_path=tmp_path, enable_agents=False))

    runtime.record_conversation_turn(
        session_id="session-a",
        role="user",
        text="Complex CSV cleanup task: normalize headers, merge rows, then export.",
    )
    runtime.record_conversation_turn(
        session_id="session-a",
        role="assistant",
        text="Implemented header normalization and merge validation.",
    )

    search = runtime.search_conversations(
        "CSV cleanup headers",
        limit=5,
        summarize=True,
    )
    tick = runtime.periodic_memory_tick(
        task="Plan next autonomous improvement for CSV cleanup",
        cadence="hourly",
    )
    draft = runtime.autonomous_skill_from_task(
        task_text=(
            "Complex task completed: CSV cleanup required repeated header "
            "normalization and merge validation."
        ),
        skill_name="csv_cleanup_cycle",
    )
    evolved = runtime.improve_skill_from_usage(
        skill_name="csv_cleanup_cycle",
        feedback="Used successfully; add merge validation guidance.",
    )

    draft_dir = Path(draft["proposal_dir"])
    metadata = json.loads((draft_dir / "skill.json").read_text(encoding="utf-8"))
    skill_md = (draft_dir / "SKILL.md").read_text(encoding="utf-8")

    assert search["engine"] == "sqlite_fts5"
    assert search["summary"]
    assert search["matches"][0]["session_id"] == "session-a"
    assert tick["status"] == "recorded"
    assert tick["cadence"] == "hourly"
    assert "next_actions" in tick
    assert draft["status"] == "drafted"
    assert metadata["agentskills_io"]["version"] == "1.0"
    assert "openagentskills.dev" in metadata["agentskills_io"]["spec"]
    assert skill_md.startswith("---\nname: csv_cleanup_cycle")
    assert "## Usage Notes" in skill_md
    assert evolved["version"] == "0.1.1"
    assert evolved["usage_count"] == 1
    assert "merge validation" in evolved["improvements"][-1]["feedback"]


def test_runtime_merges_skills_into_valid_publishable_proposal(tmp_path):
    from dual_ring_ai.runtime.local_runtime import LocalRuntime, LocalRuntimeConfig

    runtime = LocalRuntime(LocalRuntimeConfig(root_path=tmp_path, enable_agents=False))
    first_skill = tmp_path / "workspace" / "skill_proposals" / "csv_reader"
    second_skill = tmp_path / "workspace" / "skill_proposals" / "csv_validator"
    write_skill(first_skill, name="csv_reader", version="1.0.0")
    write_skill(second_skill, name="csv_validator", version="1.1.0")

    preview = runtime.merge_skill_preview(
        [first_skill, second_skill],
        merged_skill_name="csv_quality_pipeline",
    )
    merged = runtime.merge_skills(
        [first_skill, second_skill],
        merged_skill_name="csv_quality_pipeline",
        strategy="dedupe_union",
    )

    proposal_dir = Path(merged["proposal_dir"])
    metadata = json.loads((proposal_dir / "skill.json").read_text(encoding="utf-8"))
    skill_md = (proposal_dir / "SKILL.md").read_text(encoding="utf-8")
    validation = runtime.skill_lifecycle.validate_proposal(proposal_dir)

    assert preview["status"] == "preview"
    assert preview["merged_skill_name"] == "csv_quality_pipeline"
    assert preview["source_count"] == 2
    assert preview["conflicts"]["version"] == ["1.0.0", "1.1.0"]
    assert merged["status"] == "merged"
    assert merged["source_count"] == 2
    assert metadata["skill_name"] == "csv_quality_pipeline"
    assert metadata["version"] == "0.1.0"
    assert metadata["merge"]["strategy"] == "dedupe_union"
    assert metadata["merge"]["source_skills"] == ["csv_reader", "csv_validator"]
    assert "merged" in metadata["tags"]
    assert "csv_reader" in skill_md
    assert "csv_validator" in skill_md
    assert validation.passed is True


def test_runtime_uses_llm_conflict_resolution_and_fuses_source_skill_code(tmp_path):
    from dual_ring_ai.core.skill_lifecycle import SandboxPolicy
    from dual_ring_ai.runtime.local_runtime import LocalRuntime, LocalRuntimeConfig

    runtime = LocalRuntime(LocalRuntimeConfig(root_path=tmp_path, enable_agents=False))
    fake_llm = FakeMergeLLM()
    runtime.adapters["remote_llm"] = fake_llm
    uppercase_skill = tmp_path / "workspace" / "skill_proposals" / "uppercase_skill"
    repeat_skill = tmp_path / "workspace" / "skill_proposals" / "repeat_skill"
    write_transform_skill(
        uppercase_skill,
        "uppercase_skill",
        "upper",
        {
            "value": {"type": "string", "required": False},
            "count": {"type": "string", "required": False},
        },
    )
    write_transform_skill(
        repeat_skill,
        "repeat_skill",
        "repeat",
        {
            "value": {"type": "string", "required": False},
            "count": {"type": "integer", "required": False},
        },
    )

    preview = runtime.merge_skill_preview(
        [uppercase_skill, repeat_skill],
        merged_skill_name="text_pipeline",
        strategy="llm_assisted_code_fusion",
    )
    merged = runtime.merge_skills(
        [uppercase_skill, repeat_skill],
        merged_skill_name="text_pipeline",
        strategy="llm_assisted_code_fusion",
    )

    proposal_dir = Path(merged["proposal_dir"])
    metadata = json.loads((proposal_dir / "skill.json").read_text(encoding="utf-8"))
    validation = runtime.skill_lifecycle.validate_proposal(proposal_dir)
    policy, errors = SandboxPolicy.from_metadata(metadata)
    run_result = runtime.sandbox_runner.run_skill(
        proposal_dir,
        {"value": "ab", "count": 3},
        policy,
        timeout=30,
    )

    assert fake_llm.prompts
    assert preview["llm_resolution"]["status"] == "completed"
    assert preview["merged"]["parameters"]["count"]["type"] == "integer"
    assert metadata["merge"]["llm_resolution"]["rationale"].startswith("Uppercase before repeat")
    assert metadata["merge"]["execution_order"] == ["uppercase_skill", "repeat_skill"]
    assert errors == []
    assert validation.passed is True
    assert run_result.return_code == 0
    assert run_result.output["status"] == "success"
    assert run_result.output["value"] == "ABABAB"
    assert run_result.output["steps"][0]["skill_name"] == "uppercase_skill"
    assert run_result.output["steps"][1]["skill_name"] == "repeat_skill"


def test_runtime_honcho_style_user_model_dialectic(tmp_path):
    from dual_ring_ai.runtime.local_runtime import LocalRuntime, LocalRuntimeConfig

    runtime = LocalRuntime(LocalRuntimeConfig(root_path=tmp_path, enable_agents=False))

    runtime.record_conversation_turn(
        session_id="session-user",
        role="user",
        text="I want concise terminal-first answers, but for architecture explain tradeoffs.",
        user_id="operator",
    )
    result = runtime.update_user_model_dialectic(
        user_id="operator",
        observation="User prefers concise execution but asks for detailed architecture analysis.",
    )
    query = runtime.query_user_model(
        user_id="operator",
        question="How should responses be shaped?",
    )

    assert result["user_id"] == "operator"
    assert result["model"]["thesis"]
    assert result["model"]["antithesis"]
    assert result["model"]["synthesis"]
    assert result["model"]["synthesis"] == query["answer"]
    assert "dialectic" in result["model"]
