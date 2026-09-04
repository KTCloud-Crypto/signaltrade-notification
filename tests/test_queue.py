import json
from datetime import datetime, timezone
from uuid import uuid4

from signaltrade_notification.queue import SqsQueueAdapter


def test_receive_and_acknowledge():
    body = json.dumps({"message_id": str(uuid4()), "message_type": "NotificationRequested",
                       "occurred_at": datetime.now(timezone.utc).isoformat(),
                       "correlation_id": "c", "producer": "test", "schema_version": 1,
                       "payload": {"chat_id": "1", "message": "hello"}})
    class Client:
        deleted = None
        def get_queue_url(self, **kwargs): return {"QueueUrl": "queue-url"}
        def receive_message(self, **kwargs):
            return {"Messages": [{"ReceiptHandle": "receipt", "Body": body,
                                  "Attributes": {"ApproximateReceiveCount": "2"}}]}
        def delete_message(self, **kwargs): self.deleted = kwargs
    client = Client()
    queue = SqsQueueAdapter(client, "notifications")
    message = queue.receive()[0]
    assert message.receive_count == 2
    queue.acknowledge(message)
    assert client.deleted == {"QueueUrl": "queue-url", "ReceiptHandle": "receipt"}


def test_invalid_message_does_not_block_valid_message():
    valid_body = json.dumps({"message_id": str(uuid4()), "message_type": "NotificationRequested",
        "occurred_at": datetime.now(timezone.utc).isoformat(), "correlation_id": "c",
        "producer": "test", "payload": {}})
    class Client:
        def get_queue_url(self, **kwargs): return {"QueueUrl": "queue-url"}
        def receive_message(self, **kwargs):
            return {"Messages": [
                {"MessageId": "bad", "ReceiptHandle": "bad-receipt", "Body": "not-json"},
                {"MessageId": "good", "ReceiptHandle": "good-receipt", "Body": valid_body},
            ]}
    messages = SqsQueueAdapter(Client(), "notifications").receive()
    assert len(messages) == 1
    assert messages[0].receipt_handle == "good-receipt"
