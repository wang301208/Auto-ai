# 文本转语音

运行以下命令即可为 Auto-GPT 启用 TTS（Text-to-Speech）：

```shell
agpt --speak
```

Eleven Labs 提供语音设计、语音合成以及预设语音等技术，Auto-GPT 可以利用其进行语音输出。

1. 访问 [ElevenLabs](https://beta.elevenlabs.io/) 并注册账号（如尚未注册）。
2. 选择并设置 *Starter* 方案。
3. 点击右上角图标，在 *Profile* 中找到你的 API Key。

在 `.env` 文件中设置：

- `ELEVENLABS_API_KEY`
- `ELEVENLABS_VOICE_1_ID`（示例：*"premade/Adam"*）

### 可用语音列表

!!! note
    配置语音时可以使用名称或语音 ID

| 名称  | 语音 ID |
| ----- | -------- |
| Rachel | `21m00Tcm4TlvDq8ikWAM` |
| Domi   | `AZnzlk1XvdvUeBnXmlld` |
| Bella  | `EXAVITQu4vr4xnSDxMaL` |
| Antoni | `ErXwobaYiN019PkySvjV` |
| Elli   | `MF3mGyEYCl7XYWbV9V6O` |
| Josh   | `TxGEqnHWrfWFTfGW9XjX` |
| Arnold | `VR6AewLTigWG4xSOukaG` |
| Adam   | `pNInz6obpgDQGcFmaJgB` |
| Sam    | `yoZ06aMxZJJ28mfd3POQ` |

