import logging

import httpx
from pydantic import BaseModel

from signaltrade_notification.config import settings
from signaltrade_notification.http_client import get_json, service_headers

logger = logging.getLogger(__name__)


class TelegramUser(BaseModel):
    id: int
    username: str


def link_telegram_chat(code: str, chat_id: str) -> bool:
    try:
        response = httpx.post(f"{settings.identity_service_url.rstrip('/')}/internal/telegram-links",
                              json={"code": code, "chat_id": chat_id},
                              headers=service_headers(), timeout=settings.service_timeout_seconds)
        response.raise_for_status()
        return bool(response.json().get("linked"))
    except (httpx.HTTPError, TypeError, ValueError):
        logger.warning("Identity Telegram link request failed")
        return False


def get_telegram_user(chat_id: str) -> TelegramUser | None:
    try:
        body = get_json(f"{settings.identity_service_url.rstrip('/')}/internal/telegram-users/{chat_id}")
        return TelegramUser.model_validate(body)
    except (httpx.HTTPError, TypeError, ValueError):
        return None
