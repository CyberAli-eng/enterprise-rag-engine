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
from typing import Optional

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


def authorize_tenant(api_key: str, requested: Optional[str]) -> str:
    """Return the tenant this request may use, or raise 400/403.

    Keys listed in API_KEY_TENANTS may only use their own tenants ("*" = all). A key
    bound to exactly one tenant doesn't need to send tenant_id. Unlisted keys keep the
    legacy behaviour (any tenant) unless STRICT_TENANT_BINDING is on.
    """
    settings = get_settings()
    if not settings.api_key_list:  # no API_KEYS configured (local development)
        return requested or "default"

    allowed = settings.api_key_tenants.get(api_key)
    if allowed is None:
        if settings.strict_tenant_binding:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="This API key is not bound to any tenant")
        return requested or "default"

    if "*" in allowed:
        return requested or "default"
    if requested is None:
        if len(allowed) == 1:
            return allowed[0]
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="tenant_id is required: this API key can access several tenants")
    if requested not in allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail=f"This API key may not access tenant '{requested}'")
    return requested
