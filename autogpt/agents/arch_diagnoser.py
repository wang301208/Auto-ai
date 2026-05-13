"""Architecture Self-Diagnoser: Agent autonomously scans its own code architecture.

Phase 18.1: Scans for structural defects:
  - Circular imports (module dependency graph cycle detection)
  - Dead code (unreachable modules, unused exports)
  - Interface inconsistencies (mismatched method signatures, missing protocols)
  - Performance bottlenecks (heavy __init__, module-level side effects)
  - Coupling hotspots (modules imported by too many others)

All findings are scored by severity and recorded to the ModificationChain.
"""

from __future__ import annotations

import ast
import importlib.util
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from autogpt.logs import logger


class ArchIssueType(Enum):
    CIRCULAR_IMPORT = "circular_import"
    DEAD_CODE = "dead_code"
    INTERFACE_MISMATCH = "interface_mismatch"
    PERF_BOTTLENECK = "perf_bottleneck"
    COUPLING_HOTSPOT = "coupling_hotspot"
    MISSING_PROTOCOL = "missing_protocol"


class Severity(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class ArchIssue:
    issue_type: ArchIssueType
    severity: Severity
    location: str
    description: str
    suggestion: str = ""
    context: dict[str, Any] = field(default_factory=dict)

    @property
    def score(self) -> int:
        return self.severity.value


@dataclass
class ModuleInfo:
    path: str
    imports: list[str] = field(default_factory=list)
    exports: list[str] = field(default_factory=list)
    classes: list[str] = field(default_factory=list)
    functions: list[str] = field(default_factory=list)
    has_side_effects: bool = False
    import_count_by_others: int = 0


class ArchDiagnoser:
    """Scans project architecture and produces a diagnostic report.

    Usage:
        diagnoser = ArchDiagnoser(workspace=Path("G:/项目/AutoGPT-0.4.7"))
        report = diagnoser.diagnose()
        for issue in report.issues:
            print(f"[{issue.severity.name}] {issue.issue_type.value}: {issue.description}")
    """

    def __init__(
        self,
        workspace: Path,
        scan_dirs: list[str] | None = None,
        ignore_dirs: list[str] | None = None,
        coupling_threshold: int = 10,
    ) -> None:
        self.workspace = workspace
        self._scan_dirs = scan_dirs or ["autogpt", "governance", "algorithm_library"]
        self._ignore_dirs = ignore_dirs or ["__pycache__", ".git", "node_modules", ".venv"]
        self._coupling_threshold = coupling_threshold
        self._modules: dict[str, ModuleInfo] = {}
        self._import_graph: dict[str, set[str]] = defaultdict(set)

    def diagnose(self) -> ArchReport:
        self._modules.clear()
        self._import_graph.clear()

        self._scan_all_modules()
        self._build_import_graph()

        issues: list[ArchIssue] = []
        issues.extend(self._detect_circular_imports())
        issues.extend(self._detect_dead_code())
        issues.extend(self._detect_coupling_hotspots())
        issues.extend(self._detect_perf_bottlenecks())
        issues.extend(self._detect_interface_mismatches())

        issues.sort(key=lambda i: i.score, reverse=True)

        return ArchReport(
            workspace=str(self.workspace),
            modules_scanned=len(self._modules),
            issues=issues,
            import_graph=dict(self._import_graph),
        )

    def _scan_all_modules(self) -> None:
        for scan_dir in self._scan_dirs:
            base = self.workspace / scan_dir
            if not base.exists():
                continue
            for py_file in base.rglob("*.py"):
                rel = str(py_file.relative_to(self.workspace))
                if any(ignore in rel for ignore in self._ignore_dirs):
                    continue
                info = self._parse_module(py_file, rel)
                self._modules[rel] = info

    def _parse_module(self, path: Path, rel_path: str) -> ModuleInfo:
        info = ModuleInfo(path=rel_path)
        try:
            source = path.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(source, filename=str(path))
        except SyntaxError:
            return info
        except Exception:
            return info

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    info.imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    info.imports.append(node.module)
            elif isinstance(node, ast.ClassDef):
                info.classes.append(node.name)
                info.exports.append(node.name)
            elif isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                info.functions.append(node.name)
                if not node.name.startswith("_"):
                    info.exports.append(node.name)

        if self._has_module_side_effects(tree):
            info.has_side_effects = True

        return info

    @staticmethod
    def _has_module_side_effects(tree: ast.Module) -> bool:
        for node in tree.body:
            if isinstance(node, (ast.Expr, ast.Assign, ast.AugAssign)):
                if isinstance(getattr(node, "value", None), ast.Call):
                    return True
            if isinstance(node, ast.Call):
                return True
        return False

    def _build_import_graph(self) -> None:
        for rel_path, info in self._modules.items():
            for imp in info.imports:
                for other_rel, other_info in self._modules.items():
                    module_name = other_rel.replace("/", ".").replace("\\", ".").replace(".py", "")
                    if module_name.endswith(".__init__"):
                        module_name = module_name[:-9]
                    if imp == module_name or module_name.startswith(imp + "."):
                        self._import_graph[rel_path].add(other_rel)
                        other_info.import_count_by_others += 1
                        break

    def _detect_circular_imports(self) -> list[ArchIssue]:
        issues = []
        visited: set[str] = set()
        in_stack: set[str] = set()
        cycles: list[list[str]] = []

        def dfs(node: str, path: list[str]) -> None:
            if node in in_stack:
                cycle_start = path.index(node)
                cycle = path[cycle_start:] + [node]
                normalized = tuple(sorted(cycle[:-1]))
                if normalized not in {tuple(sorted(c[:-1])) for c in cycles}:
                    cycles.append(cycle)
                return
            if node in visited:
                return
            visited.add(node)
            in_stack.add(node)
            path.append(node)
            for neighbor in self._import_graph.get(node, set()):
                dfs(neighbor, path)
            path.pop()
            in_stack.discard(node)

        for mod in self._modules:
            if mod not in visited:
                dfs(mod, [])

        for cycle in cycles:
            cycle_str = " → ".join(Path(c).name for c in cycle)
            issues.append(ArchIssue(
                issue_type=ArchIssueType.CIRCULAR_IMPORT,
                severity=Severity.CRITICAL,
                location=cycle[0],
                description=f"Circular import: {cycle_str}",
                suggestion="Break the cycle by extracting shared logic to a third module or using lazy imports",
                context={"cycle": cycle},
            ))

        return issues

    def _detect_dead_code(self) -> list[ArchIssue]:
        issues = []
        imported_by_someone = set()
        for deps in self._import_graph.values():
            imported_by_someone.update(deps)

        for rel_path, info in self._modules.items():
            if rel_path.endswith("__init__.py"):
                continue
            if rel_path in imported_by_someone:
                continue
            if info.import_count_by_others > 0:
                continue
            if len(info.exports) == 0 and len(info.functions) == 0:
                issues.append(ArchIssue(
                    issue_type=ArchIssueType.DEAD_CODE,
                    severity=Severity.LOW,
                    location=rel_path,
                    description=f"Module with no exports and not imported by anyone",
                    suggestion="Consider removing this module or marking as a script entry point",
                ))

        return issues

    def _detect_coupling_hotspots(self) -> list[ArchIssue]:
        issues = []
        for rel_path, info in self._modules.items():
            if info.import_count_by_others >= self._coupling_threshold:
                severity = Severity.HIGH if info.import_count_by_others >= self._coupling_threshold * 2 else Severity.MEDIUM
                issues.append(ArchIssue(
                    issue_type=ArchIssueType.COUPLING_HOTSPOT,
                    severity=severity,
                    location=rel_path,
                    description=f"Module imported by {info.import_count_by_others} others (threshold: {self._coupling_threshold})",
                    suggestion="Split into smaller, more focused modules or introduce a facade",
                    context={"import_count": info.import_count_by_others},
                ))
        return issues

    def _detect_perf_bottlenecks(self) -> list[ArchIssue]:
        issues = []
        for rel_path, info in self._modules.items():
            if info.has_side_effects:
                issues.append(ArchIssue(
                    issue_type=ArchIssueType.PERF_BOTTLENECK,
                    severity=Severity.MEDIUM,
                    location=rel_path,
                    description="Module-level side effects detected (calls at import time)",
                    suggestion="Move initialization into functions/classes, use lazy initialization",
                ))
        return issues

    def _detect_interface_mismatches(self) -> list[ArchIssue]:
        issues = []
        class_methods: dict[str, dict[str, list[str]]] = {}

        for rel_path, info in self._modules.items():
            try:
                source = (self.workspace / rel_path).read_text(encoding="utf-8", errors="ignore")
                tree = ast.parse(source)
            except Exception:
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    methods = {}
                    for item in node.body:
                        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            arg_names = [a.arg for a in item.args.args if a.arg != "self"]
                            methods[item.name] = arg_names
                    class_methods[f"{rel_path}:{node.name}"] = methods

        base_classes: dict[str, list[str]] = defaultdict(list)
        for full_name, methods in class_methods.items():
            for method_name in methods:
                base_classes[method_name].append(full_name)

        for method_name, implementations in base_classes.items():
            if len(implementations) < 2:
                continue
            signatures = [tuple(class_methods[impl][method_name]) for impl in implementations]
            if len(set(signatures)) > 1:
                impl_summary = []
                for impl, sig in zip(implementations, signatures):
                    impl_summary.append(f"{impl.split(':')[-1]}({', '.join(sig)})")
                issues.append(ArchIssue(
                    issue_type=ArchIssueType.INTERFACE_MISMATCH,
                    severity=Severity.MEDIUM,
                    location=implementations[0],
                    description=f"Method '{method_name}' has inconsistent signatures across implementations",
                    suggestion="Unify method signatures or use Protocol/ABC to enforce consistency",
                    context={"method": method_name, "implementations": impl_summary},
                ))

        return issues


@dataclass
class ArchReport:
    workspace: str
    modules_scanned: int
    issues: list[ArchIssue]
    import_graph: dict[str, set[str]] = field(default_factory=dict)

    @property
    def total_score(self) -> int:
        return sum(i.score for i in self.issues)

    @property
    def critical_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.CRITICAL)

    @property
    def by_type(self) -> dict[ArchIssueType, list[ArchIssue]]:
        result: dict[ArchIssueType, list[ArchIssue]] = defaultdict(list)
        for i in self.issues:
            result[i.issue_type].append(i)
        return result

    def summary(self) -> dict[str, Any]:
        return {
            "workspace": self.workspace,
            "modules_scanned": self.modules_scanned,
            "total_issues": len(self.issues),
            "critical": self.critical_count,
            "total_score": self.total_score,
            "by_type": {t.value: len(v) for t, v in self.by_type.items()},
        }


__all__ = ["ArchDiagnoser", "ArchReport", "ArchIssue", "ArchIssueType", "Severity"]
