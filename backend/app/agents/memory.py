"""Short-term conversation memory in Redis (per session, 24 h TTL)."""
import json

MAX_TURNS = 20


async def history(r, sid: str, n: int = 8) -> list[dict]:
    raw = await r.lrange(f"mem:{sid}", -n, -1)
    return [json.loads(x) for x in raw]


async def remember(r, sid: str, role: str, content: str) -> None:
    key = f"mem:{sid}"
    await r.rpush(key, json.dumps({"role": role, "content": content[:2000]}))
    await r.ltrim(key, -MAX_TURNS, -1)
    await r.expire(key, 86400)
