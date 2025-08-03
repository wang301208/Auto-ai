# 🖼 图像生成配置

| 配置变量  | 可选值                          |                      |
| --------- | ------------------------------- | -------------------- |
| `IMAGE_PROVIDER` | `dalle` `huggingface` `sdwebui` | **默认：`dalle`** |

## DALL-e

在 `.env` 中确保 `IMAGE_PROVIDER` 被注释（或设为 `dalle`）：

```ini
# IMAGE_PROVIDER=dalle    # 默认值
```

其他可选配置：

| 配置变量  | 可选值             |                |
| ---------- | ------------------ | -------------- |
| `IMAGE_SIZE`     | `256` `512` `1024` | 默认：`256` |

## Hugging Face

要使用 Hugging Face 的文本生图模型，需要一个 Hugging Face API Token。设置页面链接：[Hugging Face > Settings > Tokens](https://huggingface.co/settings/tokens)

获取 API Token 后，在 `.env` 中取消注释并调整以下变量：

```ini
IMAGE_PROVIDER=huggingface
HUGGINGFACE_API_TOKEN=your-huggingface-api-token
```

其他可选配置：

| 配置变量           | 可选值                 |                                          |
| ------------------ | ---------------------- | ---------------------------------------- |
| `HUGGINGFACE_IMAGE_MODEL` | 见[可用模型] | 默认：`CompVis/stable-diffusion-v1-4` |

[可用模型]: https://huggingface.co/models?pipeline_tag=text-to-image

## Stable Diffusion WebUI

可以在 Auto-GPT 中使用自建的 Stable Diffusion WebUI：

```ini
IMAGE_PROVIDER=sdwebui
```

!!! note
    请确保运行 WebUI 时启用了 `--api`。

其他可选配置：

| 配置变量 | 可选值                  |                                  |
| -------- | ----------------------- | -------------------------------- |
| `SD_WEBUI_URL`  | WebUI 的 URL       | 默认：`http://127.0.0.1:7860` |
| `SD_WEBUI_AUTH` | `{username}:{password}` | *注意：不要复制花括号！*  |

## Selenium

```shell
sudo Xvfb :10 -ac -screen 0 1024x768x24 & DISPLAY=:10 <YOUR_CLIENT>
```

