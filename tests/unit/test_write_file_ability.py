import logging
import os

from autogpt.core.ability.builtins.file_operations import WriteFile
from autogpt.core.workspace import Workspace


def test_writefile_existing_directory(workspace: Workspace) -> None:
    logger = logging.getLogger("test")
    ability = WriteFile(logger=logger, workspace=workspace)

    directory = workspace.get_path("existing")
    os.makedirs(directory, exist_ok=True)

    filename = "existing/hello.txt"
    result = ability(filename, "content")

    assert result.success is True
    file_path = workspace.get_path(filename)
    assert file_path.read_text() == "content"


def test_writefile_empty_content(workspace: Workspace) -> None:
    logger = logging.getLogger("test")
    ability = WriteFile(logger=logger, workspace=workspace)

    filename = "empty.txt"
    result = ability(filename, "")

    assert result.success is False
    assert "was not given any content" in result.message
    assert not workspace.get_path(filename).exists()
