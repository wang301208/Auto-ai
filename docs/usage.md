# 使用方法

## 命令行参数
运行 `--help` 可列出所有可用的命令行参数：

```shell
agpt --help
```

!!! note
    尖括号 (<>) 中的内容需替换为你要指定的值

常用参数示例：

* 使用不同的 AI 设置文件
```shell
agpt --ai-settings <文件名>
```

* 使用不同的提示词设置文件
```shell
agpt --prompt-settings <文件名>
```

* 指定记忆后端
```shell
agpt --use-memory <记忆后端>
```

!!! note
    某些选项有简写，例如 `-m` 对应 `--use-memory`。更多信息请运行 `agpt --help`。

### 启用长期记忆

可在环境变量中开启长期记忆并设置阈值，将较早的消息从短期摘要移入长期向量库：

```shell
export USE_LONG_TERM_MEMORY=True
export LONG_TERM_MEMORY_THRESHOLD=10
```

### 语音模式

启用 TTS（文本转语音）：

```shell
agpt --speak
```

### 💀 连续模式 ⚠️

在 **无需** 用户授权的情况下运行 AI，完全自动化。连续模式可能很危险，可能导致 AI 无限运行或执行你通常不会授权的操作。使用需谨慎。

```shell
agpt --continuous
```

退出程序请按 ++ctrl+c++。

### ♻️ 自我反馈模式 ⚠️

该模式会**增加** Token 使用量。代理会对自身操作提供反馈，并在下一轮给出更好的建议。当前循环启用请在输入字段中键入 `S`。

### 仅使用 GPT-3.5 模式

如果没有 GPT-4 权限，可使用此模式：

```shell
agpt --gpt3only
```

同样也可在 `.env` 中将 `SMART_LLM` 设置为 `gpt-3.5-turbo`。

### 仅使用 GPT-4 模式

只使用 GPT-4：

```shell
agpt --gpt4only
```

[English version](usage.en.md)
