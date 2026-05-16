"""Phase lambda: 自优化闭环 - Agent每秒都在优化自己。

将已有的7阶段闭环(感知→诊断→假设→实验→验证→集成→反思)
从"被动触发"变为"持续运行"。

HoloAgent主循环: think→act→evolve(每N周期)
"""

from autoai.self_optimize.loop import SelfOptimizeLoop, OptimizeCycle, OptimizeReport

__all__ = ["SelfOptimizeLoop", "OptimizeCycle", "OptimizeReport"]
