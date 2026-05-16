"""自文档引擎: Agent自主生成和维护自己的文档。"""

from __future__ import annotations

import time
import logging
from dataclasses import dataclass, field
from typing import Any
from enum import Enum

logger = logging.getLogger(__name__)


class DocType(Enum):
    API = "api"
    ARCHITECTURE = "architecture"
    RUNBOOK = "runbook"
    CHANGELOG = "changelog"
    TROUBLESHOOTING = "troubleshooting"
    CAPABILITY = "capability"


class DocStatus(Enum):
    DRAFT = "draft"
    CURRENT = "current"
    STALE = "stale"
    ARCHIVED = "archived"


@dataclass
class DocSpec:
    """文档规格: 需要生成什么文档。"""
    spec_id: str
    doc_type: DocType
    target: str
    audience: str = "developer"
    sections: list[str] = field(default_factory=list)
    freshness_threshold_hours: float = 24.0
    created_at: float = field(default_factory=time.time)


@dataclass
class DocArtifact:
    """文档产物: 生成的文档内容。"""
    artifact_id: str
    spec_id: str
    doc_type: DocType
    target: str
    content: str = ""
    sections: dict[str, str] = field(default_factory=dict)
    status: DocStatus = DocStatus.CURRENT
    token_count: int = 0
    generated_at: float = field(default_factory=time.time)
    last_verified_at: float = 0.0

    @property
    def is_stale(self) -> bool:
        age = time.time() - self.generated_at
        return age > 86400

    @property
    def completeness(self) -> float:
        if not self.sections:
            return 0.0 if not self.content else 1.0
        filled = sum(1 for v in self.sections.values() if v.strip())
        return filled / len(self.sections)


class SelfDocEngine:
    """自文档引擎: Agent自主写文档。"""

    def __init__(self, agent_id: str = "default"):
        self._agent_id = agent_id
        self._specs: dict[str, DocSpec] = {}
        self._artifacts: dict[str, DocArtifact] = {}
        self._total_generated: int = 0
        self._total_stale: int = 0

    def generate_doc(self, target: str, doc_type: DocType = DocType.API, sections: list[str] | None = None) -> DocArtifact:
        """生成文档。"""
        self._total_generated += 1
        spec_id = f"dspec_{self._total_generated}"
        default_sections = {
            DocType.API: ["概述", "接口", "参数", "返回值", "示例", "错误码"],
            DocType.ARCHITECTURE: ["组件", "依赖", "数据流", "部署", "扩展点"],
            DocType.RUNBOOK: ["启动", "停止", "监控", "告警", "故障排除"],
            DocType.CHANGELOG: ["版本", "变更", "迁移", "废弃"],
            DocType.TROUBLESHOOTING: ["症状", "根因", "修复", "预防"],
            DocType.CAPABILITY: ["能力", "前提", "接口", "限制", "演进"],
        }
        spec = DocSpec(
            spec_id=spec_id,
            doc_type=doc_type,
            target=target,
            sections=sections or default_sections.get(doc_type, ["概述"]),
        )
        self._specs[spec_id] = spec
        artifact_id = f"dart_{self._total_generated}"
        content_sections = {}
        for section in spec.sections:
            content_sections[section] = self._generate_section(target, section, doc_type)
        full_content = self._assemble(target, content_sections, doc_type)
        artifact = DocArtifact(
            artifact_id=artifact_id,
            spec_id=spec_id,
            doc_type=doc_type,
            target=target,
            content=full_content,
            sections=content_sections,
            token_count=len(full_content.split()),
            generated_at=time.time(),
        )
        self._artifacts[artifact_id] = artifact
        return artifact

    def _generate_section(self, target: str, section: str, doc_type: DocType) -> str:
        templates = {
            "概述": f"{target} 模块概述。\n\n本模块提供 {target} 的核心功能。",
            "接口": f"### {target} 接口\n\n```python\nfrom autoai.{target} import *\n```\n\n主要公开类和函数参见下方。",
            "参数": f"### 参数说明\n\n| 参数 | 类型 | 必需 | 说明 |\n|------|------|------|------|\n| config | dict | 否 | 配置选项 |",
            "返回值": f"### 返回值\n\n返回操作结果对象，包含 status 和 data 字段。",
            "示例": f"### 示例\n\n```python\nfrom autoai.{target} import *\nresult = execute()\n```",
            "错误码": "### 错误码\n\n| 错误 | 说明 |\n|------|------|\n| ValueError | 参数无效 |",
            "组件": f"### 组件\n\n- {target}: 核心引擎\n- 配置: 运行时配置",
            "依赖": f"### 依赖\n\n- autoai.core: 核心基础设施",
            "数据流": f"### 数据流\n\n输入 -> {target}处理 -> 输出",
            "能力": f"### 能力\n\n{target} 提供以下能力:\n- 核心处理\n- 自动优化",
            "演进": f"### 演进\n\n{target} 的技术达尔文路径:\n- 当前: 基础实现\n- 目标: 自主进化",
        }
        return templates.get(section, f"### {section}\n\n{target} 的{section}信息。")

    def _assemble(self, target: str, sections: dict[str, str], doc_type: DocType) -> str:
        parts = [f"# {target} - {doc_type.value}文档\n"]
        for title, content in sections.items():
            parts.append(content)
            parts.append("")
        return "\n".join(parts)

    def check_freshness(self) -> list[str]:
        """检查文档新鲜度。"""
        stale = []
        for aid, artifact in self._artifacts.items():
            if artifact.is_stale and artifact.status == DocStatus.CURRENT:
                artifact.status = DocStatus.STALE
                stale.append(aid)
                self._total_stale += 1
        return stale

    def regenerate_stale(self) -> int:
        """重新生成过时文档。"""
        stale = self.check_freshness()
        regenerated = 0
        for aid in stale:
            artifact = self._artifacts.get(aid)
            if not artifact:
                continue
            spec = self._specs.get(artifact.spec_id)
            if not spec:
                continue
            new_artifact = self.generate_doc(spec.target, spec.doc_type, spec.sections)
            artifact.status = DocStatus.ARCHIVED
            regenerated += 1
        return regenerated

    def get_artifact(self, artifact_id: str) -> DocArtifact | None:
        return self._artifacts.get(artifact_id)

    @property
    def stats(self) -> dict[str, Any]:
        current = sum(1 for a in self._artifacts.values() if a.status == DocStatus.CURRENT)
        avg_completeness = (
            sum(a.completeness for a in self._artifacts.values()) / len(self._artifacts)
            if self._artifacts else 0.0
        )
        return {
            "agent_id": self._agent_id,
            "total_generated": self._total_generated,
            "current_docs": current,
            "stale_docs": self._total_stale,
            "avg_completeness": avg_completeness,
            "total_tokens": sum(a.token_count for a in self._artifacts.values()),
        }
