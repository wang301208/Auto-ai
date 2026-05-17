"""
环境感知模块 - 监控系统资源、网络状态、外部事件
实现对外部环境变化的主动感知和响应机制
"""
import asyncio
import logging
import os
import platform
import shutil
import socket
import time
from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class EnvironmentEventType(Enum):
    CPU_HIGH = "cpu_high"
    MEMORY_LOW = "memory_low"
    DISK_FULL = "disk_full"
    NETWORK_DOWN = "network_down"
    NETWORK_SLOW = "network_slow"
    EXTERNAL_EVENT = "external_event"
    SYSTEM_LOAD = "system_load"


@dataclass
class EnvironmentState:
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    memory_available_gb: float = 0.0
    disk_percent: float = 0.0
    disk_free_gb: float = 0.0
    network_latency_ms: float = 0.0
    network_available: bool = True
    process_count: int = 0
    uptime_seconds: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class EnvironmentAlert:
    event_type: EnvironmentEventType
    severity: str  # "low", "medium", "high", "critical"
    message: str
    value: float
    threshold: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    suggested_action: Optional[str] = None


class EnvironmentSensor:
    def __init__(
        self,
        check_interval: float = 30.0,
        cpu_threshold: float = 80.0,
        memory_threshold: float = 20.0,
        disk_threshold: float = 10.0,
        network_timeout: float = 5.0,
        network_test_host: str = "8.8.8.8",
        network_test_port: int = 53,
    ):
        self.check_interval = check_interval
        self.cpu_threshold = cpu_threshold
        self.memory_threshold = memory_threshold
        self.disk_threshold = disk_threshold
        self.network_timeout = network_timeout
        self.network_test_host = network_test_host
        self.network_test_port = network_test_port

        self._running = False
        self._state = EnvironmentState()
        self._alerts: list[EnvironmentAlert] = []
        self._callbacks: list[Callable[[EnvironmentAlert], None]] = []
        self._start_time = time.time()
        self._history: list[EnvironmentState] = []
        self._max_history = 100

    @property
    def state(self) -> EnvironmentState:
        return self._state

    @property
    def alerts(self) -> list[EnvironmentAlert]:
        return self._alerts.copy()

    def register_callback(self, callback: Callable[[EnvironmentAlert], None]) -> None:
        self._callbacks.append(callback)

    def unregister_callback(self, callback: Callable[[EnvironmentAlert], None]) -> None:
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def _notify_callbacks(self, alert: EnvironmentAlert) -> None:
        for callback in self._callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.warning(f"EnvironmentSensor callback failed: {e}")

    def _get_cpu_percent(self) -> float:
        try:
            import psutil
            return psutil.cpu_percent(interval=0.1)
        except ImportError:
            try:
                if platform.system() == "Windows":
                    import subprocess
                    output = subprocess.check_output(
                        "wmic cpu get loadpercentage",
                        shell=True,
                        text=True
                    )
                    for line in output.strip().split("\n"):
                        if line.strip().isdigit():
                            return float(line.strip())
                return 0.0
            except Exception:
                return 0.0

    def _get_memory_info(self) -> tuple[float, float]:
        try:
            import psutil
            mem = psutil.virtual_memory()
            return mem.percent, mem.available / (1024 ** 3)
        except ImportError:
            try:
                if platform.system() == "Windows":
                    import subprocess
                    output = subprocess.check_output(
                        "wmic OS get FreePhysicalMemory,TotalVisibleMemorySize /value",
                        shell=True,
                        text=True
                    )
                    free_kb = total_kb = 0
                    for line in output.strip().split("\n"):
                        if line.startswith("FreePhysicalMemory="):
                            free_kb = int(line.split("=")[1])
                        elif line.startswith("TotalVisibleMemorySize="):
                            total_kb = int(line.split("=")[1])
                    if total_kb > 0:
                        used_percent = (total_kb - free_kb) / total_kb * 100
                        free_gb = free_kb / (1024 ** 2)
                        return used_percent, free_gb
                return 0.0, 0.0
            except Exception:
                return 0.0, 0.0

    def _get_disk_info(self) -> tuple[float, float]:
        try:
            import psutil
            disk = psutil.disk_usage(os.getcwd())
            return disk.percent, disk.free / (1024 ** 3)
        except ImportError:
            try:
                if platform.system() == "Windows":
                    import subprocess
                    drive = os.getcwd()[:2]
                    output = subprocess.check_output(
                        f"wmic logicaldisk where \"DeviceID='{drive}'\" get FreeSpace,Size",
                        shell=True,
                        text=True
                    )
                    for line in output.strip().split("\n"):
                        parts = line.strip().split()
                        if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
                            free = int(parts[0])
                            total = int(parts[1])
                            if total > 0:
                                return (total - free) / total * 100, free / (1024 ** 3)
                return 0.0, 0.0
            except Exception:
                return 0.0, 0.0

    def _check_network(self) -> tuple[bool, float]:
        try:
            start = time.time()
            sock = socket.create_connection(
                (self.network_test_host, self.network_test_port),
                timeout=self.network_timeout
            )
            latency = (time.time() - start) * 1000
            sock.close()
            return True, latency
        except Exception:
            return False, 0.0

    def _get_process_count(self) -> int:
        try:
            import psutil
            return len(psutil.pids())
        except ImportError:
            try:
                if platform.system() == "Windows":
                    import subprocess
                    output = subprocess.check_output(
                        "tasklist /nh",
                        shell=True,
                        text=True
                    )
                    return len([l for l in output.strip().split("\n") if l.strip()])
                return 0
            except Exception:
                return 0

    def check(self) -> EnvironmentState:
        cpu = self._get_cpu_percent()
        mem_percent, mem_avail = self._get_memory_info()
        disk_percent, disk_free = self._get_disk_info()
        net_ok, net_latency = self._check_network()
        proc_count = self._get_process_count()

        self._state = EnvironmentState(
            cpu_percent=cpu,
            memory_percent=mem_percent,
            memory_available_gb=mem_avail,
            disk_percent=disk_percent,
            disk_free_gb=disk_free,
            network_latency_ms=net_latency,
            network_available=net_ok,
            process_count=proc_count,
            uptime_seconds=time.time() - self._start_time,
        )

        self._history.append(self._state)
        if len(self._history) > self._max_history:
            self._history.pop(0)

        self._check_thresholds()
        return self._state

    def _check_thresholds(self) -> None:
        now = datetime.now(UTC)

        if self._state.cpu_percent > self.cpu_threshold:
            severity = "critical" if self._state.cpu_percent > 95 else "high"
            alert = EnvironmentAlert(
                event_type=EnvironmentEventType.CPU_HIGH,
                severity=severity,
                message=f"CPU使用率过高: {self._state.cpu_percent:.1f}%",
                value=self._state.cpu_percent,
                threshold=self.cpu_threshold,
                timestamp=now,
                suggested_action="考虑降低并发数或延迟非关键任务",
            )
            self._alerts.append(alert)
            self._notify_callbacks(alert)

        if self._state.memory_available_gb < self.memory_threshold:
            severity = "critical" if self._state.memory_available_gb < self.memory_threshold / 2 else "high"
            alert = EnvironmentAlert(
                event_type=EnvironmentEventType.MEMORY_LOW,
                severity=severity,
                message=f"可用内存不足: {self._state.memory_available_gb:.2f}GB",
                value=self._state.memory_available_gb,
                threshold=self.memory_threshold,
                timestamp=now,
                suggested_action="释放缓存或减少内存密集型任务",
            )
            self._alerts.append(alert)
            self._notify_callbacks(alert)

        if self._state.disk_free_gb < self.disk_threshold:
            severity = "critical" if self._state.disk_free_gb < self.disk_threshold / 2 else "high"
            alert = EnvironmentAlert(
                event_type=EnvironmentEventType.DISK_FULL,
                severity=severity,
                message=f"磁盘空间不足: {self._state.disk_free_gb:.2f}GB",
                value=self._state.disk_free_gb,
                threshold=self.disk_threshold,
                timestamp=now,
                suggested_action="清理临时文件或归档旧数据",
            )
            self._alerts.append(alert)
            self._notify_callbacks(alert)

        if not self._state.network_available:
            alert = EnvironmentAlert(
                event_type=EnvironmentEventType.NETWORK_DOWN,
                severity="critical",
                message="网络不可用",
                value=0,
                threshold=1,
                timestamp=now,
                suggested_action="检查网络连接，启用离线模式",
            )
            self._alerts.append(alert)
            self._notify_callbacks(alert)

        if self._alerts:
            self._alerts = [a for a in self._alerts if (now - a.timestamp).total_seconds() < 300]

    def get_health_score(self) -> float:
        score = 100.0

        if self._state.cpu_percent > self.cpu_threshold:
            score -= min(30, (self._state.cpu_percent - self.cpu_threshold) / 2)

        if self._state.memory_available_gb < self.memory_threshold:
            score -= min(30, (self.memory_threshold - self._state.memory_available_gb) * 3)

        if self._state.disk_free_gb < self.disk_threshold:
            score -= min(20, (self.disk_threshold - self._state.disk_free_gb) * 2)

        if not self._state.network_available:
            score -= 20

        return max(0, score)

    def should_throttle(self) -> tuple[bool, str]:
        if self._state.cpu_percent > 90:
            return True, "cpu_high"
        if self._state.memory_available_gb < self.memory_threshold / 2:
            return True, "memory_low"
        if not self._state.network_available:
            return True, "network_down"
        return False, ""

    async def start_monitoring(self) -> None:
        self._running = True
        logger.info("[EnvironmentSensor] Starting monitoring")

        while self._running:
            try:
                self.check()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"[EnvironmentSensor] Check failed: {e}")
                await asyncio.sleep(self.check_interval)

    def stop_monitoring(self) -> None:
        self._running = False
        logger.info("[EnvironmentSensor] Stopped monitoring")

    def get_report(self) -> dict[str, Any]:
        return {
            "state": {
                "cpu_percent": self._state.cpu_percent,
                "memory_percent": self._state.memory_percent,
                "memory_available_gb": self._state.memory_available_gb,
                "disk_percent": self._state.disk_percent,
                "disk_free_gb": self._state.disk_free_gb,
                "network_latency_ms": self._state.network_latency_ms,
                "network_available": self._state.network_available,
                "process_count": self._state.process_count,
                "uptime_seconds": self._state.uptime_seconds,
            },
            "health_score": self.get_health_score(),
            "alert_count": len(self._alerts),
            "recent_alerts": [
                {
                    "type": a.event_type.value,
                    "severity": a.severity,
                    "message": a.message,
                    "suggested_action": a.suggested_action,
                }
                for a in self._alerts[-5:]
            ],
            "should_throttle": self.should_throttle(),
        }
