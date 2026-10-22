"""python -m scripts.seed_demo  ->  fills the console with realistic demo data (idempotent)."""
import json
import random
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.cnn.model import METRICS, REF_MAX, synth
from app.db.models import (AIExecutionPlans, CloudCredentials, ManagedResources, PlanStatus, Provider,
                           SecurityAlerts, Severity, TelemetryMetrics)
from app.db.session import SyncSession, init_db_sync

FLEET = [("web-1", "ec2", "normal", 61.0), ("api-2", "ec2", "cost_spike", 244.0), ("batch-3", "ec2", "idle", 138.0),
         ("db-1", "rds", "normal", 312.0), ("bastion", "ec2", "intrusion", 29.0), ("pod-payments", "pod", "normal", 18.0)]


def main():
    init_db_sync()
    rng, np_rng = random.Random(42), __import__("numpy").random.default_rng(42)
    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    with SyncSession() as s:
        cred = s.execute(select(CloudCredentials).where(CloudCredentials.name == "demo-aws")).scalar()
        if cred:
            print("demo data already present")
            return
        cred = CloudCredentials(name="demo-aws", provider=Provider.aws, secret=json.dumps({"demo": True}), region="us-east-1")
        s.add(cred)
        s.flush()
        rows, ids = [], {}
        for name, kind, pattern, cost in FLEET:
            r = ManagedResources(credential_id=cred.id, provider=Provider.aws if kind != "pod" else Provider.k8s,
                                 external_id=name, kind=kind, name=name, region="us-east-1", monthly_cost_usd=cost,
                                 tags={"env": "prod" if name == "db-1" else "dev", "owner": "platform"})
            s.add(r)
            s.flush()
            ids[name] = (r.id, pattern)
            heat = synth(pattern, np_rng)
            for mi, m in enumerate(METRICS):
                for b in range(96):
                    ts = now - timedelta(hours=24) + timedelta(minutes=15 * b + 1)
                    rows.append({"time": ts, "resource_id": r.id, "metric": m, "value": float(heat[mi, b] * REF_MAX[m]), "unit": None, "labels": {}})
        # 30 days of daily cost with a spike 8 days ago (feeds the forecast chart)
        web = ids["web-1"][0]
        for d in range(2, 31):
            base = 100 + (30 - d) * 0.8 + rng.random() * 6 + (70 if d == 8 else 0)
            rows.append({"time": now - timedelta(days=d, hours=12), "resource_id": web, "metric": "cost_hourly", "value": round(base, 2), "unit": "usd", "labels": {}})
        for i in range(0, len(rows), 1000):
            s.execute(insert(TelemetryMetrics).values(rows[i:i + 1000]).on_conflict_do_nothing())
        s.add_all([
            SecurityAlerts(resource_id=ids["bastion"][0], severity=Severity.high, source="cnn", confidence=0.93,
                           title="CNN flagged intrusion", description="Auth failure burst with outbound traffic spike", evidence={"label": "intrusion"}),
            SecurityAlerts(resource_id=ids["api-2"][0], severity=Severity.medium, source="cnn", confidence=0.88,
                           title="CNN flagged cost spike", description="Hourly cost and CPU jumped together", evidence={"label": "cost_spike"}),
            SecurityAlerts(resource_id=ids["batch-3"][0], severity=Severity.low, source="agent", confidence=0.9,
                           title="Idle instance: batch-3", description="Under 5% CPU for 24 hours; about $138 per month")])
        s.add(AIExecutionPlans(prompt="Find idle EC2 instances and cut cost", created_by="demo", status=PlanStatus.pending_approval,
                               plan={"summary": "Stop batch-3 (idle) and tag it finops:review", "steps": [{"action": "Stop batch-3", "risk": "low"}],
                                     "policy_violations": []}, terraform_hcl='resource "aws_instance" "batch_3" {}', blast_radius=2,
                               dry_run_output="static estimate"))
        s.commit()
    print("seeded 6 resources, telemetry, 3 alerts and 1 pending plan")


if __name__ == "__main__":
    main()
