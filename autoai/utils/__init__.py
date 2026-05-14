"""AutoAI的通用工具。"""

from __future__ import annotations

import yaml
from autoai.utils.ansi_colors import Fore

from .git import git_checkout, git_blame


def validate_yaml_file(file: str):
    """Validate a YAML file.

    Returns a tuple ``(bool, message)`` indicating validity and a human readable
    message describing the result.
    """
    try:
        with open(file, encoding="utf-8") as fp:
            yaml.load(fp.read(), Loader=yaml.FullLoader)
    except FileNotFoundError:
        return (False, f"The file {Fore.CYAN}`{file}`{Fore.RESET} wasn't found")
    except yaml.YAMLError as e:
        return (
            False,
            f"There was an issue while trying to read with your AI Settings file: {e}",
        )

    return (True, f"Successfully validated {Fore.CYAN}`{file}`{Fore.RESET}!")


__all__ = ["git_checkout", "git_blame", "validate_yaml_file"]
