"""阅读和理解代码库的命令。"""

from __future__ import annotations

COMMAND_CATEGORY = "code_reader"
COMMAND_CATEGORY_TITLE = "Code Reader"

from pathlib import Path
import logging

from autoai.agents.agent import Agent
from autoai.command_decorator import command
from autoai.llm.base import ChatSequence, Message
from autoai.llm.utils import create_chat_completion

logger = logging.getLogger(__name__)
CALL_COUNT = 0

# 模板 used to prompt the 模型 for code analysis
PROMPT_TEMPLATE = (
    "You are an expert Python developer. Given the following files, provide a "
    "concise explanation of their purpose and how they work.\n\n{code}\n"
)


@command(
    "read_and_understand_code",
    "Read Python files under a path and return a high level summary",
    {
        "path": {
            "type": "string",
            "description": "Path to a file or directory containing Python code",
            "required": True,
        }
    },
)
def read_and_understand_code(path: str, agent: Agent) -> str:
    """递归读取``path``下的.py文件并总结其内容。"""

    global CALL_COUNT
    base = Path(path)
    files: list[Path]
    if base.is_dir():
        files = sorted(base.rglob("*.py"))
    elif base.suffix == ".py":
        files = [base]
    else:
        files = []

    file_count = len(files)
    CALL_COUNT += 1
    logger.info(
        "code_reader",
        extra={
            "path_analyzed": str(base),
            "file_count": file_count,
            "call_count": CALL_COUNT,
        },
    )

    code_parts: list[str] = []
    for file in files:
        try:
            content = file.read_text(encoding="utf-8")
        except Exception:
            continue
        code_parts.append(f"# File: {file.name}\n{content}")

    if not code_parts:
        return "No Python code found."

    combined = "\n\n".join(code_parts)
    prompt = ChatSequence.for_model(
        agent.llm.name,
        [
            Message(
                "system",
                "You carefully read code and explain it in clear, simple terms.",
            ),
            Message("user", PROMPT_TEMPLATE.format(code=combined)),
        ],
    )

    response = create_chat_completion(prompt=prompt, config=agent.config)
    return response.content or ""
