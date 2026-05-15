"""活UI: Agent即界面。前端消亡，Agent自己决定渲染什么。

哲学:
- 没有固定UI模板，Agent根据任务/数据自主涌现界面
- 面板不是设计师画的，是Agent根据数据特征"长出来的"
- 图表不是预设的，是Agent根据数据分布自动选择的
- 交互不是硬编码的，用户输入直接变为Agent行动
- 每一帧都是Agent"思考"的结果——UI是Agent思维的可视化
"""
from autoai.living_ui.canvas import LivingCanvas, Cell, Frame, CellStyle
from autoai.living_ui.panel import PanelEmerger, EmergentPanel, PanelType
from autoai.living_ui.chart import ChartSelector, ChartSpec, ChartType
from autoai.living_ui.interaction import InteractionBridge, InputAction, InputType

__all__ = [
    "LivingCanvas", "Cell", "Frame", "CellStyle",
    "PanelEmerger", "EmergentPanel", "PanelType",
    "ChartSelector", "ChartSpec", "ChartType",
    "InteractionBridge", "InputAction", "InputType",
]
