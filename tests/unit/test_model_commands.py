"""Unit tests for model config/select/setup CLI commands."""

import os
import tempfile
from unittest.mock import patch, MagicMock

import click
from click.testing import CliRunner
import pytest

from autoai.app.commands import model


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def env_file():
    """Create a temporary .env file for testing."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
        f.write("OPENAI_API_KEY=test-key\n")
        f.write("SMART_LLM=gpt-4o\n")
        f.write("FAST_LLM=gpt-4o-mini\n")
        f.flush()
        yield f.name
    os.unlink(f.name)


class TestModelList:
    def test_model_list_runs(self, runner):
        result = runner.invoke(model, ["list"])
        assert result.exit_code == 0

    def test_model_list_shows_providers(self, runner):
        result = runner.invoke(model, ["list"])
        assert "openai" in result.output.lower() or "provider" in result.output.lower()


class TestModelProviders:
    def test_model_providers_runs(self, runner):
        result = runner.invoke(model, ["providers"])
        assert result.exit_code == 0


class TestModelRoute:
    def test_model_route_runs(self, runner):
        result = runner.invoke(model, ["route"])
        assert result.exit_code == 0


class TestModelConfig:
    def test_config_with_provider_and_model(self, runner):
        result = runner.invoke(model, ["config", "--provider", "openai", "--model", "gpt-4o", "--strategy", "local_first"])
        assert result.exit_code == 0
        assert "gpt-4o" in result.output

    def test_config_invalid_provider(self, runner):
        result = runner.invoke(model, ["config", "--provider", "nonexistent", "--model", "fake"])
        assert result.exit_code != 0

    def test_config_with_strategy(self, runner):
        result = runner.invoke(model, ["config", "--provider", "openai", "--model", "gpt-4o", "--strategy", "cloud_first"])
        assert result.exit_code == 0
        assert "cloud_first" in result.output

    def test_config_shows_summary(self, runner):
        result = runner.invoke(model, ["config", "--provider", "openai", "--model", "gpt-4o", "--strategy", "cost_optimal"])
        assert result.exit_code == 0
        assert "gpt-4o" in result.output
        assert "cost_optimal" in result.output


class TestWriteEnvKey:
    def test_write_env_key(self, tmp_path):
        env_path = tmp_path / ".env"
        env_path.write_text("EXISTING_KEY=value\n")

        from autoai.app.commands import _write_env_key
        original_cwd = os.getcwd()
        os.chdir(str(tmp_path))
        try:
            _write_env_key("NEW_KEY", "new_value")
        finally:
            os.chdir(original_cwd)

        content = env_path.read_text()
        assert "NEW_KEY=new_value" in content
        assert "EXISTING_KEY=value" in content

    def test_write_env_key_updates_existing(self, tmp_path):
        env_path = tmp_path / ".env"
        env_path.write_text("SMART_LLM=gpt-4\n")

        from autoai.app.commands import _write_env_key
        original_cwd = os.getcwd()
        os.chdir(str(tmp_path))
        try:
            _write_env_key("SMART_LLM", "gpt-4o")
        finally:
            os.chdir(original_cwd)

        content = env_path.read_text()
        assert "SMART_LLM=gpt-4o" in content
        assert "SMART_LLM=gpt-4\n" not in content


class TestSaveModelToEnv:
    def test_save_model_to_env(self, tmp_path):
        env_path = tmp_path / ".env"
        env_path.write_text("")

        mock_model = MagicMock()
        mock_model.model_id = "gpt-4o"
        mock_model.provider_name = "openai"

        from autoai.app.commands import _save_model_to_env
        original_cwd = os.getcwd()
        os.chdir(str(tmp_path))
        try:
            _save_model_to_env(mock_model, "local_first")
        finally:
            os.chdir(original_cwd)

        content = env_path.read_text()
        assert "SMART_LLM=gpt-4o" in content
        assert "ROUTING_STRATEGY=local_first" in content
