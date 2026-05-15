"""零样本工具创造: Agent根据需求自动编写并注册新命令。

Agent不仅是工具的使用者，也是工具的创造者。
当现有工具无法满足需求时，Agent可以:
1. 分析缺口: 什么操作没有对应的命令？
2. 设计接口: 输入/输出/前置条件/后置条件
3. 生成实现: 自动编写Python代码
4. 安全审查: 沙箱测试+治理审批
5. 动态注册: 运行时注册到CommandRegistry
"""
from autoai.tool_creation.creator import (
    ToolCreator,
    ToolSpec,
    CreatedTool,
    ToolRegistry,
)

__all__ = [
    "ToolCreator",
    "ToolSpec",
    "CreatedTool",
    "ToolRegistry",
]
