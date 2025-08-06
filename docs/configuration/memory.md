!!! warning
    Pinecone、Milvus、Redis 和 Weaviate 记忆后端因记忆系统的改动而变得不兼容，已被移除。
    是否在未来重新添加支持仍在讨论中，欢迎在 https://github.com/Significant-Gravitas/Auto-GPT/discussions/4280 参与讨论。

## 设置缓存类型

默认情况下，Auto-GPT 使用 `json_file` 将记忆存储在本地 JSON 文件中。

当前仅支持以下记忆后端：

* `json_file` &ndash; 本地 JSON 缓存文件，默认选项
* `chroma` &ndash; 使用 [Chroma](https://www.trychroma.com/) 向量数据库，[示例配置](#chroma-设置)
* `no_memory` &ndash; 禁用记忆功能

在 `.env` 中通过设置 `MEMORY_BACKEND` 切换后端。

## 记忆后端设置

### Chroma 设置

1. 安装依赖：

    ```shell
    pip install chromadb
    ```

2. 在 `.env` 中设置：

    ```ini
    MEMORY_BACKEND=chroma
    ```

   数据默认保存在工作空间下的 `chroma` 目录。

## 历史记忆后端

以下记忆后端在 v0.4.7 中被移除，目前不受支持。如果未来重新添加，可参考这些链接获取背景信息：

- [Pinecone](https://www.pinecone.io/)
- [Milvus](https://milvus.io/) – [自托管](https://milvus.io/docs) 或 [Zilliz Cloud](https://zilliz.com/)
- [Redis](https://redis.io)
- [Weaviate](https://weaviate.io)

是否恢复支持仍在讨论中，欢迎在 https://github.com/Significant-Gravitas/Auto-GPT/discussions/4280 参与讨论。

## 长期记忆

`MessageHistory` 负责短期对话，但你现在可以启用长期向量记忆，将总结后的内容写入长期库并在构建提示时自动检索。

在 `.env` 中添加：

```ini
USE_LONG_TERM_MEMORY=True
LONG_TERM_MEMORY_THRESHOLD=10  # 超过多少条消息后转移
```

当短期记忆中的消息数量超过阈值时，其摘要会被保存到长期记忆中并从短期记忆清除。随后每轮对话都会先读取短期摘要，再在长期记忆中进行语义检索并合并结果。

## 查看记忆使用情况

使用 `--debug` 标志可查看记忆使用情况 :)

## 🧠 记忆预置

!!! warning
    数据摄取在 v0.4.7 及更早版本中存在问题。这是一个已知问题，将在未来版本中解决。请关注以下 Issue 以获取更新。
    [Issue 4435](https://github.com/Significant-Gravitas/Auto-GPT/issues/4435)
    [Issue 4024](https://github.com/Significant-Gravitas/Auto-GPT/issues/4024)
    [Issue 2076](https://github.com/Significant-Gravitas/Auto-GPT/issues/2076)

记忆预置允许你在运行 Auto-GPT 前将文件导入记忆。

```shell
$ python data_ingestion.py -h
usage: data_ingestion.py [-h] (--file FILE | --dir DIR) [--init] [--overlap OVERLAP] [--max_length MAX_LENGTH]

Ingest a file or a directory with multiple files into memory. Make sure to set your .env before running this script.

options:
  -h, --help               show this help message and exit
  --file FILE              The file to ingest.
  --dir DIR                The directory containing the files to ingest.
  --init                   Init the memory and wipe its content (default: False)
  --overlap OVERLAP        The overlap size between chunks when ingesting files (default: 200)
  --max_length MAX_LENGTH  The max_length of each chunk when ingesting files (default: 4000)

# python data_ingestion.py --dir DataFolder --init --overlap 100 --max_length 2000
```

上例中，脚本会初始化记忆，将 `Auto-Gpt/auto_gpt_workspace/DataFolder` 目录中的所有文件导入记忆，块之间重叠 100，单个块最大长度 2000。

注意，也可以使用 `--file` 参数将单个文件导入记忆，且 `data_ingestion.py` 只会摄取 `auto_gpt_workspace` 目录内的文件。

DIR 路径是相对于 `auto_gpt_workspace` 目录的，因此 `python data_ingestion.py --dir . --init` 将导入 `auto_gpt_workspace` 目录中的所有内容。

你可以调整 `max_length` 和 `overlap` 参数，以微调 AI 在“回忆”该记忆时文档呈现方式：

- 调整 overlap 值可以让 AI 在回忆信息时获取更多上下文，但会生成更多块，从而增加记忆后端使用量和 OpenAI API 请求次数。
- 减小 `max_length` 会生成更多块，可通过允许更多消息历史进入上下文来节省提示词 Token，但也会增加块数量。
- 增大 `max_length` 能在每个块中提供更多上下文，减少块数量并节省 OpenAI API 请求，但可能使用更多提示词 Token，并降低 AI 可用的总上下文。

记忆预置是一种通过预先摄取相关数据来提升 AI 准确度的技术。数据会被拆分成若干块并加入记忆，AI 可以快速访问，从而生成更准确的响应。它适用于大数据集或需要快速访问特定信息的场景，例如在运行 Auto-GPT 之前摄取 API 或 GitHub 文档。

记忆在摄取后会立即对 AI 可用，即使在 Auto-GPT 运行过程中摄取也是如此。

