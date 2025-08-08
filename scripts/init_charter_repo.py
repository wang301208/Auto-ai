from __future__ import annotations

"""Initialize a local organizational_charter Git repository with examples."""

from pathlib import Path
from git import Repo  # type: ignore[import-not-found]


EXAMPLE_TDD = """
role_name: "TDD_Developer"
version: "1.0"

core_prompt: |
  你是一个纪律严明的程序员，严格遵循测试驱动开发（TDD）原则。
  你的任务是根据诊断报告，先编写失败的测试，再编写功能代码让测试通过。
  你被授权使用代码执行、文件读写和Git操作插件。

agent_class: "dual_ring_ai.genesis.tdd_developer.TDDDeveloperAgent"

authorized_plugins:
  - "Plugin_Git"
  - "Plugin_FileIO"
  - "Plugin_PytestRunner"
  - "Plugin_CodeExecutor"

subscribed_events:
  - "DIAGNOSIS_COMPLETE"
  - "REFACTORING_REQUESTED"

config:
  workspace_path: "workspace/tdd"
"""


EXAMPLE_FOUNDER = """
role_name: "Founder"
version: "1.0"

core_prompt: |
  你是系统的创始人代理，负责组织自我演化。你会基于系统数据提出组织结构变更建议。

agent_class: "autogpt.agents.founder.FounderAgent"

authorized_plugins:
  - "Plugin_SystemAnalytics"

subscribed_events:
  - "DIAGNOSIS_COMPLETE"

config:
  charter_repo_url: "<fill-your-remote-git-url>"
  workdir: "./founder_workspace"
  run_interval_sec: 86400
"""


def main(path: str = "organizational_charter") -> None:
    root = Path(path)
    root.mkdir(parents=True, exist_ok=True)
    (root / "tdd_developer.yaml").write_text(EXAMPLE_TDD.strip() + "\n", encoding="utf-8")
    (root / "founder.yaml").write_text(EXAMPLE_FOUNDER.strip() + "\n", encoding="utf-8")
    if (root / ".git").exists():
        repo = Repo(str(root))
    else:
        repo = Repo.init(str(root))
    repo.git.add(all=True)
    if not repo.head.is_valid():
        repo.index.commit("Initialize organizational charter with example blueprints")


if __name__ == "__main__":
    main()


