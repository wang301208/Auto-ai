from pathlib import Path
import asyncio
import json

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
        "LOCAL AGENT",
        "Autonomous Runtime Terminal",
        "borderStyle=\"round\"",
        "flexDirection=\"row\"",
        "asciiArt",
        "Command Center",
        "Available Tools",
        "Core Commands",
        "System",
        "stdin/stdout JSON-RPC",
        "Python gateway subprocess",
        "/status",
        "/health",
        "/preflight",
        "/host",
        "/tools",
        "/approvals",
        "!cmd",
        "@path",
        "/help for commands",
    ]

    assert "EmptyState" in app_source
    assert all(text in source for text in required_copy)


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
        "openai",
        "openrouter",
        "anthropic",
        "deepseek",
        "nous",
        "openai_compatible",
        "custom",
        "LOCAL_AGENT_CONFIG_PATH",
    ]

    assert all(text in quickstart_text for text in required_quickstart)
    assert all(text in config_text for text in required_config)
    assert "Zhushou" not in script_text
    assert "Hermes-style" not in script_text


def test_tui_gateway_supports_personality_and_save_commands(tmp_path):
    from tui_gateway.entry import JSONRPCServer, SLASH_COMMANDS

    server = JSONRPCServer(runtime_root=tmp_path, writer=lambda _: None)
    server.history = [{"role": "user", "text": "hello"}]

    personality = asyncio.run(server.handle_slash_exec({"text": "/personality concise operator"}))
    save = asyncio.run(server.handle_slash_exec({"text": "/save"}))
    help_output = asyncio.run(server.handle_slash_exec({"text": "/help"}))
    saved_path = tmp_path / "sessions" / f"{server.session_id}.json"

    assert {"/personality", "/save"}.issubset({item["text"] for item in SLASH_COMMANDS})
    assert personality["output"] == "Personality set: concise operator"
    assert server.personality == "concise operator"
    assert save["output"] == f"session saved: {saved_path}"
    assert saved_path.exists()
    assert "/personality" in help_output["output"]
    assert "/save" in help_output["output"]


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
        "Execution Steps",
        "Approvals",
        "Runtime Signals",
        "Context",
        "Risk",
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
        "approvalTimeoutRemaining",
        "void answerOverlay('once')",
        "Auto-approves once in",
        "timeout_remaining?: number",
    ]

    assert all(text in combined for text in required)
    assert "void answerOverlay('deny')" in app_source


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


def test_tui_gateway_supports_terminal_redirection_for_slash_shell_and_prompt(tmp_path):
    from tui_gateway.entry import JSONRPCServer

    writes = []
    server = JSONRPCServer(runtime_root=tmp_path, writer=writes.append, stream_delay=0)

    slash = asyncio.run(
        server.handle_slash_exec({"text": "/status > terminal/status.txt"})
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

    assert slash["redirect"]["mode"] == "write"
    assert shell["redirect"]["mode"] == "append"
    assert prompt == {"status": "streaming"}
    assert status_path.exists()
    assert "Session:" in status_path.read_text(encoding="utf-8")
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
    slash = asyncio.run(server.handle_complete_slash({"text": "/sta"}))
    path = asyncio.run(server.handle_complete_path({"text": "@ui-tui/src/app"}))

    assert created["session_id"] == server.session_id
    assert created["info"]["cwd"] == str(ROOT)
    assert any(item["text"] == "/status" for item in slash["items"])
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
    approvals = asyncio.run(server.handle_slash_exec({"text": "/approvals"}))
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

    assert approval.request_id in approvals["output"]
    assert approval_response == {"ok": True}
    assert clarify["request_id"].startswith("clarify_")
    assert secret["request_id"].startswith("secret_")
    assert "clarify.request" in event_types
    assert "secret.request" in event_types
    assert "/status" in help_output["output"]


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
    slash = asyncio.run(server.handle_slash_exec({"text": "/health"}))
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
    assert "runtime" in slash["output"]
    assert {
        "/health",
        "/preflight",
        "/write-preflight",
        "/host",
        "/messaging",
        "/blueprints",
        "/skills",
        "/algorithms",
        "/audits",
        "/avatar",
        "/events",
        "/ui",
        "/smoke",
        "/stress",
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
    tools = asyncio.run(server.handle_slash_exec({"text": "/tools"}))
    command_by_name = {
        command["name"]: command
        for category in catalog["categories"]
        for command in category["commands"]
    }

    shell = command_by_name["shell.exec"]
    acceptance = command_by_name["runtime.final_acceptance"]
    output = tools["output"]

    assert shell["auth_scope"] == "shell:execute"
    assert shell["risk_level"] == "high"
    assert shell["requires_approval"] is True
    assert shell["input_schema"]["required"] == ["command"]
    assert acceptance["auth_scope"] == "runtime:write"
    assert acceptance["input_schema"]["properties"]["stress_cycles"]["maximum"] == 10
    assert "Natural backend tools" in output
    assert "shell.exec | auth=shell:execute | risk=high | approval=yes" in output
    assert "schema required: command" in output
    assert 'run backend shell.exec params={"command":"python --version"}' in output
    assert "approve latest request" in output
    assert "Missing required parameters trigger clarification prompts." in output
    assert "Voice input uses the same natural-language tool gateway." in output


def test_gateway_routes_text_and_voice_natural_language_to_all_commands(tmp_path):
    from tui_gateway.entry import JSONRPCServer, SLASH_COMMANDS

    server = JSONRPCServer(runtime_root=tmp_path, writer=lambda _: None)

    capabilities = asyncio.run(server.handle_natural_capabilities({}))
    text_status = asyncio.run(server.handle_natural_invoke({"text": "帮我查看运行状态"}))
    text_shell = asyncio.run(
        server.handle_natural_invoke({"text": "运行命令 python --version"})
    )
    voice_health = asyncio.run(
        server.handle_voice_invoke({"text": "请用语音查看健康报告"})
    )
    voice_record = asyncio.run(
        server.handle_voice_record({"text": "语音查看审批列表"})
    )

    slash_commands = {item["text"] for item in SLASH_COMMANDS}
    supported_commands = {item["command"] for item in capabilities["commands"]}

    assert slash_commands.issubset(supported_commands)
    assert text_status["matched"] is True
    assert text_status["command"] == "/status"
    assert "Session:" in text_status["result"]["output"]
    assert text_shell["matched"] is True
    assert text_shell["method"] == "shell.exec"
    assert text_shell["result"]["code"] == 0
    assert "Python" in (text_shell["result"]["stdout"] + text_shell["result"]["stderr"])
    assert voice_health["source"] == "voice"
    assert voice_health["matched"] is True
    assert voice_health["command"] == "/health"
    assert "runtime" in voice_health["result"]["output"]
    assert voice_record["source"] == "voice"
    assert voice_record["matched"] is True
    assert voice_record["command"] == "/approvals"


def test_tui_frontend_resolves_plain_text_commands_before_prompt_submit():
    app_source = (ROOT / "ui-tui" / "src" / "app.tsx").read_text(encoding="utf-8")
    gateway_source = (ROOT / "tui_gateway" / "entry.py").read_text(encoding="utf-8")

    required_app = [
        "natural.resolve",
        "natural.matched",
        "natural.command",
        "await handleSlash(natural.command)",
    ]
    required_gateway = [
        "handle_natural_resolve",
        "handle_natural_invoke",
        "handle_voice_invoke",
        "handle_natural_capabilities",
        "NATURAL_COMMAND_ALIASES",
    ]

    assert all(text in app_source for text in required_app)
    assert all(text in gateway_source for text in required_gateway)


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
    adapters = asyncio.run(
        server.handle_voice_invoke({"text": "run backend runtime.adapters"})
    )
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

    assert catalog_methods.issubset(capability_methods)
    assert acceptance["matched"] is True
    assert acceptance["method"] == "runtime.final_acceptance"
    assert acceptance["result"]["report"]["summary"]["status"] in {
        "ready_for_real_integration",
        "attention_required",
    }
    assert adapters["matched"] is True
    assert adapters["method"] == "runtime.adapters"
    assert "remote_llm" in adapters["result"]["adapters"]
    assert governance["matched"] is True
    assert governance["method"] == "governance.requests"
    assert isinstance(governance["result"]["requests"], list)


def test_plain_natural_language_invokes_backend_capability_aliases(tmp_path):
    from tui_gateway.entry import JSONRPCServer

    server = JSONRPCServer(runtime_root=tmp_path, writer=lambda _: None)

    adapters = asyncio.run(
        server.handle_voice_invoke({"text": "show adapter health"})
    )
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

    assert adapters["matched"] is True
    assert adapters["source"] == "voice"
    assert adapters["method"] == "runtime.adapters"
    assert "remote_llm" in adapters["result"]["adapters"]
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
    status = asyncio.run(server.handle_natural_invoke({"text": "run backend runtime.status_snapshot"}))
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
        "runtime.status_snapshot",
        "runtime.start",
        "runtime.stop",
    }.issubset(natural_methods)
    assert status["matched"] is True
    assert status["method"] == "runtime.status_snapshot"
    assert "services" in status["result"]
    assert stopped["matched"] is True
    assert stopped["ok"] is True
    assert stopped["result"]["running"] is False
    assert started["matched"] is True
    assert started["source"] == "voice"
    assert started["ok"] is True
    assert started["result"]["running"] is True


def test_experience_learning_self_model_and_skill_drafting_are_natural_language_tools(tmp_path):
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
        server.handle_natural_invoke(
            {
                "text": (
                    "run backend self_model.update "
                    "params={\"observation\":\"I improve by reusing experience\","
                    "\"capability\":\"experience_learning\","
                    "\"preference\":\"terminal_first\"}"
                )
            }
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

    expected = {
        "experience.record",
        "experience.search",
        "self_model.read",
        "self_model.update",
        "skill.draft_from_experience",
    }
    assert expected.issubset(catalog_methods)
    assert expected.issubset(natural_methods)
    assert recorded["matched"] is True
    assert recorded["method"] == "experience.record"
    assert recorded["ok"] is True
    assert recorded["result"]["text"] == "Learned CSV cleanup from prior work"
    assert searched["source"] == "voice"
    assert searched["ok"] is True
    assert searched["result"]["matches"][0]["id"] == recorded["result"]["id"]
    assert updated["ok"] is True
    assert "experience_learning" in updated["result"]["capabilities"]
    assert read_model["result"] == updated["result"]
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


def test_memory_planning_user_model_and_skill_evolution_are_natural_tools(tmp_path):
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
        server.handle_natural_invoke(
            {
                "text": (
                    "run backend memory.periodic_tick "
                    "params={\"task\":\"Plan CSV cleanup improvement\","
                    "\"cadence\":\"daily\"}"
                )
            }
        )
    )
    user_model = asyncio.run(
        server.handle_natural_invoke(
            {
                "text": (
                    "run backend user_model.update "
                    "params={\"user_id\":\"operator\","
                    "\"observation\":\"User wants concise execution with architecture tradeoffs\"}"
                )
            }
        )
    )
    draft = asyncio.run(
        server.handle_natural_invoke(
            {
                "text": (
                    "run backend skill.autonomous_from_task "
                    "params={\"task_text\":\"Complex CSV cleanup with header normalization\","
                    "\"skill_name\":\"csv_cleanup_auto\"}"
                )
            }
        )
    )
    improved = asyncio.run(
        server.handle_natural_invoke(
            {
                "text": (
                    "run backend skill.improve_from_usage "
                    "params={\"skill_name\":\"csv_cleanup_auto\","
                    "\"feedback\":\"Used once; include validation checklist\"}"
                )
            }
        )
    )
    capabilities = asyncio.run(server.handle_natural_capabilities({}))

    natural_methods = {
        item.get("method") or item.get("command")
        for item in capabilities["commands"]
    }

    assert {
        "conversation.record",
        "memory.periodic_tick",
        "user_model.update",
        "user_model.query",
        "skill.autonomous_from_task",
        "skill.improve_from_usage",
    }.issubset(natural_methods)
    assert record["ok"] is True
    assert record["method"] == "conversation.record"
    assert search["source"] == "voice"
    assert search["result"]["engine"] == "sqlite_fts5"
    assert search["result"]["summary"]
    assert tick["result"]["status"] == "recorded"
    assert user_model["result"]["model"]["synthesis"]
    assert Path(draft["result"]["proposal_dir"], "SKILL.md").exists()
    assert improved["result"]["version"] == "0.1.1"


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

    adapters = asyncio.run(
        server.handle_voice_invoke({"text": "show adapter health"})
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

    assert adapters["source"] == "voice"
    assert adapters["method"] == "runtime.adapters"
    assert "remote_llm" in adapters["result"]["adapters"]
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
        "@path attaches project context",
    ]

    assert all(text in combined for text in required)
