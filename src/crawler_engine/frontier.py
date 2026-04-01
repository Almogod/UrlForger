import sqlite3
import tempfile
import threading
import os
from collections import deque
import redis
import json
from src.config import config

from urllib.parse import urlparse

class URLFrontier:
    def __init__(self, base_domain=None):
        self.queue = deque()
        self.visited = set()
        self.base_domain = base_domain
        self.base_path = ""
        if base_domain and "://" in base_domain:
            parsed = urlparse(base_domain)
            self.base_domain = parsed.netloc
            # Lock the crawler strictly to the provided subdirectory path (e.g. /repo or /blog)
            path = parsed.path
            if path and path != "/":
                self.base_path = path

    def add(self, url, depth=0, force_add=False):
        if not url:
            return
        
        # Domain locking: only add if same domain (unless force_add is true for external validation)
        if self.base_domain and not force_add:
            parsed = urlparse(url)
            if parsed.netloc and parsed.netloc != self.base_domain:
                return
            if self.base_path and not parsed.path.startswith(self.base_path) and parsed.path != self.base_path:
                return

        if url not in self.visited:
            self.queue.append({"url": url, "depth": depth})
            self.visited.add(url) # Mark as visited immediately to avoid multiple additions

    def get(self):
        if self.queue:
            return self.queue.popleft() # returns dict: {"url": "...", "depth": 0}
        return None

    def size(self):
        return len(self.queue)

    def peek(self):
        if self.queue:
            return self.queue[0].get("url")
        return None

class SQLiteURLFrontier:
    """Enterprise-grade frontier using SQLite for large local crawls without RAM explosion."""
    def __init__(self, base_domain=None, db_path=None):
        if not db_path:
            fd, db_path = tempfile.mkstemp(suffix=".sqlite")
            os.close(fd)
        self.db_path = db_path
        self._local = threading.local()
        
        self.base_domain = base_domain
        self.base_path = ""
        if base_domain and "://" in base_domain:
            parsed = urlparse(base_domain)
            self.base_domain = parsed.netloc
            # Lock the crawler strictly to the provided subdirectory path (e.g. /repo or /blog)
            path = parsed.path
            if path and path != "/":
                self.base_path = path

        conn = self._get_conn()
        conn.execute("CREATE TABLE IF NOT EXISTS queue (id INTEGER PRIMARY KEY, url TEXT, depth INTEGER)")
        conn.execute("CREATE TABLE IF NOT EXISTS visited (url TEXT PRIMARY KEY)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_visited ON visited(url)")
        conn.commit()

    def _get_conn(self):
        if not hasattr(self._local, 'conn'):
            self._local.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._local.conn.execute("PRAGMA journal_mode=WAL")
        return self._local.conn

    def add(self, url, depth=0, force_add=False):
        if not url:
            return
        
        if self.base_domain and not force_add:
            parsed = urlparse(url)
            if parsed.netloc and parsed.netloc != self.base_domain:
                return
            if self.base_path and not parsed.path.startswith(self.base_path) and parsed.path != self.base_path:
                return

        conn = self._get_conn()
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM visited WHERE url = ?", (url,))
        if cur.fetchone():
            return
            
        cur.execute("INSERT OR IGNORE INTO visited (url) VALUES (?)", (url,))
        cur.execute("INSERT INTO queue (url, depth) VALUES (?, ?)", (url, depth))
        conn.commit()

    def get(self):
        conn = self._get_conn()
        cur = conn.cursor()
        cur.execute("SELECT id, url, depth FROM queue ORDER BY id ASC LIMIT 1")
        row = cur.fetchone()
        if row:
            cur.execute("DELETE FROM queue WHERE id = ?", (row[0],))
            conn.commit()
            return {"url": row[1], "depth": row[2]}
        return None

    def size(self):
        cur = self._get_conn().cursor()
        cur.execute("SELECT COUNT(*) FROM queue")
        row = cur.fetchone()
        return row[0] if row else 0

    def peek(self):
        cur = self._get_conn().cursor()
        cur.execute("SELECT url FROM queue ORDER BY id ASC LIMIT 1")
        row = cur.fetchone()
        return row[0] if row else None

    def get_visited(self):
        cur = self._get_conn().cursor()
        cur.execute("SELECT url FROM visited LIMIT 1")
        row = cur.fetchone()
        return [row[0]] if row else []


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
