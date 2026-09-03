import httpx

from signaltrade_notification.config import settings


def service_headers() -> dict[str, str]:
    return {"X-SignalTrade-Service-Token": settings.internal_service_token}


def get_json(url: str):
    response = httpx.get(url, headers=service_headers(), timeout=settings.service_timeout_seconds)
    response.raise_for_status()
    return response.json()
