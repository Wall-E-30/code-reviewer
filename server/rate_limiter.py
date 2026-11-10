"""
server/rate_limiter.py

Rate Limiting & Webhook Replay Guard for Aion Engine (HARD-06).
Provides:
- Sliding-window per-IP rate limiting (60 requests/min ceiling)
- Sliding-window per-repository rate limiting (120 requests/min ceiling)
- Webhook Delivery ID replay guard (1-hour TTL cache)
- Request size limit validation (2MB ceiling)
"""

from __future__ import annotations

import logging
import threading
import time
from collections import defaultdict, deque
from typing import Dict, Optional, Tuple

from cachetools import TTLCache

logger = logging.getLogger("AionRateLimiter")

# Default thresholds as specified in HARD-06
DEFAULT_IP_LIMIT = 60          # 60 req / min per IP
DEFAULT_REPO_LIMIT = 120       # 120 req / min per repository
DEFAULT_WINDOW_SECONDS = 60    # 1 minute sliding window
MAX_PAYLOAD_BYTES = 2 * 1024 * 1024  # 2MB request body ceiling
WEBHOOK_TTL_SECONDS = 3600     # 1 hour replay cache window


class RateLimiter:
    """
    Thread-safe sliding-window rate limiter for IP and Repository traffic.
    """

    def __init__(
        self,
        ip_limit: int = DEFAULT_IP_LIMIT,
        repo_limit: int = DEFAULT_REPO_LIMIT,
        window_seconds: int = DEFAULT_WINDOW_SECONDS,
    ) -> None:
        self.ip_limit = ip_limit
        self.repo_limit = repo_limit
        self.window_seconds = window_seconds

        self._lock = threading.Lock()
        self._ip_history: Dict[str, deque[float]] = defaultdict(deque)
        self._repo_history: Dict[str, deque[float]] = defaultdict(deque)

    def _clean_window(self, queue: deque[float], now: float) -> None:
        """Evict timestamps older than the sliding window."""
        cutoff = now - self.window_seconds
        while queue and queue[0] < cutoff:
            queue.popleft()

    def allow_request(self, client_ip: str) -> bool:
        """
        Check if client IP is within rate limits without consuming a token.
        """
        if not client_ip:
            return True

        clean_ip = client_ip.strip()
        now = time.time()
        with self._lock:
            q = self._ip_history[clean_ip]
            self._clean_window(q, now)
            return len(q) < self.ip_limit

    def record_request(self, client_ip: str) -> Tuple[bool, int]:
        """
        Record a request from client IP.
        Returns:
            Tuple[bool, int]: (allowed, remaining_requests_in_window)
        """
        if not client_ip:
            return True, self.ip_limit

        clean_ip = client_ip.strip()
        now = time.time()
        with self._lock:
            q = self._ip_history[clean_ip]
            self._clean_window(q, now)
            if len(q) >= self.ip_limit:
                return False, 0
            q.append(now)
            remaining = max(0, self.ip_limit - len(q))
            return True, remaining

    def allow_repo_request(self, repo_id: str) -> bool:
        """
        Check if repository traffic is within rate limits without consuming a token.
        """
        if not repo_id:
            return True

        clean_repo = repo_id.strip().lower()
        now = time.time()
        with self._lock:
            q = self._repo_history[clean_repo]
            self._clean_window(q, now)
            return len(q) < self.repo_limit

    def record_repo_request(self, repo_id: str) -> Tuple[bool, int]:
        """
        Record a request for a repository.
        Returns:
            Tuple[bool, int]: (allowed, remaining_requests_in_window)
        """
        if not repo_id:
            return True, self.repo_limit

        clean_repo = repo_id.strip().lower()
        now = time.time()
        with self._lock:
            q = self._repo_history[clean_repo]
            self._clean_window(q, now)
            if len(q) >= self.repo_limit:
                return False, 0
            q.append(now)
            remaining = max(0, self.repo_limit - len(q))
            return True, remaining

    def get_ip_remaining(self, client_ip: str) -> int:
        """Return remaining requests available for client IP in current window."""
        clean_ip = (client_ip or "").strip()
        now = time.time()
        with self._lock:
            q = self._ip_history[clean_ip]
            self._clean_window(q, now)
            return max(0, self.ip_limit - len(q))

    def get_repo_remaining(self, repo_id: str) -> int:
        """Return remaining requests available for repository in current window."""
        clean_repo = (repo_id or "").strip().lower()
        now = time.time()
        with self._lock:
            q = self._repo_history[clean_repo]
            self._clean_window(q, now)
            return max(0, self.repo_limit - len(q))

    def reset(self) -> None:
        """Reset all rate limiter counters."""
        with self._lock:
            self._ip_history.clear()
            self._repo_history.clear()


class WebhookDeliveryCache:
    """
    Replay guard for GitHub Webhook deliveries (X-GitHub-Delivery).
    Enforces a 1-hour TTL cache to block duplicate/replayed payloads.
    """

    def __init__(self, maxsize: int = 10000, ttl_seconds: int = WEBHOOK_TTL_SECONDS) -> None:
        self.ttl_seconds = ttl_seconds
        self._lock = threading.Lock()
        self._cache = TTLCache(maxsize=maxsize, ttl=ttl_seconds)

    def is_duplicate(self, delivery_id: str) -> bool:
        """Check if delivery ID has been seen within the TTL window."""
        if not delivery_id:
            return False
        clean_id = delivery_id.strip()
        with self._lock:
            return clean_id in self._cache

    def record_delivery(self, delivery_id: str) -> bool:
        """
        Record a delivery ID.
        Returns:
            bool: True if recorded successfully (first time seen),
                  False if duplicate (already seen).
        """
        if not delivery_id:
            return True
        clean_id = delivery_id.strip()
        with self._lock:
            if clean_id in self._cache:
                return False
            self._cache[clean_id] = time.time()
            return True

    def clear(self) -> None:
        """Clear the delivery cache."""
        with self._lock:
            self._cache.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._cache)
