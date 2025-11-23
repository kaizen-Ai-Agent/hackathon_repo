import redis.asyncio as aioredis
from typing import Optional
from loguru import logger


class RedisClient:
    _client: Optional[aioredis.Redis] = None

    @classmethod
    async def init(
        cls,
        url: str,
        max_connections: int = 20,
        decode_responses: bool = True,
    ):
        """Initialize a global Redis connection pool."""
        if cls._client is None:
            try:
                cls._client = aioredis.from_url(
                    url,
                    max_connections=max_connections,
                    decode_responses=decode_responses,
                )
                # Test connection
                await cls._client.ping()
                logger.info("Redis connected successfully")
            except Exception as e:
                logger.error(f"Redis connection failed: {e}")
                raise

    @classmethod
    def get_client(cls) -> aioredis.Redis:
        """Return the initialized Redis client."""
        if cls._client is None:
            raise RuntimeError("Redis client not initialized. Call RedisClient.init() first.")
        return cls._client

    @classmethod
    async def close(cls):
        """Close Redis connection pool gracefully."""
        if cls._client:
            await cls._client.close()
            cls._client = None
            logger.info("Redis connection closed")