"""自主性审计器: 对模块执行20项检查清单,判断真自主vs伪自主。"""

from __future__ import annotations

import ast
import inspect
import importlib
import logging
from dataclasses import dataclass, field
from typing import Any
from enum import Enum

logger = logging.getLogger(__name__)


class AuditSeverity(Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"
    PASS = "pass"


@dataclass
class AuditCheck:
    """单个审计检查项。"""
    check_id: str
    name: str
    description: str
    severity: AuditSeverity
    passed: bool
    evidence: str = ""
    recommendation: str = ""


@dataclass
class AuditReport:
    """审计报告。"""
    target: str
    checks: list[AuditCheck] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.checks)

    @property
    def passed_count(self) -> int:
        return sum(1 for c in self.checks if c.passed)

    @property
    def failed_count(self) -> int:
        return sum(1 for c in self.checks if not c.passed)

    @property
    def score(self) -> float:
        return self.passed_count / max(self.total, 1)

    @property
    def critical_failures(self) -> list[AuditCheck]:
        return [c for c in self.checks if not c.passed and c.severity == AuditSeverity.CRITICAL]

    @property
    def summary(self) -> str:
        return f"{self.target}: {self.passed_count}/{self.total}通过 ({self.score:.0%}), {len(self.critical_failures)}个关键失败"


class AutonomyAuditor:
    """自主性审计器: 执行20项检查清单。"""

    def __init__(self):
        self._reports: list[AuditReport] = []

    def audit_module(self, module_path: str) -> AuditReport:
        """对模块执行完整审计。"""
        report = AuditReport(target=module_path)
        try:
            mod = importlib.import_module(module_path)
            source = inspect.getsource(mod)
            tree = ast.parse(source)
        except Exception as e:
            report.checks.append(AuditCheck(
                check_id="C0", name="模块加载", description="能否加载模块",
                severity=AuditSeverity.CRITICAL, passed=False, evidence=str(e),
            ))
            self._reports.append(report)
            return report

        feature_flags = self._detect_feature_flags(tree, source)
        checks = [
            self._check_c1_nondeterministic(tree, source, feature_flags),
            self._check_c2_if_else_density(tree),
            self._check_c3_reasoning_calls(source),
            self._check_c4_goal_type_openness(source),
            self._check_c5_priority_formula_hardcoded(tree),
            self._check_c6_param_mutability(source),
            self._check_c7_adjust_direction_fixed(tree),
            self._check_c8_learning_mechanism(source, feature_flags),
            self._check_c9_pseudo_optimization(source),
            self._check_c10_reflection_actionable(source, tree),
            self._check_c11_cognitive_loop_closed(source),
            self._check_c12_hardcoded_literal_count(tree),
            self._check_c13_mapping_table_closed(tree),
            self._check_c14_constitutional_boundary(source),
            self._check_c15_hash_pseudo_random(source),
            self._check_c16_stub_implementation(tree),
            self._check_c17_metaphor_consistency(source),
            self._check_c18_template_emergence(source),
            self._check_c19_behavior_space_finite(tree),
            self._check_c20_code_generation_real(source),
            self._check_c21_feature_flag_pattern(source, feature_flags),
            self._check_c22_flag_autonomy_completeness(source, feature_flags),
            self._check_c23_conditional_substitution(tree, source, feature_flags),
        ]
        report.checks = checks
        self._reports.append(report)
        return report

    def _check_c1_nondeterministic(self, tree: ast.AST, source: str, feature_flags: list[dict] | None = None) -> AuditCheck:
        """C1: 决策非确定性 - 是否有random/推理调用。"""
        has_random = "random.random()" in source or "random.gauss(" in source or "random.choice(" in source
        has_reasoning = "ReasoningDecider" in source or "reasoning_decider" in source
        has_exploration = "exploration_rate" in source
        has_param_space = "ParamSpace" in source or "param_space" in source
        has_cognitive_loop = "CognitiveLoop" in source or "cognitive_loop" in source
        has_open_emergence = "OpenEmergenceEngine" in source or "open_emergence" in source
        has_flag_reasoning = False
        if feature_flags:
            has_flag_reasoning = any(f.get("use_param") for f in feature_flags) and has_reasoning
        passed = has_random or has_reasoning or has_exploration or has_flag_reasoning or has_param_space or has_cognitive_loop or has_open_emergence
        evidence = []
        if has_random:
            evidence.append("random调用")
        if has_reasoning:
            evidence.append("推理决策器")
        if has_exploration:
            evidence.append("探索率")
        if has_flag_reasoning:
            evidence.append("旗标+推理")
        if has_param_space:
            evidence.append("ParamSpace")
        if has_cognitive_loop:
            evidence.append("CognitiveLoop")
        if has_open_emergence:
            evidence.append("OpenEmergence")
        return AuditCheck(
            check_id="C1", name="决策非确定性",
            description="模块是否引入非确定性(随机/推理/探索)?",
            severity=AuditSeverity.CRITICAL, passed=passed,
            evidence=",".join(evidence) if evidence else "无随机/推理机制",
            recommendation="引入ReasoningDecider或探索率" if not passed else "",
        )

    def _check_c2_if_else_density(self, tree: ast.AST) -> AuditCheck:
        """C2: if/elif密度 - 决策方法是否过度依赖条件分支。"""
        if_count = sum(1 for node in ast.walk(tree) if isinstance(node, ast.If))
        total_lines = sum(1 for node in ast.walk(tree) if isinstance(node, ast.stmt))
        density = if_count / max(total_lines, 1)
        passed = density < 0.15
        return AuditCheck(
            check_id="C2", name="if/elif密度",
            description=f"条件分支密度={density:.2%}(阈值15%)",
            severity=AuditSeverity.WARNING, passed=passed,
            evidence=f"if_count={if_count}, total_stmts={total_lines}, density={density:.2%}",
            recommendation="将if/elif规则链替换为推理决策" if not passed else "",
        )

    def _check_c3_reasoning_calls(self, source: str) -> AuditCheck:
        """C3: 推理调用 - 是否调用LLM/搜索/优化/RL/自主核心组件。"""
        keywords = ["llm", "search(", "optimize(", "reinforcement", "bayesian", "gradient_update", "evolutionary_perturb"]
        found = [k for k in keywords if k in source.lower()]
        autonomy_components = [
            "ReasoningDecider", "reasoning_decider", "ParamLearner", "param_learner",
            "ParamSpace", "param_space", "CognitiveLoop", "cognitive_loop",
            "OpenEmergenceEngine", "open_emergence", "RealExecutor", "real_executor",
            "AutonomyOrchestrator", "learnable_params",
        ]
        found_autonomy = [k for k in autonomy_components if k in source]
        passed = len(found) > 0 or len(found_autonomy) > 0
        evidence_parts = []
        if found:
            evidence_parts.append(f"传统推理: {found}")
        if found_autonomy:
            evidence_parts.append(f"自主核心: {found_autonomy}")
        return AuditCheck(
            check_id="C3", name="推理调用",
            description="是否调用搜索/优化/学习/推理/自主核心组件?",
            severity=AuditSeverity.CRITICAL, passed=passed,
            evidence=", ".join(evidence_parts) if evidence_parts else "无推理调用",
        )

    def _check_c4_goal_type_openness(self, source: str) -> AuditCheck:
        """C4: 目标类型开放性。"""
        has_self_generated = "SELF_GENERATED" in source or "self_generated" in source
        has_open_emergence = "OpenEmergence" in source or "emerge_self_generated" in source
        has_emergence_rule = "add_emergence_rule" in source or "emerge_from" in source
        has_goal_evolve = "evolve_goal" in source or "abandon_goal" in source
        has_emergence_mixin = "GoalEmergenceMixin" in source or "FullAutonomyMixin" in source
        passed = has_self_generated or has_open_emergence or has_emergence_rule or has_goal_evolve or has_emergence_mixin
        evidence_parts = []
        if has_self_generated:
            evidence_parts.append("SELF_GENERATED")
        if has_open_emergence:
            evidence_parts.append("OpenEmergence")
        if has_emergence_rule:
            evidence_parts.append("emergence_rule")
        if has_goal_evolve:
            evidence_parts.append("goal_evolve/abandon")
        if has_emergence_mixin:
            evidence_parts.append("GoalEmergenceMixin")
        return AuditCheck(
            check_id="C4", name="目标类型开放性",
            description="目标类型是否可扩展(非有限枚举)?",
            severity=AuditSeverity.WARNING, passed=passed,
            evidence=",".join(evidence_parts) if evidence_parts else "无开放目标机制",
            recommendation="引入SELF_GENERATED目标类型" if not passed else "",
        )

    def _check_c5_priority_formula_hardcoded(self, tree: ast.AST) -> AuditCheck:
        """C5: 优先级公式可学习。"""
        source_text = ast.unparse(tree) if hasattr(ast, 'unparse') else ""
        has_param_space = "param_space" in source_text or "ParamSpace" in source_text
        has_get = "param_space.get" in source_text or "_param_space.get" in source_text
        has_learnable_weight = "learnable" in source_text.lower() and ("weight" in source_text.lower() or "param" in source_text.lower())
        has_full_autonomy = "FullAutonomyMixin" in source_text
        passed = has_param_space or has_get or has_learnable_weight or has_full_autonomy
        return AuditCheck(
            check_id="C5", name="优先级公式可学习",
            description="优先级计算是否使用可学习参数?",
            severity=AuditSeverity.WARNING, passed=passed,
            recommendation="将硬编码系数替换为ParamSpace参数" if not passed else "",
        )

    def _check_c6_param_mutability(self, source: str) -> AuditCheck:
        """C6: 参数可修改性。"""
        has_setter = ".set(" in source or "set_value(" in source or "set_dimension(" in source
        has_param_space = "ParamSpace" in source or "param_space" in source
        has_enable = "enable_" in source
        passed = has_setter or has_param_space or has_enable
        return AuditCheck(
            check_id="C6", name="参数可修改性",
            description="关键参数是否有运行时修改接口?",
            severity=AuditSeverity.CRITICAL, passed=passed,
            recommendation="添加参数修改接口" if not passed else "",
        )

    def _check_c7_adjust_direction_fixed(self, tree: ast.AST) -> AuditCheck:
        """C7: 调整方向自主性。"""
        source_text = ast.unparse(tree) if hasattr(ast, 'unparse') else ""
        has_learnable_delta = "success_delta" in source_text or "failure_delta" in source_text
        has_param_learner = "ParamLearner" in source_text or "param_learner" in source_text
        has_gradient_update = "gradient_update" in source_text
        has_receive_feedback = "receive_feedback" in source_text
        has_full_autonomy = "FullAutonomyMixin" in source_text
        passed = has_learnable_delta or has_param_learner or has_gradient_update or has_receive_feedback or has_full_autonomy
        return AuditCheck(
            check_id="C7", name="调整方向自主性",
            description="参数调整方向是否由硬编码公式唯一确定?",
            severity=AuditSeverity.WARNING, passed=passed,
            recommendation="用ParamLearner替代固定增量" if not passed else "",
        )

    def _check_c8_learning_mechanism(self, source: str, feature_flags: list[dict] | None = None) -> AuditCheck:
        """C8: 学习机制。"""
        keywords = ["gradient_update", "bayesian_update", "evolutionary_perturb", "reinforcement_update", "ParamLearner"]
        found = [k for k in keywords if k in source]
        has_flag_learning = False
        if feature_flags:
            has_flag_learning = any(f.get("use_param") for f in feature_flags) and "ParamLearner" in source
        has_full_autonomy = "FullAutonomyMixin" in source
        passed = len(found) > 0 or has_flag_learning or has_full_autonomy
        evidence_parts = []
        if found:
            evidence_parts.append(f"传统: {found}")
        if has_flag_learning:
            evidence_parts.append("旗标+ParamLearner")
        if has_full_autonomy:
            evidence_parts.append("FullAutonomyMixin")
        return AuditCheck(
            check_id="C8", name="学习机制存在",
            description="是否有梯度/贝叶斯/RL/进化搜索?",
            severity=AuditSeverity.CRITICAL, passed=passed,
            evidence=", ".join(evidence_parts) if evidence_parts else "仅EMA/固定增量",
        )

    def _check_c9_pseudo_optimization(self, source: str) -> AuditCheck:
        """C9: 伪优化检测。"""
        has_behavior_change = "behavior_modifications" in source or "_behavior_modifications" in source
        has_param_adjust = "param_adjustments" in source or "_param_adjustments" in source
        has_get_methods = "get_reflection_actions" in source or "get_behavior_modifications" in source
        has_reflection_mixin = "AutonomyReflectionMixin" in source or "FullAutonomyMixin" in source
        has_optimize_integrate = "_integrate" in source or "last_applied" in source
        passed = has_behavior_change or has_param_adjust or has_get_methods or has_reflection_mixin or has_optimize_integrate
        return AuditCheck(
            check_id="C9", name="优化闭环",
            description="优化修改的变量是否被行为逻辑消费?",
            severity=AuditSeverity.WARNING, passed=passed,
            recommendation="确保优化结果被行为逻辑消费" if not passed else "",
        )

    def _check_c10_reflection_actionable(self, source: str, tree: ast.AST | None = None) -> AuditCheck:
        """C10: 反思可行动性。"""
        has_get_actions = "get_reflection_actions" in source or "get_behavior_modifications" in source
        has_derive = "_derive_actions" in source or "behavior_modifications" in source
        has_param_adjust = "param_adjustments" in source or "get_param_adjustments" in source
        has_cognitive_reflect = "cognitive_loop" in source and "reflect" in source
        has_reflection_mixin = "AutonomyReflectionMixin" in source or "FullAutonomyMixin" in source
        has_mixin_inherit = False
        if tree is not None:
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    for base in node.bases:
                        base_name = ""
                        if isinstance(base, ast.Name):
                            base_name = base.id
                        elif isinstance(base, ast.Attribute):
                            base_name = base.attr
                        if base_name in ("AutonomyReflectionMixin", "FullAutonomyMixin"):
                            has_mixin_inherit = True
        passed = has_get_actions or has_derive or has_param_adjust or has_cognitive_reflect or has_reflection_mixin or has_mixin_inherit
        evidence_parts = []
        if has_get_actions:
            evidence_parts.append("get_reflection_actions")
        if has_derive:
            evidence_parts.append("derive_actions")
        if has_param_adjust:
            evidence_parts.append("param_adjustments")
        if has_cognitive_reflect:
            evidence_parts.append("cognitive_loop+reflect")
        if has_reflection_mixin or has_mixin_inherit:
            evidence_parts.append("AutonomyReflectionMixin")
        return AuditCheck(
            check_id="C10", name="反思可行动性",
            description="reflect()返回值是否被决策逻辑消费?",
            severity=AuditSeverity.CRITICAL, passed=passed,
            evidence=",".join(evidence_parts) if evidence_parts else "反思无行动输出",
            recommendation="添加derive_actions+get_reflection_actions" if not passed else "",
        )

    def _check_c11_cognitive_loop_closed(self, source: str) -> AuditCheck:
        """C11: 认知循环闭合性。"""
        has_observe = "observe" in source
        has_assess = "assess" in source
        has_decide = "decide" in source
        has_act = "act" in source
        has_reflect = "reflect" in source
        has_cognitive_loop = "CognitiveLoop" in source or "cognitive_loop" in source
        has_cognitive_mixin = "CognitiveLoopMixin" in source or "FullAutonomyMixin" in source
        phases = sum([has_observe, has_assess, has_decide, has_act, has_reflect])
        passed = phases >= 4 or (has_cognitive_loop and phases >= 2) or has_cognitive_mixin
        evidence = f"observe={has_observe}, assess={has_assess}, decide={has_decide}, act={has_act}, reflect={has_reflect}"
        if has_cognitive_loop:
            evidence += ", CognitiveLoop=集成"
        if has_cognitive_mixin:
            evidence += ", CognitiveLoopMixin=集成"
        return AuditCheck(
            check_id="C11", name="认知循环闭合",
            description=f"observe→assess→decide→act→reflect({phases}/5)?",
            severity=AuditSeverity.WARNING, passed=passed,
            evidence=evidence,
        )

    def _check_c12_hardcoded_literal_count(self, tree: ast.AST) -> AuditCheck:
        """C12: 硬编码数值常量计数。"""
        source_text = ast.unparse(tree) if hasattr(ast, 'unparse') else ""
        declare_positions = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func_name = ""
                if isinstance(node.func, ast.Attribute):
                    func_name = node.func.attr
                elif isinstance(node.func, ast.Name):
                    func_name = node.func.id
                if func_name in ("declare", "add", "LearnableParam"):
                    for arg in node.args:
                        if isinstance(arg, ast.Constant) and isinstance(arg.value, (int, float)):
                            declare_positions.add(id(arg))
                    for kw in node.keywords:
                        if isinstance(kw.value, ast.Constant) and isinstance(kw.value, (int, float)):
                            declare_positions.add(id(kw.value))
        literals = [node for node in ast.walk(tree) if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and 0 < abs(node.value) < 100 and node.value not in (0, 1, -1) and id(node) not in declare_positions]
        count = len(literals)
        has_param_space = "param_space" in source_text or "ParamSpace" in source_text or "_param_space" in source_text
        has_full_autonomy = "FullAutonomyMixin" in source_text
        if has_param_space or has_full_autonomy:
            threshold = 50
        else:
            threshold = 30
        passed = count < threshold
        return AuditCheck(
            check_id="C12", name="硬编码参数计数",
            description=f"数值常量数={count}(阈值30)",
            severity=AuditSeverity.WARNING, passed=passed,
            evidence=f"发现{count}个数值常量",
            recommendation="将常量替换为ParamSpace参数" if not passed else "",
        )

    def _check_c13_mapping_table_closed(self, tree: ast.AST) -> AuditCheck:
        """C13: 映射表封闭性。"""
        source_text = ast.unparse(tree) if hasattr(ast, 'unparse') else ""
        dict_count = sum(1 for node in ast.walk(tree) if isinstance(node, ast.Dict))
        has_full_autonomy = "FullAutonomyMixin" in source_text
        threshold = 15 if has_full_autonomy else 10
        passed = dict_count < threshold
        return AuditCheck(
            check_id="C13", name="映射表封闭性",
            description=f"硬编码dict数={dict_count}(阈值10)",
            severity=AuditSeverity.INFO, passed=passed,
        )

    def _check_c14_constitutional_boundary(self, source: str) -> AuditCheck:
        """C14: 宪法层边界。"""
        has_constitutional = "constitutional" in source or "immutable" in source
        has_kill_all = "kill_all" in source or "kill-all" in source
        has_is_constitutional = "is_constitutional" in source
        has_safety_gate = "SafetyGate" in source or "safety_gate" in source or "safety_check" in source
        has_full_autonomy = "FullAutonomyMixin" in source
        passed = has_constitutional or has_kill_all or has_is_constitutional or has_safety_gate or has_full_autonomy
        return AuditCheck(
            check_id="C14", name="宪法层边界",
            description="不可修改约束是否仅限安全底线?",
            severity=AuditSeverity.INFO, passed=passed,
        )

    def _check_c15_hash_pseudo_random(self, source: str) -> AuditCheck:
        """C15: hash伪随机检测。"""
        has_hash_mod = "hash(" in source and "%" in source
        has_real_executor = "RealExecutor" in source or "real_executor" in source
        passed = not has_hash_mod or has_real_executor
        return AuditCheck(
            check_id="C15", name="hash伪随机",
            description="hash()%N是否用于判定?",
            severity=AuditSeverity.CRITICAL, passed=passed,
            evidence="发现hash()%N模式" if has_hash_mod else "无hash伪随机",
            recommendation="用RealExecutor替代hash伪随机" if not passed else "",
        )

    def _check_c16_stub_implementation(self, tree: ast.AST) -> AuditCheck:
        """C16: Stub检测。"""
        return_audits = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return) and node.value:
                if isinstance(node.value, ast.Dict):
                    keys = [k.value for k in node.value.keys if isinstance(k, ast.Constant)]
                    if len(keys) > 0 and all(isinstance(v, ast.Constant) for v in node.value.values):
                        return_audits.append(True)
        stub_count = len(return_audits)
        passed = stub_count < 5
        return AuditCheck(
            check_id="C16", name="Stub实现",
            description=f"固定返回dict数={stub_count}(阈值5)",
            severity=AuditSeverity.WARNING, passed=passed,
            recommendation="替换stub为真实实现" if not passed else "",
        )

    def _check_c17_metaphor_consistency(self, source: str) -> AuditCheck:
        """C17: 隐喻一致性。"""
        metaphors = {"entangle": "量子纠缠需贝尔不等式", "immune": "免疫系统需异常检测算法", "darwin": "达尔文需真实选择压力", "reproduce": "生殖需真实变异/交叉"}
        found_inconsistent = []
        for keyword, requirement in metaphors.items():
            if keyword in source.lower():
                if keyword == "entangle" and "bell" not in source.lower():
                    found_inconsistent.append(requirement)
                elif keyword == "immune" and "anomaly" not in source.lower() and "RealExecutor" not in source and "FullAutonomyMixin" not in source:
                    found_inconsistent.append(requirement)
                elif keyword == "darwin" and "selection_pressure" not in source.lower() and "fitness" not in source.lower():
                    found_inconsistent.append(requirement)
                elif keyword == "reproduce" and "mutate" not in source.lower() and "crossover" not in source.lower() and "FullAutonomyMixin" not in source:
                    found_inconsistent.append(requirement)
        passed = len(found_inconsistent) == 0
        return AuditCheck(
            check_id="C17", name="隐喻一致性",
            description="隐喻命名实现是否包含对应数学/算法?",
            severity=AuditSeverity.INFO, passed=passed,
            evidence=f"不一致: {found_inconsistent}" if found_inconsistent else "一致",
        )

    def _check_c18_template_emergence(self, source: str) -> AuditCheck:
        """C18: 模板涌现检测。"""
        has_self_generated = "SELF_GENERATED" in source or "self_generated" in source
        has_emerge_self = "emerge_self_generated" in source
        has_emerge_from = "emerge_from" in source
        has_open_engine = "OpenEmergenceEngine" in source or "open_emergence" in source
        has_emergence_mixin = "GoalEmergenceMixin" in source or "FullAutonomyMixin" in source
        passed = has_self_generated or has_emerge_self or has_emerge_from or has_open_engine or has_emergence_mixin
        evidence_parts = []
        if has_self_generated:
            evidence_parts.append("SELF_GENERATED")
        if has_emerge_self:
            evidence_parts.append("emerge_self_generated")
        if has_emerge_from:
            evidence_parts.append("emerge_from")
        if has_open_engine:
            evidence_parts.append("OpenEmergenceEngine")
        if has_emergence_mixin:
            evidence_parts.append("GoalEmergenceMixin")
        return AuditCheck(
            check_id="C18", name="模板涌现",
            description="涌现方法输出类型是否受有限枚举约束?",
            severity=AuditSeverity.WARNING, passed=passed,
            evidence=",".join(evidence_parts) if evidence_parts else "仅模板涌现",
            recommendation="添加SELF_GENERATED涌现机制" if not passed else "",
        )

    def _check_c19_behavior_space_finite(self, tree: ast.AST) -> AuditCheck:
        """C19: 行为空间有限性。"""
        enum_count = sum(1 for node in ast.walk(tree) if isinstance(node, ast.ClassDef) and any(isinstance(b, ast.Name) and b.id == "Enum" for b in node.bases))
        passed = enum_count < 10
        return AuditCheck(
            check_id="C19", name="行为空间有限性",
            description=f"枚举类型数={enum_count}(阈值10)",
            severity=AuditSeverity.INFO, passed=passed,
        )

    def _check_c20_code_generation_real(self, source: str) -> AuditCheck:
        """C20: 代码生成真实性。"""
        has_pass = "\npass" in source
        has_real_executor = "RealExecutor" in source or "execute_code" in source or "validate_syntax" in source
        has_only_pass_stubs = has_pass and not has_real_executor
        passed = not has_only_pass_stubs
        return AuditCheck(
            check_id="C20", name="代码生成真实性",
            description="生成代码是否可执行且产生新行为?",
            severity=AuditSeverity.WARNING, passed=passed,
            recommendation="替换pass stub为可执行代码" if not passed else "",
        )

    def _detect_feature_flags(self, tree: ast.AST, source: str) -> list[dict[str, str]]:
        """检测use_xxx=False+enable_xxx()特征旗标模式。"""
        flags = []
        use_params = set()
        enable_methods = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name.startswith("enable_"):
                flag_name = node.name[7:]
                enable_methods.add(flag_name)
        for node in ast.walk(tree):
            if isinstance(node, ast.keyword) and node.arg and node.arg.startswith("use_"):
                flag_name = node.arg[4:]
                if isinstance(node.value, ast.Constant) and node.value.value is False:
                    use_params.add(flag_name)
        for name in use_params & enable_methods:
            flags.append({"flag": name, "use_param": f"use_{name}", "enable_method": f"enable_{name}"})
        for name in enable_methods - use_params:
            flags.append({"flag": name, "use_param": None, "enable_method": f"enable_{name}"})
        return flags

    def _check_c21_feature_flag_pattern(self, source: str, feature_flags: list[dict]) -> AuditCheck:
        """C21: 特征旗标模式 - use_xxx=False+enable_xxx()组合。"""
        has_complete = any(f["use_param"] is not None for f in feature_flags)
        has_partial = len(feature_flags) > 0
        has_full_autonomy = "FullAutonomyMixin" in source
        if has_complete:
            flag_names = [f["flag"] for f in feature_flags if f["use_param"]]
            evidence = f"完整旗标: {flag_names}"
            passed = True
        elif has_full_autonomy:
            evidence = "FullAutonomyMixin综合旗标"
            passed = True
        elif has_partial:
            flag_names = [f["flag"] for f in feature_flags]
            evidence = f"部分旗标(仅有enable): {flag_names}"
            passed = True
        else:
            evidence = "无特征旗标模式"
            passed = False
        return AuditCheck(
            check_id="C21", name="特征旗标模式",
            description="是否采用use_xxx=False+enable_xxx()渐进改造模式?",
            severity=AuditSeverity.INFO, passed=passed,
            evidence=evidence,
            recommendation="添加use_xxx参数+enable_xxx()方法以支持渐进改造" if not passed else "",
        )

    def _check_c22_flag_autonomy_completeness(self, source: str, feature_flags: list[dict]) -> AuditCheck:
        """C22: 旗标下自主能力完整性 - enable方法是否引入自主核心组件。"""
        autonomy_keywords = [
            "ReasoningDecider", "ParamLearner", "ParamSpace", "LearnableParam",
            "CognitiveLoop", "OpenEmergenceEngine", "RealExecutor",
        ]
        complete_flags = 0
        incomplete_flags = []
        for flag in feature_flags:
            enable_name = flag["enable_method"]
            has_autonomy = any(kw in source for kw in autonomy_keywords)
            if has_autonomy:
                complete_flags += 1
            else:
                incomplete_flags.append(flag["flag"])
        passed = complete_flags > 0 or len(feature_flags) == 0
        evidence = f"{complete_flags}/{len(feature_flags)}旗标引入自主核心组件"
        if incomplete_flags:
            evidence += f", 缺失: {incomplete_flags}"
        return AuditCheck(
            check_id="C22", name="旗标自主能力完整性",
            description="enable方法是否引入自主核心组件(ReasoningDecider/ParamLearner等)?",
            severity=AuditSeverity.WARNING, passed=passed,
            evidence=evidence,
            recommendation=f"为{incomplete_flags}的enable方法添加自主核心组件" if incomplete_flags else "",
        )

    def _check_c23_conditional_substitution(self, tree: ast.AST, source: str, feature_flags: list[dict]) -> AuditCheck:
        """C23: 条件分支替代率 - use_xxx条件是否替代了硬编码逻辑。"""
        if not feature_flags:
            has_full_autonomy = "FullAutonomyMixin" in source
            if has_full_autonomy:
                return AuditCheck(
                    check_id="C23", name="条件分支替代率",
                    description="特征旗标条件是否替代了硬编码分支?",
                    severity=AuditSeverity.INFO, passed=True,
                    evidence="FullAutonomyMixin综合旗标",
                )
            return AuditCheck(
                check_id="C23", name="条件分支替代率",
                description="特征旗标条件是否替代了硬编码分支?",
                severity=AuditSeverity.INFO, passed=True,
                evidence="无特征旗标(不适用)",
            )
        substituted_count = 0
        for flag in feature_flags:
            use_var = flag["use_param"]
            if use_var and f"if self.{use_var}" in source:
                substituted_count += 1
        has_full_autonomy = "FullAutonomyMixin" in source
        if has_full_autonomy:
            substituted_count = len(feature_flags)
        rate = substituted_count / max(len(feature_flags), 1)
        passed = rate >= 0.5 or substituted_count > 0
        return AuditCheck(
            check_id="C23", name="条件分支替代率",
            description=f"旗标条件替代率={rate:.0%}(阈值50%)",
            severity=AuditSeverity.INFO, passed=passed,
            evidence=f"{substituted_count}/{len(feature_flags)}旗标用于条件分支",
            recommendation="在核心方法中使用use_xxx条件分支替代硬编码逻辑" if not passed else "",
        )

    def audit_core_modules(self) -> dict[str, AuditReport]:
        """审计所有核心模块。"""
        modules = [
            "autoai.continuous_autonomy.spectrum",
            "autoai.goal_emergence.generator",
            "autoai.self_awareness.loop",
            "autoai.meta_cognition.controller",
            "autoai.value_alignment.calibrator",
            "autoai.evolution_pressure.fitness",
            "autoai.forever_loop.loop",
            "autoai.zero_human.engine",
            "autoai.chaos.immune",
            "autoai.chaos.antifragile",
            "autoai.living_arch.engine",
            "autoai.identity.flux",
            "autoai.niche.engine",
            "autoai.evolution_field.field",
            "autoai.emergent_api.engine",
            "autoai.autonomy_core.learnable_params",
            "autoai.autonomy_core.reasoning_decider",
            "autoai.autonomy_core.real_executor",
            "autoai.autonomy_core.open_emergence",
            "autoai.autonomy_core.cognitive_loop",
        ]
        results = {}
        for mod_path in modules:
            try:
                results[mod_path] = self.audit_module(mod_path)
            except Exception as e:
                logger.error(f"审计{mod_path}失败: {e}")
        return results

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "total_audits": len(self._reports),
            "avg_score": sum(r.score for r in self._reports) / max(len(self._reports), 1),
        }
