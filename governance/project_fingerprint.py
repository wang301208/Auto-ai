"""Project Fingerprint: Cross-project experience migration.

Extracts a characteristic fingerprint from a project (language, framework,
scale, complexity, dependency graph), computes similarity between projects,
and migrates fix patterns from similar projects via the ExperienceStore.

Usage:
    fp1 = ProjectFingerprint.extract(Path("/project/a"))
    fp2 = ProjectFingerprint.extract(Path("/project/b"))
    similarity = fp1.similarity(fp2)
    if similarity > 0.7:
        store.migrate_from(other_store, min_confidence=0.5)
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ProjectFingerprint:
    """Characteristic fingerprint of a software project."""

    project_name: str
    languages: dict[str, float] = field(default_factory=dict)
    frameworks: list[str] = field(default_factory=list)
    file_count: int = 0
    total_lines: int = 0
    test_file_count: int = 0
    has_ci: bool = False
    has_docker: bool = False
    dependency_count: int = 0
    avg_file_length: float = 0.0
    test_ratio: float = 0.0
    complexity_score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def similarity(self, other: ProjectFingerprint) -> float:
        """Compute similarity score [0, 1] between two project fingerprints."""
        scores = []

        lang_sim = self._dict_cosine(self.languages, other.languages)
        scores.append(("language", lang_sim, 0.3))

        fw_common = set(self.frameworks) & set(other.frameworks)
        fw_union = set(self.frameworks) | set(other.frameworks)
        fw_sim = len(fw_common) / len(fw_union) if fw_union else 0.5
        scores.append(("framework", fw_sim, 0.2))

        size_sim = 1.0 - abs(math.log1p(self.file_count) - math.log1p(other.file_count)) / 10.0
        size_sim = max(0.0, size_sim)
        scores.append(("size", size_sim, 0.15))

        test_sim = 1.0 - abs(self.test_ratio - other.test_ratio)
        scores.append(("test_ratio", test_sim, 0.1))

        ci_sim = 1.0 if self.has_ci == other.has_ci else 0.5
        scores.append(("ci", ci_sim, 0.05))

        docker_sim = 1.0 if self.has_docker == other.has_docker else 0.5
        scores.append(("docker", docker_sim, 0.05))

        comp_sim = 1.0 - abs(self.complexity_score - other.complexity_score) / 10.0
        comp_sim = max(0.0, comp_sim)
        scores.append(("complexity", comp_sim, 0.15))

        return sum(s * w for _, s, w in scores)

    def _dict_cosine(self, a: dict[str, float], b: dict[str, float]) -> float:
        all_keys = set(a.keys()) | set(b.keys())
        if not all_keys:
            return 1.0
        dot = sum(a.get(k, 0.0) * b.get(k, 0.0) for k in all_keys)
        norm_a = math.sqrt(sum(v * v for v in a.values())) if a else 0.0
        norm_b = math.sqrt(sum(v * v for v in b.values())) if b else 0.0
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_name": self.project_name,
            "languages": self.languages,
            "frameworks": self.frameworks,
            "file_count": self.file_count,
            "total_lines": self.total_lines,
            "test_file_count": self.test_file_count,
            "has_ci": self.has_ci,
            "has_docker": self.has_docker,
            "dependency_count": self.dependency_count,
            "avg_file_length": self.avg_file_length,
            "test_ratio": self.test_ratio,
            "complexity_score": self.complexity_score,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ProjectFingerprint:
        return cls(
            project_name=d["project_name"],
            languages=d.get("languages", {}),
            frameworks=d.get("frameworks", []),
            file_count=d.get("file_count", 0),
            total_lines=d.get("total_lines", 0),
            test_file_count=d.get("test_file_count", 0),
            has_ci=d.get("has_ci", False),
            has_docker=d.get("has_docker", False),
            dependency_count=d.get("dependency_count", 0),
            avg_file_length=d.get("avg_file_length", 0.0),
            test_ratio=d.get("test_ratio", 0.0),
            complexity_score=d.get("complexity_score", 0.0),
            metadata=d.get("metadata", {}),
        )

    @classmethod
    def extract(cls, workspace: Path, project_name: str = "") -> ProjectFingerprint:
        """Extract fingerprint by scanning the project directory."""
        if not project_name:
            project_name = workspace.name

        languages: dict[str, float] = {}
        frameworks: list[str] = []
        file_count = 0
        total_lines = 0
        test_file_count = 0

        lang_exts = {
            ".py": "python", ".js": "javascript", ".ts": "typescript",
            ".java": "java", ".go": "go", ".rs": "rust",
            ".rb": "ruby", ".php": "php", ".c": "c", ".cpp": "cpp",
            ".cs": "csharp", ".swift": "swift", ".kt": "kotlin",
            ".scala": "scala", ".sh": "shell", ".r": "r",
        }

        skip_dirs = {
            "node_modules", ".git", "__pycache__", ".pytest_cache",
            "venv", ".venv", "dist", "build", ".tox", ".mypy_cache",
        }

        for path in workspace.rglob("*"):
            if any(skip in path.parts for skip in skip_dirs):
                continue
            if not path.is_file():
                continue

            file_count += 1
            ext = path.suffix.lower()
            lang = lang_exts.get(ext)
            if lang:
                languages[lang] = languages.get(lang, 0) + 1

            name_lower = path.name.lower()
            if "test" in name_lower or name_lower.startswith("test_"):
                test_file_count += 1

            if ext in {".py", ".js", ".ts", ".java", ".go", ".rs", ".rb", ".c", ".cpp"}:
                try:
                    lines = path.read_text(encoding="utf-8", errors="ignore").count("\n") + 1
                    total_lines += lines
                except Exception:
                    pass

        total_lang = sum(languages.values())
        if total_lang > 0:
            languages = {k: v / total_lang for k, v in languages.items()}

        has_ci = (workspace / ".github" / "workflows").is_dir() or (workspace / ".gitlab-ci.yml").is_file()
        has_docker = (workspace / "Dockerfile").is_file() or (workspace / "docker-compose.yml").is_file()

        dependency_count = 0
        for dep_file in ["requirements.txt", "Pipfile", "pyproject.toml", "package.json", "go.mod", "Cargo.toml"]:
            if (workspace / dep_file).is_file():
                dependency_count += cls._count_deps(workspace / dep_file)

        frameworks = cls._detect_frameworks(workspace, languages)

        avg_file_length = total_lines / file_count if file_count > 0 else 0.0
        test_ratio = test_file_count / file_count if file_count > 0 else 0.0
        complexity_score = math.log1p(total_lines) * (1.0 + dependency_count * 0.01) * (1.0 - test_ratio * 0.5)

        return cls(
            project_name=project_name,
            languages=languages,
            frameworks=frameworks,
            file_count=file_count,
            total_lines=total_lines,
            test_file_count=test_file_count,
            has_ci=has_ci,
            has_docker=has_docker,
            dependency_count=dependency_count,
            avg_file_length=avg_file_length,
            test_ratio=test_ratio,
            complexity_score=complexity_score,
        )

    @classmethod
    def _count_deps(cls, path: Path) -> int:
        name = path.name
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return 0
        if name == "requirements.txt":
            return len([l for l in text.splitlines() if l.strip() and not l.startswith("#")])
        if name == "package.json":
            try:
                d = json.loads(text)
                return len(d.get("dependencies", {})) + len(d.get("devDependencies", {}))
            except Exception:
                return 0
        if name == "pyproject.toml":
            return text.count("=") // 2
        return 1

    @classmethod
    def _detect_frameworks(cls, workspace: Path, languages: dict[str, float]) -> list[str]:
        fw = []
        if languages.get("python", 0) > 0.1:
            for indicator, name in [
                ("django", "django"), ("flask", "flask"), ("fastapi", "fastapi"),
                ("pydantic", "pydantic"), ("pytest", "pytest"), ("sqlalchemy", "sqlalchemy"),
            ]:
                for p in workspace.rglob("*.py"):
                    try:
                        if indicator in p.read_text(encoding="utf-8", errors="ignore").lower():
                            fw.append(name)
                            break
                    except Exception:
                        pass
        if languages.get("javascript", 0) > 0.1 or languages.get("typescript", 0) > 0.1:
            pkg = workspace / "package.json"
            if pkg.is_file():
                try:
                    d = json.loads(pkg.read_text())
                    all_deps = {**d.get("dependencies", {}), **d.get("devDependencies", {})}
                    for indicator, name in [("react", "react"), ("vue", "vue"), ("next", "nextjs"), ("express", "express")]:
                        if any(indicator in k.lower() for k in all_deps):
                            fw.append(name)
                except Exception:
                    pass
        return list(set(fw))


class ProjectRegistry:
    """Registry of known project fingerprints for cross-project migration."""

    def __init__(self, store_path: Path | None = None) -> None:
        self._projects: dict[str, ProjectFingerprint] = {}
        self._store_path = store_path
        if store_path and store_path.exists():
            self._load()

    def register(self, fp: ProjectFingerprint) -> None:
        self._projects[fp.project_name] = fp
        self._save()

    def find_similar(self, fp: ProjectFingerprint, min_similarity: float = 0.5, limit: int = 5) -> list[tuple[str, float]]:
        scored = []
        for name, other in self._projects.items():
            if name == fp.project_name:
                continue
            sim = fp.similarity(other)
            if sim >= min_similarity:
                scored.append((name, sim))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:limit]

    def get(self, project_name: str) -> ProjectFingerprint | None:
        return self._projects.get(project_name)

    @property
    def size(self) -> int:
        return len(self._projects)

    def _save(self) -> None:
        if self._store_path is None:
            return
        data = {name: fp.to_dict() for name, fp in self._projects.items()}
        self._store_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def _load(self) -> None:
        try:
            data = json.loads(self._store_path.read_text(encoding="utf-8"))
            for name, d in data.items():
                self._projects[name] = ProjectFingerprint.from_dict(d)
        except Exception:
            pass


__all__ = ["ProjectFingerprint", "ProjectRegistry"]
