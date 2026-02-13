"""
Rate limiting middleware for FastAPI applications.

Provides IP-based and user-based rate limiting to prevent abuse and ensure fair usage.
"""

import asyncio
import json
import os
from typing import Dict, Optional, Callable
from functools import wraps

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse


# ============================================================================
# Configuration
# ============================================================================

# Rate limit configurations per endpoint
RATE_LIMITS = {
    "default": "100 per minute",
    "audit_estimate": "10 per minute",
    "audit_run": "30 per minute",
    "credit_purchase": "5 per minute",
    "webhook": "10 per minute",
}

REDIS_URL = os.getenv("REDIS_URL")

# ============================================================================
# In-Memory Rate Limiter (fallback when Redis unavailable)
# ============================================================================

class InMemoryRateLimiter:
    """Thread-safe in-memory rate limiter for development/testing."""

    def __init__(self):
        self._requests: Dict[str, list[float]] = {}
        self._lock = asyncio.Lock()

    async def is_allowed(
        self,
        key: str,
        limit: int,
        window: int = 60
    ) -> tuple[bool, Dict[str, int]]:
        """
        Check if request is allowed under rate limit.

        Returns:
            (allowed, info) tuple where info contains metadata
        """
        async with self._lock:
            now = asyncio.get_event_loop().time()

            # Initialize key if not exists
            if key not in self._requests:
                self._requests[key] = []

            # Remove expired entries outside window
            window_start = now - window
            self._requests[key] = [
                timestamp for timestamp in self._requests[key]
                if timestamp > window_start
            ]

            # Check if under limit
            current_count = len(self._requests[key])
            if current_count >= limit:
                return False, {
                    "limit": limit,
                    "remaining": 0,
                    "reset": int(window_start + window)
                }

            # Add current request
            self._requests[key].append(now)

            return True, {
                "limit": limit,
                "remaining": limit - current_count - 1,
                "reset": int(now + window)
            }


# ============================================================================
# Rate Limiter Class
# ============================================================================

class RateLimiter:
    """
    Configurable rate limiter with multiple strategies.

    Supports both Redis (distributed) and in-memory (fallback) storage.
    """

    def __init__(
        self,
        default_limit: str = "100 per minute",
        redis_url: Optional[str] = None,
        storage_url: Optional[str] = None,
        burst_requests: int = 10,
        burst_period: int = 60,
        skip_successful: bool = False,
        skip_failed: bool = False,
        key_prefix: str = "rate_limit",
        headers: Optional[Dict[str, str]] = None,
        description: Optional[str] = None,
        block: bool = False,
    ):
        """
        Initialize the rate limiter.

        Args:
            default_limit: Default requests per minute (per strategy)
            redis_url: Optional Redis URL for distributed rate limiting
            storage_url: Optional Redis URL for distributed rate limiting
            burst_requests: Max requests allowed in burst period
            burst_period: Seconds in burst period
            skip_successful: Don't count successful requests toward rate limit
            skip_failed: Don't count failed requests toward rate limit
            key_prefix: Prefix for Redis key storage
            headers: Custom headers to add in rate limit responses
            description: Human-readable description
            block: Block status for new rate limiters (maintenance mode)
        """
        self.default_limit = default_limit
        self.redis_url = redis_url or storage_url
        self.burst_requests = burst_requests
        self.burst_period = burst_period
        self.skip_successful = skip_successful
        self.skip_failed = skip_failed
        self.key_prefix = key_prefix
        self.headers = headers
        self.description = description
        self.block = block
        self._memory = InMemoryRateLimiter()
        self._redis_client = None

        if self.redis_url:
            self._init_redis()

    def _init_redis(self) -> None:
        """Initialize Redis connection."""
        try:
            import redis.asyncio as aioredis
            self._redis_client = aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
        except ImportError:
            self._redis_client = None

    def _get_key(self, identifier: str, key_func_name: str) -> str:
        """Generate Redis key for rate limiting."""
        return f"{self.key_prefix}:{identifier}:{key_func_name}"

    async def is_blocked(self, identifier: str, request: Request) -> bool:
        """Check if request should be blocked."""
        # Check maintenance mode first
        if self.block:
            raise HTTPException(
                status_code=503,
                detail="Service temporarily unavailable"
            )

        # Check user-specific blocks if configured
        user_blocks = await self._get_user_blocks(request)
        if user_blocks and request.headers.get("X-User-Block") in user_blocks:
            raise HTTPException(
                status_code=403,
                detail="You have exceeded your rate limit"
            )

        return False

    async def _get_user_blocks(self, request: Request) -> Optional[list[str]]:
        """Get user-specific rate limit blocks from Redis or use defaults."""
        if self._redis_client:
            try:
                user_id = await self._get_user_id(request)
                if not user_id:
                    return []
                key = f"{self.key_prefix}:user_blocks:{user_id}"
                blocks_data = await self._redis_client.get(key)
                if blocks_data:
                    data = json.loads(blocks_data)
                    return data.get("blocks", [])
            except Exception:
                return []
        else:
            # Default blocks for new users (in-memory mode)
            return []

    async def _get_user_id(self, request: Request) -> Optional[str]:
        """Extract user ID from request for rate limiting."""
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return None

        # Note: In production, verify with WorkOS
        # For now, return a placeholder
        return None

    async def check_and_increment(
        self,
        identifier: str,
        request: Request,
        increment_by: int = 1
    ) -> bool:
        """
        Check and increment rate limit for a request.

        Returns True if request should be allowed, False if rate limit exceeded.
        """
        if self.block:
            return False

        # Get user identifier for rate limiting
        user_id = await self._get_user_id(request)
        identifier_key = f"{user_id}:{identifier}" if user_id else identifier

        # Check user-specific blocks
        user_blocks = await self._get_user_blocks(request)
        if user_blocks and request.headers.get("X-User-Block") in user_blocks:
            return False

        # Parse default limit (e.g., "100 per minute" -> 100)
        limit = int(self.default_limit.split()[0]) if isinstance(self.default_limit, str) else 100

        # Check rate limit
        if self._redis_client:
            allowed, info = await self._check_redis(identifier_key, limit)
        else:
            allowed, info = await self._check_memory(identifier_key, limit)

        return allowed

    async def _check_redis(self, key: str, limit: int) -> tuple[bool, Dict[str, int]]:
        """Check rate limit using Redis."""
        try:
            current = await self._redis_client.incr(key)
            if current == 1:
                # Set expiry on first request
                await self._redis_client.expire(key, 60)

            allowed = current <= limit
            return allowed, {
                "limit": limit,
                "remaining": max(0, limit - current),
                "reset": 60
            }
        except Exception:
            # Fallback to memory on Redis error
            return await self._check_memory(key, limit)

    async def _check_memory(self, key: str, limit: int) -> tuple[bool, Dict[str, int]]:
        """Check rate limit using in-memory storage."""
        return await self._memory.is_allowed(key, limit, 60)

    async def cleanup_expired_keys(self, identifier: str) -> None:
        """Clean up expired rate limit keys."""
        if not self._redis_client:
            return

        # Redis handles TTL automatically, but we can manually cleanup
        try:
            cursor = "0"
            while cursor != 0:
                cursor, keys = await self._redis_client.scan(
                    cursor=cursor,
                    match=f"{self.key_prefix}:*",
                    count=100
                )
                if keys:
                    # Check TTL and delete expired
                    for key in keys:
                        ttl = await self._redis_client.ttl(key)
                        if ttl == -1:  # No expiry set
                            await self._redis_client.expire(key, 60)
        except Exception:
            pass

    def get_rate_limit_headers(self, remaining: int) -> Dict[str, str]:
        """Get rate limit headers for response."""
        headers = {}
        if remaining > 0:
            headers["X-RateLimit-Remaining"] = str(remaining)
            headers["Retry-After"] = str(max(0, remaining))

        return headers

    @staticmethod
    def _get_rate_limit_config(endpoint: str) -> Dict[str, str]:
        """Get rate limit configuration for an endpoint."""
        config = RATE_LIMITS.get(endpoint, RATE_LIMITS["default"])
        return {
            "limit": config,
            "remaining": config,
            "reset": config,
            "burst": config
        }


# ============================================================================
# Rate Limiter Instance
# ============================================================================

_rate_limiter = RateLimiter(
    default_limit="100 per minute",
    redis_url=REDIS_URL,
    key_prefix="rate_limit",
)


# ============================================================================
# Helper Functions
# ============================================================================

def get_rate_limit_strategy(endpoint: str) -> str:
    """Determine rate limiting strategy for endpoint."""
    if endpoint in RATE_LIMITS:
        return "strict"
    return "default"


def create_rate_limiter(endpoint: str, strategy: str = "default") -> RateLimiter:
    """Create rate limiter for an endpoint."""
    return _rate_limiter


# ============================================================================
# Decorator
# ============================================================================

def rate_limit(
    endpoint: str = "default",
    strategy: str = "default",
    limit: Optional[int] = None,
    burst: Optional[int] = None
):
    """
    Decorator to apply rate limiting to an endpoint.

    Usage:
        @app.get("/api/v1/audit/estimate")
        @rate_limit(endpoint="audit_estimate", limit=10)
        async def estimate_audit(...):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = kwargs.get("request") or (
                args[0] if args and isinstance(args[0], Request) else None
            )

            if not request:
                return await func(*args, **kwargs)

            # Apply rate limiting
            limiter = create_rate_limiter(endpoint, strategy)

            # Check if allowed
            user_id = getattr(request.state, 'user_id', None) if hasattr(request, 'state') else None
            identifier = f"{endpoint}:{user_id}" if user_id else endpoint

            allowed = await limiter.check_and_increment(identifier, request)

            if not allowed:
                raise HTTPException(
                    status_code=429,
                    detail="Rate limit exceeded",
                    headers={
                        "Retry-After": "60",
                        "X-RateLimit-Limit": "100",
                        "X-RateLimit-Remaining": "0",
                    }
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator
