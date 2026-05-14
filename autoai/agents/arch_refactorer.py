"""Architecture Self-Refactorer: Agent autonomously generates refactoring patches.

Phase 18.2: Based on ArchReport from ArchDiagnoser, generates:
  - Module merge patches (coupling hotspots → facade extraction)
  - Module split patches (god modules → focused sub-modules)
  - Lazy import patches (circular imports → deferred imports)
  - Dead code removal patches
  - Interface unification patches

All patches go through SelfModifyPipeline for safe apply→test→commit flow.
"""

from __future__ import annotations

import re
import textwrap
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from autoai.agents.arch_diagnoser import (
    ArchIssue,
    ArchIssueType,
    ArchReport,
    Severity,
)
from autoai.logs import logger


@dataclass
class RefactorPlan:
    issue: ArchIssue
    patch_diff: str
    target_files: list[str]
    estimated_risk: float = 0.5
    description: str = ""


@dataclass
class RefactorResult:
    plans_generated: int = 0
    plans_applied: int = 0
    plans_rejected: int = 0
    details: list[dict[str, Any]] = field(default_factory=list)


class ArchRefactorer:
    """Generates refactoring patches from 架构 diagnostic reports.

    Usage:
        refactorer = ArchRefactorer(workspace=Path("..."))
        result = refactorer.generate_plans(report)
        for plan in result:
            print(f"Patch for {plan.issue.description}: {len(plan.patch_diff)} chars")
    """

    def __init__(
        self,
        workspace: Path,
        max_risk: float = 0.7,
        auto_apply: bool = False,
    ) -> None:
        self.workspace = workspace
        self._max_risk = max_risk
        self._auto_apply = auto_apply
        self._generators = {
            ArchIssueType.CIRCULAR_IMPORT: self._gen_lazy_import_patch,
            ArchIssueType.DEAD_CODE: self._gen_dead_code_removal_patch,
            ArchIssueType.COUPLING_HOTSPOT: self._gen_facade_extraction_patch,
            ArchIssueType.PERF_BOTTLENECK: self._gen_lazy_init_patch,
            ArchIssueType.INTERFACE_MISMATCH: self._gen_interface_unify_patch,
            ArchIssueType.MISSING_PROTOCOL: self._gen_protocol_patch,
        }

    def generate_plans(self, report: ArchReport) -> list[RefactorPlan]:
        plans = []
        for issue in report.issues:
            generator = self._generators.get(issue.issue_type)
            if generator is None:
                continue
            try:
                plan = generator(issue)
                if plan is not None and plan.estimated_risk <= self._max_risk:
                    plans.append(plan)
                elif plan is not None:
                    logger.debug(f"[Arch重构] 拒绝ed pl一个(risk {plan.estimated_risk:.2f} > {self._max_risk})")
            except Exception as e:
                logger.warn(f"[ArchRefactor] Plan generation failed for {issue.issue_type.value}: {e}")

        plans.sort(key=lambda p: p.issue.score - p.estimated_risk * 10, reverse=True)
        return plans

    async def apply_plans(
        self,
        plans: list[RefactorPlan],
        self_modify_pipeline: Any | None = None,
    ) -> RefactorResult:
        result = RefactorResult(plans_generated=len(plans))

        for plan in plans:
            if self_modify_pipeline is None or not self_modify_pipeline.can_modify:
                result.plans_rejected += 1
                result.details.append({
                    "issue": plan.issue.description,
                    "status": "skipped_no_pipeline",
                })
                continue

            try:
                from governance.modification_chain import ModificationType
                mod_result = await self_modify_pipeline.execute_modification(
                    patch_diff=plan.patch_diff,
                    target_files=plan.target_files,
                    mod_type=ModificationType.CODE_PATCH,
                )
                if mod_result.get("success"):
                    result.plans_applied += 1
                    result.details.append({
                        "issue": plan.issue.description,
                        "status": "applied",
                        "test_result": mod_result.get("test_result"),
                    })
                else:
                    result.plans_rejected += 1
                    result.details.append({
                        "issue": plan.issue.description,
                        "status": "test_failed",
                        "reverted": mod_result.get("reverted", False),
                    })
            except Exception as e:
                result.plans_rejected += 1
                result.details.append({
                    "issue": plan.issue.description,
                    "status": "error",
                    "error": str(e),
                })

        return result

    def _gen_lazy_import_patch(self, issue: ArchIssue) -> RefactorPlan | None:
        cycle = issue.context.get("cycle", [])
        if len(cycle) < 2:
            return None

        target_file = cycle[0]
        abs_path = self.workspace / target_file
        if not abs_path.exists():
            return None

        try:
            source = abs_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return None

        lines = source.split("\n")
        import_lines = []
        code_lines = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith(("import ", "from ")) and not stripped.startswith("#"):
                import_lines.append(line)
            else:
                code_lines.append(line)

        if not import_lines:
            return None

        lazy_imports = []
        remaining_imports = []
        for line in import_lines:
            if any(mod in line for mod in [Path(c).stem for c in cycle[1:]]):
                lazy_imports.append(line)
            else:
                remaining_imports.append(line)

        if not lazy_imports:
            return None

        new_source_parts = []
        new_source_parts.extend(remaining_imports)
        new_source_parts.append("")
        new_source_parts.append("# Lazy imports to break circular dependency")
        for line in lazy_imports:
            new_source_parts.append(f"# {line}  # moved to lazy import below")
        new_source_parts.append("")
        new_source_parts.extend(code_lines)

        for line in lazy_imports:
            match = re.match(r"from\s+(\S+)\s+import\s+(.+)", line)
            if match:
                module, names = match.group(1), match.group(2)
                new_source_parts.append(f"def _lazy_import_{module.replace('.', '_')}():")
                new_source_parts.append(f"    from {module} import {names}")
                new_source_parts.append(f"    return {names.split(',')[0].strip()}")
                new_source_parts.append("")
            else:
                match2 = re.match(r"import\s+(\S+)(?:\s+as\s+(\S+))?", line)
                if match2:
                    mod_name = match2.group(1)
                    alias = match2.group(2) or mod_name
                    new_source_parts.append(f"def _lazy_import_{alias.replace('.', '_')}():")
                    new_source_parts.append(f"    import {mod_name} as {alias}")
                    new_source_parts.append(f"    return {alias}")
                    new_source_parts.append("")

        patch_diff = self._make_unified_diff(target_file, source, "\n".join(new_source_parts))

        return RefactorPlan(
            issue=issue,
            patch_diff=patch_diff,
            target_files=[target_file],
            estimated_risk=0.6,
            description=f"Break circular import by lazy-loading in {Path(target_file).name}",
        )

    def _gen_dead_code_removal_patch(self, issue: ArchIssue) -> RefactorPlan | None:
        target_file = issue.location
        abs_path = self.workspace / target_file
        if not abs_path.exists():
            return None

        try:
            source = abs_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return None

        if len(source.strip()) < 50:
            patch_diff = self._make_unified_diff(target_file, source, "")
            return RefactorPlan(
                issue=issue,
                patch_diff=patch_diff,
                target_files=[target_file],
                estimated_risk=0.8,
                description=f"Remove dead module {Path(target_file).name}",
            )

        return RefactorPlan(
            issue=issue,
            patch_diff=f"# Dead code detected in {target_file}\n# Manual review recommended\n",
            target_files=[target_file],
            estimated_risk=0.9,
            description=f"Flag dead code in {Path(target_file).name} for manual review",
        )

    def _gen_facade_extraction_patch(self, issue: ArchIssue) -> RefactorPlan | None:
        target_file = issue.location
        module_stem = Path(target_file).stem
        if module_stem == "__init__":
            module_stem = Path(target_file).parent.name

        facade_content = textwrap.dedent(f'''\
            """Facade module for {module_stem} - reduces coupling.

            Auto-generated by ArchRefactorer to consolidate access points.
            """
            from {Path(target_file).parent.as_posix().replace("/", ".")}.{module_stem} import *  # noqa: F401,F403
        ''')

        facade_path = str(Path(target_file).parent / f"{module_stem}_facade.py")
        patch_diff = f"--- /dev/null\n+++ {facade_path}\n@@ -0,0 +1,{len(facade_content.splitlines())} @@\n"
        for line in facade_content.splitlines():
            patch_diff += f"+{line}\n"

        return RefactorPlan(
            issue=issue,
            patch_diff=patch_diff,
            target_files=[facade_path],
            estimated_risk=0.4,
            description=f"Extract facade for {module_stem} to reduce coupling",
        )

    def _gen_lazy_init_patch(self, issue: ArchIssue) -> RefactorPlan | None:
        target_file = issue.location
        abs_path = self.workspace / target_file
        if not abs_path.exists():
            return None

        try:
            source = abs_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return None

        lines = source.split("\n")
        new_lines = []
        moved_count = 0

        for line in lines:
            stripped = line.strip()
            if re.match(r"^[A-Z_]+\s*=\s*.+\(", stripped) and not stripped.startswith("#"):
                match = re.match(r"^([A-Z_]+)\s*=\s*(.+)$", stripped)
                if match:
                    var_name = match.group(1)
                    init_expr = match.group(2)
                    indent = len(line) - len(line.lstrip())
                    prefix = " " * indent
                    new_lines.append(f"{prefix}{var_name} = None  # lazy init")
                    new_lines.append("")
                    new_lines.append(f"{prefix}def _init_{var_name.lower()}():")
                    new_lines.append(f"{prefix}    global {var_name}")
                    new_lines.append(f"{prefix}    if {var_name} is None:")
                    new_lines.append(f"{prefix}        {var_name} = {init_expr}")
                    new_lines.append(f"{prefix}    return {var_name}")
                    moved_count += 1
                    continue
            new_lines.append(line)

        if moved_count == 0:
            return None

        new_source = "\n".join(new_lines)
        patch_diff = self._make_unified_diff(target_file, source, new_source)

        return RefactorPlan(
            issue=issue,
            patch_diff=patch_diff,
            target_files=[target_file],
            estimated_risk=0.5,
            description=f"Lazy-initialize {moved_count} module-level side effect(s) in {Path(target_file).name}",
        )

    def _gen_interface_unify_patch(self, issue: ArchIssue) -> RefactorPlan | None:
        method = issue.context.get("method", "")
        implementations = issue.context.get("implementations", [])
        if not method or not implementations:
            return None

        return RefactorPlan(
            issue=issue,
            patch_diff=f"# Interface mismatch: {method}\n# Implementations: {implementations}\n# Recommend: define Protocol/ABC with unified signature\n",
            target_files=[issue.location],
            estimated_risk=0.3,
            description=f"Unify '{method}' signature across implementations",
        )

    def _gen_protocol_patch(self, issue: ArchIssue) -> RefactorPlan | None:
        return RefactorPlan(
            issue=issue,
            patch_diff=f"# Missing protocol for {issue.location}\n# Recommend: define typing.Protocol\n",
            target_files=[issue.location],
            estimated_risk=0.2,
            description=f"Add Protocol definition for {Path(issue.location).name}",
        )

    @staticmethod
    def _make_unified_diff(filepath: str, old_content: str, new_content: str) -> str:
        old_lines = old_content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)

        diff = f"--- {filepath}\n+++ {filepath}\n"

        old_idx = 0
        new_idx = 0
        while old_idx < len(old_lines) or new_idx < len(new_lines):
            matching = 0
            while (old_idx + matching < len(old_lines) and
                   new_idx + matching < len(new_lines) and
                   old_lines[old_idx + matching] == new_lines[new_idx + matching]):
                matching += 1

            if matching > 3:
                context_before = min(3, old_idx - (old_idx - matching))
                for i in range(max(0, old_idx - 3), old_idx):
                    diff += f" {old_lines[i]}"
                old_idx += matching
                new_idx += matching
                continue

            if old_idx < len(old_lines):
                diff += f"-{old_lines[old_idx]}"
                old_idx += 1
            if new_idx < len(new_lines):
                diff += f"+{new_lines[new_idx]}"
                new_idx += 1

        return diff


__all__ = ["ArchRefactorer", "RefactorPlan", "RefactorResult"]
