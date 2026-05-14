from __future__ import annotations

from types import ModuleType
from autoai.skills import get as get_skill


def main() -> None:
    """Example script that loads and runs a skill from the library."""
    rec = {"name": "hello_world", "version": "1.0", "parameters": {"foo": "bar"}}
    skill = get_skill(rec["name"], rec["version"])
    assert skill is not None

    module = ModuleType("skill")
    exec(skill.code, module.__dict__)
    module.run(**rec["parameters"])


if __name__ == "__main__":
    main()
