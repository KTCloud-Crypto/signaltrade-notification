import asyncio
import logging
import signal
import threading

from prometheus_client import Counter, start_http_server

from signaltrade_notification.config import settings
from signaltrade_notification.delivery import deliver_notification
from signaltrade_notification.deduplication import RedisDeliveryDeduplicator
from signaltrade_notification.queue import QueueMessage, SqsQueueAdapter
from signaltrade_notification.poller import run_telegram_poller

logger = logging.getLogger(__name__)
DELIVERED = Counter("signaltrade_notifications_delivered_total", "Delivered notifications")
FAILED = Counter("signaltrade_notifications_failed_total", "Failed notification deliveries")


def process_notification(queue: SqsQueueAdapter, message: QueueMessage,
                         deduplicator: RedisDeliveryDeduplicator | None = None) -> bool:
    lease = deduplicator.begin(str(message.envelope.message_id)) if deduplicator else None
    if lease and lease.state == "delivered":
        queue.acknowledge(message)
        logger.info("Duplicate notification acknowledged: message_id=%s",
                    message.envelope.message_id)
        return True
    if lease and lease.state == "processing":
        return False
    try:
        delivered = deliver_notification(message.envelope)
    except Exception:
        if lease:
            deduplicator.release(lease)
        raise
    if delivered:
        if lease:
            deduplicator.complete(lease)
        queue.acknowledge(message)
        DELIVERED.inc()
        logger.info("Notification delivered: message_id=%s notification_type=%s",
                    message.envelope.message_id,
                    message.envelope.payload.get("notification_type"))
    else:
        if lease:
            deduplicator.release(lease)
        FAILED.inc()
    return delivered


def consume_notifications(stop: threading.Event) -> None:
    queue = SqsQueueAdapter.from_settings()
    deduplicator = RedisDeliveryDeduplicator.from_url(
        settings.redis_url,
        settings.notification_processing_ttl_seconds,
        settings.notification_dedup_ttl_seconds,
    )
    while not stop.is_set():
        try:
            for message in queue.receive(
                visibility_timeout=settings.sqs_notification_visibility_timeout_seconds):
                if not process_notification(queue, message, deduplicator):
                    logger.warning("Notification delivery failed; message left unacknowledged: %s",
                                   message.envelope.message_id)
        except Exception:
            logger.exception("Notification receive failed; retrying")
            stop.wait(1)


async def main() -> None:
    logging.basicConfig(level=settings.log_level.upper())
    # Telegram authenticates with a token embedded in the request URL. Keep the
    # HTTP client's access log from writing that credential to container logs.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    stop = asyncio.Event()
    delivery_stop = threading.Event()
    loop = asyncio.get_running_loop()
    def request_stop() -> None:
        stop.set()
        delivery_stop.set()
    for signal_name in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(signal_name, request_stop)
    if settings.metrics_enabled:
        start_http_server(settings.notification_metrics_port)
    logger.info("Notification worker started: queue=%s",
                settings.sqs_notification_queue_name)
    poller = asyncio.create_task(run_telegram_poller(stop))
    delivery = asyncio.create_task(asyncio.to_thread(consume_notifications, delivery_stop))
    await stop.wait()
    await asyncio.gather(poller, delivery, return_exceptions=True)


def run() -> None:
    asyncio.run(main())
