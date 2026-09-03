import asyncio
from unittest.mock import AsyncMock

from signaltrade_notification.poller import TelegramPoller, help_text


def update(text: str, chat_type: str = "private") -> dict:
    return {"update_id": 1, "message": {"text": text,
            "chat": {"id": 1234, "type": chat_type}}}


def test_help_preserves_command_contract():
    for command in ("/status", "/pause", "/balance", "/positions", "/close"):
        assert command in help_text()


def test_positions_uses_http_clients(monkeypatch):
    poller = TelegramPoller("token")
    poller._send_message = AsyncMock()
    monkeypatch.setattr("signaltrade_notification.poller.positions_text",
                        lambda chat_id: "📦 position")
    asyncio.run(poller._handle_update(AsyncMock(), update("/positions")))
    assert poller._send_message.await_args.args[2] == "📦 position"


def test_non_command_is_ignored():
    poller = TelegramPoller("token")
    poller._send_message = AsyncMock()
    asyncio.run(poller._handle_update(AsyncMock(), update("hello")))
    poller._send_message.assert_not_awaited()
