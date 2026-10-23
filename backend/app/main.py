from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app

from app.agents import crag
from app.agents.swarm import build_swarm
from app.api import mcp, routes
from app.core.config import get_settings
from app.core.metrics import LLM_COST, LLM_LATENCY, LLM_REQUESTS, LLM_TOKENS
from app.core.observability import setup_otel
from app.db.models import LLMUsageTracker
from app.db.session import SessionLocal, init_db
from app.llm.gateway import build_gateway
from app.security.middleware import SecurityMiddleware


async def track_usage(res, task, user):
    LLM_REQUESTS.labels(res.provider, task, str(res.cache_hit).lower(), str(res.failover).lower()).inc()
    LLM_LATENCY.labels(res.provider).observe(res.latency_ms / 1000)
    LLM_COST.labels(res.provider).inc(res.cost_usd)
    LLM_TOKENS.labels(res.provider, "prompt").inc(res.prompt_tokens)
    LLM_TOKENS.labels(res.provider, "completion").inc(res.completion_tokens)
    async with SessionLocal() as s:
        s.add(LLMUsageTracker(provider=res.provider, model=res.model, task=task, prompt_tokens=res.prompt_tokens,
                              completion_tokens=res.completion_tokens, latency_ms=res.latency_ms,
                              cost_usd=res.cost_usd, cache_hit=res.cache_hit, failover=res.failover, user=user))
        await s.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    app.state.redis = aioredis.from_url(get_settings().redis_url, decode_responses=True)
    app.state.gateway = build_gateway(app.state.redis, track_usage)
    crag.set_gateway(app.state.gateway)
    app.state.swarm = build_swarm(app.state.gateway)
    try:  # seed the knowledge base on first boot
        from app.agents import rag
        from app.knowledge.seed import DOCS
        c = rag.client()
        if not await c.collection_exists(rag.COLLECTION):
            await rag.ingest(DOCS)
    except Exception:
        pass
    yield
    await app.state.redis.aclose()


app = FastAPI(title="CloudPulse AI", version="2.2.0", lifespan=lifespan)
app.add_middleware(SecurityMiddleware)
app.add_middleware(CORSMiddleware, allow_origins=get_settings().cors_origins.split(","),
                   allow_methods=["GET", "POST"], allow_headers=["Authorization", "Content-Type", "X-OTP"],
                   allow_credentials=True)
app.include_router(routes.router)
app.include_router(mcp.router)
app.mount("/metrics", make_asgi_app())  # block at the reverse proxy; scrape on the internal network only
setup_otel(app)


@app.get("/healthz")
async def healthz():
    return {"status": "ok", "version": app.version}
