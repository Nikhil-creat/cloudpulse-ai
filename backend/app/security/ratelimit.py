import time

from fastapi import Depends, HTTPException, Request

from app.core.security import Principal, current_principal


async def allow(redis, key: str, limit: int, window: int) -> bool:
    """Fixed-window counter in Redis."""
    bucket = f"rl:{key}:{int(time.time() // window)}"
    n = await redis.incr(bucket)
    if n == 1:
        await redis.expire(bucket, window + 1)
    return n <= limit


def rate_limit(limit: int, window: int = 60):
    async def dep(request: Request, p: Principal = Depends(current_principal)):
        if not await allow(request.app.state.redis, f"{request.url.path}:{p.sub}", limit, window):
            raise HTTPException(429, f"Rate limit: {limit} requests per {window}s", headers={"Retry-After": str(window)})
    return dep
