'use strict';
// Fixed-window rate limiter. Uses Upstash Redis (REST) when configured, else per-instance memory.
const mem = new Map();
async function hit(key, windowSec, limit) {
  const url = process.env.UPSTASH_REDIS_REST_URL, token = process.env.UPSTASH_REDIS_REST_TOKEN;
  if (url && token) {
    try {
      const r = await fetch(`${url}/pipeline`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify([['INCR', key], ['EXPIRE', key, String(windowSec), 'NX']]),
      });
      const j = await r.json();
      return Number(j[0].result) <= limit;
    } catch (_) { /* fall through to memory */ }
  }
  const now = Date.now(), e = mem.get(key);
  if (!e || e.exp < now) { mem.set(key, { n: 1, exp: now + windowSec * 1000 }); return true; }
  e.n += 1;
  if (mem.size > 5000) for (const [k, v] of mem) if (v.exp < now) mem.delete(k);
  return e.n <= limit;
}
module.exports = { hit };
