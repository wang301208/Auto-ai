# Auto-GPT：GPT-4 自主实验

[English README](README.en.md)

[![Official Website](https://img.shields.io/badge/Official%20Website-agpt.co-blue?style=flat&logo=world&logoColor=white)](https://agpt.co)
[![Unit Tests](https://img.shields.io/github/actions/workflow/status/Significant-Gravitas/Auto-GPT/ci.yml?label=unit%20tests)](https://github.com/Significant-Gravitas/Auto-GPT/actions/workflows/ci.yml)
[![Discord Follow](https://dcbadge.vercel.app/api/server/autogpt?style=flat)](https://discord.gg/autogpt)
[![GitHub Repo stars](https://img.shields.io/github/stars/Significant-Gravitas/auto-gpt?style=social)](https://github.com/Significant-Gravitas/Auto-GPT/stargazers)
[![Twitter Follow](https://img.shields.io/twitter/follow/siggravitas?style=social)](https://twitter.com/SigGravitas)

## 💡 获取帮助 - [Q&A](https://github.com/Significant-Gravitas/Auto-GPT/discussions/categories/q-a) 或 [Discord 💬](https://discord.gg/autogpt)

---

### 🔴 请使用 `stable` 而非 `master` 🔴

**最新稳定版下载地址：https://github.com/Significant-Gravitas/Auto-GPT/releases/latest**
`master` 分支处于快速开发中，可能经常处于 **不可用** 状态。

---

Auto-GPT 是一个实验性的开源应用，用于展示 GPT-4 语言模型的能力。该程序由 GPT-4 驱动，将 LLM 的“思考”串联起来，自主完成你设定的任何目标。作为 GPT-4 完全自主运行的首批示例之一，Auto-GPT 正在推动 AI 的边界。

## 🚀 功能

- 🌐 可访问互联网进行搜索和信息收集
- 💾 管理短期与长期记忆
- 🧠 使用 GPT-4 进行文本生成
- 🔗 访问常见网站和平台
- 🗃️ 使用 GPT-3.5 进行文件存储与摘要
- 🔌 通过插件扩展能力
- 🔁 [自我改进循环](docs/self_improvement.md) 与插件缺口检测
- 🧬 [AlphaEvolve 策略演化](docs/evolve_population.md)

## 快速开始

0. 查看 [wiki](https://github.com/Significant-Gravitas/Nexus/wiki)
1. 获取 OpenAI [API Key](https://platform.openai.com/account/api-keys)
2. 下载 [最新发行版](https://github.com/Significant-Gravitas/Auto-GPT/releases/latest)
3. [安装](#安装) Auto-GPT
4. 配置其他功能或安装一些 [插件][docs/plugins]
5. 运行应用：

```bash
agpt
```

首次运行会在工作目录中创建 `auto_gpt_workspace` 等文件。
使用 `agpt --help` 查看所有可用参数。

完整的设置和配置选项请参阅 [文档][docs]。

[docs]: https://docs.agpt.co/

## 安装

Auto-GPT 需要 **Python 3.10 或更高版本**。

克隆仓库并进入项目目录：

```bash
git clone -b stable https://github.com/Significant-Gravitas/Auto-GPT.git
cd Auto-GPT
```

### 从源码安装

```bash
python -m venv venv
source venv/bin/activate  # Windows 使用 `venv\\Scripts\\activate`
pip install -e .
# AlphaEvolve 可选组件
pip install -e .[alphaevolve]
```

或使用 [Poetry](https://python-poetry.org/)：

```bash
poetry install
# AlphaEvolve 可选组件
poetry install --with alphaevolve
```

## 配置

复制示例环境并添加 API 密钥：

```bash
cp .env.template .env
# 或使用中文模板：
# cp .env.template-zh .env
```

编辑 `.env` 并设置 `OPENAI_API_KEY` 及其他所需值。
去掉行首的 `#` 以启用可选设置。

若使用 Azure OpenAI，请设置 `USE_AZURE=true` 并将 `azure.yaml.template` 复制为
`azure.yaml`，然后填写所需字段。

## 运行应用

```bash
agpt
```

首次运行将创建 `auto_gpt_workspace` 等文件。更多运行时选项见 [docs/setup]。

### 命令行选项

使用 `agpt` 命令行工具启动 Auto-GPT 或运行 AlphaEvolve 工作流。
无子命令的 `agpt` 启动 Auto-GPT，而 `agpt alphaevolve` 运行 [AlphaEvolve](docs/evolve_population.md)。

常用参数包括：

- `--working-directory PATH` – 配置和数据文件所在位置（默认为项目根目录）
- `-w, --workspace-directory PATH` – 代理工作区目录（默认为工作目录下的 `auto_gpt_workspace`）
- `--ai-settings FILE` – AI 配置的 YAML 文件路径
- `--prompt-settings FILE` – 提示设置的 YAML 文件路径
- `--use-memory BACKEND` – 选择记忆后端，如 `local`、`redis`
- `--speak` – 启用文本转语音
- `--continuous` – 无需用户确认持续运行
- `--gpt3only` – 全部使用 GPT‑3.5
- `--gpt4only` – 全部使用 GPT‑4
- `--debug` – 启用调试日志

示例：

```bash
agpt --ai-settings ai_settings.yaml --use-memory redis
```

执行 `agpt --help` 查看完整参数列表。

## 插件

插件可以为 Auto-GPT 增加额外能力。配置存放在工作目录中的 `plugins_config.yaml`。

```yaml
example-plugin:
  enabled: true
  config:
    api_key: "..."
```

参见 [官方插件仓库](https://github.com/Significant-Gravitas/Auto-GPT-Plugins) 和 [插件模板](https://github.com/Significant-Gravitas/Auto-GPT-Plugin-Template) 以获取示例。
启用前请务必检查插件代码以确保安全。

## 📖 文档
* [⚙️ 设置][docs/setup]
* [💻 用法][docs/usage]
* [🔌 插件][docs/plugins]
* [🔧 自我改进](docs/self_improvement.md)
* [🧬 策略演化](docs/evolve_population.md)
* 配置
  * [🔍 Web 搜索](https://docs.agpt.co/configuration/search/)
  * [🧠 记忆](https://docs.agpt.co/configuration/memory/)
  * [🗣️ 语音（TTS）](https://docs.agpt.co/configuration/voice/)
  * [🖼️ 图像生成](https://docs.agpt.co/configuration/imagegen/)

[docs/setup]: https://docs.agpt.co/setup/
[docs/usage]: https://docs.agpt.co/usage/
[docs/plugins]: https://docs.agpt.co/plugins/

## 🤝 参与贡献

请阅读 [贡献指南](CONTRIBUTING-zh.md) 与 [行为准则](CODE_OF_CONDUCT-zh.md) 了解如何参与本项目。

## 💖 资助 Auto-GPT 的开发

如果你愿意请我们喝杯咖啡，你的支持将帮助我们承担 Auto-GPT 的开发成本并推动全自动 AI 的边界！
本项目的发展离不开所有 [贡献者](https://github.com/Significant-Gravitas/Auto-GPT/graphs/contributors) 和 [赞助商](https://github.com/sponsors/Torantulino)。
若希望赞助本项目并让你的头像或公司 Logo 显示在下方，[请点击这里](https://github.com/sponsors/Torantulino)。

<p align="center">
<div align="center" class="logo-container">
<a href="https://www.zilliz.com/">
<picture height="40px">
  <source media="(prefers-color-scheme: light)" srcset="https://user-images.githubusercontent.com/22963551/234158272-7917382e-ff80-469e-8d8c-94f4477b8b5a.png">
  <img src="https://user-images.githubusercontent.com/22963551/234158222-30e2d7a7-f0a9-433d-a305-e3aa0b194444.png" height="40px" alt="Zilliz" />
</picture>
</a>

<a href="https://roost.ai">
<img src="https://user-images.githubusercontent.com/22963551/234180283-b58cb03c-c95a-4196-93c1-28b52a388e9d.png" height="40px" alt="Roost.AI" />
</a>

<a href="https://nuclei.ai/">
<picture height="40px">
  <source media="(prefers-color-scheme: light)" srcset="https://user-images.githubusercontent.com/22963551/234153428-24a6f31d-c0c6-4c9b-b3f4-9110148f67b4.png">
  <img src="https://user-images.githubusercontent.com/22963551/234181283-691c5d71-ca94-4646-a1cf-6e818bd86faa.png" height="40px" alt="NucleiAI" />
</picture>
</a>

<a href="https://www.algohash.org/">
<picture>
  <source media="(prefers-color-scheme: light)" srcset="https://user-images.githubusercontent.com/22963551/234180375-1365891c-0ba6-4d49-94c3-847c85fe03b0.png" >
  <img src="https://user-images.githubusercontent.com/22963551/234180359-143e4a7a-4a71-4830-99c8-9b165cde995f.png" height="40px" alt="Algohash" />
</picture>
</a>

<a href="https://github.com/weaviate/weaviate">
<picture height="40px">
  <source media="(prefers-color-scheme: light)" srcset="https://user-images.githubusercontent.com/22963551/234181699-3d7f6ea8-57f-4e98-b812-37be1081be4b.png">
  <img src="https://user-images.githubusercontent.com/22963551/234181695-fc895159-b921-4895-9a13-65e6eff5b0e7.png" height="40px" alt="TypingMind" />
</picture>
</a>

<a href="https://chatgpv.com/?ref=spni76459e4fa3f30a">
<img src="https://github-production-user-asset-6210df.s3.amazonaws.com/22963551/239132565-623a2dd6-eaeb-4941-b40f-c5a29ca6bebc.png" height="40px" alt="ChatGPV" />
</a>

</div>
</p>

