from pathlib import Path
import asyncio
import json

import pytest
from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[1]


def test_only_terminal_ui_frontend_entrypoints_remain():
    assert (ROOT / "ui-tui" / "package.json").exists()
    assert (ROOT / "ui-tui" / "src" / "entry.tsx").exists()
    assert (ROOT / "tui_gateway" / "entry.py").exists()

    removed_frontends = [
        ROOT / "dual_ring_ai" / "dashboard" / "static",
        ROOT / "dual_ring_ai" / "desktop",
        ROOT / ".dual_ring_runtime" / "desktop",
        ROOT / "openevolve" / "scripts" / "templates",
        ROOT / "openevolve" / "scripts" / "static",
        ROOT / "".join(("auto", "gpt")) / "core" / "runner" / "cli_web_app",
        ROOT / "".join(("auto", "gpt")) / "js" / "overlay.js",
    ]
    assert all(not path.exists() for path in removed_frontends)


def test_tui_frontend_uses_stdio_gateway_not_http_transport():
    tui_files = list((ROOT / "ui-tui" / "src").rglob("*.ts")) + list(
        (ROOT / "ui-tui" / "src").rglob("*.tsx")
    )
    source = "\n".join(path.read_text(encoding="utf-8") for path in tui_files)

    assert "spawn(python, ['-m', 'tui_gateway.entry']" in source
    assert "stdio: ['pipe', 'pipe', 'pipe']" in source
    forbidden_transports = [
        "WebSocket",
        "EventSource",
        "fetch(",
        "axios",
        "ws://",
        "http://127.0.0.1",
        "http://localhost",
    ]
    assert all(token not in source for token in forbidden_transports)


def test_tui_uses_alternate_screen_and_single_startup_branding():
    entry_source = (ROOT / "ui-tui" / "src" / "entry.tsx").read_text(encoding="utf-8")
    app_source = (ROOT / "ui-tui" / "src" / "app.tsx").read_text(encoding="utf-8")

    assert "enterAlternateScreen" in entry_source
    assert "exitAlternateScreen" in entry_source
    assert "const hideBranding = showEmptyState" in app_source
    assert "{!hideBranding ? <Branding info={info} /> : null}" in app_source


def test_tui_surfaces_startup_autonomous_self_maintenance():
    app_source = (ROOT / "ui-tui" / "src" / "app.tsx").read_text(encoding="utf-8")
    panel_source = (
        ROOT / "ui-tui" / "src" / "components" / "runtimeActivityPanel.tsx"
    ).read_text(encoding="utf-8")

    assert app_source.index("gateway.on('event', onEvent)") < app_source.index("'session.create'")
    assert "case 'system.maintenance':" in app_source
    assert "setAutonomyMaintenance" in app_source
    assert "自主自我已启动" in app_source
    assert "maintenance={autonomyMaintenance}" in app_source
    assert "自主自我" in panel_source


def test_terminal_ui_does_not_expose_legacy_branding():
    terminal_files = [
        ROOT / "ui-tui" / "package.json",
        ROOT / "tui_gateway" / "entry.py",
    ]
    terminal_files.extend((ROOT / "ui-tui" / "src").rglob("*.ts"))
    terminal_files.extend((ROOT / "ui-tui" / "src").rglob("*.tsx"))

    source = "\n".join(path.read_text(encoding="utf-8") for path in terminal_files)

    legacy_tokens = [
        "".join(("Her", "mes")),
        "".join(("HER", "MES")),
        "".join(("Gene", "sis")),
        "".join(("Zhu", "shou")),
        "".join(("Auto", "GPT")),
        "".join(("Auto", "-GPT")),
        chr(0x9983),
        chr(0x93AE),
        chr(0x9354),
        chr(0x6748),
        chr(0x5A11),
    ]
    assert all(token not in source for token in legacy_tokens)


def test_tui_empty_state_contains_project_intro_copy():
    empty_state = ROOT / "ui-tui" / "src" / "components" / "emptyState.tsx"
    app_source = (ROOT / "ui-tui" / "src" / "app.tsx").read_text(encoding="utf-8")
    source = empty_state.read_text(encoding="utf-8")

    required_copy = [
        "本地智能体",
        "自主运行时终端",
        "borderStyle=\"round\"",
        "flexDirection=\"row\"",
        "asciiArt",
        "自然语言交互",
        "自动处理",
        "标准输入输出 JSON-RPC",
        "直接说出目标",
        "会自动选择路径",
        "风险操作会弹出审批",
        "长对话会自动压缩上下文",
        "输入自然语言即可开始",
    ]

    assert "EmptyState" in app_source
    assert all(text in source for text in required_copy)
    assert "/model" not in source
    assert "/usage" not in source
    assert "/clear" not in source
    assert "!命令" not in source
    assert "@路径" not in source


def test_quickstart_and_configuration_reference_cover_cli_setup_and_first_chat():
    quickstart = ROOT / "docs" / "quickstart.md"
    config_reference = ROOT / "docs" / "configuration-reference.md"
    launch_script = ROOT / "scripts" / "launch_tui.py"
    test_script = ROOT / "scripts" / "test_tui.py"

    assert quickstart.exists()
    assert config_reference.exists()

    quickstart_text = quickstart.read_text(encoding="utf-8")
    config_text = config_reference.read_text(encoding="utf-8")
    script_text = "\n".join(
        [
            launch_script.read_text(encoding="utf-8"),
            test_script.read_text(encoding="utf-8"),
        ]
    )

    required_quickstart = [
        "local-agent setup",
        "local-agent model",
        "local-agent",
        "First conversation",
        "Two-minute path",
        "doctor",
    ]
    required_config = [
        "config.yaml",
        ".env",
        "providers",
        "custom",
        "LOCAL_AGENT_CONFIG_PATH",
    ]

    assert all(text in quickstart_text for text in required_quickstart)
    assert all(text in config_text for text in required_config)
    assert "Zhushou" not in script_text
    assert "Hermes-style" not in script_text


def legacy_tui_gateway_supports_personality_and_save_commands(tmp_path):
    from tui_gateway.entry import JSONRPCServer, SLASH_COMMANDS

    server = JSONRPCServer(runtime_root=tmp_path, writer=lambda _: None)
    server.history = [{"role": "user", "text": "hello"}]

    personality = asyncio.run(server.handle_slash_exec({"text": "/personality concise operator"}))
    save = asyncio.run(server.handle_slash_exec({"text": "/save"}))
    help_output = asyncio.run(server.handle_slash_exec({"text": "/help"}))
    saved_path = tmp_path / "sessions" / f"{server.session_id}.json"

    assert {"/personality", "/save"}.issubset({item["text"] for item in SLASH_COMMANDS})
    assert personality["output"] == "助手风格已设置：concise operator"
    assert server.personality == "concise operator"
    assert save["output"] == f"会话已保存：{saved_path}"
    assert saved_path.exists()
    assert "/personality" in help_output["output"]
    assert "/save" in help_output["output"]


def test_tui_gateway_only_keeps_help_new_and_model_slash_commands(tmp_path):
    from tui_gateway.entry import JSONRPCServer, SLASH_COMMANDS

    server = JSONRPCServer(runtime_root=tmp_path, writer=lambda _: None)

    help_output = asyncio.run(server.handle_slash_exec({"text": "/help"}))
    removed = asyncio.run(server.handle_slash_exec({"text": "/status"}))
    model = asyncio.run(server.handle_slash_exec({"text": "/model custom-model"}))
    new_session = asyncio.run(server.handle_slash_exec({"text": "/new"}))

    assert [item["text"] for item in SLASH_COMMANDS] == ["/help", "/new", "/model"]
    assert "/help" in help_output["output"]
    assert "/new" in help_output["output"]
    assert "/model" in help_output["output"]
    assert "/status" not in help_output["output"]
    assert removed["warning"].startswith(("未知命令", "鏈煡鍛戒护"))
    assert model["output"].endswith("custom:custom-model")
    assert new_session["output"]


def test_removed_slash_commands_do_not_become_user_natural_maintenance_intents(tmp_path):
    from tui_gateway.entry import JSONRPCServer

    server = JSONRPCServer(runtime_root=tmp_path, writer=lambda _: None)
    maintenance_samples = [
        "查看运行状态",
        "查看健康报告",
        "写入预检报告",
        "查看用量",
        "查看日志",
        "查看队列",
        "压缩上下文",
        "保存会话",
    ]

    for text in maintenance_samples:
        resolved = asyncio.run(server.handle_natural_resolve({"text": text}))
        assert resolved["matched"] is False
        assert "legacy_command" not in resolved

    model = asyncio.run(server.handle_natural_resolve({"text": "查看模型"}))
    close = asyncio.run(server.handle_natural_resolve({"text": "退出"}))

    assert model["method"] == "model.options"
    assert close["method"] == "session.close"


def test_natural_capabilities_do_not_expose_removed_slash_names(tmp_path):
    from tui_gateway.entry import JSONRPCServer

    server = JSONRPCServer(runtime_root=tmp_path, writer=lambda _: None)

    capabilities = asyncio.run(server.handle_natural_capabilities({}))
    commands = capabilities["commands"]
    visible = {item["command"] for item in commands}
    removed = {
        "/status",
        "/health",
        "/preflight",
        "/tools",
        "/approvals",
        "/usage",
        "/logs",
        "/queue",
        "/compact",
        "/resume",
        "/save",
        "/personality",
        "/quit",
        "/exit",
        "/q",
    }

    assert removed.isdisjoint(visible)
    assert {"/help", "/new", "/model"}.issubset(visible)
    assert not any(item["command"] == "runtime.status_snapshot" for item in commands)
    assert all("legacy_command" not in item for item in commands)


def test_natural_capabilities_hide_self_running_system_maintenance(tmp_path):
    from tui_gateway.entry import JSONRPCServer

    server = JSONRPCServer(runtime_root=tmp_path, writer=lambda _: None)

    capabilities = asyncio.run(server.handle_natural_capabilities({}))
    methods = {item.get("method") for item in capabilities["commands"]}
    autonomous_methods = {
        "runtime.status_snapshot",
        "runtime.health",
        "runtime.preflight",
        "runtime.write_preflight",
        "runtime.host_probe",
        "runtime.adapters",
        "runtime.logs",
        "runtime.events",
        "runtime.terminal_ui",
        "session.status",
        "session.usage",
        "session.compress",
        "session.save",
        "session.list",
        "memory.periodic_tick",
        "skill.autonomous_from_task",
        "skill.improve_from_usage",
    }

    assert autonomous_methods.isdisjoint(methods)
    assert "prompt.submit" in methods
    assert "shell.exec" in methods
    assert "runtime.platform_message" in methods
    assert "conversation.search" in methods


def test_session_create_and_prompt_run_autonomous_maintenance(tmp_path):
    from tui_gateway.entry import JSONRPCServer

    writes = []
    server = JSONRPCServer(runtime_root=tmp_path, writer=writes.append, stream_delay=0)

    async def run_flow():
        created = await server.handle_session_create({"cols": 100})
        prompt = await server.handle_prompt_submit({"text": "完成复杂的 CSV 清洗与表头归一化任务"})
        await server.wait_for_background()
        return created, prompt

    created, prompt = asyncio.run(run_flow())
    event_types = [
        item.get("params", {}).get("type")
        for item in writes
        if item.get("method") == "event"
    ]
    cycles = tmp_path / "experience" / "periodic_memory.jsonl"
    skill_dir = tmp_path / "workspace" / "skill_proposals" / "completed_complex_csv_task_skill"
    saved_session = tmp_path / "sessions" / f"{server.session_id}.json"

    assert created["session_id"] == server.session_id
    assert prompt == {"status": "streaming"}
    assert cycles.exists()
    assert saved_session.exists()
    assert (skill_dir / "SKILL.md").exists()
    assert "system.maintenance" in event_types
    assert "approval.queue" in event_types


def test_project_runs_high_self_autonomy_loop_and_records_self_state(tmp_path):
    from tui_gateway.entry import JSONRPCServer

    writes = []
    server = JSONRPCServer(runtime_root=tmp_path, writer=writes.append, stream_delay=0)

    async def run_flow():
        await server.handle_session_create({"cols": 100})
        await server.handle_prompt_submit({"text": "完成复杂的 CSV 清洗与表头归一化任务"})
        await server.wait_for_background()

    asyncio.run(run_flow())
    maintenance_events = [
        item.get("params", {}).get("payload", {})
        for item in writes
        if item.get("method") == "event"
        and item.get("params", {}).get("type") == "system.maintenance"
    ]
    autonomy_log = tmp_path / "experience" / "autonomy_loop.jsonl"
    self_state_path = tmp_path / "experience" / "self_state.json"
    self_model = json.loads((tmp_path / "experience" / "self_model.json").read_text(encoding="utf-8"))

    assert maintenance_events
    assert all(event["autonomy_level"] == "highly_self_directed" for event in maintenance_events)
    assert all(event["next_actions"] for event in maintenance_events)
    assert all(event["self_state"]["identity"] == "local_autonomous_agent" for event in maintenance_events)
    assert autonomy_log.exists()
    assert self_state_path.exists()
    self_state = json.loads(self_state_path.read_text(encoding="utf-8"))
    records = [
        json.loads(line)
        for line in autonomy_log.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert records
    assert self_state["autonomy_level"] == "highly_self_directed"
    assert self_state["identity"] == "local_autonomous_agent"
    assert self_state["active_goal"] == "完成复杂的 CSV 清洗与表头归一化任务"
    assert "self_run_system_maintenance" in self_state["principles"]
    assert "autonomous_self_operation" in self_state["capabilities"]
    assert self_state["next_actions"]
    assert self_state["last_maintenance"]["trigger"] == "prompt_complete"
    assert any(record["trigger"] == "prompt_complete" for record in records)
    assert "autonomous_self_operation" in self_model["capabilities"]
    assert any(
        "Autonomous maintenance" in item["text"]
        for item in self_model["observations"]
    )


def test_session_start_boots_full_autonomous_self_automation(tmp_path):
    from datetime import UTC, datetime, timedelta

    from tui_gateway.entry import JSONRPCServer

    cron_jobs = {
        "jobs": [
            {
                "id": "cron_due",
                "name": "startup due memory tick",
                "method": "memory.periodic_tick",
                "params": {"task": "startup due task", "cadence": "startup-cron"},
                "interval_seconds": 0,
                "next_run_at": (datetime.now(UTC) - timedelta(seconds=5)).isoformat(),
                "run_count": 0,
                "status": "active",
            }
        ]
    }
    (tmp_path / "cron_jobs.json").write_text(
        json.dumps(cron_jobs, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    writes = []
    server = JSONRPCServer(runtime_root=tmp_path, writer=writes.append, stream_delay=0)

    asyncio.run(server.handle_session_create({"cols": 100}))
    events = [
        item.get("params", {})
        for item in writes
        if item.get("method") == "event"
    ]
    maintenance_events = [
        event.get("payload", {})
        for event in events
        if event.get("type") == "system.maintenance"
    ]
    latest = maintenance_events[-1]
    action_names = {item["name"] for item in latest["actions"]}
    updated_cron = json.loads((tmp_path / "cron_jobs.json").read_text(encoding="utf-8"))
    self_state = json.loads((tmp_path / "experience" / "self_state.json").read_text(encoding="utf-8"))

    assert "autonomous.startup_orchestrator" in action_names
    assert "cron.run_due" in action_names
    assert "context.compaction.check" in action_names
    assert "self_evolution.governance_ready" in action_names
    assert "self_evolution.startup_policy" in action_names
    assert "approval.queue" in [event.get("type") for event in events]
    assert "cron.run_due" in [event.get("type") for event in events]
    assert updated_cron["jobs"][0]["status"] == "completed"
    assert self_state["last_maintenance"]["trigger"] == "session_start"
    assert "autonomous_startup_orchestration" in self_state["capabilities"]
    assert "scheduled_task_execution" in self_state["capabilities"]
    assert "governed_self_evolution_readiness" in self_state["capabilities"]


def test_high_self_evolution_creates_guarded_core_training_and_deploy_requests(tmp_path):
    from tui_gateway.entry import JSONRPCServer

    writes = []
    server = JSONRPCServer(runtime_root=tmp_path, writer=writes.append, stream_delay=0)

    async def run_flow():
        await server.handle_session_create({"cols": 100})
        await server.handle_prompt_submit(
            {"text": "自动修改核心源码、自动训练微调模型权重、自动架构迁移并上线"}
        )
        await server.wait_for_background()

    asyncio.run(run_flow())
    governance = server.runtime.governance.list_requests("pending")
    request_types = {request.request_type for request in governance}
    evolution_root = tmp_path / "self_evolution"
    self_state = json.loads((tmp_path / "experience" / "self_state.json").read_text(encoding="utf-8"))
    maintenance_events = [
        item.get("params", {}).get("payload", {})
        for item in writes
        if item.get("method") == "event"
        and item.get("params", {}).get("type") == "system.maintenance"
    ]
    latest_actions = {item["name"] for item in maintenance_events[-1]["actions"]}

    assert {
        "core_source_change",
        "model_finetune",
        "architecture_migration_deploy",
    }.issubset(request_types)
    assert any((evolution_root / "core_source_changes").glob("*/proposal.json"))
    assert any((evolution_root / "model_finetunes").glob("*/training_job.json"))
    assert any((evolution_root / "architecture_migrations").glob("*/deployment_plan.json"))
    assert {
        "self_evolution.core_source_change",
        "self_evolution.model_finetune",
        "self_evolution.architecture_migration_deploy",
    }.issubset(latest_actions)
    assert {
        "guarded_core_source_modification",
        "autonomous_model_finetuning",
        "governed_architecture_migration",
    }.issubset(set(self_state["capabilities"]))


def test_approved_self_evolution_requests_execute_and_write_audit_artifacts(tmp_path):
    from dual_ring_ai.runtime.local_runtime import LocalRuntime, LocalRuntimeConfig

    runtime = LocalRuntime(
        LocalRuntimeConfig(
            root_path=tmp_path,
            security_defaults={
                "network": True,
                "shell": True,
                "filesystem": {"read": ["*"], "write": ["*"]},
                "environment": {"allow": ["*"], "request": []},
            },
        )
    )
    source_path = tmp_path / "dual_ring_ai" / "runtime_marker.txt"
    source_path.parent.mkdir(parents=True)
    source_path.write_text("old\n", encoding="utf-8")
    core_dir = tmp_path / "self_evolution" / "core_source_changes" / "case"
    core_dir.mkdir(parents=True)
    proposal_path = core_dir / "proposal.json"
    patch_path = core_dir / "candidate.patch"
    proposal_path.write_text('{"type":"core_source_change"}', encoding="utf-8")
    patch_path.write_text(
        "\n".join(
            [
                "--- a/dual_ring_ai/runtime_marker.txt",
                "+++ b/dual_ring_ai/runtime_marker.txt",
                "@@ -1 +1 @@",
                "-old",
                "+new",
                "",
            ]
        ),
        encoding="utf-8",
    )
    core_request = runtime.governance.create_request(
        request_type="core_source_change",
        title="Apply core patch",
        payload={"proposal_path": str(proposal_path), "patch_path": str(patch_path)},
        requested_by="test",
        risk_level="critical",
    )

    with pytest.raises(PermissionError):
        runtime.apply_core_source_change_from_approval(core_request.request_id, approved_by="test")

    runtime.governance.decide(core_request.request_id, "approved", "test")
    core_result = runtime.apply_core_source_change_from_approval(core_request.request_id, approved_by="test")

    job_dir = tmp_path / "self_evolution" / "model_finetunes" / "case"
    job_dir.mkdir(parents=True)
    job_path = job_dir / "training_job.json"
    job_path.write_text(
        json.dumps(
            {
                "type": "model_finetune",
                "dataset_sources": ["experience/conversations.sqlite3"],
                "outputs": {"adapter_or_weights": str(job_dir / "outputs")},
                "safety": {"eval_required_before_promotion": True},
            }
        ),
        encoding="utf-8",
    )
    train_request = runtime.governance.create_request(
        request_type="model_finetune",
        title="Run training job",
        payload={"training_job_path": str(job_path)},
        requested_by="test",
        risk_level="critical",
    )
    runtime.governance.decide(train_request.request_id, "approved", "test")
    train_result = runtime.run_model_finetune_from_approval(train_request.request_id, approved_by="test")

    deploy_dir = tmp_path / "self_evolution" / "architecture_migrations" / "case"
    deploy_dir.mkdir(parents=True)
    plan_path = deploy_dir / "deployment_plan.json"
    plan_path.write_text(
        json.dumps(
            {
                "type": "architecture_migration_deploy",
                "phases": ["design", "test", "canary", "deploy", "rollback_ready"],
                "safety": {"rollback_required": True, "canary_required": True},
            }
        ),
        encoding="utf-8",
    )
    deploy_request = runtime.governance.create_request(
        request_type="architecture_migration_deploy",
        title="Deploy migration",
        payload={"deployment_plan_path": str(plan_path)},
        requested_by="test",
        risk_level="critical",
    )
    runtime.governance.decide(deploy_request.request_id, "approved", "test")
    deploy_result = runtime.deploy_architecture_migration_from_approval(
        deploy_request.request_id,
        approved_by="test",
    )

    audit_path = tmp_path / "self_evolution" / "audit.jsonl"
    audit_text = audit_path.read_text(encoding="utf-8")

    assert source_path.read_text(encoding="utf-8") == "new\n"
    assert Path(core_result["rollback_artifact"]).exists()
    assert core_result["status"] == "applied"
    assert train_result["status"] == "completed"
    assert Path(train_result["adapter_manifest_path"]).exists()
    assert deploy_result["status"] == "deployed"
    assert Path(deploy_result["deployment_run_path"]).exists()
    assert Path(deploy_result["rollback_plan_path"]).exists()
    assert "core_source_change.applied" in audit_text
    assert "model_finetune.completed" in audit_text
    assert "architecture_migration.deployed" in audit_text


def test_approving_self_evolution_request_from_tui_executes_backend_action(tmp_path):
    from tui_gateway.entry import JSONRPCServer

    writes = []
    server = JSONRPCServer(runtime_root=tmp_path, writer=writes.append, stream_delay=0)
    job_dir = tmp_path / "self_evolution" / "model_finetunes" / "case"
    job_dir.mkdir(parents=True)
    job_path = job_dir / "training_job.json"
    job_path.write_text(
        json.dumps(
            {
                "type": "model_finetune",
                "dataset_sources": ["experience/conversations.sqlite3"],
                "outputs": {"adapter_or_weights": str(job_dir / "outputs")},
            }
        ),
        encoding="utf-8",
    )
    request = server.runtime.governance.create_request(
        request_type="model_finetune",
        title="Run approved model fine-tune",
        payload={"training_job_path": str(job_path)},
        requested_by="test",
        risk_level="critical",
    )

    approved = asyncio.run(
        server.handle_approval_respond(
            {"request_id": request.request_id, "decision": "approved"}
        )
    )

    assert approved["ok"] is True
    assert approved["executed"]["method"] == "self_evolution.run_model_finetune"
    assert approved["executed"]["result"]["status"] == "completed"
    assert any(
        item.get("params", {}).get("type") == "tool.complete"
        and item.get("params", {}).get("payload", {}).get("name") == "self_evolution.run_model_finetune"
        for item in writes
    )


def test_reserved_slash_features_have_direct_natural_language_intents(tmp_path):
    from tui_gateway.entry import JSONRPCServer

    server = JSONRPCServer(runtime_root=tmp_path, writer=lambda _: None)
    samples = {
        "显示可用命令": ("natural.capabilities", {}),
        "开启新会话": ("session.create", {}),
        "继续会话 abc12345": ("session.resume", {"session_id": "abc12345"}),
        "打开模型选择器": ("model.options", {}),
        "切换模型 custom-model": ("model.configure", {"model": "custom-model"}),
        "把模型切到 custom-model": ("model.configure", {"model": "custom-model"}),
    }

    for text, (method, params) in samples.items():
        resolved = asyncio.run(server.handle_natural_resolve({"text": text}))
        assert resolved["matched"] is True
        assert resolved["method"] == method
        assert resolved["method"] != "slash.exec"
        for key, value in params.items():
            assert resolved["params"][key] == value


def test_tui_frontend_handles_runtime_steps_and_approval_queue():
    app_source = (ROOT / "ui-tui" / "src" / "app.tsx").read_text(encoding="utf-8")
    types_source = (ROOT / "ui-tui" / "src" / "types.ts").read_text(encoding="utf-8")
    panel_source = (
        ROOT / "ui-tui" / "src" / "components" / "runtimeActivityPanel.tsx"
    ).read_text(encoding="utf-8")

    required = [
        "RuntimeActivityPanel",
        "plan.update",
        "step.update",
        "approval.queue",
        "RuntimeStep",
        "ApprovalQueueItem",
        "执行步骤",
        "审批",
        "运行信号",
        "上下文",
        "风险",
        "runtime.risk",
        "context.compaction",
        "pending",
    ]
    combined = "\n".join([app_source, types_source, panel_source])

    assert all(text in combined for text in required)


def test_tui_approval_countdown_defaults_to_auto_approve():
    app_source = (ROOT / "ui-tui" / "src" / "app.tsx").read_text(encoding="utf-8")
    types_source = (ROOT / "ui-tui" / "src" / "types.ts").read_text(encoding="utf-8")
    overlay_source = (
        ROOT / "ui-tui" / "src" / "components" / "overlays.tsx"
    ).read_text(encoding="utf-8")
    combined = "\n".join([app_source, types_source, overlay_source])

    required = [
        "APPROVAL_AUTO_APPROVE_SECONDS = 30",
        "APPROVAL_TIMEOUT_DECISION = 'once'",
        "approvalTimeoutRemaining",
        "void answerOverlay(APPROVAL_TIMEOUT_DECISION)",
        "30 秒未操作将自动本次同意",
        "timeout_remaining?: number",
    ]

    assert all(text in combined for text in required)
    assert "timeout_remaining ?? APPROVAL_AUTO_APPROVE_SECONDS) <= 0" in app_source
    assert "void answerOverlay('deny')" not in app_source


def test_gateway_auto_approves_expired_manual_review_requests(tmp_path):
    from datetime import UTC, datetime, timedelta

    from tui_gateway.entry import JSONRPCServer

    writes = []
    server = JSONRPCServer(runtime_root=tmp_path, writer=writes.append, stream_delay=0)
    queued = asyncio.run(
        server.handle_natural_invoke(
            {
                "text": (
                    "run backend shell.exec "
                    "params={\"command\":\"python --version\"}"
                ),
                "auth_scopes": ["shell:execute"],
            }
        )
    )
    request_path = (
        tmp_path
        / "governance"
        / "requests"
        / f"{queued['approval_id']}.json"
    )
    request_payload = json.loads(request_path.read_text(encoding="utf-8"))
    request_payload["created_at"] = (
        datetime.now(UTC) - timedelta(seconds=31)
    ).isoformat()
    request_path.write_text(
        json.dumps(request_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    approvals = asyncio.run(server.handle_governance_requests({}))
    stored = server.runtime.governance.get_request(queued["approval_id"])
    completed_tools = [
        item.get("params", {}).get("payload", {})
        for item in writes
        if item.get("method") == "event"
        and item.get("params", {}).get("type") == "tool.complete"
    ]

    assert queued["requires_approval"] is True
    assert stored.status == "approved"
    assert stored.decided_by == "auto_approve_timeout"
    assert approvals["auto_approved"][0]["request_id"] == queued["approval_id"]
    assert approvals["auto_approved"][0]["executed"]["method"] == "shell.exec"
    assert any(item.get("name") == "shell.exec" for item in completed_tools)


def test_tui_frontend_supports_full_terminal_interaction_contract():
    app_source = (ROOT / "ui-tui" / "src" / "app.tsx").read_text(encoding="utf-8")
    text_input_source = (
        ROOT / "ui-tui" / "src" / "components" / "textInput.tsx"
    ).read_text(encoding="utf-8")
    tool_activity_source = (
        ROOT / "ui-tui" / "src" / "components" / "toolActivity.tsx"
    ).read_text(encoding="utf-8")
    gateway_source = (ROOT / "tui_gateway" / "entry.py").read_text(encoding="utf-8")
    combined = "\n".join(
        [app_source, text_input_source, tool_activity_source, gateway_source]
    )

    required = [
        "inputBuffer",
        "key.meta || key.shift",
        "input.endsWith('\\\\')",
        "composedInput",
        "complete.slash",
        "complete.path",
        "applyCompletion",
        "historyIndex",
        "session.interrupt",
        "terminal.redirect",
        "tool.progress",
        "ToolActivityPanel",
        "preview",
        "summary",
        "ink-text-input",
    ]

    assert all(text in combined for text in required)


def test_tui_input_mouse_wheel_navigates_message_history():
    app_source = (ROOT / "ui-tui" / "src" / "app.tsx").read_text(encoding="utf-8")
    entry_source = (ROOT / "ui-tui" / "src" / "entry.tsx").read_text(encoding="utf-8")
    text_input_source = (
        ROOT / "ui-tui" / "src" / "components" / "textInput.tsx"
    ).read_text(encoding="utf-8")

    required_entry = [
        "enableMouseReporting",
        "disableMouseReporting",
        "\\x1b[?1000h\\x1b[?1006h",
        "\\x1b[?1006l\\x1b[?1000l",
    ]
    required_input = [
        "mouseWheelDirection",
        "containsTerminalMouseEvent",
        "onHistoryPrevious",
        "onHistoryNext",
        "isWheelOverInputArea",
    ]
    required_app = [
        "navigateInputHistory",
        "navigateInputHistory('previous')",
        "navigateInputHistory('next')",
        "onHistoryPrevious",
        "onHistoryNext",
    ]

    assert all(text in entry_source for text in required_entry)
    assert all(text in text_input_source for text in required_input)
    assert all(text in app_source for text in required_app)


def test_tui_enter_executes_selected_slash_completion():
    app_source = (ROOT / "ui-tui" / "src" / "app.tsx").read_text(encoding="utf-8")

    required = [
        "submitCurrentInput",
        "completionItems.length",
        "completionItems[completionIndex]",
        "applyCompletionText",
        "completion.startsWith('/') && text.startsWith('/') && replaceFrom === 1",
        "void submitCurrentInput(applyCompletionText(input, item.text))",
        "onSubmit={() => {",
        "void submitCurrentInput(composedInput)",
    ]

    assert all(text in app_source for text in required)
    assert "`${input.slice(0, replaceFrom)}${item.text}`" not in app_source


def test_tui_custom_model_picker_collects_base_url_key_and_model():
    app_source = (ROOT / "ui-tui" / "src" / "app.tsx").read_text(encoding="utf-8")
    types_source = (ROOT / "ui-tui" / "src" / "types.ts").read_text(encoding="utf-8")
    overlay_source = (
        ROOT / "ui-tui" / "src" / "components" / "overlays.tsx"
    ).read_text(encoding="utf-8")
    combined = "\n".join([app_source, types_source, overlay_source])

    required = [
        "modelSetup",
        "base_url",
        "api_key_env",
        "api_key",
        "model.setup",
        "自定义模型配置",
        "接口地址",
        "密钥环境变量",
        "API 密钥",
        "模型型号",
    ]

    assert all(text in combined for text in required)
    assert "'model.configure', {\n            provider: selected.slug" not in app_source


def test_tui_gateway_supports_terminal_redirection_for_slash_shell_and_prompt(tmp_path):
    from tui_gateway.entry import JSONRPCServer

    writes = []
    server = JSONRPCServer(runtime_root=tmp_path, writer=writes.append, stream_delay=0)

    status = asyncio.run(server.handle_session_status({}))
    redirect = asyncio.run(
        server._apply_terminal_redirect(status["output"], {"path": "terminal/status.txt", "mode": "write"})
    )
    shell = asyncio.run(
        server.handle_shell_exec({"command": "python --version >> terminal/status.txt"})
    )

    async def run_prompt():
        result = await server.handle_prompt_submit(
            {"text": "check status > terminal/prompt.txt"}
        )
        await server.wait_for_background()
        return result

    prompt = asyncio.run(run_prompt())
    status_path = tmp_path / "terminal" / "status.txt"
    prompt_path = tmp_path / "terminal" / "prompt.txt"
    complete_events = [
        item["params"]["payload"]
        for item in writes
        if item.get("method") == "event"
        and item["params"]["type"] == "message.complete"
    ]

    assert redirect["mode"] == "write"
    assert shell["redirect"]["mode"] == "append"
    assert prompt == {"status": "streaming"}
    assert status_path.exists()
    assert "会话：" in status_path.read_text(encoding="utf-8")
    assert "Python" in status_path.read_text(encoding="utf-8")
    assert prompt_path.exists()
    assert prompt_path.read_text(encoding="utf-8").strip()
    assert complete_events[-1]["redirect"]["path"] == str(prompt_path)


def test_tui_gateway_streams_runtime_steps_and_approval_queue(tmp_path):
    from tui_gateway.entry import JSONRPCServer

    writes = []
    server = JSONRPCServer(runtime_root=tmp_path, writer=writes.append, stream_delay=0)
    approval = server.runtime.governance.create_request(
        request_type="shell",
        title="Run command",
        payload={"command": "echo ok"},
        requested_by="test",
        risk_level="low",
    )

    async def run_prompt():
        result = await server.handle_prompt_submit({"text": "check approvals"})
        await server.wait_for_background()
        return result

    result = asyncio.run(run_prompt())
    events = [
        item["params"]
        for item in writes
        if item.get("method") == "event"
    ]
    event_types = [item["type"] for item in events]
    approval_events = [
        item["payload"]
        for item in events
        if item["type"] == "approval.queue"
    ]

    assert result == {"status": "streaming"}
    assert "plan.update" in event_types
    assert "step.update" in event_types
    assert "approval.queue" in event_types
    assert "approval.request" in event_types
    assert any(
        queued["request_id"] == approval.request_id
        for payload in approval_events
        for queued in payload["approvals"]
    )


def test_control_api_no_longer_serves_web_or_desktop_frontends(tmp_path):
    from dual_ring_ai.dashboard.cockpit_api import create_cockpit_app
    from dual_ring_ai.runtime.local_runtime import LocalRuntime, LocalRuntimeConfig

    runtime = LocalRuntime(LocalRuntimeConfig(root_path=tmp_path))
    client = TestClient(create_cockpit_app(runtime))

    assert client.get("/").status_code == 404
    assert client.get("/desktop/contract").status_code == 404
    assert client.get("/status").status_code == 200
    assert client.get("/api/status").status_code == 200


def test_tui_gateway_uses_jsonrpc_event_envelope(tmp_path):
    from tui_gateway.entry import JSONRPCServer

    writes = []
    server = JSONRPCServer(runtime_root=tmp_path, writer=writes.append)

    asyncio.run(server.send_event("status.update", {"text": "ready"}))

    assert writes == [
        {
            "jsonrpc": "2.0",
            "method": "event",
            "params": {
                "type": "status.update",
                "session_id": server.session_id,
                "payload": {"text": "ready"},
            },
        }
    ]


def test_tui_gateway_session_and_completion_contract(tmp_path):
    from tui_gateway.entry import JSONRPCServer

    server = JSONRPCServer(runtime_root=tmp_path, writer=lambda _: None)

    created = asyncio.run(server.handle_session_create({"cols": 100}))
    slash = asyncio.run(server.handle_complete_slash({"text": "/"}))
    path = asyncio.run(server.handle_complete_path({"text": "@ui-tui/src/app"}))

    assert created["session_id"] == server.session_id
    assert created["info"]["cwd"] == str(ROOT)
    assert [item["text"] for item in slash["items"]] == ["/help", "/new", "/model"]
    assert slash["replace_from"] == 1
    assert any(item["text"].endswith("ui-tui/src/app.tsx") for item in path["items"])


def test_tui_gateway_prompt_submit_streams_runtime_result(tmp_path):
    from tui_gateway.entry import JSONRPCServer

    writes = []
    server = JSONRPCServer(runtime_root=tmp_path, writer=writes.append, stream_delay=0)

    async def run_prompt():
        result = await server.handle_prompt_submit({"text": "check status"})
        await server.wait_for_background()
        return result

    result = asyncio.run(run_prompt())
    event_types = [
        item["params"]["type"]
        for item in writes
        if item.get("method") == "event"
    ]
    complete = [
        item["params"]["payload"]
        for item in writes
        if item.get("method") == "event"
        and item["params"]["type"] == "message.complete"
    ][0]

    assert result == {"status": "streaming"}
    assert event_types[:3] == ["session.info", "message.start", "thinking.delta"]
    assert "tool.start" in event_types
    assert "tool.complete" in event_types
    assert event_types[-1] == "message.complete"
    assert complete["text"]
    assert complete["usage"]["total"] > 0


def test_tui_gateway_prompt_submit_response_precedes_stream_events(tmp_path):
    from tui_gateway.entry import JSONRPCServer

    writes = []
    server = JSONRPCServer(runtime_root=tmp_path, writer=writes.append, stream_delay=0)

    async def run_request():
        await server.handle_request(
            '{"jsonrpc":"2.0","id":"r1","method":"prompt.submit","params":{"text":"hello"}}'
        )
        first = list(writes)
        await server.wait_for_background()
        return first

    first_writes = asyncio.run(run_request())

    assert first_writes == [
        {
            "jsonrpc": "2.0",
            "id": "r1",
            "result": {"status": "streaming"},
        }
    ]
    assert [item["params"]["type"] for item in writes if item.get("method") == "event"][:3] == [
        "session.info",
        "message.start",
        "thinking.delta",
    ]


def test_tui_gateway_prompt_flows_and_slash_commands(tmp_path):
    from tui_gateway.entry import JSONRPCServer

    writes = []
    server = JSONRPCServer(runtime_root=tmp_path, writer=writes.append)

    approval = server.runtime.governance.create_request(
        request_type="shell",
        title="Run command",
        payload={"command": "echo ok"},
        requested_by="test",
        risk_level="low",
    )
    approvals = asyncio.run(server.handle_governance_requests({}))
    approval_response = asyncio.run(
        server.handle_approval_respond(
            {"request_id": approval.request_id, "decision": "once"}
        )
    )
    clarify = asyncio.run(
        server.handle_demo_clarify(
            {"question": "Pick one", "choices": ["A", "B"]}
        )
    )
    secret = asyncio.run(
        server.handle_demo_secret({"env_var": "OPENAI_API_KEY"})
    )
    help_output = asyncio.run(server.handle_slash_exec({"text": "/help"}))

    event_types = [
        item["params"]["type"]
        for item in writes
        if item.get("method") == "event"
    ]

    assert any(item["request_id"] == approval.request_id for item in approvals["requests"])
    assert approval_response == {"ok": True}
    assert clarify["request_id"].startswith("clarify_")
    assert secret["request_id"].startswith("secret_")
    assert "clarify.request" in event_types
    assert "secret.request" in event_types
    assert "/status" not in help_output["output"]
    assert "/help" in help_output["output"]


def test_tui_gateway_shell_and_command_catalog(tmp_path):
    from tui_gateway.entry import JSONRPCServer

    server = JSONRPCServer(runtime_root=tmp_path, writer=lambda _: None)

    shell = asyncio.run(server.handle_shell_exec({"command": "python --version"}))
    catalog = asyncio.run(server.handle_commands_catalog({}))
    tools = asyncio.run(server.handle_toolsets_list({}))
    pasted = asyncio.run(server.handle_clipboard_paste({}))

    assert shell["code"] == 0
    assert "Python" in (shell["stdout"] + shell["stderr"])
    assert any(category["name"] == "core" for category in catalog["categories"])
    assert "runtime" in tools["toolsets"]
    assert pasted["attached"] is False


def test_tui_gateway_exposes_real_backend_runtime_capabilities(tmp_path):
    from tui_gateway.entry import JSONRPCServer

    server = JSONRPCServer(runtime_root=tmp_path, writer=lambda _: None)

    health = asyncio.run(server.handle_runtime_health({}))
    preflight = asyncio.run(server.handle_runtime_preflight({}))
    host = asyncio.run(server.handle_runtime_host_probe({}))
    messaging = asyncio.run(server.handle_runtime_messaging_status({}))
    blueprints = asyncio.run(server.handle_runtime_blueprints({}))
    skills = asyncio.run(server.handle_runtime_skills({}))
    algorithms = asyncio.run(server.handle_runtime_algorithms({}))
    audits = asyncio.run(server.handle_runtime_audits({}))
    avatar = asyncio.run(server.handle_runtime_avatar({}))
    ui_status = asyncio.run(server.handle_runtime_terminal_ui({}))
    events = asyncio.run(server.handle_runtime_events({"limit": 5}))
    preflight_write = asyncio.run(server.handle_runtime_write_preflight({}))
    smoke = asyncio.run(server.handle_runtime_operational_smoke({"cycles": 1}))
    stress = asyncio.run(server.handle_runtime_interaction_stress({"cycles": 1}))
    catalog = asyncio.run(server.handle_commands_catalog({}))

    command_names = {
        command["name"]
        for category in catalog["categories"]
        for command in category["commands"]
    }

    assert "services" in health["runtime"]
    assert "adapters" in health
    assert "summary" in preflight
    assert "tools" in host
    assert messaging["status"] in {"ready", "disabled"}
    assert isinstance(blueprints["blueprints"], list)
    assert isinstance(skills["skills"], list)
    assert isinstance(algorithms["algorithms"], list)
    assert "skill_lifecycle" in audits
    assert "algorithm_evolution" in audits
    assert avatar["avatar_event"]["animation"]
    assert ui_status["status"] == "ready"
    assert isinstance(events["events"], list)
    assert Path(preflight_write["path"]).exists()
    assert smoke["summary"]["cycles"] == 1
    assert stress["cycles"] == 1
    assert {
        "runtime.health",
        "runtime.preflight",
        "runtime.write_preflight",
        "runtime.host_probe",
        "runtime.messaging_status",
        "runtime.blueprints",
        "runtime.skills",
        "runtime.algorithms",
        "runtime.audits",
        "runtime.avatar",
        "runtime.events",
        "runtime.terminal_ui",
        "runtime.operational_smoke",
        "runtime.interaction_stress",
    }.issubset(command_names)


def test_tui_gateway_exposes_backend_action_capabilities(tmp_path):
    from tui_gateway.entry import JSONRPCServer

    server = JSONRPCServer(runtime_root=tmp_path, writer=lambda _: None)
    server.runtime.start()

    host_write = asyncio.run(server.handle_runtime_write_host_probe({}))
    acceptance = asyncio.run(
        server.handle_runtime_final_acceptance({"stress_cycles": 1})
    )
    adapters = asyncio.run(server.handle_runtime_adapters({}))
    approvals = asyncio.run(server.handle_governance_requests({}))
    decision_request = server.runtime.governance.create_request(
        request_type="shell",
        title="Run command",
        payload={"command": "echo ok"},
        requested_by="test",
        risk_level="low",
    )
    decision = asyncio.run(
        server.handle_governance_decide(
            {
                "request_id": decision_request.request_id,
                "decision": "approved",
                "decided_by": "test",
                "comments": "ok",
            }
        )
    )
    platform = asyncio.run(
        server.handle_runtime_platform_message(
            {"platform": "missing", "payload": {"text": "hello"}}
        )
    )
    catalog = asyncio.run(server.handle_commands_catalog({}))
    capabilities = asyncio.run(server.handle_natural_capabilities({}))

    command_names = {
        command["name"]
        for category in catalog["categories"]
        for command in category["commands"]
    }
    natural_methods = {
        item.get("method", item["command"])
        for item in capabilities["commands"]
    }

    assert Path(host_write["path"]).exists()
    assert Path(acceptance["path"]).exists()
    assert acceptance["report"]["summary"]["status"] in {
        "ready_for_real_integration",
        "attention_required",
    }
    assert "remote_llm" in adapters["adapters"]
    assert isinstance(approvals["requests"], list)
    assert decision["request"]["status"] == "approved"
    assert platform["status"] == "error"
    assert "platform adapter is not configured" in platform["error"]
    assert {
        "runtime.write_host_probe",
        "runtime.final_acceptance",
        "runtime.adapters",
        "runtime.platform_message",
        "governance.requests",
        "governance.decide",
        "skill.request_publish",
        "skill.publish_approved",
        "algorithm.request_research",
        "algorithm.run_experiment",
        "algorithm.request_promotion",
        "algorithm.apply_promotion",
        "organization.request_change",
        "organization.apply_change",
        "organization.rollback",
    }.issubset(command_names)
    assert {
        "runtime.final_acceptance",
        "governance.requests",
        "governance.decide",
        "skill.request_publish",
        "algorithm.request_research",
        "organization.request_change",
    }.issubset(natural_methods)


def test_tui_tools_catalog_shows_backend_schema_auth_risk_and_natural_usage(tmp_path):
    from tui_gateway.entry import JSONRPCServer

    server = JSONRPCServer(runtime_root=tmp_path, writer=lambda _: None)

    catalog = asyncio.run(server.handle_commands_catalog({}))
    capabilities = asyncio.run(server.handle_natural_capabilities({}))
    command_by_name = {
        command["name"]: command
        for category in catalog["categories"]
        for command in category["commands"]
    }

    shell = command_by_name["shell.exec"]
    acceptance = command_by_name["runtime.final_acceptance"]

    assert shell["auth_scope"] == "shell:execute"
    assert shell["risk_level"] == "high"
    assert shell["requires_approval"] is True
    assert shell["input_schema"]["required"] == ["command"]
    assert acceptance["auth_scope"] == "runtime:write"
    assert acceptance["input_schema"]["properties"]["stress_cycles"]["maximum"] == 10
    assert any(item.get("method") == "shell.exec" for item in capabilities["commands"])
    assert any("text" in item["input_modes"] for item in capabilities["commands"])
    assert any("voice" in item["input_modes"] for item in capabilities["commands"])
    assert not any(item["command"] == "/status" for item in capabilities["commands"])



def test_gateway_routes_text_and_voice_natural_language_to_all_commands(tmp_path):
    from tui_gateway.entry import JSONRPCServer, SLASH_COMMANDS

    server = JSONRPCServer(runtime_root=tmp_path, writer=lambda _: None)

    capabilities = asyncio.run(server.handle_natural_capabilities({}))
    text_shell = asyncio.run(
        server.handle_natural_invoke({"text": "运行命令 python --version"})
    )
    voice_platform = asyncio.run(
        server.handle_voice_invoke({"text": "给飞书发消息：部署完成"})
    )

    slash_commands = {item["text"] for item in SLASH_COMMANDS}
    supported_commands = {item["command"] for item in capabilities["commands"]}

    assert slash_commands.issubset(supported_commands)
    assert text_shell["matched"] is True
    assert text_shell["method"] == "shell.exec"
    assert text_shell["result"]["code"] == 0
    assert "Python" in (text_shell["result"]["stdout"] + text_shell["result"]["stderr"])
    assert voice_platform["source"] == "voice"
    assert voice_platform["matched"] is True
    assert voice_platform["method"] == "runtime.platform_message"


def test_tui_chinese_utf8_environment_and_visible_copy(tmp_path):
    from tui_gateway.entry import JSONRPCServer

    gateway_source = (ROOT / "ui-tui" / "src" / "gatewayClient.ts").read_text(encoding="utf-8")
    launch_source = (ROOT / "scripts" / "launch_tui.py").read_text(encoding="utf-8")
    branding_source = (ROOT / "ui-tui" / "src" / "components" / "branding.tsx").read_text(encoding="utf-8")
    empty_source = (ROOT / "ui-tui" / "src" / "components" / "emptyState.tsx").read_text(encoding="utf-8")
    overlay_source = (ROOT / "ui-tui" / "src" / "components" / "overlays.tsx").read_text(encoding="utf-8")
    server = JSONRPCServer(runtime_root=tmp_path, writer=lambda _: None)

    combined_source = "\n".join([gateway_source, launch_source, branding_source, empty_source, overlay_source])
    snapshot = server.runtime.status_snapshot()
    combined_output = json.dumps(snapshot, ensure_ascii=False)

    assert "PYTHONIOENCODING" in combined_source
    assert "PYTHONUTF8" in combined_source
    assert "zh_CN.UTF-8" in combined_source
    assert "本地智能体终端" in combined_source
    assert "自然语言交互" in combined_source
    assert "需要审批" in combined_source
    assert "services" in snapshot
    assert not any(fragment in combined_output for fragment in ["娌", "瀹", "鐘", "�"])


def test_tui_frontend_invokes_plain_text_intents_without_slash_roundtrip():
    app_source = (ROOT / "ui-tui" / "src" / "app.tsx").read_text(encoding="utf-8")
    gateway_source = (ROOT / "tui_gateway" / "entry.py").read_text(encoding="utf-8")

    required_app = [
        "natural.resolve",
        "natural.matched",
        "natural.invoke",
        "formatNaturalResult(executed)",
    ]
    required_gateway = [
        "handle_natural_resolve",
        "handle_natural_invoke",
        "handle_voice_invoke",
        "handle_natural_capabilities",
        "NATURAL_DIRECT_ALIASES",
    ]

    assert all(text in app_source for text in required_app)
    assert all(text in gateway_source for text in required_gateway)
    assert "await handleSlash(natural.command)" not in app_source
    assert "NATURAL_SLASH_BACKEND_METHODS" not in gateway_source


def test_natural_language_can_execute_any_backend_catalog_method(tmp_path):
    from tui_gateway.entry import JSONRPCServer

    server = JSONRPCServer(runtime_root=tmp_path, writer=lambda _: None)

    catalog = asyncio.run(server.handle_commands_catalog({}))
    capabilities = asyncio.run(server.handle_natural_capabilities({}))
    acceptance = asyncio.run(
        server.handle_natural_invoke(
            {
                "text": (
                    "run backend runtime.final_acceptance "
                    "params={\"stress_cycles\":1}"
                )
            }
        )
    )
    adapters = asyncio.run(server._execute_agent_tool("runtime.adapters", {}))
    governance = asyncio.run(
        server.handle_natural_invoke({"text": "run backend governance.requests"})
    )

    catalog_methods = {
        command["name"]
        for category in catalog["categories"]
        for command in category["commands"]
        if not command["name"].startswith("/")
    }
    capability_methods = {
        item.get("method")
        for item in capabilities["commands"]
        if item.get("method")
    }

    assert capability_methods.issubset(
        catalog_methods
        | {
            "/help",
            "/new",
            "/model",
            "!shell",
            "prompt.submit",
            "natural.capabilities",
            "model.options",
            "session.create",
            "session.close",
            "session.steer",
        }
    )
    assert acceptance["matched"] is True
    assert acceptance["method"] == "runtime.final_acceptance"
    assert acceptance["result"]["report"]["summary"]["status"] in {
        "ready_for_real_integration",
        "attention_required",
    }
    assert adapters["ok"] is True
    assert "remote_llm" in adapters["adapters"]
    assert governance["matched"] is True
    assert governance["method"] == "governance.requests"
    assert isinstance(governance["result"]["requests"], list)


def test_plain_natural_language_invokes_backend_capability_aliases(tmp_path):
    from tui_gateway.entry import JSONRPCServer

    server = JSONRPCServer(runtime_root=tmp_path, writer=lambda _: None)

    adapters = asyncio.run(server._execute_agent_tool("runtime.adapters", {}))
    acceptance = asyncio.run(
        server.handle_natural_invoke(
            {
                "text": (
                    "create final acceptance report "
                    "params={\"stress_cycles\":1}"
                )
            }
        )
    )
    approvals = asyncio.run(
        server.handle_natural_invoke({"text": "show governance requests"})
    )
    platform = asyncio.run(
        server.handle_natural_invoke(
            {
                "text": (
                    "send platform message "
                    "params={\"platform\":\"missing\",\"payload\":{\"text\":\"hello\"}}"
                )
            }
        )
    )

    assert adapters["ok"] is True
    assert "remote_llm" in adapters["adapters"]
    assert acceptance["matched"] is True
    assert acceptance["method"] == "runtime.final_acceptance"
    assert acceptance["result"]["report"]["summary"]["status"] in {
        "ready_for_real_integration",
        "attention_required",
    }
    assert approvals["matched"] is True
    assert approvals["method"] == "governance.requests"
    assert isinstance(approvals["result"]["requests"], list)
    assert platform["matched"] is True
    assert platform["method"] == "runtime.platform_message"
    assert platform["ok"] is False
    assert platform["error"]["code"] == "BACKEND_ERROR"


def test_natural_language_intent_recognizer_handles_chinese_freeform_requests(tmp_path):
    from tui_gateway.entry import JSONRPCServer

    server = JSONRPCServer(runtime_root=tmp_path, writer=lambda _: None)
    approval = server.runtime.governance.create_request(
        request_type="agent_tool",
        title="Run shell command",
        payload={"method": "shell.exec", "params": {"command": "python --version"}},
        requested_by="test",
        risk_level="high",
    )

    remember = asyncio.run(
        server.handle_natural_invoke({"text": "请记住：CSV 清洗时要先统一表头"})
    )
    search = asyncio.run(
        server.handle_natural_invoke({"text": "帮我搜索过去对话里关于 CSV 的内容"})
    )
    platform = asyncio.run(
        server.handle_natural_invoke({"text": "给飞书发消息：部署完成"})
    )
    approval_once = asyncio.run(
        server.handle_natural_invoke({"text": "同意最新审批"})
    )

    assert remember["matched"] is True
    assert remember["method"] == "experience.record"
    assert remember["params"]["text"] == "CSV 清洗时要先统一表头"
    assert remember["ok"] is True
    assert search["matched"] is True
    assert search["method"] == "conversation.search"
    assert search["params"]["query"] == "CSV"
    assert platform["matched"] is True
    assert platform["method"] == "runtime.platform_message"
    assert platform["params"] == {"platform": "feishu", "payload": {"text": "部署完成"}}
    assert approval_once["matched"] is True
    assert approval_once["method"] == "approval.respond"
    assert approval_once["params"] == {"request_id": approval.request_id, "decision": "once"}


def test_natural_language_intent_recognizer_extracts_common_english_freeform_params(tmp_path):
    from tui_gateway.entry import JSONRPCServer

    server = JSONRPCServer(runtime_root=tmp_path, writer=lambda _: None)

    recall = asyncio.run(
        server.handle_natural_invoke({"text": "search previous conversations for deployment rollback"})
    )
    remember = asyncio.run(
        server.handle_natural_invoke({"text": "remember that deployment rollback needs approval"})
    )
    platform = asyncio.run(
        server.handle_natural_invoke({"text": "send feishu message deployment finished"})
    )
    acceptance = asyncio.run(
        server.handle_natural_invoke({"text": "run final acceptance with 2 cycles"})
    )

    assert recall["matched"] is True
    assert recall["method"] == "conversation.search"
    assert recall["params"]["query"] == "deployment rollback"
    assert remember["matched"] is True
    assert remember["method"] == "experience.record"
    assert remember["params"]["text"] == "deployment rollback needs approval"
    assert platform["matched"] is True
    assert platform["method"] == "runtime.platform_message"
    assert platform["params"] == {"platform": "feishu", "payload": {"text": "deployment finished"}}
    assert acceptance["matched"] is True
    assert acceptance["method"] == "runtime.final_acceptance"
    assert acceptance["params"] == {"stress_cycles": 2}


def test_natural_language_intent_recognizer_understands_plain_chinese_intents(tmp_path):
    from tui_gateway.entry import JSONRPCServer

    server = JSONRPCServer(runtime_root=tmp_path, writer=lambda _: None)

    remember = asyncio.run(
        server.handle_natural_resolve({"text": "把这个经验存起来：CSV 清洗前先统一表头"})
    )
    recall = asyncio.run(
        server.handle_natural_resolve({"text": "回忆一下之前关于 CSV 清洗的对话"})
    )
    shell = asyncio.run(
        server.handle_natural_resolve({"text": "帮我跑一下 python --version"})
    )
    model = asyncio.run(
        server.handle_natural_resolve({"text": "切换到模型 LongCat-Flash-Lite"})
    )
    weixin = asyncio.run(
        server.handle_natural_resolve({"text": "给微信发消息：部署完成"})
    )

    assert remember["matched"] is True
    assert remember["intent"] == "memory.record_experience"
    assert remember["method"] == "experience.record"
    assert remember["params"]["text"] == "CSV 清洗前先统一表头"
    assert recall["matched"] is True
    assert recall["intent"] == "memory.search_conversation"
    assert recall["method"] == "conversation.search"
    assert recall["params"]["query"] == "CSV 清洗"
    assert shell["matched"] is True
    assert shell["intent"] == "system.shell_exec"
    assert shell["method"] == "shell.exec"
    assert shell["command_text"] == "python --version"
    assert model["matched"] is True
    assert model["intent"] == "model.configure"
    assert model["method"] == "model.configure"
    assert model["params"]["model"] == "LongCat-Flash-Lite"
    assert weixin["matched"] is True
    assert weixin["intent"] == "messaging.send"
    assert weixin["method"] == "runtime.platform_message"
    assert weixin["params"] == {"platform": "weixin", "payload": {"text": "部署完成"}}


def test_prompt_submit_is_invoked_by_text_and_voice_natural_language(tmp_path):
    from tui_gateway.entry import JSONRPCServer

    text_writes = []
    voice_writes = []
    text_server = JSONRPCServer(runtime_root=tmp_path / "text", writer=text_writes.append, stream_delay=0)
    voice_server = JSONRPCServer(runtime_root=tmp_path / "voice", writer=voice_writes.append, stream_delay=0)

    async def run_text():
        result = await text_server.handle_natural_invoke({"text": "chat hello runtime"})
        await text_server.wait_for_background()
        return result

    async def run_voice():
        result = await voice_server.handle_voice_invoke({"text": "ask hello runtime"})
        await voice_server.wait_for_background()
        return result

    text_result = asyncio.run(run_text())
    voice_result = asyncio.run(run_voice())
    text_events = [
        item["params"]["type"]
        for item in text_writes
        if item.get("method") == "event"
    ]
    voice_events = [
        item["params"]["type"]
        for item in voice_writes
        if item.get("method") == "event"
    ]

    assert text_result["matched"] is True
    assert text_result["method"] == "prompt.submit"
    assert text_result["ok"] is True
    assert text_result["result"] == {"status": "streaming"}
    assert "message.complete" in text_events
    assert voice_result["matched"] is True
    assert voice_result["source"] == "voice"
    assert voice_result["method"] == "prompt.submit"
    assert voice_result["ok"] is True
    assert voice_result["result"] == {"status": "streaming"}
    assert "message.complete" in voice_events


def test_runtime_lifecycle_methods_are_natural_language_tools(tmp_path):
    from tui_gateway.entry import JSONRPCServer

    server = JSONRPCServer(runtime_root=tmp_path, writer=lambda _: None)

    catalog = asyncio.run(server.handle_commands_catalog({}))
    capabilities = asyncio.run(server.handle_natural_capabilities({}))
    status = asyncio.run(server._execute_agent_tool("runtime.status_snapshot", {}))
    stopped = asyncio.run(server.handle_natural_invoke({"text": "run backend runtime.stop"}))
    started = asyncio.run(server.handle_voice_invoke({"text": "run backend runtime.start"}))

    catalog_methods = {
        command["name"]
        for category in catalog["categories"]
        for command in category["commands"]
    }
    natural_methods = {
        item.get("method") or item.get("command")
        for item in capabilities["commands"]
    }

    assert {
        "runtime.status_snapshot",
        "runtime.start",
        "runtime.stop",
    }.issubset(catalog_methods)
    assert {
        "runtime.start",
        "runtime.stop",
    }.issubset(natural_methods)
    assert "runtime.status_snapshot" not in natural_methods
    assert status["ok"] is True
    assert "services" in status
    assert stopped["matched"] is True
    assert stopped["ok"] is True
    assert stopped["result"]["running"] is False
    assert started["matched"] is True
    assert started["source"] == "voice"
    assert started["ok"] is True
    assert started["result"]["running"] is True


def test_experience_learning_exposes_user_memory_while_self_model_updates_self_run(tmp_path):
    from tui_gateway.entry import JSONRPCServer

    server = JSONRPCServer(runtime_root=tmp_path, writer=lambda _: None)

    catalog = asyncio.run(server.handle_commands_catalog({}))
    capabilities = asyncio.run(server.handle_natural_capabilities({}))
    recorded = asyncio.run(
        server.handle_natural_invoke(
            {
                "text": (
                    "run backend experience.record "
                    "params={\"text\":\"Learned CSV cleanup from prior work\",\"tags\":[\"csv\"]}"
                )
            }
        )
    )
    searched = asyncio.run(
        server.handle_voice_invoke({"text": "run backend experience.search query=CSV"})
    )
    updated = asyncio.run(
        server._execute_agent_tool(
            "self_model.update",
            {
                "observation": "I improve by reusing experience",
                "capability": "experience_learning",
                "preference": "terminal_first",
            },
        )
    )
    read_model = asyncio.run(
        server.handle_natural_invoke({"text": "run backend self_model.read"})
    )
    drafted = asyncio.run(
        server.handle_natural_invoke(
            {
                "text": (
                    "run backend skill.draft_from_experience "
                    "params={\"query\":\"CSV\",\"skill_name\":\"csv_experience_skill\"}"
                )
            }
        )
    )

    catalog_methods = {
        command["name"]
        for category in catalog["categories"]
        for command in category["commands"]
    }
    natural_methods = {
        item.get("method") or item.get("command")
        for item in capabilities["commands"]
    }

    expected_catalog = {
        "experience.record",
        "experience.search",
        "self_model.read",
        "self_model.update",
        "skill.draft_from_experience",
    }
    expected_natural = {
        "experience.record",
        "experience.search",
        "self_model.read",
        "skill.draft_from_experience",
    }
    assert expected_catalog.issubset(catalog_methods)
    assert expected_natural.issubset(natural_methods)
    assert "self_model.update" not in natural_methods
    assert recorded["matched"] is True
    assert recorded["method"] == "experience.record"
    assert recorded["ok"] is True
    assert recorded["result"]["text"] == "Learned CSV cleanup from prior work"
    assert searched["source"] == "voice"
    assert searched["ok"] is True
    assert searched["result"]["matches"][0]["id"] == recorded["result"]["id"]
    assert updated["ok"] is True
    assert "experience_learning" in updated["capabilities"]
    assert read_model["result"]["capabilities"] == updated["capabilities"]
    assert read_model["result"]["preferences"] == updated["preferences"]
    assert drafted["ok"] is True
    assert drafted["result"]["status"] == "drafted"
    assert Path(drafted["result"]["proposal_dir"]).exists()


def test_prompt_usage_auto_records_conversation_experience_and_updates_self_model(tmp_path):
    from tui_gateway.entry import JSONRPCServer

    writes = []
    server = JSONRPCServer(runtime_root=tmp_path, writer=writes.append, stream_delay=0)

    async def run_prompt():
        result = await server.handle_natural_invoke({"text": "chat remember that CSV cleanup uses normalized headers"})
        await server.wait_for_background()
        return result

    prompt = asyncio.run(run_prompt())
    search = asyncio.run(
        server.handle_voice_invoke({"text": "run backend conversation.search query=CSV"})
    )
    model = asyncio.run(
        server.handle_natural_invoke({"text": "run backend self_model.read"})
    )

    assert prompt["matched"] is True
    assert prompt["method"] == "prompt.submit"
    assert search["source"] == "voice"
    assert search["ok"] is True
    assert search["result"]["matches"]
    assert "CSV cleanup" in search["result"]["matches"][0]["text"]
    assert model["ok"] is True
    assert model["result"]["version"] >= 1
    assert any(
        "chat prompt" in item["text"]
        for item in model["result"]["observations"]
    )


def test_memory_planning_user_model_and_skill_evolution_self_run_with_backend_escape_hatch(tmp_path):
    from tui_gateway.entry import JSONRPCServer

    server = JSONRPCServer(runtime_root=tmp_path, writer=lambda _: None)

    record = asyncio.run(
        server.handle_natural_invoke(
            {
                "text": (
                    "run backend conversation.record "
                    "params={\"session_id\":\"s1\",\"role\":\"user\","
                    "\"text\":\"CSV cleanup needs header normalization\","
                    "\"user_id\":\"operator\"}"
                )
            }
        )
    )
    search = asyncio.run(
        server.handle_voice_invoke(
            {"text": "run backend conversation.search query=CSV"}
        )
    )
    tick = asyncio.run(
        server._execute_agent_tool(
            "memory.periodic_tick",
            {"task": "Plan CSV cleanup improvement", "cadence": "daily"},
        )
    )
    user_model = asyncio.run(
        server._execute_agent_tool(
            "user_model.update",
            {
                "user_id": "operator",
                "observation": "User wants concise execution with architecture tradeoffs",
            },
        )
    )
    draft = asyncio.run(
        server._execute_agent_tool(
            "skill.autonomous_from_task",
            {
                "task_text": "Complex CSV cleanup with header normalization",
                "skill_name": "csv_cleanup_auto",
            },
        )
    )
    improved = asyncio.run(
        server._execute_agent_tool(
            "skill.improve_from_usage",
            {
                "skill_name": "csv_cleanup_auto",
                "feedback": "Used once; include validation checklist",
            },
        )
    )
    capabilities = asyncio.run(server.handle_natural_capabilities({}))

    natural_methods = {
        item.get("method") or item.get("command")
        for item in capabilities["commands"]
    }

    assert {
        "conversation.record",
        "user_model.query",
    }.issubset(natural_methods)
    assert {
        "memory.periodic_tick",
        "user_model.update",
        "skill.autonomous_from_task",
        "skill.improve_from_usage",
    }.isdisjoint(natural_methods)
    assert record["ok"] is True
    assert record["method"] == "conversation.record"
    assert search["source"] == "voice"
    assert search["result"]["engine"] == "sqlite_fts5"
    assert search["result"]["summary"]
    assert tick["status"] == "recorded"
    assert user_model["model"]["synthesis"]
    assert Path(draft["proposal_dir"], "SKILL.md").exists()
    assert improved["version"] == "0.1.1"


def test_skill_merge_preview_and_merge_are_natural_language_tools(tmp_path):
    from dual_ring_ai.test_controlled_skill_lifecycle import write_skill
    from tui_gateway.entry import JSONRPCServer

    server = JSONRPCServer(runtime_root=tmp_path, writer=lambda _: None)
    first_skill = tmp_path / "workspace" / "skill_proposals" / "reader"
    second_skill = tmp_path / "workspace" / "skill_proposals" / "validator"
    write_skill(first_skill, name="reader", version="1.0.0")
    write_skill(second_skill, name="validator", version="1.0.1")
    merge_params = json.dumps(
        {
            "skill_paths": [str(first_skill), str(second_skill)],
            "merged_skill_name": "csv_quality_pipeline",
        }
    )

    catalog = asyncio.run(server.handle_commands_catalog({}))
    capabilities = asyncio.run(server.handle_natural_capabilities({}))
    preview = asyncio.run(
        server.handle_natural_invoke(
            {
                "text": (
                    "run backend skill.merge_preview "
                    f"params={merge_params}"
                )
            }
        )
    )
    merged = asyncio.run(
        server.handle_voice_invoke(
            {
                "text": (
                    "run backend skill.merge "
                    f"params={merge_params}"
                )
            }
        )
    )

    catalog_methods = {
        command["name"]
        for category in catalog["categories"]
        for command in category["commands"]
    }
    natural_methods = {
        item.get("method") or item.get("command")
        for item in capabilities["commands"]
    }

    assert {"skill.merge_preview", "skill.merge"}.issubset(catalog_methods)
    assert {"skill.merge_preview", "skill.merge"}.issubset(natural_methods)
    assert preview["ok"] is True
    assert preview["result"]["status"] == "preview"
    assert preview["result"]["source_count"] == 2
    assert merged["source"] == "voice"
    assert merged["ok"] is True
    assert merged["result"]["status"] == "merged"
    assert Path(merged["result"]["proposal_dir"], "skill.json").exists()


def test_natural_language_extracts_common_backend_parameters_without_json(tmp_path):
    from tui_gateway.entry import JSONRPCServer

    server = JSONRPCServer(runtime_root=tmp_path, writer=lambda _: None)

    platform = asyncio.run(
        server.handle_natural_invoke(
            {"text": "send platform message to missing text hello from natural language"}
        )
    )
    acceptance = asyncio.run(
        server.handle_natural_invoke({"text": "run final acceptance with 1 stress cycle"})
    )

    assert platform["matched"] is True
    assert platform["method"] == "runtime.platform_message"
    assert platform["params"] == {
        "platform": "missing",
        "payload": {"text": "hello from natural language"},
    }
    assert platform["ok"] is False
    assert platform["error"]["code"] == "BACKEND_ERROR"
    assert acceptance["matched"] is True
    assert acceptance["method"] == "runtime.final_acceptance"
    assert acceptance["params"] == {"stress_cycles": 1}
    assert acceptance["result"]["report"]["summary"]["status"] in {
        "ready_for_real_integration",
        "attention_required",
    }


def test_natural_tool_missing_parameter_requests_clarification_and_executes_answer(tmp_path):
    from tui_gateway.entry import JSONRPCServer

    writes = []
    server = JSONRPCServer(runtime_root=tmp_path, writer=writes.append)

    queued = asyncio.run(
        server.handle_natural_invoke(
            {
                "text": "run backend shell.exec",
                "auth_scopes": ["shell:execute"],
            }
        )
    )
    answered = asyncio.run(
        server.handle_clarify_respond(
            {
                "request_id": queued["clarification_id"],
                "answer": "python --version",
            }
        )
    )
    events = [
        item["params"]
        for item in writes
        if item.get("method") == "event"
    ]
    clarify_events = [
        event["payload"]
        for event in events
        if event["type"] == "clarify.request"
    ]

    assert queued["ok"] is False
    assert queued["requires_clarification"] is True
    assert queued["missing"] == "command"
    assert clarify_events[0]["field"] == "command"
    assert clarify_events[0]["method"] == "shell.exec"
    assert answered["ok"] is True
    assert answered["executed"]["ok"] is False
    assert answered["executed"]["requires_approval"] is True
    assert answered["executed"]["request"]["payload"]["params"] == {
        "command": "python --version"
    }


def test_natural_tool_supports_multi_turn_parameter_clarification(tmp_path):
    from tui_gateway.entry import JSONRPCServer

    writes = []
    server = JSONRPCServer(runtime_root=tmp_path, writer=writes.append)

    first = asyncio.run(
        server.handle_natural_invoke({"text": "run backend runtime.platform_message"})
    )
    second = asyncio.run(
        server.handle_clarify_respond(
            {"request_id": first["clarification_id"], "answer": "missing"}
        )
    )
    third = asyncio.run(
        server.handle_clarify_respond(
            {
                "request_id": second["clarification"]["clarification_id"],
                "answer": "hello from clarification",
            }
        )
    )
    events = [
        item["params"]
        for item in writes
        if item.get("method") == "event"
    ]
    clarify_fields = [
        event["payload"]["field"]
        for event in events
        if event["type"] == "clarify.request"
    ]

    assert first["requires_clarification"] is True
    assert first["missing"] == "platform"
    assert second["ok"] is True
    assert second["requires_clarification"] is True
    assert second["clarification"]["missing"] == "payload"
    assert third["ok"] is True
    assert third["executed"]["ok"] is False
    assert third["executed"]["error"]["code"] == "BACKEND_ERROR"
    assert clarify_fields[:2] == ["platform", "payload"]


def test_natural_agent_executor_validates_auth_risk_and_retries(tmp_path):
    from tui_gateway.entry import JSONRPCServer

    writes = []
    server = JSONRPCServer(runtime_root=tmp_path, writer=writes.append)

    capabilities = asyncio.run(server.handle_natural_capabilities({}))
    missing_params = asyncio.run(
        server.handle_natural_invoke({"text": "run backend runtime.platform_message"})
    )
    denied = asyncio.run(
        server.handle_natural_invoke(
            {
                "text": (
                    "run backend runtime.final_acceptance "
                    "params={\"stress_cycles\":1}"
                ),
                "auth_scopes": ["runtime:read"],
            }
        )
    )
    approval = asyncio.run(
        server.handle_natural_invoke(
            {
                "text": (
                    "run backend organization.rollback "
                    "params={\"role_name\":\"Missing\",\"requested_by\":\"test\",\"reason\":\"test\"}"
                ),
                "auth_scopes": ["organization:write"],
            }
        )
    )
    retryable = asyncio.run(
        server.handle_natural_invoke(
            {
                "text": (
                    "run backend runtime.platform_message "
                    "params={\"platform\":\"missing\",\"payload\":{\"text\":\"hello\"}}"
                )
            }
        )
    )

    methods = {
        item.get("method"): item
        for item in capabilities["commands"]
        if item.get("method")
    }
    events = [
        item["params"]["type"]
        for item in writes
        if item.get("method") == "event"
    ]

    assert methods["runtime.final_acceptance"]["input_schema"]["type"] == "object"
    assert methods["runtime.final_acceptance"]["auth_scope"] == "runtime:write"
    assert methods["runtime.final_acceptance"]["retry"]["max_attempts"] >= 1
    assert missing_params["ok"] is False
    assert missing_params["requires_clarification"] is True
    assert missing_params["missing"] == "platform"
    assert denied["ok"] is False
    assert denied["error"]["code"] == "PERMISSION_DENIED"
    assert approval["ok"] is False
    assert approval["requires_approval"] is True
    assert approval["approval_id"].startswith("approval_")
    assert "approval.queue" in events
    assert "clarify.request" in events
    assert retryable["ok"] is False
    assert retryable["error"]["code"] == "BACKEND_ERROR"
    assert retryable["attempts"] == methods["runtime.platform_message"]["retry"]["max_attempts"]


def test_natural_agent_tool_emits_tool_activity_events(tmp_path):
    from tui_gateway.entry import JSONRPCServer

    writes = []
    server = JSONRPCServer(runtime_root=tmp_path, writer=writes.append)

    result = asyncio.run(
        server.handle_natural_invoke({"text": "run backend runtime.adapters"})
    )
    events = [
        item["params"]
        for item in writes
        if item.get("method") == "event"
    ]
    event_types = [event["type"] for event in events]
    started = [
        event["payload"]
        for event in events
        if event["type"] == "tool.start"
    ]
    completed = [
        event["payload"]
        for event in events
        if event["type"] == "tool.complete"
    ]

    assert result["ok"] is True
    assert "tool.start" in event_types
    assert "tool.complete" in event_types
    assert started[0]["name"] == "runtime.adapters"
    assert completed[0]["name"] == "runtime.adapters"
    assert completed[0]["summary"] == "completed"


def test_agent_parallel_runs_backend_tools_concurrently_and_preserves_order(tmp_path):
    from tui_gateway.entry import JSONRPCServer

    writes = []
    server = JSONRPCServer(runtime_root=tmp_path, writer=writes.append)

    result = asyncio.run(
        server.handle_natural_invoke(
            {
                "text": (
                    "parallel agents "
                    "tasks=[{\"method\":\"runtime.adapters\"},"
                    "{\"method\":\"governance.requests\"},"
                    "{\"method\":\"runtime.status_snapshot\"}]"
                )
            }
        )
    )
    events = [
        item["params"]
        for item in writes
        if item.get("method") == "event"
    ]
    event_types = [event["type"] for event in events]
    step_payloads = [
        event["payload"]
        for event in events
        if event["type"] == "step.update"
    ]
    tool_starts = [
        event["payload"]["name"]
        for event in events
        if event["type"] == "tool.start"
    ]

    assert result["matched"] is True
    assert result["method"] == "agent.parallel"
    assert result["ok"] is True
    assert result["total"] == 3
    assert result["completed"] == 3
    assert result["failed"] == 0
    assert [item["method"] for item in result["results"]] == [
        "runtime.adapters",
        "governance.requests",
        "runtime.status_snapshot",
    ]
    assert "agent.parallel.start" in event_types
    assert "agent.parallel.complete" in event_types
    assert any(step["status"] == "running" for step in step_payloads)
    assert any(step["status"] == "complete" for step in step_payloads)
    assert tool_starts[0] == "agent.parallel"
    assert [name for name in tool_starts if name != "agent.parallel"][:3] == [
        "runtime.adapters",
        "governance.requests",
        "runtime.status_snapshot",
    ]


def test_agent_parallel_returns_failed_items_without_stopping_other_tasks(tmp_path):
    from tui_gateway.entry import JSONRPCServer

    writes = []
    server = JSONRPCServer(runtime_root=tmp_path, writer=writes.append)

    result = asyncio.run(
        server.handle_agent_parallel(
            {
                "tasks": [
                    {"method": "runtime.adapters"},
                    {
                        "method": "runtime.platform_message",
                        "params": {
                            "platform": "missing",
                            "payload": {"text": "hello"},
                        },
                    },
                    {"method": "runtime.status_snapshot"},
                ],
                "max_concurrency": 3,
            }
        )
    )
    completed = [
        item["params"]["payload"]
        for item in writes
        if item.get("method") == "event"
        and item["params"]["type"] == "tool.complete"
    ]

    assert result["ok"] is False
    assert result["total"] == 3
    assert result["completed"] == 2
    assert result["failed"] == 1
    assert result["results"][0]["ok"] is True
    assert result["results"][1]["ok"] is False
    assert result["results"][2]["ok"] is True
    assert result["results"][1]["error"]["code"] == "BACKEND_ERROR"
    assert {item["name"] for item in completed} == {
        "runtime.adapters",
        "runtime.platform_message",
        "runtime.status_snapshot",
    }


def test_tui_exposes_parallel_agent_runtime_events_and_natural_tool():
    app_source = (ROOT / "ui-tui" / "src" / "app.tsx").read_text(encoding="utf-8")
    types_source = (ROOT / "ui-tui" / "src" / "types.ts").read_text(encoding="utf-8")
    panel_source = (
        ROOT / "ui-tui" / "src" / "components" / "runtimeActivityPanel.tsx"
    ).read_text(encoding="utf-8")
    gateway_source = (ROOT / "tui_gateway" / "entry.py").read_text(encoding="utf-8")
    combined = "\n".join([app_source, types_source, panel_source, gateway_source])

    required = [
        "agent.parallel",
        "agent.parallel.start",
        "agent.parallel.complete",
        "parallel_group_id",
        "Parallel Agents",
        "max_concurrency",
        "tasks",
    ]

    assert all(text in combined for text in required)


def test_approved_agent_tool_executes_original_backend_action(tmp_path):
    from tui_gateway.entry import JSONRPCServer

    server = JSONRPCServer(runtime_root=tmp_path, writer=lambda _: None)
    queued = asyncio.run(
        server.handle_natural_invoke(
            {
                "text": (
                    "run backend shell.exec "
                    "params={\"command\":\"python --version\"}"
                ),
                "auth_scopes": ["shell:execute"],
            }
        )
    )

    approved = asyncio.run(
        server.handle_approval_respond(
            {"request_id": queued["approval_id"], "decision": "once"}
        )
    )

    assert queued["requires_approval"] is True
    assert approved["ok"] is True
    assert approved["executed"]["ok"] is True
    assert approved["executed"]["method"] == "shell.exec"
    assert approved["executed"]["result"]["code"] == 0
    assert "Python" in (
        approved["executed"]["result"]["stdout"]
        + approved["executed"]["result"]["stderr"]
    )


def test_approved_agent_tool_emits_tool_events_and_result(tmp_path):
    from tui_gateway.entry import JSONRPCServer

    writes = []
    server = JSONRPCServer(runtime_root=tmp_path, writer=writes.append)
    queued = asyncio.run(
        server.handle_natural_invoke(
            {
                "text": (
                    "run backend shell.exec "
                    "params={\"command\":\"python --version\"}"
                ),
                "auth_scopes": ["shell:execute"],
            }
        )
    )

    approved = asyncio.run(
        server.handle_approval_respond(
            {"request_id": queued["approval_id"], "decision": "once"}
        )
    )
    events = [
        item["params"]
        for item in writes
        if item.get("method") == "event"
    ]
    event_types = [event["type"] for event in events]
    completed = [
        event["payload"]
        for event in events
        if event["type"] == "tool.complete"
    ]

    assert approved["executed"]["ok"] is True
    assert approved["executed"]["method"] == "shell.exec"
    assert "tool.start" in event_types
    assert "tool.complete" in event_types
    assert completed[-1]["name"] == "shell.exec"
    assert completed[-1]["summary"] == "completed"


def test_natural_language_can_approve_latest_agent_tool_request(tmp_path):
    from tui_gateway.entry import JSONRPCServer

    writes = []
    server = JSONRPCServer(runtime_root=tmp_path, writer=writes.append)
    queued = asyncio.run(
        server.handle_natural_invoke(
            {
                "text": (
                    "run backend shell.exec "
                    "params={\"command\":\"python --version\"}"
                ),
                "auth_scopes": ["shell:execute"],
            }
        )
    )

    approved = asyncio.run(
        server.handle_natural_invoke({"text": "approve latest request"})
    )
    events = [
        item["params"]["type"]
        for item in writes
        if item.get("method") == "event"
    ]

    assert queued["requires_approval"] is True
    assert approved["matched"] is True
    assert approved["method"] == "approval.respond"
    assert approved["params"]["request_id"] == queued["approval_id"]
    assert approved["result"]["executed"]["ok"] is True
    assert approved["result"]["executed"]["method"] == "shell.exec"
    assert "tool.start" in events
    assert "tool.complete" in events


def test_voice_invoke_can_call_backend_alias_and_approve_latest_request(tmp_path):
    from tui_gateway.entry import JSONRPCServer

    server = JSONRPCServer(runtime_root=tmp_path, writer=lambda _: None)

    platform = asyncio.run(
        server.handle_voice_invoke({"text": "给飞书发消息：部署完成"})
    )
    queued = asyncio.run(
        server.handle_voice_invoke(
            {
                "text": (
                    "run backend shell.exec "
                    "params={\"command\":\"python --version\"}"
                ),
                "auth_scopes": ["shell:execute"],
            }
        )
    )
    approved = asyncio.run(
        server.handle_voice_invoke({"text": "approve latest request"})
    )

    assert platform["source"] == "voice"
    assert platform["method"] == "runtime.platform_message"
    assert queued["source"] == "voice"
    assert queued["requires_approval"] is True
    assert approved["source"] == "voice"
    assert approved["method"] == "approval.respond"
    assert approved["result"]["executed"]["ok"] is True
    assert approved["result"]["executed"]["method"] == "shell.exec"


def test_write_backend_tools_have_explicit_schema_auth_and_risk(tmp_path):
    from tui_gateway.entry import JSONRPCServer

    server = JSONRPCServer(runtime_root=tmp_path, writer=lambda _: None)
    capabilities = asyncio.run(server.handle_natural_capabilities({}))
    methods = {
        item.get("method"): item
        for item in capabilities["commands"]
        if item.get("method")
    }

    expected = {
        "skill.request_publish": ("skill:write", "high", ["proposal_dir"]),
        "skill.publish_approved": ("skill:write", "high", ["request_id"]),
        "skill.merge": ("skill:write", "medium", ["skill_paths", "merged_skill_name"]),
        "algorithm.request_research": ("algorithm:write", "high", ["proposal_path"]),
        "algorithm.run_experiment": (
            "algorithm:write",
            "high",
            ["request_id", "dataset_path", "thresholds"],
        ),
        "algorithm.request_promotion": (
            "algorithm:write",
            "critical",
            ["report_path", "blueprint_path"],
        ),
        "algorithm.apply_promotion": ("algorithm:write", "critical", ["request_id"]),
        "organization.request_change": (
            "organization:write",
            "critical",
            ["proposal_path"],
        ),
        "organization.apply_change": (
            "organization:write",
            "critical",
            ["request_id"],
        ),
        "organization.rollback": ("organization:write", "critical", ["role_name"]),
    }

    for method, (scope, risk, required) in expected.items():
        policy = methods[method]
        assert policy["auth_scope"] == scope
        assert policy["risk_level"] == risk
        assert policy["input_schema"]["required"] == required


def test_tui_frontend_invokes_natural_backend_methods_before_prompt_submit():
    app_source = (ROOT / "ui-tui" / "src" / "app.tsx").read_text(encoding="utf-8")

    required = [
        "natural.invoke",
        "natural.result",
        "natural.method",
        "formatNaturalResult",
    ]

    assert all(text in app_source for text in required)


def test_tui_surfaces_approved_agent_tool_execution_result():
    app_source = (ROOT / "ui-tui" / "src" / "app.tsx").read_text(encoding="utf-8")

    required = [
        "approval.respond",
        "response.executed",
        "formatNaturalResult({",
        "method: response.executed.method",
        "result: response.executed.result",
    ]

    assert all(text in app_source for text in required)


def test_tui_surfaces_clarification_execution_result():
    app_source = (ROOT / "ui-tui" / "src" / "app.tsx").read_text(encoding="utf-8")

    required = [
        "clarify.respond",
        "response.executed",
        "method: response.executed.method",
        "result: response.executed.result",
    ]

    assert all(text in app_source for text in required)


def test_tui_gateway_streams_reasoning_risk_review_and_context_compaction(tmp_path):
    from tui_gateway.entry import JSONRPCServer

    writes = []
    server = JSONRPCServer(runtime_root=tmp_path, writer=writes.append, stream_delay=0)
    server.history = [
        {"role": "user", "text": f"history {index} " + ("x" * 24000)}
        for index in range(24)
    ]

    async def run_prompt():
        result = await server.handle_prompt_submit(
            {"text": "run shell command and modify organization approval"}
        )
        await server.wait_for_background()
        return result

    result = asyncio.run(run_prompt())
    events = [
        item["params"]
        for item in writes
        if item.get("method") == "event"
    ]
    event_types = [item["type"] for item in events]

    assert result == {"status": "streaming"}
    assert "reasoning.delta" in event_types
    assert "runtime.risk" in event_types
    assert "approval.queue" in event_types
    assert "context.compaction" in event_types
    assert "session.info" in event_types
    assert any(
        item["payload"].get("level") in {"medium", "high", "critical"}
        for item in events
        if item["type"] == "runtime.risk"
    )
    assert len(server.history) <= 20


def test_tui_gateway_manual_compact_emits_context_event(tmp_path):
    from tui_gateway.entry import JSONRPCServer

    writes = []
    server = JSONRPCServer(runtime_root=tmp_path, writer=writes.append)
    server.history = [
        {"role": "user", "text": f"message {index}"}
        for index in range(25)
    ]

    compacted = asyncio.run(server.handle_session_compress({}))
    events = [
        item["params"]
        for item in writes
        if item.get("method") == "event"
    ]

    assert compacted["removed"] == 5
    assert len(compacted["messages"]) == 20
    assert any(item["type"] == "context.compaction" for item in events)


def test_mcp_stdio_server_can_be_registered_listed_and_called(tmp_path):
    from tui_gateway.entry import JSONRPCServer
    import sys

    server_script = tmp_path / "mcp_echo_server.py"
    server_script.write_text(
        """
import json
import sys

for line in sys.stdin:
    if not line.strip():
        continue
    request = json.loads(line)
    method = request.get("method")
    request_id = request.get("id")
    if method == "initialize":
        response = {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "echo", "version": "1.0.0"},
            },
        }
    elif method == "notifications/initialized":
        continue
    elif method == "tools/list":
        response = {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "tools": [
                    {
                        "name": "echo",
                        "description": "Echo text",
                        "inputSchema": {
                            "type": "object",
                            "properties": {"text": {"type": "string"}},
                        },
                    }
                ]
            },
        }
    elif method == "tools/call":
        text = request.get("params", {}).get("arguments", {}).get("text", "")
        response = {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "content": [{"type": "text", "text": f"echo:{text}"}],
                "isError": False,
            },
        }
    else:
        response = {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": -32601, "message": "unknown method"},
        }
    sys.stdout.write(json.dumps(response) + "\\n")
    sys.stdout.flush()
""".strip(),
        encoding="utf-8",
    )
    server = JSONRPCServer(runtime_root=tmp_path / "runtime", writer=lambda _: None)

    added = asyncio.run(
        server.handle_mcp_server_add(
            {
                "name": "echo",
                "command": sys.executable,
                "args": [str(server_script)],
            }
        )
    )
    listed = asyncio.run(server.handle_mcp_servers({}))
    tools = asyncio.run(server.handle_mcp_tools({"server": "echo"}))
    called = asyncio.run(
        server.handle_mcp_call(
            {
                "server": "echo",
                "tool": "echo",
                "arguments": {"text": "hello"},
            }
        )
    )
    catalog = asyncio.run(server.handle_commands_catalog({}))
    toolsets = asyncio.run(server.handle_toolsets_list({}))

    catalog_methods = {
        command["name"]
        for category in catalog["categories"]
        for command in category["commands"]
    }

    assert added["ok"] is True
    assert listed["servers"][0]["name"] == "echo"
    assert tools["tools"][0]["name"] == "echo"
    assert called["ok"] is True
    assert called["result"]["content"][0]["text"] == "echo:hello"
    assert "mcp.call" in catalog_methods
    assert "mcp" in toolsets["toolsets"]


def test_cron_scheduler_persists_and_runs_due_backend_job(tmp_path):
    from tui_gateway.entry import JSONRPCServer

    server = JSONRPCServer(runtime_root=tmp_path, writer=lambda _: None)

    created = asyncio.run(
        server.handle_cron_create(
            {
                "name": "status delivery",
                "method": "runtime.status_snapshot",
                "params": {},
                "interval_seconds": 60,
                "run_at": "2000-01-01T00:00:00+00:00",
            }
        )
    )
    due = asyncio.run(server.handle_cron_run_due({"now": "2000-01-01T00:00:01+00:00"}))
    reloaded = JSONRPCServer(runtime_root=tmp_path, writer=lambda _: None)
    listed = asyncio.run(reloaded.handle_cron_list({}))

    assert created["ok"] is True
    assert created["job"]["id"].startswith("cron_")
    assert due["executed"] == 1
    assert due["results"][0]["ok"] is True
    assert "services" in due["results"][0]["result"]
    assert listed["jobs"][0]["name"] == "status delivery"
    assert listed["jobs"][0]["run_count"] == 1


def test_context_files_are_attached_and_injected_into_prompt(tmp_path):
    from tui_gateway.entry import JSONRPCServer

    writes = []
    context_file = tmp_path / "notes.md"
    context_file.write_text("project rule: always normalize CSV headers", encoding="utf-8")
    server = JSONRPCServer(runtime_root=tmp_path, writer=writes.append, stream_delay=0)
    captured = {}

    def fake_interaction(text):
        captured["text"] = text
        return {"response_text": "context received", "response": {"status": "test"}}

    server.runtime.handle_interaction = fake_interaction

    async def run_prompt():
        result = await server.handle_prompt_submit(
            {"text": f"Use this context @{context_file} and answer"}
        )
        await server.wait_for_background()
        return result

    result = asyncio.run(run_prompt())
    files = asyncio.run(server.handle_context_files({}))
    events = [
        item["params"]
        for item in writes
        if item.get("method") == "event"
    ]

    assert result == {"status": "streaming"}
    assert "project rule: always normalize CSV headers" in captured["text"]
    assert "[Project Context Files]" in captured["text"]
    assert files["files"][0]["path"] == str(context_file.resolve())
    assert any(item["type"] == "context.files" for item in events)


def test_tui_exposes_mcp_cron_and_context_backend_tools():
    app_source = (ROOT / "ui-tui" / "src" / "app.tsx").read_text(encoding="utf-8")
    empty_source = (ROOT / "ui-tui" / "src" / "components" / "emptyState.tsx").read_text(encoding="utf-8")
    gateway_source = (ROOT / "tui_gateway" / "entry.py").read_text(encoding="utf-8")
    combined = "\n".join([app_source, empty_source, gateway_source])

    required = [
        "mcp.server.add",
        "mcp.tools",
        "mcp.call",
        "cron.create",
        "cron.run_due",
        "context.attach",
        "context.files",
    ]

    assert all(text in combined for text in required)
    assert "@路径" not in empty_source
