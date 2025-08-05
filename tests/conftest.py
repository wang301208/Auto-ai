import os
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
import yaml
from pytest_mock import MockerFixture

import sys
from types import ModuleType

# Stub out optional heavy dependencies
sys.modules.setdefault("spacy", ModuleType("spacy"))
sys.modules.setdefault("chromadb", ModuleType("chromadb"))
sys.modules.setdefault("docx", ModuleType("docx"))
sys.modules.setdefault("markdown", ModuleType("markdown"))
sys.modules.setdefault("PyPDF2", ModuleType("PyPDF2"))
bs4_stub = ModuleType("bs4")
bs4_stub.BeautifulSoup = object
sys.modules.setdefault("bs4", bs4_stub)
ple_stub = ModuleType("pylatexenc")
latex2text_stub = ModuleType("pylatexenc.latex2text")
class LatexNodes2Text:  # type: ignore
    def latex_to_text(self, s: str) -> str:
        return s
latex2text_stub.LatexNodes2Text = LatexNodes2Text
ple_stub.latex2text = latex2text_stub
sys.modules.setdefault("pylatexenc", ple_stub)
sys.modules.setdefault("pylatexenc.latex2text", latex2text_stub)
orjson_stub = ModuleType("orjson")
orjson_stub.OPT_SERIALIZE_NUMPY = 0
orjson_stub.OPT_SERIALIZE_DATACLASS = 0
orjson_stub.dumps = lambda obj, option=0: b""
orjson_stub.loads = lambda b: {}
sys.modules.setdefault("orjson", orjson_stub)

from autogpt.agents import Agent
from autogpt.config import AIConfig, Config, ConfigBuilder
from autogpt.llm.api_manager import ApiManager
from autogpt.logs import logger
from autogpt.memory.vector import get_memory
from autogpt.models.command_registry import CommandRegistry
from autogpt.prompts.prompt import DEFAULT_TRIGGERING_PROMPT
from autogpt.workspace import Workspace

pytest_plugins = [
    "tests.integration.agent_factory",
    "tests.integration.memory.utils",
]


PLACEHOLDER_OPENAI_KEYS = {"", "sk-dummy", "your-openai-api-key"}
PLACEHOLDER_HUGGINGFACE_KEYS = {"", "your-huggingface-api-key"}


def pytest_runtest_setup(item: pytest.Item) -> None:
    """Skip tests requiring external API keys if they are not available."""
    if item.get_closest_marker("requires_openai_api_key"):
        key = os.environ.get("OPENAI_API_KEY")
        if key in PLACEHOLDER_OPENAI_KEYS or key is None:
            pytest.skip("OPENAI_API_KEY is not set or is placeholder.")

    if item.get_closest_marker("requires_huggingface_api_key"):
        key = os.environ.get("HUGGINGFACE_API_KEY")
        if key in PLACEHOLDER_HUGGINGFACE_KEYS or key is None:
            pytest.skip("HUGGINGFACE_API_KEY is not set or is placeholder.")


@pytest.fixture()
def workspace_root(tmp_path: Path) -> Path:
    return tmp_path / "home/users/monty/auto_gpt_workspace"


@pytest.fixture()
def workspace(workspace_root: Path) -> Workspace:
    workspace_root = Workspace.make_workspace(workspace_root)
    return Workspace(workspace_root, restrict_to_workspace=True)


@pytest.fixture
def temp_plugins_config_file():
    """Create a plugins_config.yaml file in a temp directory so that it doesn't mess with existing ones"""
    config_directory = TemporaryDirectory()
    config_file = os.path.join(config_directory.name, "plugins_config.yaml")
    with open(config_file, "w+") as f:
        f.write(yaml.dump({}))

    yield config_file


@pytest.fixture()
def config(
    temp_plugins_config_file: str, mocker: MockerFixture, workspace: Workspace
) -> Config:
    config = ConfigBuilder.build_config_from_env(workspace.root.parent)
    if not os.environ.get("OPENAI_API_KEY"):
        os.environ["OPENAI_API_KEY"] = "sk-dummy"

    config.workspace_path = workspace.root

    # HACK: this is necessary to ensure PLAIN_OUTPUT takes effect
    logger.config = config

    config.plugins_dir = "tests/unit/data/test_plugins"
    config.plugins_config_file = temp_plugins_config_file

    # avoid circular dependency
    from autogpt.plugins.plugins_config import PluginsConfig

    config.plugins_config = PluginsConfig.load_config(
        plugins_config_file=config.plugins_config_file,
        plugins_denylist=config.plugins_denylist,
        plugins_allowlist=config.plugins_allowlist,
    )

    # Do a little setup and teardown since the config object is a singleton
    mocker.patch.multiple(
        config,
        workspace_path=workspace.root,
        file_logger_path=workspace.get_path("file_logger.txt"),
    )
    yield config


@pytest.fixture()
def api_manager() -> ApiManager:
    if ApiManager in ApiManager._instances:
        del ApiManager._instances[ApiManager]
    return ApiManager()


@pytest.fixture
def agent(config: Config) -> Agent:
    ai_config = AIConfig(
        ai_name="Base",
        ai_role="A base AI",
        ai_goals=[],
    )

    command_registry = CommandRegistry()
    ai_config.command_registry = command_registry
    config.memory_backend = "json_file"
    memory_json_file = get_memory(config)
    memory_json_file.clear()

    return Agent(
        memory=memory_json_file,
        command_registry=command_registry,
        ai_config=ai_config,
        config=config,
        triggering_prompt=DEFAULT_TRIGGERING_PROMPT,
    )
