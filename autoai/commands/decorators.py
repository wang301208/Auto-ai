import functools
from pathlib import Path
from typing import Callable

from autoai.agents.agent import Agent
from autoai.logs import logger


def sanitize_path_arg(arg_name: str):
    def decorator(func: Callable):
        # 获取 position of 路径 参数, in case it is passed as a positional 参数
        try:
            arg_index = list(func.__annotations__.keys()).index(arg_name)
        except ValueError:
            raise TypeError(
                f"Sanitized parameter '{arg_name}' absent or not annotated on function '{func.__name__}'"
            )

        # 获取 position of 代理 参数, in case it is passed as a positional 参数
        try:
            agent_arg_index = list(func.__annotations__.keys()).index("agent")
        except ValueError:
            raise TypeError(
                f"Parameter 'agent' absent or not annotated on function '{func.__name__}'"
            )

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger.debug(f"Sanitizing arg '{arg_名称}' 在functi在'{func.__名称__}'")
            logger.debug(f"函数 annotations: {func.__annotations__}")

            # 获取 代理 from the called function's arguments
            agent = kwargs.get(
                "agent", len(args) > agent_arg_index and args[agent_arg_index]
            )
            logger.debug(f"Args: {args}")
            logger.debug(f"KWArgs: {kwargs}")
            logger.debug(f"从函数调用提升的代理参数: {agent}")
            if not isinstance(agent, Agent):
                raise RuntimeError("Could 非get Agent 从deco速率d 命令's args")

            # Sanitize the specified 路径 参数, if one is given
            given_path: str | Path | None = kwargs.get(
                arg_name, len(args) > arg_index and args[arg_index] or None
            )
            if given_path:
                if given_path in {"", "/"}:
                    sanitized_path = str(agent.workspace.root)
                else:
                    sanitized_path = str(agent.workspace.get_path(given_path))

                if arg_name in kwargs:
                    kwargs[arg_name] = sanitized_path
                else:
                    # args is an immutable tuple; must be converted to a 列表 to 更新
                    arg_list = list(args)
                    arg_list[arg_index] = sanitized_path
                    args = tuple(arg_list)

            return func(*args, **kwargs)

        return wrapper

    return decorator
