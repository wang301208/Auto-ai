import ast
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


def to_numbered_list(
    items: list[str], no_items_response: str = "", **template_args: str
) -> str:
    if items:
        return "\n".join(
            f"{i+1}. {item.format(**template_args)}" for i, item in enumerate(items)
        )
    else:
        return no_items_response


def json_loads(json_str: str) -> Any:
    """解析JSON字符串, 回退到 ``ast.literal_eval`` on failure.

        Args:
            json_str: 要解析的字符串.

        Raises:
            ValueError: If both ``json.loads`` and ``ast.literal_eval`` fail.
"""

    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        logger.debug("json.loads失败: %s; 尝试ast.literal_eval", e)
        try:
            return ast.literal_eval(json_str)
        except (ValueError, SyntaxError) as literal_error:
            logger.error(
                "Failed to parse string as JSON; json.loads error: %s; ast.literal_eval error: %s",
                e,
                literal_error,
            )
            raise ValueError("无法将字符串解析为JSON") from literal_error
