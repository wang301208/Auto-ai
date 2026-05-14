"""Tests for sandbox and distributed execution modules."""

import asyncio
import os
import pytest
import time


# ======================================================================
# Sandbox Tests
# ======================================================================

class TestSandboxConfig:
    def test_default_config(self):
        from autoai.sandbox.base import SandboxConfig
        config = SandboxConfig()
        assert config.enabled
        assert "read_file" in config.allowed_commands
        assert "execute_shell" in config.denied_commands

    def test_command_allowed(self):
        from autoai.sandbox.base import SandboxConfig
        config = SandboxConfig()
        assert config.is_command_allowed("read_file")
        assert not config.is_command_allowed("execute_shell")
        assert not config.is_command_allowed("unknown_command")

    def test_path_allowed_workspace(self):
        from autoai.sandbox.base import SandboxConfig
        config = SandboxConfig(workspace_dir="/tmp/workspace")
        assert config.is_path_allowed("/tmp/workspace/file.txt")
        assert not config.is_path_allowed("/etc/passwd")

    def test_path_denied_system(self):
        from autoai.sandbox.base import SandboxConfig
        config = SandboxConfig()
        if os.name != "nt":
            assert not config.is_path_allowed("/etc/shadow")
        else:
            assert not config.is_path_allowed("C:\\Windows\\System32")

    def test_custom_allowed_paths(self):
        from autoai.sandbox.base import SandboxConfig
        config = SandboxConfig(
            allowed_paths={"/tmp/safe"},
            denied_paths=set(),
            workspace_dir="",
        )
        assert config.is_path_allowed("/tmp/safe/file.txt")


class TestSandboxResult:
    def test_success_result(self):
        from autoai.sandbox.base import SandboxResult
        result = SandboxResult(success=True, output="hello", exit_code=0)
        assert result.success
        assert not result.has_violations

    def test_violation_result(self):
        from autoai.sandbox.base import SandboxResult, SandboxViolation, ViolationType
        v = SandboxViolation(type=ViolationType.COMMAND_BLOCKED, detail="blocked")
        result = SandboxResult(success=False, violations=[v])
        assert result.has_violations


class TestSubprocessSandbox:
    @pytest.mark.asyncio
    async def test_execute_allowed_command(self):
        from autoai.sandbox import SubprocessSandbox, SandboxConfig
        config = SandboxConfig(
            allowed_commands={"execute_code"},
            allow_subprocess=True,
            workspace_dir=os.getcwd(),
        )
        sandbox = SubprocessSandbox(config)
        result = await sandbox.execute("execute_code", {"code": "print('hello')"})
        assert result.success
        assert "hello" in result.output

    @pytest.mark.asyncio
    async def test_blocked_command(self):
        from autoai.sandbox import SubprocessSandbox, SandboxConfig
        config = SandboxConfig(allowed_commands={"read_file"}, denied_commands={"execute_shell"})
        sandbox = SubprocessSandbox(config)
        result = await sandbox.execute("execute_shell", {"code": "rm -rf /"})
        assert not result.success
        assert result.has_violations

    @pytest.mark.asyncio
    async def test_blocked_path(self):
        from autoai.sandbox import SubprocessSandbox, SandboxConfig
        config = SandboxConfig(workspace_dir="/tmp/safe_workspace")
        sandbox = SubprocessSandbox(config)
        result = await sandbox.execute("read_file", {"path": "/etc/shadow"})
        assert not result.success
        assert result.has_violations

    @pytest.mark.asyncio
    async def test_validate_command(self):
        from autoai.sandbox import SubprocessSandbox, SandboxConfig
        config = SandboxConfig(allowed_commands={"read_file"}, denied_commands={"delete_file"})
        sandbox = SubprocessSandbox(config)
        assert len(sandbox.validate_command("delete_file")) > 0
        assert len(sandbox.validate_command("read_file")) == 0

    @pytest.mark.asyncio
    async def test_subprocess_not_allowed(self):
        from autoai.sandbox import SubprocessSandbox, SandboxConfig
        config = SandboxConfig(allowed_commands={"execute_code"}, allow_subprocess=False)
        sandbox = SubprocessSandbox(config)
        result = await sandbox.execute("execute_code", {"code": "import os; os.system('ls')"})
        assert not result.success

    @pytest.mark.asyncio
    async def test_timeout(self):
        from autoai.sandbox import SubprocessSandbox, SandboxConfig
        config = SandboxConfig(allow_subprocess=True, timeout_seconds=1.0, workspace_dir=os.getcwd())
        sandbox = SubprocessSandbox(config)
        result = await sandbox.execute(
            "execute_code",
            {"code": "import time; time.sleep(10)"},
            timeout=1.0,
        )
        assert not result.success


class TestSeccompSandbox:
    def test_import_or_fallback(self):
        from autoai.sandbox import SeccompSandbox
        if SeccompSandbox is None:
            pytest.skip("SeccompSandbox not available on this platform")

    @pytest.mark.asyncio
    async def test_fallback_on_non_linux(self):
        import platform
        if platform.system() == "Linux":
            pytest.skip("This test is for non-Linux platforms")
        from autoai.sandbox.seccomp_sandbox import SeccompSandbox
        from autoai.sandbox.base import SandboxConfig
        sandbox = SeccompSandbox(SandboxConfig())
        assert sandbox._fallback is not None


# ======================================================================
# Distributed Execution Tests
# ======================================================================

class TestWorkerInfo:
    def test_worker_availability(self):
        from autoai.distributed.base import WorkerInfo, WorkerStatus
        w = WorkerInfo(status=WorkerStatus.IDLE)
        assert w.is_available
        w.status = WorkerStatus.BUSY
        assert not w.is_available

    def test_worker_reliability(self):
        from autoai.distributed.base import WorkerInfo
        w = WorkerInfo(tasks_completed=9, tasks_failed=1)
        assert w.reliability == pytest.approx(0.9)

    def test_no_tasks_reliability(self):
        from autoai.distributed.base import WorkerInfo
        w = WorkerInfo()
        assert w.reliability == 1.0


class TestDispatchFuture:
    def test_set_result(self):
        from autoai.distributed.base import DispatchFuture
        f = DispatchFuture()
        f.set_result({"status": "ok"})
        assert f.done
        assert f.result == {"status": "ok"}

    def test_set_error(self):
        from autoai.distributed.base import DispatchFuture
        f = DispatchFuture()
        f.set_error("timeout")
        assert f.done
        assert f.error == "timeout"


class TestLocalBackend:
    @pytest.mark.asyncio
    async def test_start_stop(self):
        from autoai.distributed import LocalBackend
        backend = LocalBackend()
        await backend.start()
        assert backend.is_running
        assert backend.total_workers == 1
        await backend.stop()
        assert not backend.is_running

    @pytest.mark.asyncio
    async def test_dispatch_and_result(self):
        from autoai.distributed import LocalBackend
        backend = LocalBackend()
        await backend.start()

        class MockTask:
            task_id = "test-1"
            name = "test task"

        future = await backend.dispatch(MockTask())
        result = await backend.get_result(future, timeout=5.0)
        assert result["status"] == "executed"
        assert result["task_id"] == "test-1"
        await backend.stop()

    @pytest.mark.asyncio
    async def test_dispatch_with_executor(self):
        from autoai.distributed import LocalBackend

        async def custom_executor(task):
            return {"custom": True, "task_id": task.task_id}

        backend = LocalBackend()
        backend.set_executor(custom_executor)
        await backend.start()

        class MockTask:
            task_id = "custom-1"
            name = "custom"

        future = await backend.dispatch(MockTask())
        result = await backend.get_result(future, timeout=5.0)
        assert result["custom"] is True
        await backend.stop()

    @pytest.mark.asyncio
    async def test_multiple_dispatches(self):
        from autoai.distributed import LocalBackend
        backend = LocalBackend(max_concurrent=2)
        await backend.start()

        class MockTask:
            def __init__(self, tid):
                self.task_id = tid
                self.name = f"task-{tid}"

        futures = []
        for i in range(5):
            f = await backend.dispatch(MockTask(f"t{i}"))
            futures.append(f)

        results = []
        for f in futures:
            r = await backend.get_result(f, timeout=10.0)
            results.append(r)

        assert len(results) == 5
        assert all(r["status"] == "executed" for r in results)
        await backend.stop()

    @pytest.mark.asyncio
    async def test_worker_selection(self):
        from autoai.distributed import LocalBackend
        from autoai.distributed.base import WorkerInfo, WorkerStatus
        backend = LocalBackend()
        await backend.start()

        extra = WorkerInfo(worker_id="extra-1", status=WorkerStatus.IDLE, roles={"coder"})
        backend.register_worker(extra)

        workers = backend.get_available_workers(required_roles={"coder"})
        assert len(workers) >= 1

        await backend.stop()

    @pytest.mark.asyncio
    async def test_summary(self):
        from autoai.distributed import LocalBackend
        backend = LocalBackend()
        await backend.start()
        s = backend.summary()
        assert s["running"]
        assert s["total_workers"] == 1
        await backend.stop()


# ======================================================================
# Integration: SystemBootstrap with Sandbox + Distributed
# ======================================================================

class TestSystemBootstrapSandboxDistributed:
    def test_config_new_fields(self):
        from autoai.agents.system_bootstrap import SystemConfig
        config = SystemConfig()
        assert config.enable_sandbox is True
        assert config.sandbox_type == "subprocess"
        assert config.enable_distributed is False
        assert config.distributed_backend == "local"

    def test_setup_creates_sandbox(self):
        from autoai.agents.system_bootstrap import MultiAgentSystem, SystemConfig
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmpdir:
            config = SystemConfig(
                enable_health_monitor=False,
                enable_agent_pool=False,
                enable_tui=False,
                enable_model_router=False,
                enable_sandbox=True,
                sandbox_type="subprocess",
            )
            system = MultiAgentSystem(workspace_path=Path(tmpdir), config=config)
            system.setup()
            assert system.sandbox is not None

    def test_setup_creates_distributed(self):
        from autoai.agents.system_bootstrap import MultiAgentSystem, SystemConfig
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmpdir:
            config = SystemConfig(
                enable_health_monitor=False,
                enable_agent_pool=False,
                enable_tui=False,
                enable_model_router=False,
                enable_distributed=True,
                distributed_backend="local",
            )
            system = MultiAgentSystem(workspace_path=Path(tmpdir), config=config)
            system.setup()
            assert system.distributed is not None

    def test_status_includes_sandbox_distributed(self):
        from autoai.agents.system_bootstrap import MultiAgentSystem, SystemConfig
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmpdir:
            config = SystemConfig(
                enable_health_monitor=False,
                enable_agent_pool=False,
                enable_tui=False,
                enable_model_router=False,
                enable_sandbox=True,
                enable_distributed=True,
                distributed_backend="local",
            )
            system = MultiAgentSystem(workspace_path=Path(tmpdir), config=config)
            system.setup()
            status = system.get_system_status()
            assert "sandbox" in status
            assert "distributed" in status
