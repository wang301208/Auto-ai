import itertools
from pathlib import Path

import pytest

from autogpt.config.ai_config import AIConfig
from autogpt.workspace import Workspace

_WORKSPACE_ROOT = Path("home/users/monty/auto_gpt_workspace")

_ACCESSIBLE_PATHS = [
    Path("."),
    Path("test_file.txt"),
    Path("test_folder"),
    Path("test_folder/test_file.txt"),
    Path("test_folder/.."),
    Path("test_folder/../test_file.txt"),
    Path("test_folder/../test_folder"),
    Path("test_folder/../test_folder/test_file.txt"),
]

_INACCESSIBLE_PATHS = (
    [
        # Takes us out of the workspace
        Path(".."),
        Path("../test_file.txt"),
        Path("../not_auto_gpt_workspace"),
        Path("../not_auto_gpt_workspace/test_file.txt"),
        Path("test_folder/../.."),
        Path("test_folder/../../test_file.txt"),
        Path("test_folder/../../not_auto_gpt_workspace"),
        Path("test_folder/../../not_auto_gpt_workspace/test_file.txt"),
    ]
    + [
        # Contains null bytes
        Path(template.format(null_byte=null_byte))
        for template, null_byte in itertools.product(
            [
                "{null_byte}",
                "{null_byte}test_file.txt",
                "test_folder/{null_byte}",
                "test_folder/{null_byte}test_file.txt",
            ],
            Workspace.NULL_BYTES,
        )
    ]
    + [
        # Absolute paths
        Path("/"),
        Path("/test_file.txt"),
        Path("/home"),
    ]
)


@pytest.fixture()
def workspace_root(tmp_path: Path) -> Path:
    return tmp_path / _WORKSPACE_ROOT


@pytest.fixture(params=_ACCESSIBLE_PATHS)
def accessible_path(request: pytest.FixtureRequest) -> Path:
    return request.param


@pytest.fixture(params=_INACCESSIBLE_PATHS)
def inaccessible_path(request: pytest.FixtureRequest) -> Path:
    return request.param


def test_sanitize_path_accessible(accessible_path: Path, workspace_root: Path) -> None:
    full_path = Workspace._sanitize_path(
        accessible_path,
        root=workspace_root,
        restrict_to_root=True,
    )
    assert full_path.is_absolute()
    assert full_path.is_relative_to(workspace_root)


def test_sanitize_path_inaccessible(
    inaccessible_path: Path, workspace_root: Path
) -> None:
    with pytest.raises(ValueError):
        Workspace._sanitize_path(
            inaccessible_path,
            root=workspace_root,
            restrict_to_root=True,
        )


def test_get_path_accessible(accessible_path: Path, workspace_root: Path) -> None:
    workspace = Workspace(workspace_root, True)
    full_path = workspace.get_path(accessible_path)
    assert full_path.is_absolute()
    assert full_path.is_relative_to(workspace_root)


def test_get_path_inaccessible(inaccessible_path: Path, workspace_root: Path) -> None:
    workspace = Workspace(workspace_root, True)
    with pytest.raises(ValueError):
        workspace.get_path(inaccessible_path)


def test_make_workspace_creates_default_config_files(tmp_path: Path) -> None:
    workspace_path = Workspace.make_workspace(tmp_path / "workspace")
    repo_root = Path(__file__).resolve().parents[2]

    env_path = workspace_path / ".env"
    template_env = (repo_root / ".env.template").read_text()
    assert env_path.read_text() == template_env

    prompt_path = workspace_path / "prompt_settings.yaml"
    assert prompt_path.read_text() == (repo_root / "prompt_settings.yaml").read_text()

    ai_settings_file = workspace_path / "ai_settings.yaml"
    ai_config = AIConfig.load(ai_settings_file)
    assert ai_config.ai_name == ""
    assert ai_config.ai_goals == []
