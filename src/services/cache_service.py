import redis
import json
import pickle
from typing import Optional, Any
from src.config import config
from src.utils.logger import logger

class CacheService:
    def __init__(self):
        self.enabled = False
        try:
            self.client = redis.from_url(config.REDIS_URL, decode_responses=False)
            self.client.ping()
            self.enabled = True
            logger.info("Redis cache connected")
        except Exception as e:
            if config.APP_ENV != "production":
                logger.info(f"Redis cache disabled (Development fallback): Use a local Redis server to enable high-performance caching.")
            else:
                logger.warning(f"Redis not available, caching disabled: {e}")

    def get(self, key: str) -> Optional[Any]:
        if not self.enabled:
            return None
        try:
            data = self.client.get(key)
            if data:
                return pickle.loads(data)
        except Exception as e:
            logger.error(f"Cache get error: {e}")
        return None

    def set(self, key: str, value: Any, ttl: int = 3600):
        if not self.enabled:
            return False
        try:
            self.client.setex(key, ttl, pickle.dumps(value))
            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False

cache_service = CacheService()
