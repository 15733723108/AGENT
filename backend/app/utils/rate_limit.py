"""Redis 工具：限流（令牌桶）与会话记忆缓存。Redis 不可用时自动降级为内存。"""
import time
from functools import lru_cache
from typing import Optional

from app.config import settings

try:
    import redis

    _redis_available = True
except Exception:  # pragma: no cover
    redis = None
    _redis_available = False

_MEM_STORE: dict = {}


class RedisClient:
    def __init__(self):
        self._client = None
        if _redis_available:
            try:
                self._client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
                self._client.ping()
            except Exception:
                self._client = None

    @property
    def available(self) -> bool:
        return self._client is not None

    def get(self, key: str) -> Optional[str]:
        if self._client:
            return self._client.get(key)
        return _MEM_STORE.get(key)

    def set(self, key: str, value: str, ex: int = 3600) -> None:
        if self._client:
            self._client.set(key, value, ex=ex)
        else:
            _MEM_STORE[key] = value

    def delete(self, key: str) -> None:
        if self._client:
            self._client.delete(key)
        else:
            _MEM_STORE.pop(key, None)

    def incr(self, key: str, ex: int = 60) -> int:
        if self._client:
            val = self._client.incr(key)
            self._client.expire(key, ex)
            return val
        now = int(time.time())
        bucket = _MEM_STORE.setdefault(key, {"count": 0, "ts": now})
        if now - bucket["ts"] >= ex:
            bucket["count"] = 0
            bucket["ts"] = now
        bucket["count"] += 1
        return bucket["count"]


@lru_cache
def get_redis() -> RedisClient:
    return RedisClient()


def check_rate_limit(user_id: int, module: str, limit: int = 20, window: int = 60) -> bool:
    """令牌桶限流：返回 True 表示允许。默认 20 次/60 秒。"""
    client = get_redis()
    key = f"rate:{user_id}:{module}"
    count = client.incr(key, ex=window)
    return count <= limit
