import logging

import httpx

from signaltrade_notification.config import settings
from signaltrade_notification.http_client import get_json

logger = logging.getLogger(__name__)


def get_open_positions(user_id: int) -> list[dict] | None:
    try:
        body = get_json(f"{settings.portfolio_service_url.rstrip('/')}/internal/portfolio/users/{user_id}/open-positions")
        return body if isinstance(body, list) else None
    except (httpx.HTTPError, TypeError, ValueError):
        logger.warning("Portfolio open-position lookup failed")
        return None


def get_user_balance(user_id: int) -> list[dict] | None:
    try:
        body = get_json(f"{settings.portfolio_service_url.rstrip('/')}/internal/portfolio/users/{user_id}/balance")
        return body if isinstance(body, list) else None
    except (httpx.HTTPError, TypeError, ValueError):
        logger.warning("Portfolio balance lookup failed")
        return None
