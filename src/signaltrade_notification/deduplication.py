from dataclasses import dataclass
from typing import Any, Literal
from uuid import uuid4


@dataclass(frozen=True, slots=True)
class DeliveryLease:
    state: Literal["acquired", "processing", "delivered"]
    key: str
    token: str | None = None


class RedisDeliveryDeduplicator:
    def __init__(self, client: Any, processing_ttl_seconds: int,
                 delivered_ttl_seconds: int) -> None:
        self.client = client
        self.processing_ttl_seconds = processing_ttl_seconds
        self.delivered_ttl_seconds = delivered_ttl_seconds

    @classmethod
    def from_url(cls, redis_url: str, processing_ttl_seconds: int,
                 delivered_ttl_seconds: int) -> "RedisDeliveryDeduplicator":
        from redis import Redis
        return cls(Redis.from_url(redis_url, decode_responses=True),
                   processing_ttl_seconds, delivered_ttl_seconds)

    def begin(self, message_id: str) -> DeliveryLease:
        key = f"signaltrade:notification:delivery:{message_id}"
        token = str(uuid4())
        if self.client.set(key, token, nx=True, ex=self.processing_ttl_seconds):
            return DeliveryLease("acquired", key, token)
        value = self.client.get(key)
        return DeliveryLease("delivered" if value == "delivered" else "processing", key)

    def complete(self, lease: DeliveryLease) -> None:
        self.client.set(lease.key, "delivered", ex=self.delivered_ttl_seconds)

    def release(self, lease: DeliveryLease) -> None:
        self.client.eval(
            "if redis.call('get', KEYS[1]) == ARGV[1] then "
            "return redis.call('del', KEYS[1]) else return 0 end",
            1, lease.key, lease.token,
        )
