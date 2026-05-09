# Messaging Gateway

This package mirrors Hermes' gateway/platform-adapter shape for external chat
surfaces. It is separate from the terminal TUI.

```text
platform transport
  -> platform adapter
  -> MessageEvent
  -> GatewayRunner
  -> LocalRuntime.handle_interaction()
  -> adapter.send()
```

Built-in adapters:

- `feishu`: Feishu/Lark style `websocket` or `webhook` mode.
- `dingtalk`: DingTalk Stream Mode with session-webhook replies.
- `weixin`: personal Weixin/iLink style long-poll mode.

Example `LocalRuntimeConfig.adapters`:

```json
{
  "messaging_gateway": {
    "enabled": true,
    "platforms": {
      "feishu": {
        "enabled": true,
        "extra": {
          "connection_mode": "websocket",
          "app_id": "cli_xxx",
          "app_secret": "secret_xxx",
          "allowed_users": ["ou_xxx"]
        }
      },
      "dingtalk": {
        "enabled": true,
        "extra": {
          "client_id": "ding_xxx",
          "client_secret": "secret_xxx",
          "allowed_users": ["user_xxx"]
        }
      },
      "weixin": {
        "enabled": true,
        "extra": {
          "account_id": "acct_xxx",
          "token": "token_xxx",
          "dm_policy": "allowlist",
          "allow_from": ["wx_user_xxx"]
        }
      }
    }
  }
}
```

The current adapters provide the normalized gateway contract and testable
message routing. Live vendor SDK loops can be added behind each adapter's
`connect()` method without changing `GatewayRunner` or the runtime interface.
