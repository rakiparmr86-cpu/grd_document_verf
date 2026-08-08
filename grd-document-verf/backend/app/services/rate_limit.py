from __future__ import annotations

from dataclasses import dataclass
from time import time
from typing import Annotated

from fastapi import Depends, HTTPException, Request, Response, status
from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.core.config import settings
from app.core.security import AuthContext, get_auth_context

INCREMENT_WITH_EXPIRY = """
local current = redis.call('INCR', KEYS[1])
if current == 1 then
    redis.call('EXPIRE', KEYS[1], ARGV[1])
end
local ttl = redis.call('TTL', KEYS[1])
return {current, ttl}
"""

_redis_client: Redis | None = None


@dataclass(frozen=True)
class RateLimitRule:
    identity: str
    limit: int


@dataclass(frozen=True)
class RateLimitUsage:
    limit: int
    current: int
    retry_after: int

    @property
    def remaining(self) -> int:
        return max(self.limit - self.current, 0)


def _get_redis_client() -> Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = Redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=settings.rate_limit_redis_timeout_seconds,
            socket_timeout=settings.rate_limit_redis_timeout_seconds,
        )
    return _redis_client


async def close_rate_limit_client() -> None:
    global _redis_client
    client = _redis_client
    _redis_client = None
    if client is not None:
        await client.aclose()


async def _consume(
    scope: str,
    rules: list[RateLimitRule],
    window_seconds: int,
) -> list[RateLimitUsage]:
    timestamp = int(time())
    window_id = timestamp // window_seconds
    retry_after = window_seconds - (timestamp % window_seconds)
    expiry = retry_after + 1
    client = _get_redis_client()
    usages: list[RateLimitUsage] = []

    try:
        for rule in rules:
            key = f"grd:rate-limit:{scope}:{rule.identity}:{window_id}"
            current, ttl = await client.eval(
                INCREMENT_WITH_EXPIRY,
                1,
                key,
                expiry,
            )
            usages.append(
                RateLimitUsage(
                    limit=rule.limit,
                    current=int(current),
                    retry_after=max(int(ttl), 1),
                )
            )
    except RedisError as exc:
        if settings.rate_limit_fail_open:
            return []
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Rate limiting service is unavailable",
        ) from exc

    exceeded = [usage for usage in usages if usage.current > usage.limit]
    if exceeded:
        wait_seconds = max(usage.retry_after for usage in exceeded)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Try again later.",
            headers={
                "Retry-After": str(wait_seconds),
                "X-RateLimit-Limit": str(min(usage.limit for usage in usages)),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(wait_seconds),
            },
        )
    return usages


def _set_headers(response: Response, usages: list[RateLimitUsage]) -> None:
    if not usages:
        return
    response.headers["X-RateLimit-Limit"] = str(
        min(usage.limit for usage in usages)
    )
    response.headers["X-RateLimit-Remaining"] = str(
        min(usage.remaining for usage in usages)
    )
    response.headers["X-RateLimit-Reset"] = str(
        max(usage.retry_after for usage in usages)
    )


async def enforce_api_rate_limit(
    response: Response,
    context: Annotated[AuthContext, Depends(get_auth_context)],
) -> AuthContext:
    if not settings.rate_limit_enabled:
        return context
    usages = await _consume(
        "api",
        [
            RateLimitRule(
                f"tenant:{context.tenant_id}:user:{context.user_id}",
                settings.api_rate_limit_user_requests,
            ),
            RateLimitRule(
                f"tenant:{context.tenant_id}",
                settings.api_rate_limit_tenant_requests,
            ),
        ],
        settings.api_rate_limit_window_seconds,
    )
    _set_headers(response, usages)
    return context


async def enforce_upload_rate_limit(
    response: Response,
    context: Annotated[AuthContext, Depends(get_auth_context)],
) -> AuthContext:
    if not settings.rate_limit_enabled:
        return context
    usages = await _consume(
        "upload",
        [
            RateLimitRule(
                f"tenant:{context.tenant_id}:user:{context.user_id}",
                settings.upload_rate_limit_user_requests,
            ),
            RateLimitRule(
                f"tenant:{context.tenant_id}",
                settings.upload_rate_limit_tenant_requests,
            ),
        ],
        settings.upload_rate_limit_window_seconds,
    )
    _set_headers(response, usages)
    return context


async def enforce_login_rate_limit(request: Request, response: Response) -> None:
    if not settings.rate_limit_enabled:
        return
    client_ip = request.client.host if request.client is not None else "unknown"
    usages = await _consume(
        "login",
        [RateLimitRule(f"ip:{client_ip}", settings.login_rate_limit_requests)],
        settings.login_rate_limit_window_seconds,
    )
    _set_headers(response, usages)
