"""Phase iota: 活UI测试 - 画布/面板涌现/图表自选/交互即行动"""
from __future__ import annotations

import pytest

from autoai.living_ui import (
    LivingCanvas, Cell, Frame, CellStyle,
    PanelEmerger, EmergentPanel, PanelType,
    ChartSelector, ChartSpec, ChartType,
    InteractionBridge, InputAction, InputType,
)


class TestLivingCanvas:
    def test_blank_frame(self):
        frame = Frame.blank(80, 24)
        assert frame.width == 80
        assert frame.height == 24

    def test_write_line(self):
        frame = Frame.blank(40, 10)
        frame.write_line(0, "Hello World")
        assert frame.cells[0][0].content == "H"

    def test_write_centered(self):
        frame = Frame.blank(40, 10)
        frame.write_centered(0, "TITLE")
        assert frame.cells[0][17].content == "T"

    def test_cell_render(self):
        cell = Cell(content="X", style=CellStyle.BOLD)
        rendered = cell.render()
        assert "X" in rendered

    def test_frame_render(self):
        frame = Frame.blank(20, 5)
        frame.write_line(0, "Test")
        output = frame.render()
        assert "Test" in output

    def test_frame_diff(self):
        f1 = Frame.blank(20, 5)
        f2 = Frame.blank(20, 5)
        f2.write_line(0, "Changed")
        diff = f1.diff(f2)
        assert len(diff) > 0

    def test_canvas_think_frame(self):
        canvas = LivingCanvas(40, 10)
        frame = canvas.think_frame({"status": "active"})
        assert frame.frame_id == 0

    def test_canvas_draw_border(self):
        canvas = LivingCanvas(40, 10)
        frame = Frame.blank(40, 10)
        canvas.draw_border(frame, 0, 0, 20, 5, "Panel")
        assert frame.cells[0][0].content == "+"

    def test_canvas_stats(self):
        canvas = LivingCanvas()
        stats = canvas.stats
        assert stats["width"] == 80
        assert stats["height"] == 24


class TestPanelEmerger:
    def test_emerge_from_errors(self):
        emerger = PanelEmerger()
        panels = emerger.emerge_from_context({"errors": ["fail1", "fail2"]})
        alert_panels = [p for p in panels if p.panel_type == PanelType.ALERT]
        assert len(alert_panels) >= 1

    def test_emerge_from_metrics(self):
        emerger = PanelEmerger()
        panels = emerger.emerge_from_context({"metrics": {"cpu": 0.8, "mem": 0.6}})
        metric_panels = [p for p in panels if p.panel_type == PanelType.METRICS]
        assert len(metric_panels) >= 1

    def test_emerge_from_tasks(self):
        emerger = PanelEmerger()
        panels = emerger.emerge_from_context({"tasks": [{"name": "t1", "status": "running"}]})
        status_panels = [p for p in panels if p.panel_type == PanelType.STATUS]
        assert len(status_panels) >= 1

    def test_emerge_from_data(self):
        emerger = PanelEmerger()
        data = [{"name": "a", "val": 1}, {"name": "b", "val": 2}]
        panels = emerger.emerge_from_context({"data": data})
        table_panels = [p for p in panels if p.panel_type == PanelType.TABLE]
        assert len(table_panels) >= 1

    def test_layout(self):
        emerger = PanelEmerger()
        emerger.emerge_from_context({"metrics": {"x": 1}, "tasks": [{"name": "t"}]})
        layout = emerger.layout(80, 24)
        assert len(layout) >= 2

    def test_panel_expiry(self):
        panel = EmergentPanel(panel_id="t", panel_type=PanelType.ALERT, lifetime_seconds=0.001)
        import time
        time.sleep(0.01)
        assert panel.is_expired

    def test_panel_refresh(self):
        panel = EmergentPanel(panel_id="t", panel_type=PanelType.STATUS)
        panel.refresh(new_lines=["updated"])
        assert panel.refreshed_count == 1


class TestChartSelector:
    def test_select_bar_for_dict(self):
        selector = ChartSelector()
        spec = selector.select({"a": 10, "b": 20, "c": 30, "d": 40, "e": 50, "f": 60, "g": 70})
        assert spec.chart_type == ChartType.BAR

    def test_select_pie_for_small_dict(self):
        selector = ChartSelector()
        spec = selector.select({"a": 10, "b": 20, "c": 30})
        assert spec.chart_type == ChartType.PIE_TEXT

    def test_select_sparkline_for_list(self):
        selector = ChartSelector()
        spec = selector.select([1, 3, 5, 7, 9, 2, 4, 6, 8])
        assert spec.chart_type == ChartType.SPARKLINE

    def test_select_gauge_for_float(self):
        selector = ChartSelector()
        spec = selector.select(0.75)
        assert spec.chart_type == ChartType.GAUGE

    def test_select_table_for_dict_list(self):
        selector = ChartSelector()
        spec = selector.select([{"a": 1}, {"a": 2}])
        assert spec.chart_type == ChartType.TABLE

    def test_bar_render(self):
        spec = ChartSpec(chart_type=ChartType.BAR, data={"x": 5, "y": 10}, width=40)
        lines = spec.render_text()
        assert len(lines) >= 2
        assert "x" in lines[0]

    def test_sparkline_render(self):
        spec = ChartSpec(chart_type=ChartType.SPARKLINE, data=[1, 5, 3, 8, 2])
        lines = spec.render_text()
        assert len(lines) >= 1

    def test_gauge_render(self):
        spec = ChartSpec(chart_type=ChartType.GAUGE, data=0.75, width=40)
        lines = spec.render_text()
        assert "75%" in lines[0]

    def test_trend_render(self):
        spec = ChartSpec(chart_type=ChartType.TREND, data=[10, 20, 15, 25])
        lines = spec.render_text()
        assert len(lines) >= 1


class TestInteractionBridge:
    def test_command_input(self):
        bridge = InteractionBridge()
        result = bridge.process_input("/status")
        assert result.action.input_type == InputType.COMMAND
        assert result.action.action_name == "status"

    def test_command_with_args(self):
        bridge = InteractionBridge()
        result = bridge.process_input("/set --key val")
        assert result.action.action_name == "set"
        assert result.action.action_args.get("key") == "val"

    def test_confirm_yes(self):
        bridge = InteractionBridge()
        result = bridge.process_input("yes")
        assert result.action.input_type == InputType.CONFIRM
        assert result.action.action_args["value"] is True

    def test_confirm_no(self):
        bridge = InteractionBridge()
        result = bridge.process_input("n")
        assert result.action.action_args["value"] is False

    def test_value_input(self):
        bridge = InteractionBridge()
        result = bridge.process_input("some text")
        assert result.action.input_type == InputType.VALUE
        assert result.action.action_args["value"] == "some text"

    def test_handler_execution(self):
        bridge = InteractionBridge()
        bridge.register_handler("greet", lambda name="world": f"Hello {name}")
        result = bridge.process_input("/greet --name Agent")
        assert result.success

    def test_select_action(self):
        bridge = InteractionBridge()
        action = bridge.create_select_action(["A", "B", "C"], selected=1)
        assert action.input_type == InputType.SELECT
        assert action.action_args["selected"] == 1

    def test_navigate_action(self):
        bridge = InteractionBridge()
        action = bridge.create_navigate_action("dashboard")
        assert action.input_type == InputType.NAVIGATE

    def test_as_cli_command(self):
        action = InputAction(
            input_type=InputType.COMMAND,
            raw_input="/run --task build",
            action_name="run",
            action_args={"task": "build"},
        )
        assert "--task build" in action.as_cli_command

    def test_stats(self):
        bridge = InteractionBridge()
        bridge.process_input("/test")
        bridge.process_input("yes")
        stats = bridge.stats
        assert stats["inputs_processed"] == 2
