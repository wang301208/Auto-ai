import importlib
import logging
import types
from pathlib import Path

from pytest_mock import MockerFixture

from autogpt.agents.agent import Agent
from autogpt.commands import code_reader


def test_read_and_understand_code_reads_all_files(
    tmp_path: Path, agent: Agent, mocker: MockerFixture, caplog
) -> None:
    importlib.reload(code_reader)
    file1 = tmp_path / "a.py"
    file1.write_text("print('a')")
    sub = tmp_path / "sub"
    sub.mkdir()
    file2 = sub / "b.py"
    file2.write_text("print('b')")

    mock_resp = types.SimpleNamespace(content="analysis")
    create_chat = mocker.patch(
        "autogpt.commands.code_reader.create_chat_completion", return_value=mock_resp
    )

    with caplog.at_level(logging.INFO):
        result = code_reader.read_and_understand_code(str(tmp_path), agent)

    assert result == "analysis"
    create_chat.assert_called_once()
    prompt = create_chat.call_args[1]["prompt"].messages[1].content
    assert "print('a')" in prompt
    assert "print('b')" in prompt

    assert code_reader.CALL_COUNT == 1
    record = next(r for r in caplog.records if r.msg == "code_reader")
    assert record.path_analyzed == str(tmp_path)
    assert record.file_count == 2
