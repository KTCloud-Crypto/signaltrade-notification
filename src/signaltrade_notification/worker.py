import logging
import signal
import threading

from prometheus_client import Counter, start_http_server

from signaltrade_notification.config import settings
from signaltrade_notification.delivery import deliver_notification
from signaltrade_notification.queue import QueueMessage, SqsQueueAdapter

logger = logging.getLogger(__name__)
DELIVERED = Counter("signaltrade_notifications_delivered_total", "Delivered notifications")
FAILED = Counter("signaltrade_notifications_failed_total", "Failed notification deliveries")


def process_notification(queue: SqsQueueAdapter, message: QueueMessage) -> bool:
    delivered = deliver_notification(message.envelope)
    if delivered:
        queue.acknowledge(message)
        DELIVERED.inc()
        logger.info("Notification delivered: message_id=%s notification_type=%s",
                    message.envelope.message_id,
                    message.envelope.payload.get("notification_type"))
    else:
        FAILED.inc()
    return delivered


def consume_notifications(stop: threading.Event) -> None:
    queue = SqsQueueAdapter.from_settings()
    while not stop.is_set():
        try:
            for message in queue.receive(
                visibility_timeout=settings.sqs_notification_visibility_timeout_seconds):
                if not process_notification(queue, message):
                    logger.warning("Notification delivery failed; message left unacknowledged: %s",
                                   message.envelope.message_id)
        except Exception:
            logger.exception("Notification receive failed; retrying")
            stop.wait(1)


def run() -> None:
    logging.basicConfig(level=settings.log_level.upper())
    stop = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    signal.signal(signal.SIGINT, lambda *_: stop.set())
    if settings.metrics_enabled:
        start_http_server(settings.notification_metrics_port)
    logger.info("Notification worker started: queue=%s",
                settings.sqs_notification_queue_name)
    consume_notifications(stop)
