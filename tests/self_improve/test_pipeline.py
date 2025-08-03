from pathlib import Path

from autogpt.self_improve import (
    CriticAgent,
    DatabaseManager,
    PatchAgent,
    Profiler,
    install_exception_logger,
)


def test_self_improvement_pipeline(tmp_path: Path) -> None:
    db_path = tmp_path / "improvement.db"
    db = DatabaseManager(db_path)
    install_exception_logger(db, tmp_path / "log.txt")

    try:
        raise ValueError("boom")
    except Exception:  # noqa: BLE001
        import sys

        sys.excepthook(*sys.exc_info())

    with Profiler(db, "run"):
        sum(range(10))

    db.log_execution("add", "10")

    critic = CriticAgent(db)
    report = critic.generate_report()
    assert "Diagnostic Report" in report

    file_path = tmp_path / "target.py"
    original = "def foo() -> int:\n    return 1\n"
    modified = "def foo() -> int:\n    return 2\n"
    file_path.write_text(original)
    import difflib

    diff = "".join(
        difflib.unified_diff(
            original.splitlines(True),
            modified.splitlines(True),
            fromfile="target.py",
            tofile="target.py",
        )
    )
    patcher = PatchAgent()
    patcher.apply_diff(diff, cwd=tmp_path)
    patcher.verify([file_path])
    assert "return 2" in file_path.read_text()
