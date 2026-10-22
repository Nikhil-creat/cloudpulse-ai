import asyncio
import json
import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import Response, StreamingResponse
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from sqlalchemy import Integer, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents import memory
from app.core import forecast
from app.core.metrics import GUARD_BLOCKS
from app.core.security import (Principal, create_token, principal_from_token, require_role, verify_password)
from app.security import guard, totp
from app.security.ratelimit import rate_limit
from app.db.audit import audit
from app.db.models import AIExecutionPlans, PlanStatus, SecurityAlerts, User
from app.db.session import get_session

router = APIRouter(prefix="/api")
SYSTEM = ("You are CloudPulse Copilot, an expert in multi-cloud FinOps, security and observability. "
          "Be concise. Never claim an action was executed: remediation always requires human approval.")
REMEDIATE = re.compile(r"\b(audit|remediat|fix|optimi[sz]e|cost|idle|rightsiz|harden|secure|dry.?run)\b", re.I)


class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    session_id: str = Field(default="default", max_length=64, pattern=r"^[A-Za-z0-9_-]+$")


def sse(event: str, data) -> str:
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"


@router.post("/auth/token")
async def login(request: Request, form: OAuth2PasswordRequestForm = Depends(), session: AsyncSession = Depends(get_session)):
    user = (await session.execute(select(User).where(User.email == form.username))).scalar()
    if not user or not verify_password(form.password, user.password_hash):
        raise HTTPException(401, "Incorrect email or password")
    if user.totp_enabled and not totp.verify(user.totp_secret, request.headers.get("x-otp", "")):
        raise HTTPException(401, "One-time code required or incorrect")
    await audit(session, user.email, "auth.login")
    return {"access_token": create_token(user.email, user.role), "token_type": "bearer", "role": user.role,
            "mfa": user.totp_enabled}


@router.post("/auth/totp/enroll")
async def totp_enroll(session: AsyncSession = Depends(get_session), p: Principal = Depends(require_role("viewer"))):
    user = (await session.execute(select(User).where(User.email == p.sub))).scalar()
    user.totp_secret, user.totp_enabled = totp.new_secret(), False
    await session.commit()
    return {"secret": user.totp_secret, "otpauth_uri": totp.uri(user.totp_secret, user.email)}


class OtpIn(BaseModel):
    code: str = Field(min_length=6, max_length=6)


@router.post("/auth/totp/verify")
async def totp_verify(body: OtpIn, session: AsyncSession = Depends(get_session), p: Principal = Depends(require_role("viewer"))):
    user = (await session.execute(select(User).where(User.email == p.sub))).scalar()
    if not user.totp_secret or not totp.verify(user.totp_secret, body.code):
        raise HTTPException(400, "Invalid code")
    user.totp_enabled = True
    await session.commit()
    await audit(session, p.sub, "auth.mfa_enabled")
    return {"mfa": True}


@router.post("/chat", dependencies=[Depends(rate_limit(30, 60))])
async def chat(body: ChatIn, request: Request, p: Principal = Depends(require_role("viewer"))):
    gw, swarm, r = request.app.state.gateway, request.app.state.swarm, request.app.state.redis
    g = guard.check_input(body.message)
    sid = f"{p.sub}:{body.session_id}"

    async def gen():
        if g.blocked:
            for reason in g.reasons:
                GUARD_BLOCKS.labels(reason=reason[:24]).inc()
            yield sse("error", "Blocked by the LLM firewall: the message looks like a prompt-injection attempt.")
            yield sse("done", True)
            return
        if g.redactions:
            yield sse("status", f"Redacted sensitive values before sending: {', '.join(g.redactions)}")
        try:
            if REMEDIATE.search(g.clean):
                yield sse("status", "Swarm engaged: FinOps + Security agents, then planner and policy critic")
                final = {}
                async for upd in swarm.astream({"request": g.clean, "user": p.sub}, stream_mode="updates"):
                    for node, out in upd.items():
                        for line in out.get("log", []):
                            yield sse("agent", {"node": node, "line": line})
                        if "plan" in out:
                            final = out
                if final:
                    yield sse("plan", {"plan_id": final["plan_id"], **final["plan"]})
                    await memory.remember(r, sid, "user", g.clean)
                    await memory.remember(r, sid, "assistant", "Proposed plan: " + str(final["plan"].get("summary", ""))[:500])
            else:
                msgs = [{"role": "system", "content": SYSTEM}, *await memory.history(r, sid),
                        {"role": "user", "content": g.clean}]
                answer = []
                async for tok in gw.stream(msgs, user=p.sub):
                    answer.append(tok)
                    yield sse("token", guard.scrub_output(tok))
                await memory.remember(r, sid, "user", g.clean)
                await memory.remember(r, sid, "assistant", "".join(answer))
        except Exception as e:
            yield sse("error", str(e))
        yield sse("done", True)

    return StreamingResponse(gen(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})


def _plan_dict(r: AIExecutionPlans) -> dict:
    return {"id": str(r.id), "status": r.status.value, "prompt": r.prompt, "plan": r.plan,
            "terraform_hcl": r.terraform_hcl, "dry_run_output": r.dry_run_output,
            "blast_radius": r.blast_radius, "approved_by": r.approved_by, "created_at": r.created_at}


@router.get("/plans")
async def list_plans(s: AsyncSession = Depends(get_session), p: Principal = Depends(require_role("viewer"))):
    rows = (await s.execute(select(AIExecutionPlans).order_by(AIExecutionPlans.created_at.desc()).limit(50))).scalars()
    return [_plan_dict(r) for r in rows]


@router.get("/plans/{plan_id}")
async def get_plan(plan_id: str, s: AsyncSession = Depends(get_session), p: Principal = Depends(require_role("viewer"))):
    r = await s.get(AIExecutionPlans, plan_id)
    if not r:
        raise HTTPException(404, "Plan not found")
    return _plan_dict(r)


@router.post("/plans/{plan_id}/approve")
async def approve(plan_id: str, s: AsyncSession = Depends(get_session), p: Principal = Depends(require_role("operator"))):
    from app.core.config import get_settings
    r = await s.get(AIExecutionPlans, plan_id)
    if not r or r.status != PlanStatus.pending_approval:
        raise HTTPException(409, "Plan is not pending approval")
    if (r.blast_radius > get_settings().blast_radius_max or (r.plan or {}).get("policy_violations")) and p.role != "admin":
        raise HTTPException(403, "Blast radius or policy violations require admin approval")
    if r.created_by == p.sub and p.role != "admin":
        raise HTTPException(403, "Four-eyes rule: a different operator must approve")
    r.status, r.approved_by, r.approved_at = PlanStatus.approved, p.sub, datetime.now(timezone.utc)
    await s.commit()
    await audit(s, p.sub, "plan.approved", plan_id, {"blast": r.blast_radius})
    from app.workers.tasks import apply_plan
    apply_plan.apply_async(args=[plan_id], queue="apply")
    return {"status": "approved", "queued": True}


@router.post("/plans/{plan_id}/reject")
async def reject(plan_id: str, s: AsyncSession = Depends(get_session), p: Principal = Depends(require_role("operator"))):
    r = await s.get(AIExecutionPlans, plan_id)
    if not r or r.status != PlanStatus.pending_approval:
        raise HTTPException(409, "Plan is not pending approval")
    r.status = PlanStatus.rejected
    await s.commit()
    await audit(s, p.sub, "plan.rejected", plan_id)
    return {"status": "rejected"}


@router.get("/alerts")
async def alerts(s: AsyncSession = Depends(get_session), p: Principal = Depends(require_role("viewer"))):
    rows = (await s.execute(select(SecurityAlerts).order_by(SecurityAlerts.detected_at.desc()).limit(100))).scalars()
    return [{"id": str(a.id), "severity": a.severity.value, "title": a.title, "source": a.source,
             "confidence": a.confidence, "status": a.status, "detected_at": a.detected_at} for a in rows]


@router.get("/heatmap/{resource_id}.png")
async def heatmap(resource_id: str, p: Principal = Depends(require_role("viewer"))):
    from app.workers.tasks import heatmap_for
    return Response(heatmap_for(resource_id), media_type="image/png")


@router.websocket("/ws/{channel}")
async def ws(websocket: WebSocket, channel: str, token: str):
    if channel not in {"telemetry", "agent-logs"}:
        return await websocket.close(code=4404)
    try:
        principal_from_token(token)
    except HTTPException:
        return await websocket.close(code=4401)
    await websocket.accept()
    pubsub = websocket.app.state.redis.pubsub()
    await pubsub.subscribe(channel)
    try:
        while True:
            msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if msg:
                await websocket.send_text(msg["data"] if isinstance(msg["data"], str) else msg["data"].decode())
            await asyncio.sleep(0.05)
    except WebSocketDisconnect:
        pass
    finally:
        await pubsub.close()


@router.get("/stats")
async def stats(s: AsyncSession = Depends(get_session), p: Principal = Depends(require_role("viewer"))):
    from sqlalchemy import func
    from app.db.models import LLMUsageTracker, ManagedResources
    n_res, cost = (await s.execute(select(func.count(ManagedResources.id), func.coalesce(func.sum(ManagedResources.monthly_cost_usd), 0)))).one()
    open_alerts = (await s.execute(select(func.count(SecurityAlerts.id)).where(SecurityAlerts.status == "open"))).scalar()
    pending = (await s.execute(select(func.count(AIExecutionPlans.id)).where(AIExecutionPlans.status == PlanStatus.pending_approval))).scalar()
    since = func.now() - func.make_interval(0, 0, 0, 0, 24)
    llm = (await s.execute(select(func.count(LLMUsageTracker.id), func.coalesce(func.sum(LLMUsageTracker.cost_usd), 0),
                                  func.coalesce(func.avg(LLMUsageTracker.cache_hit.cast(Integer)), 0))
                           .where(LLMUsageTracker.ts > since))).one()
    return {"resources": n_res, "monthly_cost_usd": float(cost), "open_alerts": open_alerts, "pending_plans": pending,
            "llm_requests_24h": llm[0], "llm_cost_24h_usd": float(llm[1]), "cache_hit_rate": float(llm[2])}


@router.get("/finops/forecast")
async def finops_forecast(s: AsyncSession = Depends(get_session), p: Principal = Depends(require_role("viewer"))):
    from sqlalchemy import func
    from app.db.models import TelemetryMetrics
    day = func.date_trunc("day", TelemetryMetrics.time)
    rows = (await s.execute(select(day, func.sum(TelemetryMetrics.value)).where(TelemetryMetrics.metric == "cost_hourly")
                            .group_by(day).order_by(day).limit(60))).all()
    daily = [float(r[1]) for r in rows]
    now = datetime.now(timezone.utc)
    return {"history": [{"day": r[0].date().isoformat(), "cost": float(r[1])} for r in rows],
            "forecast_7d": forecast.ewma_forecast(daily, 7), "anomaly_days": forecast.zscore_anomalies(daily),
            "month_end_projection": forecast.month_end_projection(daily, now.day)}


@router.get("/usage")
async def usage(s: AsyncSession = Depends(get_session), p: Principal = Depends(require_role("operator"))):
    from sqlalchemy import func
    from app.db.models import LLMUsageTracker
    rows = (await s.execute(select(LLMUsageTracker.provider, func.count(), func.sum(LLMUsageTracker.prompt_tokens + LLMUsageTracker.completion_tokens),
                                   func.sum(LLMUsageTracker.cost_usd), func.avg(LLMUsageTracker.latency_ms))
                            .group_by(LLMUsageTracker.provider))).all()
    return [{"provider": r[0], "requests": r[1], "tokens": int(r[2] or 0), "cost_usd": float(r[3] or 0), "avg_latency_ms": float(r[4] or 0)} for r in rows]
