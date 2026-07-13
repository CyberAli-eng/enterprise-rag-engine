"""
Authentication and simple in-memory rate limiting.

Auth: API keys passed via the `X-API-Key` header, checked against the
configured allow-list. Keys live only in environment variables / secret
managers — never in source control.

Rate limiting: a lightweight in-memory sliding-window limiter keyed by API
key (or client IP as a fallback). Good enough for a single-instance
deployment; swap for Redis-backed limiting if you scale horizontally.
"""
import time
from collections import defaultdict, deque

from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader

from app.config import get_settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

_request_log: dict[str, deque] = defaultdict(deque)


def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    settings = get_settings()

    # If no keys are configured (e.g. local dev), allow through but warn via env check.
    if not settings.api_key_list:
        return "anonymous"

    if not api_key or api_key not in settings.api_key_list:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid API key",
        )
    return api_key


def enforce_rate_limit(request: Request, api_key: str = Depends(verify_api_key)) -> None:
    settings = get_settings()
    limit = settings.rate_limit_per_minute
    now = time.time()
    window = 60.0

    identity = api_key if api_key != "anonymous" else (request.client.host if request.client else "unknown")
    log = _request_log[identity]

    while log and now - log[0] > window:
        log.popleft()

    if len(log) >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Try again shortly.",
        )
    log.append(now)
