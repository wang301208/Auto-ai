import json
import os
import yaml
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_remote_llm_adapter_is_enabled_by_default_and_requires_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    from dual_ring_ai.adapters.remote_llm import RemoteLLMAdapter

    adapter = RemoteLLMAdapter()

    assert adapter.probe()["status"] == "unconfigured"
    result = adapter.generate_response("hello", {})

    assert result["provider"] == "remote_openai_compatible"
    assert result["status"] == "unconfigured"
    assert "OPENAI_API_KEY" in result["reason"]


def test_remote_llm_adapter_dry_run_masks_secret_and_shapes_request(monkeypatch):
    monkeypatch.setenv("REMOTE_LLM_API_KEY", "secret-value")

    from dual_ring_ai.adapters.remote_llm import RemoteLLMAdapter

    adapter = RemoteLLMAdapter(
        enabled=True,
        dry_run=True,
        api_key_env="REMOTE_LLM_API_KEY",
        base_url="https://llm.example/v1",
        model="model-x",
    )
    result = adapter.generate_response(
        "Plan next step",
        {"services": {"governance": "ready"}},
    )

    assert result["status"] == "dry_run"
    assert result["provider"] == "remote_openai_compatible"
    assert result["request"]["method"] == "POST"
    assert result["request"]["url"] == "https://llm.example/v1/chat/completions"
    assert result["request"]["headers"]["Authorization"] == "Bearer ***"
    assert result["request"]["json"]["model"] == "model-x"
    assert result["request"]["json"]["messages"][-1]["content"] == "Plan next step"
    assert "secret-value" not in json.dumps(result)


def test_remote_llm_system_prompt_requires_truthful_capability_boundaries(monkeypatch):
    monkeypatch.setenv("REMOTE_LLM_API_KEY", "secret-value")

    from dual_ring_ai.adapters.remote_llm import RemoteLLMAdapter

    adapter = RemoteLLMAdapter(
        enabled=True,
        dry_run=True,
        api_key_env="REMOTE_LLM_API_KEY",
        base_url="https://llm.example/v1",
        model="model-x",
    )
    result = adapter.generate_response(
        "控制电脑并安装软件",
        {
            "capabilities": {
                "shell": True,
                "computer_control": False,
                "software_management": False,
            }
        },
    )
    system_prompt = result["request"]["json"]["messages"][0]["content"]

    assert "Do not claim abilities that are not exposed in backend context" in system_prompt
    assert "Do not say the system can perform advanced operations" in system_prompt
    assert "computer_control" in system_prompt


def test_remote_llm_adapter_refuses_live_request_without_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    from dual_ring_ai.adapters.remote_llm import RemoteLLMAdapter

    adapter = RemoteLLMAdapter(enabled=True, dry_run=False)
    result = adapter.generate_response("hello", {})

    assert result["status"] == "unconfigured"
    assert "OPENAI_API_KEY" in result["reason"]
    assert "request" not in result


def test_local_runtime_wires_remote_llm_health_and_interaction_dry_run(tmp_path):
    from dual_ring_ai.runtime.local_runtime import LocalRuntime, LocalRuntimeConfig

    runtime = LocalRuntime(
        LocalRuntimeConfig(
            root_path=tmp_path,
            adapters={
                "remote_llm": {
                    "enabled": True,
                    "dry_run": True,
                    "api_key": "test-secret",
                    "base_url": "https://llm.example/v1",
                    "model": "model-x",
                }
            },
        )
    )

    health = runtime.adapter_health()
    interaction = runtime.handle_interaction("hello remote model")

    assert health["remote_llm"]["status"] == "dry_run"
    assert health["remote_llm"]["url"] == "https://llm.example/v1/models"
    assert interaction["response"]["provider"] == "remote_openai_compatible"
    assert interaction["response"]["status"] == "dry_run"
    assert interaction["response"]["request"]["json"]["model"] == "model-x"
    assert "test-secret" not in json.dumps(interaction)


def test_local_runtime_uses_local_llm_by_default_without_remote_probe(tmp_path, monkeypatch):
    from dual_ring_ai.runtime.local_runtime import LocalRuntime, LocalRuntimeConfig

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    runtime = LocalRuntime(LocalRuntimeConfig(root_path=tmp_path))

    health = runtime.adapter_health()
    interaction = runtime.handle_interaction("status")

    assert health["remote_llm"]["status"] == "disabled"
    assert interaction["response"]["provider"] == "local_rule_based"
    assert "remote_llm_status" not in interaction["response"]
    assert interaction["response_text"]


def test_local_runtime_falls_back_to_local_llm_when_remote_is_enabled_but_unconfigured(tmp_path, monkeypatch):
    from dual_ring_ai.runtime.local_runtime import LocalRuntime, LocalRuntimeConfig

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    runtime = LocalRuntime(
        LocalRuntimeConfig(
            root_path=tmp_path,
            adapters={"remote_llm": {"enabled": True, "dry_run": False}},
        )
    )

    health = runtime.adapter_health()
    interaction = runtime.handle_interaction("status")

    assert health["remote_llm"]["status"] == "unconfigured"
    assert interaction["response"]["provider"] == "local_rule_based"
    assert interaction["response"]["remote_llm_status"]["status"] == "unconfigured"
    assert interaction["response_text"]


def test_local_runtime_falls_back_to_local_llm_when_remote_is_unavailable(tmp_path):
    from dual_ring_ai.runtime.local_runtime import LocalRuntime, LocalRuntimeConfig

    runtime = LocalRuntime(
        LocalRuntimeConfig(
            root_path=tmp_path,
            adapters={
                "remote_llm": {
                    "enabled": True,
                    "dry_run": False,
                    "api_key": "test-key",
                    "base_url": "http://127.0.0.1:1/v1",
                    "timeout": 0.1,
                }
            },
        )
    )

    health = runtime.adapter_health()
    interaction = runtime.handle_interaction("status")

    assert health["remote_llm"]["status"] == "unavailable"
    assert interaction["response"]["provider"] == "local_rule_based"
    assert interaction["response"]["remote_llm_status"]["status"] == "unavailable"
    assert interaction["response_text"]


def test_tui_gateway_loads_and_persists_remote_model_config(tmp_path, monkeypatch):
    monkeypatch.setenv("REMOTE_LLM_API_KEY", "secret-value")

    from tui_gateway.entry import JSONRPCServer

    config_path = tmp_path / "agent_config.json"
    config_path.write_text(
        json.dumps(
            {
                "root_path": str(tmp_path / "runtime"),
                "adapters": {
                    "remote_llm": {
                        "enabled": True,
                        "dry_run": True,
                        "api_key_env": "REMOTE_LLM_API_KEY",
                        "base_url": "https://llm.example/v1",
                        "model": "model-a",
                    }
                },
                "security_defaults": {
                    "network": True,
                    "shell": True,
                    "filesystem": {"read": ["*"], "write": ["*"]},
                    "environment": {"allow": ["*"], "request": ["REMOTE_LLM_API_KEY"]},
                },
            }
        ),
        encoding="utf-8",
    )

    server = JSONRPCServer(config_path=config_path, writer=lambda _: None)
    options = __import__("asyncio").run(server.handle_model_options({}))
    configured = __import__("asyncio").run(
        server.handle_model_configure(
            {
                "provider": "openai_compatible",
                "base_url": "https://openrouter.ai/api/v1",
                "model": "openrouter/test-model",
                "api_key_env": "OPENROUTER_API_KEY",
                "dry_run": True,
            }
        )
    )
    saved = json.loads(config_path.read_text(encoding="utf-8"))
    updated_options = __import__("asyncio").run(server.handle_model_options({}))

    assert options["provider"] == "custom"
    assert options["model"] == "model-a"
    assert options["providers"][0]["status"] == "dry_run"
    assert configured["ok"] is True
    assert configured["config_path"] == str(config_path)
    assert saved["adapters"]["remote_llm"]["base_url"] == "https://openrouter.ai/api/v1"
    assert saved["adapters"]["remote_llm"]["model"] == "openrouter/test-model"
    assert saved["adapters"]["remote_llm"]["api_key_env"] == "OPENROUTER_API_KEY"
    assert saved["adapters"]["remote_llm"]["dry_run"] is True
    assert updated_options["model"] == "openrouter/test-model"
    assert updated_options["providers"][0]["base_url"] == "https://openrouter.ai/api/v1"


def test_tui_gateway_model_options_only_expose_custom_model_route(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    from tui_gateway.entry import JSONRPCServer

    config_path = tmp_path / "agent_config.json"
    server = JSONRPCServer(config_path=config_path, runtime_root=tmp_path / "runtime", writer=lambda _: None)

    providers = __import__("asyncio").run(server.handle_model_providers({}))
    options = __import__("asyncio").run(server.handle_model_options({}))
    configured = __import__("asyncio").run(
        server.handle_model_configure(
            {
                "provider": "openrouter",
                "base_url": "https://openrouter.ai/api/v1",
                "model": "openai/gpt-4o-mini",
                "api_key_env": "OPENROUTER_API_KEY",
            }
        )
    )
    saved = json.loads(config_path.read_text(encoding="utf-8"))
    updated = __import__("asyncio").run(server.handle_model_options({}))

    assert [item["slug"] for item in providers["providers"]] == ["custom"]
    assert [item["slug"] for item in options["providers"]] == ["custom"]
    assert options["provider"] == "custom"
    assert configured["provider"] == "custom"
    assert saved["model"] == {"provider": "custom", "name": "openai/gpt-4o-mini"}
    assert saved["providers"] == {
        "custom": {
            "base_url": "https://openrouter.ai/api/v1",
            "api_key_env": "OPENROUTER_API_KEY",
        }
    }
    assert updated["provider"] == "custom"
    assert updated["providers"][0]["base_url"] == "https://openrouter.ai/api/v1"


def test_tui_gateway_matches_provider_model_yaml_and_env_config_flow(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    from tui_gateway.entry import JSONRPCServer

    config_path = tmp_path / "config.yaml"
    env_path = tmp_path / ".env"
    env_path.write_text("OPENROUTER_API_KEY=env-secret\n", encoding="utf-8")
    config_path.write_text(
        yaml.safe_dump(
            {
                "root_path": str(tmp_path / "runtime"),
                "model": {
                    "provider": "openrouter",
                    "name": "openai/gpt-4o-mini",
                },
                "providers": {
                    "openrouter": {
                        "base_url": "https://openrouter.ai/api/v1",
                        "api_key_env": "OPENROUTER_API_KEY",
                    }
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    server = JSONRPCServer(config_path=config_path, writer=lambda _: None)
    options = __import__("asyncio").run(server.handle_model_options({}))
    switched = __import__("asyncio").run(
        server.handle_slash_exec({"text": "/model openai:gpt-4o-mini"})
    )
    saved = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    updated = __import__("asyncio").run(server.handle_model_options({}))

    assert options["provider"] == "custom"
    assert options["model"] == "openai/gpt-4o-mini"
    assert options["env_loaded"] is True
    assert options["providers"][0]["slug"] == "custom"
    assert not any(provider["slug"] == "openai" for provider in options["providers"])
    assert not any(provider["slug"] == "anthropic" for provider in options["providers"])
    assert switched["output"] == "模型已配置：custom:gpt-4o-mini"
    assert saved["model"] == {"provider": "custom", "name": "gpt-4o-mini"}
    assert saved["providers"]["custom"]["base_url"] == "https://api.openai.com/v1"
    assert saved["providers"]["custom"]["api_key_env"] == "OPENAI_API_KEY"
    assert updated["provider"] == "custom"
    assert updated["model"] == "gpt-4o-mini"


def test_tui_gateway_model_setup_wizard_records_api_key_and_oauth_config(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    from tui_gateway.entry import JSONRPCServer

    config_path = tmp_path / "config.yaml"
    server = JSONRPCServer(config_path=config_path, runtime_root=tmp_path / "runtime", writer=lambda _: None)

    providers = __import__("asyncio").run(server.handle_model_providers({}))
    setup = __import__("asyncio").run(
        server.handle_model_setup(
            {
                "provider": "openai",
                "model": "gpt-4o-mini",
                "api_key": "sk-test-secret",
            }
        )
    )
    oauth = __import__("asyncio").run(
        server.handle_model_setup(
            {
                "provider": "nous",
                "model": "portal-chat",
                "auth_type": "oauth",
                "client_id": "client-id",
                "auth_url": "https://portal.example/oauth/authorize",
                "token_url": "https://portal.example/oauth/token",
            }
        )
    )
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    env_text = (tmp_path / ".env").read_text(encoding="utf-8")

    assert [item["slug"] for item in providers["providers"]] == ["custom"]
    assert setup["ok"] is True
    assert setup["env_path"] == str(tmp_path / ".env")
    assert "OPENAI_API_KEY=sk-test-secret" in env_text
    assert "sk-test-secret" not in json.dumps(setup)
    assert oauth["ok"] is True
    assert oauth["provider"] == "custom"
    assert oauth["auth_type"] == "oauth"
    assert config["providers"]["custom"]["auth_type"] == "oauth"
    assert config["providers"]["custom"]["oauth"]["client_id"] == "client-id"
    assert config["model"] == {"provider": "custom", "name": "portal-chat"}


def test_tui_gateway_auto_loads_project_config_yaml_without_env(tmp_path, monkeypatch):
    monkeypatch.delenv("LOCAL_AGENT_CONFIG_PATH", raising=False)
    monkeypatch.delenv("DUAL_RING_CONFIG_PATH", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "secret-value")

    from tui_gateway.entry import JSONRPCServer

    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "root_path": str(tmp_path),
                "model": {"provider": "custom", "name": "LongCat-Flash-Lite"},
                "providers": {
                    "custom": {
                        "base_url": "https://api.longcat.chat/openai",
                        "api_key_env": "OPENAI_API_KEY",
                    }
                },
                "adapters": {
                    "remote_llm": {
                        "enabled": True,
                        "dry_run": True,
                        "api_key_env": "OPENAI_API_KEY",
                        "base_url": "https://api.longcat.chat/openai",
                        "model": "LongCat-Flash-Lite",
                    }
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    server = JSONRPCServer(runtime_root=tmp_path, writer=lambda _: None)
    options = __import__("asyncio").run(server.handle_model_options({}))

    assert server.config_path == config_path.resolve()
    assert options["model"] == "LongCat-Flash-Lite"
    assert options["providers"][0]["base_url"] == "https://api.longcat.chat/openai"


def test_tui_gateway_client_sets_default_config_path_for_gateway_process():
    gateway_source = (ROOT / "ui-tui" / "src" / "gatewayClient.ts").read_text(encoding="utf-8")

    assert "defaultConfigPath" in gateway_source
    assert "LOCAL_AGENT_CONFIG_PATH: process.env.LOCAL_AGENT_CONFIG_PATH || defaultConfigPath" in gateway_source


def test_local_agent_cli_quickstart_model_and_doctor_noninteractive(tmp_path, monkeypatch):
    import subprocess
    import sys

    config_path = tmp_path / "config.yaml"
    env = {
        **os.environ,
        "LOCAL_AGENT_CONFIG_PATH": str(config_path),
        "PYTHONPATH": str(ROOT),
    }

    setup = subprocess.run(
        [
            sys.executable,
            "-m",
            "tui_gateway.cli",
            "setup",
            "--provider",
            "openai",
            "--model",
            "gpt-4o-mini",
            "--api-key",
            "sk-test-secret",
            "--config",
            str(config_path),
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    model = subprocess.run(
        [
            sys.executable,
            "-m",
            "tui_gateway.cli",
            "model",
            "openrouter:openai/gpt-4o-mini",
            "--config",
            str(config_path),
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    doctor = subprocess.run(
        [sys.executable, "-m", "tui_gateway.cli", "doctor", "--config", str(config_path)],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    saved = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    env_text = (tmp_path / ".env").read_text(encoding="utf-8")
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert "设置完成" in setup.stdout
    assert "sk-test-secret" not in setup.stdout
    assert "模型已配置：custom:openai/gpt-4o-mini" in model.stdout
    assert "运行时检查" in doctor.stdout
    assert "OPENAI_API_KEY=sk-test-secret" in env_text
    assert saved["model"] == {"provider": "custom", "name": "openai/gpt-4o-mini"}
    assert 'local-agent = "tui_gateway.cli:main"' in pyproject
