# 配置

配置由 `Config` 对象控制。你可以通过 `.env` 文件设置配置变量。当创建工作空间时，Auto-GPT 会自动从 `.env.template` 生成 `.env` 文件、一个空的 `ai_settings.yaml`，并在缺少时复制 `prompt_settings.yaml`。可通过编辑这些文件来自定义代理。如需中文注释的模板，可手动复制 `.env.template-zh`。

## 环境变量

- `AI_SETTINGS_FILE`：AI 设置文件在 Auto-GPT 根目录下的相对位置。默认值：ai_settings.yaml
- `AUDIO_TO_TEXT_PROVIDER`：音频转文本提供方。目前仅支持 `huggingface`。默认值：huggingface
- `AUTHORISE_COMMAND_KEY`：授权命令时接受的键。默认值：y
- `AZURE_CONFIG_FILE`：Azure 配置文件在 Auto-GPT 根目录下的相对位置。默认值：azure.yaml
- `BROWSE_CHUNK_MAX_LENGTH`：浏览网页时，用于摘要的分块长度。默认值：3000
- `BROWSE_SPACY_LANGUAGE_MODEL`：创建分块时使用的 [spaCy 语言模型](https://spacy.io/usage/models)。默认值：en_core_web_sm
- `CHAT_MESSAGES_ENABLED`：是否启用聊天消息。可选。
- `DISABLED_COMMAND_CATEGORIES`：要禁用的命令类别。命令类别是 Python 模块名称，例如 `autogpt.commands.execute_code`。所有命令模块见源代码中的 `autogpt/commands` 目录。默认值：None
- `ELEVENLABS_API_KEY`：ElevenLabs API 密钥。可选。
- `ELEVENLABS_VOICE_ID`：ElevenLabs 语音 ID。可选。
- `EMBEDDING_MODEL`：用于嵌入任务的 LLM 模型。默认值：text-embedding-ada-002
- `EXECUTE_LOCAL_COMMANDS`：是否在本地执行 Shell 命令。默认值：True
- `EXIT_KEY`：退出时接受的键。默认值：n
- `FAST_LLM`：用于大多数任务的 LLM 模型。默认值：gpt-3.5-turbo
- `GITHUB_API_KEY`：[GitHub API 密钥](https://github.com/settings/tokens)。可选。
- `GITHUB_USERNAME`：GitHub 用户名。可选。
- `GOOGLE_API_KEY`：Google API 密钥。可选。
- `GOOGLE_CUSTOM_SEARCH_ENGINE_ID`：[Google 自定义搜索引擎 ID](https://programmablesearchengine.google.com/controlpanel/all)。可选。
- `HEADLESS_BROWSER`：在 Auto-GPT 使用浏览器时是否启用无头模式。设置为 `False` 可观察浏览器操作。默认值：True
- `HUGGINGFACE_API_TOKEN`：HuggingFace API，用于图像生成和音频转文本。可选。
- `HUGGINGFACE_AUDIO_TO_TEXT_MODEL`：HuggingFace 音频转文本模型。默认值：CompVis/stable-diffusion-v1-4
- `HUGGINGFACE_IMAGE_MODEL`：用于图像生成的 HuggingFace 模型。默认值：CompVis/stable-diffusion-v1-4
- `IMAGE_PROVIDER`：图像提供方。可选值：`dalle`、`huggingface`、`sdwebui`。默认值：dalle
- `IMAGE_SIZE`：生成图像的默认尺寸。默认值：256
- `MEMORY_BACKEND`：使用的记忆后端。目前支持 `json_file` 和 `chroma`。默认值：json_file
- `MEMORY_INDEX`：在记忆后端中用于作用域、命名或索引的值。默认值：auto-gpt
- `OPENAI_API_KEY`：**必填**——你的 [OpenAI API Key](https://platform.openai.com/account/api-keys)。
- `OPENAI_ORGANIZATION`：OpenAI 组织 ID。可选。
- `PLAIN_OUTPUT`：纯文本输出，禁用旋转指示器。默认值：False
- `PLUGINS_CONFIG_FILE`：插件配置文件相对于 Auto-GPT 根目录的路径。默认值：plugins_config.yaml
- `PROMPT_SETTINGS_FILE`：提示词设置文件相对于 Auto-GPT 根目录的位置。默认值：prompt_settings.yaml
- `REDIS_HOST`：Redis 主机。默认值：localhost
- `REDIS_PASSWORD`：Redis 密码。可选。默认值为空
- `REDIS_PORT`：Redis 端口。默认值：6379
- `RESTRICT_TO_WORKSPACE`：是否将文件读写限制在工作空间目录内。默认值：True
- `SD_WEBUI_AUTH`：Stable Diffusion Web UI 的 `username:password`。可选。
- `SD_WEBUI_URL`：Stable Diffusion Web UI 的 URL。默认值：http://localhost:7860
- `SHELL_ALLOWLIST`：允许 Auto-GPT 执行的 Shell 命令列表，仅在 `SHELL_COMMAND_CONTROL` 设为 `allowlist` 时生效。默认值：None
- `SHELL_COMMAND_CONTROL`：决定使用 `allowlist` 还是 `denylist` 来控制可执行的 Shell 命令。默认值：denylist
- `SHELL_DENYLIST`：不允许 Auto-GPT 执行的 Shell 命令列表，仅在 `SHELL_COMMAND_CONTROL` 设为 `denylist` 时生效。默认值：sudo,su
- `SMART_LLM`：用于“智能”任务的 LLM 模型。默认值：gpt-4
- `STREAMELEMENTS_VOICE`：使用的 StreamElements 语音。默认值：Brian
- `TEMPERATURE`：传递给 OpenAI 的 temperature 值，范围 0-2。值越低越确定，值越高越随机。详见 https://platform.openai.com/docs/api-reference/completions/create#completions/create-temperature
- `TEXT_TO_SPEECH_PROVIDER`：文本转语音提供方。可选值：`gtts`、`macos`、`elevenlabs`、`streamelements`。默认值：gtts
- `USER_AGENT`：浏览网站时使用的 User-Agent。默认值："Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.97 Safari/537.36"
- `USE_AZURE`：是否使用 Azure 的 LLM。默认值：False
- `USE_LIBRARIAN`：是否使用 LibrarianAgent 进行技能推荐。默认值：True
- `USE_WEB_BROWSER`：使用的网页浏览器，选项有 `chrome`、`firefox`、`safari`、`edge`。默认值：chrome
- `WIPE_REDIS_ON_START`：启动时是否清空数据/索引。默认值：True
- `SELF_DEVELOP`：启用后台自我开发循环。默认值：False
- `SELF_DEVELOP_INTERVAL`：启用自我开发时仓库扫描的间隔秒数。默认值：300

