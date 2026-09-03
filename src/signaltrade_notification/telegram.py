import json
import logging
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from signaltrade_notification.config import settings

logger = logging.getLogger(__name__)


def send_message(chat_id: str, text: str) -> bool:
    if not chat_id or not settings.telegram_bot_token:
        return False
    request = Request(
        f"{settings.telegram_api_base_url.rstrip('/')}/bot{settings.telegram_bot_token}/sendMessage",
        data=json.dumps({"chat_id": chat_id, "text": text}).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(request, timeout=settings.telegram_api_timeout_seconds):
            return True
    except (HTTPError, URLError, TimeoutError) as error:
        logger.error("Telegram notification failed: %s", type(error).__name__)
        return False
