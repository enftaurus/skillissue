import time
from collections import defaultdict
from typing import Callable, Dict, List, Optional
from fastapi import Request, Response, HTTPException, status
import threading

class SlidingWindowRateLimiter:
    def __init__(self):
        self._lock = threading.Lock()
        # key -> list of timestamps
        self._requests: Dict[str, List[float]] = defaultdict(list)

    def is_allowed(self, key: str, max_requests: int, window_seconds: int) -> tuple[bool, int, int]:
        """
        Check if request is allowed under sliding window.
        Returns: (is_allowed, remaining_requests, retry_after_seconds)
        """
        now = time.time()
        window_start = now - window_seconds

        with self._lock:
            # Filter out timestamps outside window
            timestamps = [ts for ts in self._requests[key] if ts > window_start]
            
            if len(timestamps) >= max_requests:
                # Oldest timestamp in window determines retry-after
                oldest_in_window = timestamps[0]
                retry_after = max(1, int(oldest_in_window + window_seconds - now))
                self._requests[key] = timestamps
                return False, 0, retry_after

            # Allow request
            timestamps.append(now)
            self._requests[key] = timestamps
            remaining = max(0, max_requests - len(timestamps))
            return True, remaining, 0

    def cleanup(self, max_age_seconds: int = 3600):
        """Periodically clean up stale keys to prevent memory growth."""
        now = time.time()
        with self._lock:
            stale_keys = [
                k for k, timestamps in self._requests.items()
                if not timestamps or timestamps[-1] < (now - max_age_seconds)
            ]
            for k in stale_keys:
                del self._requests[k]

# Global singleton rate limiter instance
limiter = SlidingWindowRateLimiter()

def rate_limit(max_requests: int, window_seconds: int = 60, key_func: Optional[Callable[[Request], str]] = None):
    """
    FastAPI dependency factory enforcing rate limits with standard HTTP 429 response.
    """
    async def dependency(request: Request, response: Response):
        if key_func:
            key = key_func(request)
        else:
            # Default to client host IP
            client_ip = request.client.host if request.client else "unknown"
            # If authenticated user header or state exists, prefer it
            user_id = getattr(request.state, "user_id", None)
            key = f"{request.url.path}:{user_id or client_ip}"

        allowed, remaining, retry_after = limiter.is_allowed(key, max_requests, window_seconds)

        response.headers["X-RateLimit-Limit"] = str(max_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)

        if not allowed:
            response.headers["Retry-After"] = str(retry_after)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded: maximum {max_requests} requests per {window_seconds}s. Try again in {retry_after}s.",
                headers={"Retry-After": str(retry_after), "X-RateLimit-Limit": str(max_requests), "X-RateLimit-Remaining": "0"}
            )

    return dependency
