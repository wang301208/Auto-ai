import autogpt.agents.archaeologist as arch_module
from autogpt.agents.archaeologist import Archaeologist
from autogpt.config import Config
from autogpt.event_bus import MessageQueue
from autogpt.llm import ChatModelInfo, ChatModelResponse

class DummyResponse(ChatModelResponse):
    def __init__(self, content: str) -> None:
        super().__init__(
            model_info=ChatModelInfo(
                name="test-model",
                max_tokens=1000,
                prompt_token_cost=0.0,
                completion_token_cost=0.0,
            ),
            content=content,
            function_call=None,
        )

def test_evaluate_plugin_combo_caches(monkeypatch):
    calls = {"n": 0}
    def fake_create(prompt, config, temperature=0, functions=None, model=None, max_tokens=None):
        calls["n"] += 1
        return DummyResponse("yes")
    monkeypatch.setattr(arch_module, "create_chat_completion", fake_create)
    arch = Archaeologist(MessageQueue(), config=Config(use_librarian=False))
    plugins = ["fetch_data", "send_email"]
    assert arch.evaluate_plugin_combo(plugins)
    assert arch.evaluate_plugin_combo(plugins)
    assert calls["n"] == 1

def test_evaluate_plugin_combo_heuristic_fail(monkeypatch):
    calls = {"n": 0}
    def fake_create(prompt, config, temperature=0, functions=None, model=None, max_tokens=None):
        calls["n"] += 1
        return DummyResponse("yes")
    monkeypatch.setattr(arch_module, "create_chat_completion", fake_create)
    arch = Archaeologist(MessageQueue(), config=Config(use_librarian=False))
    plugins = ["analyze_data", "summarize_results"]
    assert not arch.evaluate_plugin_combo(plugins)
    assert calls["n"] == 0
