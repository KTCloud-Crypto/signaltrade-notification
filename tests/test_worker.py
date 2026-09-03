from datetime import datetime, timezone
from unittest.mock import MagicMock
from uuid import uuid4

from signaltrade_notification.envelope import MessageEnvelope
from signaltrade_notification.queue import QueueMessage
from signaltrade_notification.worker import process_notification


def message() -> QueueMessage:
    envelope = MessageEnvelope(message_id=uuid4(), message_type="NotificationRequested",
        occurred_at=datetime.now(timezone.utc), correlation_id="c", producer="test",
        payload={"chat_id": "1", "message": "hello"})
    return QueueMessage("receipt", envelope, 1)


def test_worker_acks_only_successful_delivery(monkeypatch):
    queue = MagicMock()
    item = message()
    monkeypatch.setattr("signaltrade_notification.worker.deliver_notification", lambda _: True)
    assert process_notification(queue, item) is True
    queue.acknowledge.assert_called_once_with(item)
    queue.reset_mock()
    monkeypatch.setattr("signaltrade_notification.worker.deliver_notification", lambda _: False)
    assert process_notification(queue, item) is False
    queue.acknowledge.assert_not_called()
