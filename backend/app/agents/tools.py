"""Tool registry shared by the agent swarm and the MCP server."""
from dataclasses import dataclass
from typing import Awaitable, Callable

from sqlalchemy import func, select

from app.agents import crag, terraform
from app.db.models import ManagedResources, SecurityAlerts, TelemetryMetrics
from app.db.session import SessionLocal


@dataclass
class Tool:
    name: str
    description: str
    schema: dict
    fn: Callable[..., Awaitable[object]]
    mcp: bool = True


REGISTRY: dict[str, Tool] = {}


def tool(name: str, description: str, schema: dict, mcp: bool = True):
    def deco(fn):
        REGISTRY[name] = Tool(name, description, {"type": "object", "properties": schema}, fn, mcp)
        return fn
    return deco


@tool("list_resources", "List managed cloud resources with monthly cost.",
      {"provider": {"type": "string", "enum": ["aws", "gcp", "k8s"]}, "limit": {"type": "integer"}})
async def list_resources(provider: str | None = None, limit: int = 25):
    async with SessionLocal() as s:
        q = select(ManagedResources).order_by(ManagedResources.monthly_cost_usd.desc()).limit(limit)
        if provider:
            q = q.where(ManagedResources.provider == provider)
        return [{"id": str(r.id), "name": r.name, "kind": r.kind, "provider": r.provider.value,
                 "monthly_cost_usd": r.monthly_cost_usd, "tags": r.tags} for r in (await s.execute(q)).scalars()]


@tool("metric_summary", "Avg/max of a metric per resource over the last N hours.",
      {"metric": {"type": "string"}, "hours": {"type": "integer"}})
async def metric_summary(metric: str = "cpu", hours: int = 24):
    async with SessionLocal() as s:
        q = (select(TelemetryMetrics.resource_id, func.avg(TelemetryMetrics.value), func.max(TelemetryMetrics.value))
             .where(TelemetryMetrics.metric == metric,
                    TelemetryMetrics.time > func.now() - func.make_interval(0, 0, 0, 0, hours))
             .group_by(TelemetryMetrics.resource_id).limit(50))
        return [{"resource_id": str(r[0]), "avg": round(r[1], 2), "max": round(r[2], 2)} for r in (await s.execute(q)).all()]


@tool("open_alerts", "List open security alerts, highest severity first.", {"limit": {"type": "integer"}})
async def open_alerts(limit: int = 20):
    async with SessionLocal() as s:
        q = select(SecurityAlerts).where(SecurityAlerts.status == "open").order_by(SecurityAlerts.detected_at.desc()).limit(limit)
        return [{"id": str(a.id), "severity": a.severity.value, "title": a.title, "source": a.source,
                 "confidence": a.confidence} for a in (await s.execute(q)).scalars()]


@tool("search_runbooks", "Corrective-RAG search over security benchmarks, runbooks and Terraform state; returns docs plus a confidence verdict.",
      {"query": {"type": "string"}, "k": {"type": "integer"}})
async def search_runbooks(query: str, k: int = 4):
    return await crag.crag_search(query, k)


@tool("terraform_dry_run", "Run terraform plan (never apply) on HCL and return the blast radius.",
      {"hcl": {"type": "string"}}, mcp=False)
async def terraform_dry_run(hcl: str):
    radius, log = await terraform.dry_run(hcl)
    return {"blast_radius": radius, "log": log[-2000:]}


def describe(names: list[str]) -> str:
    return "\n".join(f"- {n}: {REGISTRY[n].description} args={list(REGISTRY[n].schema['properties'])}" for n in names)
