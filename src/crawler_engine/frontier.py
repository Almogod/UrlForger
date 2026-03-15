from collections import deque
import redis
import json
from src.config import config

class URLFrontier:
    def __init__(self):
        self.queue = deque()
        self.visited = set()

    def add(self, url):
        if url not in self.visited:
            self.queue.append(url)

    def get(self):
        if self.queue:
            url = self.queue.popleft()
            self.visited.add(url)
            return url
        return None

    def size(self):
        return len(self.queue)

class RedisURLFrontier:
    """Enterprise-grade frontier using Redis for distributed crawling."""
    def __init__(self, job_id: str):
        self.r = redis.from_url(config.REDIS_URL)
        self.queue_key = f"frontier:queue:{job_id}"
        self.visited_key = f"frontier:visited:{job_id}"

    def add(self, url):
        if not self.r.sismember(self.visited_key, url):
            self.r.lpush(self.queue_key, url)

    def get(self):
        url = self.r.rpop(self.queue_key)
        if url:
            url = url.decode('utf-8')
            self.r.sadd(self.visited_key, url)
            return url
        return None

    def size(self):
        return self.r.llen(self.queue_key)

    def clear(self):
        self.r.delete(self.queue_key, self.visited_key)
