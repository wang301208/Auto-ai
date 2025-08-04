!!! warning
    Pinecone、Milvus、Redis 和 Weaviate 记忆后端因记忆系统的改动而变得不兼容，已被移除。
    是否在未来重新添加支持仍在讨论中，欢迎在 https://github.com/Significant-Gravitas/Auto-GPT/discussions/4280 参与讨论。

## 设置缓存类型

默认情况下，Auto-GPT 使用 LocalCache（将记忆存储在 JSON 文件中）。

若要切换到其他后端，可在 `.env` 中将 `MEMORY_BACKEND` 修改为你想要的值：

* `json_file` 使用本地 JSON 缓存文件
* `chroma` 使用 [Chroma](https://www.trychroma.com/) 向量数据库
* `pinecone` 使用在环境变量中配置的 Pinecone.io 账户
* `redis` 使用你配置的 redis 缓存
* `milvus` 使用你配置的 milvus 缓存
* `weaviate` 使用你配置的 weaviate 缓存

!!! warning
    Pinecone、Milvus、Redis 和 Weaviate 记忆后端因记忆系统的改动而变得不兼容，已被移除。
    是否在未来重新添加支持仍在讨论中，欢迎在 https://github.com/Significant-Gravitas/Auto-GPT/discussions/4280 参与讨论。

## 记忆后端设置

记忆后端链接：

- [Chroma](https://www.trychroma.com/)
- [Pinecone](https://www.pinecone.io/)
- [Milvus](https://milvus.io/) &ndash; [自托管](https://milvus.io/docs)，或使用 [Zilliz Cloud](https://zilliz.com/)
- [Redis](https://redis.io)
- [Weaviate](https://weaviate.io)

!!! warning
    Pinecone、Milvus、Redis 和 Weaviate 记忆后端因记忆系统的改动而变得不兼容，已被移除。
    是否在未来重新添加支持仍在讨论中，欢迎在 https://github.com/Significant-Gravitas/Auto-GPT/discussions/4280 参与讨论。

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

### Redis 设置

!!! caution
    此设置不应公开访问，缺少安全措施。
    请避免在没有密码的情况下将 Redis 暴露在互联网，或完全避免暴露！

1. 启动 Redis 服务器并确保其监听 6379 端口。
   你可以使用 [redis.io](https://redis.io) 的本地安装或任何托管服务。

3. 在 `.env` 中设置以下变量：

    ```shell
    MEMORY_BACKEND=redis
    REDIS_HOST=localhost
    REDIS_PORT=6379
    REDIS_PASSWORD=<PASSWORD>
    ```

    将 `<PASSWORD>` 替换为你的密码，省略尖括号。

    可选配置：

    - `WIPE_REDIS_ON_START=False` 在运行之间保留存储在 Redis 中的记忆。
    - `MEMORY_INDEX=<WHATEVER>` 指定在 Redis 中使用的记忆索引名称，默认值为 `auto-gpt`。

!!! warning
    Pinecone、Milvus、Redis 和 Weaviate 记忆后端因记忆系统的改动而变得不兼容，已被移除。
    是否在未来重新添加支持仍在讨论中，欢迎在 https://github.com/Significant-Gravitas/Auto-GPT/discussions/4280 参与讨论。

### 🌲 Pinecone API Key 设置

Pinecone 允许存储大量向量化记忆，使代理在任何时候只需加载相关记忆。

1. 前往 [pinecone](https://app.pinecone.io/) 并注册账号（如尚未注册）。
2. 选择 *Starter* 套餐以避免收费。
3. 在左侧边栏的默认项目下找到你的 API Key 和区域。

在 `.env` 文件中设置：

- `PINECONE_API_KEY`
- `PINECONE_ENV`（示例：`us-east4-gcp`）
- `MEMORY_BACKEND=pinecone`

!!! warning
    Pinecone、Milvus、Redis 和 Weaviate 记忆后端因记忆系统的改动而变得不兼容，已被移除。
    是否在未来重新添加支持仍在讨论中，欢迎在 https://github.com/Significant-Gravitas/Auto-GPT/discussions/4280 参与讨论。

### Milvus 设置

[Milvus](https://milvus.io/) 是一个开源、高度可扩展的向量数据库，可存储大量向量化记忆并提供快速的相关搜索。可本地部署或使用 [Zilliz Cloud](https://zilliz.com/) 提供的云服务。

1. 本地部署 Milvus 服务或使用托管的 Zilliz Cloud 数据库：
    - [本地安装并部署 Milvus](https://milvus.io/docs/install_standalone-operator.md)

    - 设置托管的 Zilliz Cloud 数据库
        1. 访问 [Zilliz Cloud](https://zilliz.com/) 并注册账号（如尚未注册）。
        2. 在 *Databases* 选项卡中创建新数据库。
            - 记下你的用户名和密码
            - 等待数据库状态变为 RUNNING
        3. 在所创建数据库的 *Database detail* 选项卡中可以找到公共云端点，例如：`https://xxx-xxxx.xxxx.xxxx.zillizcloud.com:443`。

2. 运行 `pip3 install pymilvus` 安装所需客户端库。确保 PyMilvus 版本与你的 Milvus 版本[兼容](https://github.com/milvus-io/pymilvus#compatibility)，以避免问题。参见 [PyMilvus 安装说明](https://github.com/milvus-io/pymilvus#installation)。

3. 更新 `.env`：
    - `MEMORY_BACKEND=milvus`
    - 二选一：
        - `MILVUS_ADDR=host:ip`（本地实例）
        - `MILVUS_ADDR=https://xxx-xxxx.xxxx.xxxx.zillizcloud.com:443`（Zilliz Cloud）
    - `MILVUS_USERNAME='username-of-your-milvus-instance'`
    - `MILVUS_PASSWORD='password-of-your-milvus-instance'`
    - `MILVUS_SECURE=True` 使用安全连接，仅当你的 Milvus 实例启用了 TLS 时使用。
        *注意：将 `MILVUS_ADDR` 设置为 `https://` URL 会覆盖此设置。*
    - `MILVUS_COLLECTION` 更改在 Milvus 中使用的集合名称，默认值为 `autogpt`。

!!! warning
    Pinecone、Milvus、Redis 和 Weaviate 记忆后端因记忆系统的改动而变得不兼容，已被移除。
    是否在未来重新添加支持仍在讨论中，欢迎在 https://github.com/Significant-Gravitas/Auto-GPT/discussions/4280 参与讨论。

### Weaviate 设置

[Weaviate](https://weaviate.io/) 是一个开源向量数据库，可存储数据对象和来自机器学习模型的向量嵌入，并能无缝扩展到数十亿个对象。要设置 Weaviate 数据库，请查看其[快速入门教程](https://weaviate.io/developers/weaviate/quickstart)。

虽然仍处于实验阶段，但支持使用 [嵌入式 Weaviate](https://weaviate.io/developers/weaviate/installation/embedded)，可让 Auto-GPT 进程自行启动一个 Weaviate 实例。要启用它，将 `USE_WEAVIATE_EMBEDDED` 设置为 `True`，并确保执行 `pip install "weaviate-client>=3.15.4"`。

#### 安装 Weaviate 客户端

在使用前安装 Weaviate 客户端。

```shell
$ pip install weaviate-client
```

#### 设置环境变量

在 `.env` 文件中设置以下内容：

```ini
MEMORY_BACKEND=weaviate
WEAVIATE_HOST="127.0.0.1" # 运行中 Weaviate 实例的 IP 或域名
WEAVIATE_PORT="8080"
WEAVIATE_PROTOCOL="http"
WEAVIATE_USERNAME="your username"
WEAVIATE_PASSWORD="your password"
WEAVIATE_API_KEY="your weaviate API key if you have one"
WEAVIATE_EMBEDDED_PATH="/home/me/.local/share/weaviate" # 可选，运行嵌入式实例时数据持久化的位置
USE_WEAVIATE_EMBEDDED=False # 设为 True 以运行嵌入式 Weaviate
MEMORY_INDEX="Autogpt" # 为应用创建的索引名称
```

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

!!! attention
    如果使用 Redis 作为记忆，请确保运行 Auto-GPT 时设置 `WIPE_REDIS_ON_START=False`

    对于其他记忆后端，我们目前在启动 Auto-GPT 时会强制清空记忆。要在这些后端摄取数据，你可以在 Auto-GPT 运行期间随时调用 `data_ingestion.py` 脚本。

记忆在摄取后会立即对 AI 可用，即使在 Auto-GPT 运行过程中摄取也是如此。

