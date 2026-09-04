import asyncio
from unittest.mock import AsyncMock

import pytest

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


def test_offset_advances_only_after_update_is_fully_processed():
    poller = TelegramPoller("token")
    poller._handle_update = AsyncMock(side_effect=[None, RuntimeError("send failed")])
    updates = [{"update_id": 10}, {"update_id": 11}]

    with pytest.raises(RuntimeError, match="send failed"):
        asyncio.run(poller._process_updates(AsyncMock(), updates))

    assert poller._offset == 11


def test_failed_first_update_is_not_confirmed():
    poller = TelegramPoller("token")
    poller._handle_update = AsyncMock(side_effect=RuntimeError("command failed"))

    with pytest.raises(RuntimeError, match="command failed"):
        asyncio.run(poller._process_updates(AsyncMock(), [{"update_id": 20}]))

    assert poller._offset is None
