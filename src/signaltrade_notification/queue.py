from dataclasses import dataclass
import logging
from typing import Any

import boto3

from signaltrade_notification.config import settings
from signaltrade_notification.envelope import MessageEnvelope

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class QueueMessage:
    receipt_handle: str
    envelope: MessageEnvelope
    receive_count: int


class SqsQueueAdapter:
    def __init__(self, client: Any, queue_name: str) -> None:
        self._client = client
        self._queue_name = queue_name
        self._queue_url: str | None = None

    @classmethod
    def from_settings(cls) -> "SqsQueueAdapter":
        options: dict[str, Any] = {"region_name": settings.aws_region}
        if settings.sqs_endpoint_url:
            options["endpoint_url"] = settings.sqs_endpoint_url
        return cls(boto3.client("sqs", **options), settings.sqs_notification_queue_name)

    def _get_queue_url(self) -> str:
        if self._queue_url is None:
            self._queue_url = self._client.get_queue_url(
                QueueName=self._queue_name)["QueueUrl"]
        return self._queue_url

    def receive(self, *, max_messages: int = 10, wait_time_seconds: int = 10,
                visibility_timeout: int = 120) -> list[QueueMessage]:
        response = self._client.receive_message(
            QueueUrl=self._get_queue_url(), MaxNumberOfMessages=max_messages,
            WaitTimeSeconds=wait_time_seconds, VisibilityTimeout=visibility_timeout,
            AttributeNames=["ApproximateReceiveCount"])
        messages = []
        for item in response.get("Messages", []):
            try:
                messages.append(QueueMessage(
                    item["ReceiptHandle"],
                    MessageEnvelope.from_json(item["Body"]),
                    int(item.get("Attributes", {}).get("ApproximateReceiveCount", "1")),
                ))
            except (KeyError, TypeError, ValueError):
                logger.warning(
                    "Invalid notification queue message left for DLQ redrive: message_id=%s",
                    item.get("MessageId", "unknown"),
                )
        return messages

    def acknowledge(self, message: QueueMessage) -> None:
        self._client.delete_message(QueueUrl=self._get_queue_url(),
                                    ReceiptHandle=message.receipt_handle)
