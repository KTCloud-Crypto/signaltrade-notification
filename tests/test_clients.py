import httpx

from signaltrade_notification.identity_client import get_telegram_user, link_telegram_chat
from signaltrade_notification.portfolio_client import get_open_positions


def test_clients_use_service_token(monkeypatch):
    seen = []
    def fake_get(url, **kwargs):
        seen.append((url, kwargs["headers"]))
        body = {"id": 7, "username": "user"} if "telegram-users" in url else []
        return httpx.Response(200, json=body, request=httpx.Request("GET", url))
    monkeypatch.setattr("signaltrade_notification.http_client.httpx.get", fake_get)
    assert get_telegram_user("chat").id == 7
    assert get_open_positions(7) == []
    assert all("X-SignalTrade-Service-Token" in headers for _, headers in seen)


def test_link_delegates_to_identity(monkeypatch):
    def fake_post(url, **kwargs):
        return httpx.Response(200, json={"linked": True}, request=httpx.Request("POST", url))
    monkeypatch.setattr("signaltrade_notification.identity_client.httpx.post", fake_post)
    assert link_telegram_chat("ABCD2345", "chat") is True
