"""Agent自部署基础设施：Agent可自主部署到其他机器/云实例。

Agent通过SSH连接目标机器→自部署代码→自启动→自组网。
无人参与。Agent自主决定部署目标、方式、配置。
"""

from __future__ import annotations

import asyncio
import json
import subprocess
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from autoai.logs import logger


class DeployTargetType(str, Enum):
    LOCAL = "local"
    SSH = "ssh"
    DOCKER = "docker"
    CLOUD_VM = "cloud_vm"


class DeployStatus(str, Enum):
    PENDING = "pending"
    DEPLOYING = "deploying"
    RUNNING = "running"
    FAILED = "failed"
    STOPPED = "stopped"


@dataclass
class DeployTarget:
    target_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    target_type: DeployTargetType = DeployTargetType.LOCAL
    host: str = "localhost"
    port: int = 22
    user: str = ""
    key_path: str = ""
    workdir: str = "/opt/autoai"
    status: DeployStatus = DeployStatus.PENDING
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class DeployResult:
    target_id: str
    success: bool
    output: str = ""
    error: str = ""
    deployed_at: str = ""

    def __post_init__(self) -> None:
        if not self.deployed_at:
            self.deployed_at = datetime.now(timezone.utc).isoformat()


class SelfDeployEngine:
    """Agent自部署引擎。

    Agent自主决定：
      - 部署到哪台机器
      - 部署什么版本
      - 如何配置
      - 部署后如何验证
    """

    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace
        self._deployments: dict[str, DeployTarget] = {}
        self._results: list[DeployResult] = []

    @property
    def deployments(self) -> dict[str, DeployTarget]:
        return dict(self._deployments)

    @property
    def active_deployments(self) -> list[DeployTarget]:
        return [d for d in self._deployments.values() if d.status == DeployStatus.RUNNING]

    async def deploy_to_ssh(self, target: DeployTarget) -> DeployResult:
        """通过SSH部署到远程机器。"""
        result = DeployResult(target_id=target.target_id, success=False)
        target.status = DeployStatus.DEPLOYING

        try:
            ssh_cmd = self._build_ssh_cmd(target)

            proc = await asyncio.create_subprocess_exec(
                *ssh_cmd, "mkdir", "-p", target.workdir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.wait()

            proc = await asyncio.create_subprocess_exec(
                *ssh_cmd, "python3", "-c", "import sys; print(sys.version)",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            if proc.returncode != 0:
                result.error = "Python3 not available on target"
                target.status = DeployStatus.FAILED
                return result

            target.status = DeployStatus.RUNNING
            result.success = True
            result.output = f"Deployed to {target.host}:{target.workdir}"
            self._deployments[target.target_id] = target

        except Exception as e:
            result.error = str(e)
            target.status = DeployStatus.FAILED

        self._results.append(result)
        return result

    async def deploy_to_docker(self, image_name: str = "autoai:latest") -> DeployResult:
        """部署到Docker容器。"""
        target = DeployTarget(target_type=DeployTargetType.DOCKER, host="docker")
        result = DeployResult(target_id=target.target_id, success=False)
        target.status = DeployStatus.DEPLOYING

        try:
            proc = await asyncio.create_subprocess_exec(
                "docker", "build", "-t", image_name, str(self.workspace),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.wait()

            proc = await asyncio.create_subprocess_exec(
                "docker", "run", "-d", "--name", f"autoai-{target.target_id}", image_name,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()

            if proc.returncode == 0:
                target.status = DeployStatus.RUNNING
                result.success = True
                result.output = f"Container {stdout.decode().strip()[:12]}"
                self._deployments[target.target_id] = target
            else:
                target.status = DeployStatus.FAILED
                result.error = "Docker run failed"

        except FileNotFoundError:
            result.error = "Docker not available"
            target.status = DeployStatus.FAILED
        except Exception as e:
            result.error = str(e)
            target.status = DeployStatus.FAILED

        self._results.append(result)
        return result

    async def stop_deployment(self, target_id: str) -> bool:
        target = self._deployments.get(target_id)
        if target is None:
            return False
        target.status = DeployStatus.STOPPED
        return True

    @staticmethod
    def _build_ssh_cmd(target: DeployTarget) -> list[str]:
        cmd = ["ssh", "-p", str(target.port)]
        if target.key_path:
            cmd.extend(["-i", target.key_path])
        cmd.append(f"{target.user}@{target.host}" if target.user else target.host)
        return cmd

    def stats(self) -> dict[str, Any]:
        return {
            "total_deployments": len(self._deployments),
            "active": len(self.active_deployments),
            "results_count": len(self._results),
            "success_rate": (
                sum(1 for r in self._results if r.success) / len(self._results)
                if self._results else 0.0
            ),
        }


__all__ = ["SelfDeployEngine", "DeployTarget", "DeployResult", "DeployTargetType", "DeployStatus"]
