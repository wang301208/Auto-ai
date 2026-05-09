import asyncio
from pathlib import Path


def test_gateway_routes_platform_message_to_runtime_and_sends_reply(tmp_path):
    from dual_ring_ai.gateway import GatewayRunner, MessageEvent, MessageType
    from dual_ring_ai.gateway.platforms import FeishuAdapter, PlatformConfig
    from dual_ring_ai.runtime.local_runtime import LocalRuntime, LocalRuntimeConfig

    runtime = LocalRuntime(LocalRuntimeConfig(root_path=tmp_path))
    adapter = FeishuAdapter(
        PlatformConfig(
            name="feishu",
            enabled=True,
            extra={"app_id": "cli_test", "app_secret": "secret", "connection_mode": "websocket"},
        )
    )
    runner = GatewayRunner(runtime)
    runner.register(adapter)

    event = MessageEvent(
        platform="feishu",
        chat_id="oc_chat",
        user_id="ou_user",
        text="hello",
        message_type=MessageType.TEXT,
        raw={"message_id": "om_1"},
    )

    result = asyncio.run(adapter.receive(event))

    assert result["status"] == "sent"
    assert adapter.sent_messages[-1]["chat_id"] == "oc_chat"
    assert adapter.sent_messages[-1]["content"]
    assert runner.history[-1]["event"].platform == "feishu"
    assert runner.history[-1]["response"]["response_text"]


def test_platform_adapters_normalize_vendor_payloads():
    from dual_ring_ai.gateway.platforms import (
        DingTalkAdapter,
        FeishuAdapter,
        PlatformConfig,
        WeixinAdapter,
    )

    feishu = FeishuAdapter(PlatformConfig(name="feishu", enabled=True))
    dingtalk = DingTalkAdapter(PlatformConfig(name="dingtalk", enabled=True))
    weixin = WeixinAdapter(PlatformConfig(name="weixin", enabled=True))

    feishu_event = feishu.normalize_inbound(
        {
            "event": {
                "message": {
                    "chat_id": "oc_1",
                    "message_id": "om_1",
                    "content": "{\"text\":\"hi feishu\"}",
                    "message_type": "text",
                },
                "sender": {"sender_id": {"open_id": "ou_1"}},
            }
        }
    )
    dingtalk_event = dingtalk.normalize_inbound(
        {
            "conversationId": "cid_1",
            "senderStaffId": "user_1",
            "text": {"content": "hi dingtalk"},
            "sessionWebhook": "https://api.dingtalk.com/robot/sendBySession",
            "msgId": "msg_1",
        }
    )
    weixin_event = weixin.normalize_inbound(
        {
            "from_user": "wx_user",
            "chat_id": "wx_chat",
            "content": "hi weixin",
            "msg_id": "wx_1",
            "msg_type": "text",
        }
    )

    assert feishu_event.text == "hi feishu"
    assert feishu_event.chat_id == "oc_1"
    assert dingtalk_event.text == "hi dingtalk"
    assert dingtalk_event.metadata["session_webhook"].startswith("https://api.dingtalk.com/")
    assert weixin_event.text == "hi weixin"
    assert weixin_event.user_id == "wx_user"


def test_platform_security_and_connection_modes():
    from dual_ring_ai.gateway.platforms import (
        DingTalkAdapter,
        FeishuAdapter,
        PlatformConfig,
        WeixinAdapter,
    )

    feishu = FeishuAdapter(
        PlatformConfig(
            name="feishu",
            enabled=True,
            extra={"connection_mode": "webhook", "allowed_users": ["ou_allowed"]},
        )
    )
    dingtalk = DingTalkAdapter(
        PlatformConfig(
            name="dingtalk",
            enabled=True,
            extra={"client_id": "cid", "client_secret": "secret", "allowed_users": ["user_1"]},
        )
    )
    weixin = WeixinAdapter(
        PlatformConfig(
            name="weixin",
            enabled=True,
            extra={"account_id": "acct", "token": "token", "dm_policy": "allowlist", "allow_from": ["wx_user"]},
        )
    )

    assert feishu.connection_mode == "webhook"
    assert feishu.is_authorized("ou_allowed")
    assert not feishu.is_authorized("ou_other")
    assert asyncio.run(dingtalk.connect()) is True
    assert dingtalk.transport == "stream"
    assert asyncio.run(weixin.connect()) is True
    assert weixin.transport == "long_poll"
    assert weixin.is_authorized("wx_user")
    assert not weixin.is_authorized("wx_other")


def test_local_runtime_builds_messaging_gateway(tmp_path):
    from dual_ring_ai.runtime.local_runtime import LocalRuntime, LocalRuntimeConfig

    runtime = LocalRuntime(
        LocalRuntimeConfig(
            root_path=tmp_path,
            adapters={
                "messaging_gateway": {
                    "enabled": True,
                    "platforms": {
                        "feishu": {"enabled": True, "extra": {"connection_mode": "websocket"}},
                        "dingtalk": {
                            "enabled": True,
                            "extra": {"allowed_users": ["user_1"]},
                        },
                        "weixin": {
                            "enabled": True,
                            "extra": {"dm_policy": "open"},
                        },
                    },
                }
            },
        )
    )

    status = runtime.messaging_gateway_status()
    health = runtime.adapter_health()
    result = runtime.handle_platform_message(
        "feishu",
        {
            "event": {
                "message": {
                    "chat_id": "oc_1",
                    "message_id": "om_1",
                    "content": "{\"text\":\"runtime ping\"}",
                    "message_type": "text",
                },
                "sender": {"sender_id": {"open_id": "ou_1"}},
            }
        },
    )

    assert status["status"] == "ready"
    assert health["messaging_gateway"]["status"] == "ready"
    assert set(status["platforms"]) == {"feishu", "dingtalk", "weixin"}
    assert result["status"] == "sent"
