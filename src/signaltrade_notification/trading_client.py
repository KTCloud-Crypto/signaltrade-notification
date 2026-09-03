import httpx

from signaltrade_notification.config import settings
from signaltrade_notification.http_client import service_headers


async def request_manual_liquidations(user_id: int, subscription_ids: list[int]) -> tuple[int, list[str]] | None:
    try:
        async with httpx.AsyncClient(timeout=settings.service_timeout_seconds) as client:
            response = await client.post(
                f"{settings.trading_service_url.rstrip('/')}/internal/trading/users/{user_id}/manual-liquidations",
                json=subscription_ids, headers=service_headers())
            response.raise_for_status()
        body = response.json()
        return int(body["requested"]), [str(item) for item in body["failures"]]
    except (httpx.HTTPError, KeyError, TypeError, ValueError):
        return None
