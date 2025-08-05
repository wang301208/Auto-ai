from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import scripts.use_recommended_skill as script


def test_main_calls_recommended_skill() -> None:
    skill = SimpleNamespace(code="def run(foo: str) -> None: pass")
    mock_run = MagicMock()

    def fake_exec(code: str, ns: dict) -> None:  # pragma: no cover - patched in test
        ns["run"] = mock_run

    with patch("scripts.use_recommended_skill.get_skill", return_value=skill) as get_mock, patch(
        "scripts.use_recommended_skill.exec", side_effect=fake_exec
    ):
        script.main()

    get_mock.assert_called_once_with("hello_world", "1.0")
    mock_run.assert_called_once_with(foo="bar")
