import httpx

from signaltrade_notification.config import settings
from signaltrade_notification.http_client import get_json, service_headers


def get_subscriptions(user_id: int) -> list[dict] | None:
    try:
        body = get_json(f"{settings.strategy_service_url.rstrip('/')}/internal/strategy/users/{user_id}/subscriptions")
        return body if isinstance(body, list) else None
    except (httpx.HTTPError, TypeError, ValueError):
        return None


def set_subscriptions_paused(user_id: int, subscription_ids: list[int], paused: bool) -> int | None:
    try:
        response = httpx.post(
            f"{settings.strategy_service_url.rstrip('/')}/internal/strategy/subscriptions/pause",
            json={"user_id": user_id, "subscription_ids": subscription_ids, "paused": paused},
            headers=service_headers(), timeout=settings.service_timeout_seconds)
        response.raise_for_status()
        return int(response.json()["updated"])
    except (httpx.HTTPError, KeyError, TypeError, ValueError):
        return None
