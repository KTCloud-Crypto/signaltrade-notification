from datetime import datetime, timezone
from uuid import uuid4

import pytest

from signaltrade_notification.delivery import deliver_notification
from signaltrade_notification.envelope import MessageEnvelope


def envelope(**payload) -> MessageEnvelope:
    return MessageEnvelope(message_id=uuid4(), message_type="NotificationRequested",
                           occurred_at=datetime.now(timezone.utc), correlation_id="test",
                           producer="test", payload=payload)


def test_delivery_forwards_chat_and_message(monkeypatch):
    sent = []
    monkeypatch.setattr("signaltrade_notification.delivery.send_message",
                        lambda chat_id, text: sent.append((chat_id, text)) or True)
    assert deliver_notification(envelope(chat_id="123", message="hello")) is True
    assert sent == [("123", "hello")]


def test_delivery_rejects_invalid_contract():
    with pytest.raises(ValueError, match="requires chat_id and message"):
        deliver_notification(envelope(chat_id="123"))
