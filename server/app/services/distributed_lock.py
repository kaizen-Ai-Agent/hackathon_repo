import uuid
import aioredis
from typing import Optional


class DistributedLock:
    def __init__(self, redis: aioredis.Redis, name: str, ttl_ms: int = 30000):
        self.redis = redis
        self.name = name
        self.ttl_ms = ttl_ms
        self.token = str(uuid.uuid4())


async def acquire(self) -> bool:
    ok = await self.redis.set(self.name, self.token, px=self.ttl_ms, exist=aioredis.commands.SetCode.NX)
    return bool(ok)


async def release(self) -> bool:
    # safe release via Lua script
    script = """
        if redis.call('get',KEYS[1]) == ARGV[1] then
            return redis.call('del',KEYS[1])
        else
            return 0
        end
    """
    res = await self.redis.eval(script, keys=[self.name], args=[self.token])
    return res == 1