import asyncio
import json
import subprocess
import tempfile
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import redis
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.cnn.model import METRICS, AnomalyClassifier, build_heatmap, to_png
from app.collectors.clouds import collect
from app.core.config import get_settings
from app.db.audit import audit
from app.db.models import (AIExecutionPlans, CloudCredentials, ManagedResources, PlanStatus, SecurityAlerts,
                           Severity, TelemetryMetrics)
from app.db.session import SessionLocal, SyncSession
from app.workers.celery_app import celery

_clf = None


def classifier() -> AnomalyClassifier:
    global _clf
    if _clf is None:
        _clf = AnomalyClassifier()
    return _clf


def _series(session, resource_id, hours=24):
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    rows = session.execute(select(TelemetryMetrics.metric, TelemetryMetrics.time, TelemetryMetrics.value)
                           .where(TelemetryMetrics.resource_id == resource_id, TelemetryMetrics.time >= since)).all()
    out = {m: [] for m in METRICS}
    for m, t, v in rows:
        out.setdefault(m, []).append((t, v))
    return out


def heatmap_for(resource_id: str) -> bytes:
    with SyncSession() as s:
        return to_png(build_heatmap(_series(s, resource_id)))


@celery.task(name="app.workers.tasks.collect_all")
def collect_all():
    r = redis.from_url(get_settings().redis_url)
    with SyncSession() as s:
        for cred in s.execute(select(CloudCredentials)).scalars():
            secret = json.loads(cred.secret)
            try:
                samples = asyncio.run(collect(cred.provider.value, secret, cred.region))
            except Exception as e:
                r.publish("agent-logs", json.dumps({"node": "collector", "line": f"{cred.name}: {e}"}))
                continue
            ids = {}
            for ext, metric, value, unit, ts in samples:
                if ext not in ids:
                    stmt = insert(ManagedResources).values(credential_id=cred.id, provider=cred.provider,
                                                           external_id=ext, kind="instance", name=ext, region=cred.region)
                    stmt = stmt.on_conflict_do_update(index_elements=["credential_id", "external_id"],
                                                      set_={"last_seen": datetime.now(timezone.utc)}).returning(ManagedResources.id)
                    ids[ext] = s.execute(stmt).scalar()
                s.execute(insert(TelemetryMetrics).values(time=ts, resource_id=ids[ext], metric=metric,
                                                          value=value, unit=unit).on_conflict_do_nothing())
                r.publish("telemetry", json.dumps({"resource": str(ids[ext]), "metric": metric, "value": value,
                                                   "ts": ts.isoformat()}))
            s.commit()


@celery.task(name="app.workers.tasks.run_cnn")
def run_cnn():
    clf, found = classifier(), 0
    with SyncSession() as s:
        for rid in s.execute(select(ManagedResources.id)).scalars().all():
            res = clf.predict(build_heatmap(_series(s, rid)))
            if res["label"] != "normal" and res["confidence"] >= 0.8:
                sev = Severity.high if res["label"] == "intrusion" else Severity.medium
                s.add(SecurityAlerts(resource_id=rid, severity=sev, source="cnn", confidence=res["confidence"],
                                     title=f"CNN flagged {res['label'].replace('_', ' ')}", evidence=res))
                found += 1
        s.commit()
    return found


@celery.task(name="app.workers.tasks.apply_plan", bind=True, max_retries=0)
def apply_plan(self, plan_id: str):
    """Runs only for APPROVED plans; re-plans then applies the exact saved plan file."""
    async def run():
        async with SessionLocal() as s:
            plan = await s.get(AIExecutionPlans, uuid.UUID(plan_id))
            if not plan or plan.status != PlanStatus.approved or not plan.terraform_hcl:
                return
            with tempfile.TemporaryDirectory() as d:
                Path(d, "main.tf").write_text(plan.terraform_hcl)
                ok = True
                for cmd in (["init", "-input=false", "-no-color"], ["plan", "-input=false", "-out=tfplan", "-no-color"],
                            ["apply", "-input=false", "-no-color", "tfplan"]):
                    p = subprocess.run(["terraform", *cmd], cwd=d, capture_output=True, text=True)
                    plan.dry_run_output = (plan.dry_run_output or "")[-2000:] + "\n" + p.stdout[-2000:]
                    if p.returncode:
                        ok = False
                        break
            plan.status = PlanStatus.applied if ok else PlanStatus.failed
            await s.commit()
            await audit(s, "worker", "plan.applied" if ok else "plan.failed", plan_id)
    asyncio.run(run())
