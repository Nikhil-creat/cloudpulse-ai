"""LangGraph multi-agent swarm: triage -> (FinOps || Security) -> Remediation Planner -> HITL gate."""
import json
import operator
import re
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph

from app.agents import terraform
from app.security import guard, policy
from app.agents.tools import REGISTRY, describe
from app.core.config import get_settings
from app.db.audit import audit
from app.db.models import AIExecutionPlans
from app.db.session import SessionLocal

FINOPS_TOOLS = ["list_resources", "metric_summary", "search_runbooks"]
SEC_TOOLS = ["open_alerts", "search_runbooks", "list_resources"]


class State(TypedDict, total=False):
    request: str
    user: str
    findings: Annotated[list, operator.add]
    log: Annotated[list, operator.add]
    plan_id: str
    plan: dict


def _json(text: str) -> dict:
    m = re.search(r"\{.*\}", text, re.S)
    try:
        return json.loads(m.group(0)) if m else {}
    except json.JSONDecodeError:
        return {}


async def agent_loop(gw, role: str, system: str, request: str, tools: list[str], steps: int = 4) -> tuple[str, list]:
    """ReAct-style loop with provider-agnostic JSON tool calls."""
    sys = (f"{system}\nTools:\n{describe(tools)}\nReply ONLY with JSON: "
           '{"tool":"name","args":{}} to call a tool, or {"final":"your findings"} when done.')
    msgs = [{"role": "system", "content": sys}, {"role": "user", "content": request}]
    trace = []
    for _ in range(steps):
        out = _json((await gw.complete(msgs, task="tool_call", use_cache=False)).text)
        if "final" in out:
            return str(out["final"]), trace
        name = out.get("tool")
        if name not in tools:
            break
        try:
            result = await REGISTRY[name].fn(**(out.get("args") or {}))
        except Exception as e:
            result = {"error": str(e)}
        trace.append(f"{role} called {name}")
        msgs += [{"role": "assistant", "content": json.dumps(out)},
                 {"role": "user", "content": guard.fence_untrusted(name, guard.scrub_output(json.dumps(result, default=str))[:6000])}]
    return "No conclusive findings.", trace


def build_swarm(gw):
    async def triage(st: State):
        return {"log": [f"triage: received '{st['request'][:80]}'"]}

    async def finops(st: State):
        text, tr = await agent_loop(gw, "finops", "You are the FinOps Cost Optimizer. Find idle/oversized resources "
                                    "and quantify monthly savings.", st["request"], FINOPS_TOOLS)
        return {"findings": [{"agent": "finops", "text": text}], "log": tr + ["finops: done"]}

    async def security(st: State):
        text, tr = await agent_loop(gw, "security", "You are the Security Compliance Auditor. Map issues to CIS "
                                    "controls and rank by severity.", st["request"], SEC_TOOLS)
        return {"findings": [{"agent": "security", "text": text}], "log": tr + ["security: done"]}

    async def planner(st: State):
        prompt = ("You are the Remediation Planner. From the findings propose a minimal, reversible plan. "
                  'Reply ONLY JSON: {"summary":str,"steps":[{"action":str,"risk":"low|medium|high"}],"terraform_hcl":str}\n'
                  f"Request: {st['request']}\nFindings: {json.dumps(st.get('findings', []))}")
        res = await gw.complete([{"role": "user", "content": prompt}], task="reasoning", use_cache=False)
        plan = _json(res.text) or {"summary": res.text[:500], "steps": [], "terraform_hcl": ""}
        hcl = plan.get("terraform_hcl", "")
        # Critic agent: policy-as-code gate with one self-correction pass
        violations = policy.check(hcl)
        if violations:
            fix = await gw.complete([{"role": "user", "content":
                "Revise this Terraform so it fixes every violation. Reply ONLY the HCL.\nViolations: "
                + json.dumps(violations) + "\nHCL:\n" + hcl}], task="reasoning", use_cache=False)
            hcl = re.sub(r"^```\w*\n|```$", "", fix.text.strip(), flags=re.M)
            plan["terraform_hcl"] = hcl
            violations = policy.check(hcl)
        plan["policy_violations"] = violations
        radius, log = await terraform.dry_run(hcl) if hcl else ({"score": 0}, "no terraform generated")
        async with SessionLocal() as s:
            row = AIExecutionPlans(prompt=st["request"], created_by=st.get("user", "system"), plan=plan,
                                   terraform_hcl=hcl, dry_run_output=log[-4000:], blast_radius=radius["score"])
            s.add(row)
            await s.commit()
            await audit(s, st.get("user", "system"), "plan.proposed", str(row.id), {"blast": radius})
        gated = bool(violations) or radius["score"] > get_settings().blast_radius_max
        return {"plan": {**plan, "blast_radius": radius, "requires_admin": gated},
                "plan_id": str(row.id), "log": [f"planner: plan {row.id} awaiting human approval"]}

    g = StateGraph(State)
    for n, f in [("triage", triage), ("finops", finops), ("security", security), ("planner", planner)]:
        g.add_node(n, f)
    g.add_edge(START, "triage")
    g.add_edge("triage", "finops")
    g.add_edge("triage", "security")
    g.add_edge("finops", "planner")
    g.add_edge("security", "planner")
    g.add_edge("planner", END)  # HITL gate = plan stays pending_approval until /api/plans/{id}/approve
    return g.compile()
