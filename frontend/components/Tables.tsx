"use client";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { get, planAction, post } from "@/lib/api";

type Alert = { id: string; severity: string; title: string; source: string; confidence: number; status: string };
type Plan = { id: string; status: string; prompt: string; blast_radius: number; plan: { summary?: string; policy_violations?: { rule: string; message: string }[] } };

type Explain = { root_cause: string; next_steps: string[]; confidence: string; sources: string[]; retrieval: string };

export function Alerts({ token }: { token: string }) {
  const [rows, setRows] = useState<Alert[]>([]); const [exp, setExp] = useState<Record<string, Explain | string>>({});
  useEffect(() => { get<Alert[]>(token, "/api/alerts").then(setRows).catch(() => {}); }, [token]);
  async function explain(id: string) {
    setExp(e => ({ ...e, [id]: "Analyzing…" }));
    try { const r = await post<Explain>(token, `/api/alerts/${id}/explain`); setExp(e => ({ ...e, [id]: r })); }
    catch (err) { setExp(e => ({ ...e, [id]: (err as Error).message })); }
  }
  return (
    <div className="space-y-2">
      {rows.map(a => (
        <div key={a.id} className="rounded-lg border border-white/15 p-4 text-sm">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div><b className="font-medium">{a.title}</b><span className="ml-2 text-muted">{a.severity} · {a.source} · {(a.confidence * 100).toFixed(0)}%</span></div>
            <Button variant="ghost" className="h-8 px-3 text-xs" onClick={() => explain(a.id)}>Explain with AI</Button>
          </div>
          {typeof exp[a.id] === "string" && <p className="mt-2 text-muted">{exp[a.id] as string}</p>}
          {exp[a.id] && typeof exp[a.id] === "object" && (() => { const x = exp[a.id] as Explain; return (
            <div className="mt-3 space-y-2 border-t border-white/10 pt-3">
              <p>{x.root_cause}</p>
              <ul className="list-disc pl-5 text-muted">{x.next_steps?.map((n, i) => <li key={i}>{n}</li>)}</ul>
              <p className="text-xs text-muted">Confidence {x.confidence} · retrieval {x.retrieval} · sources: {x.sources.join(", ") || "none"}</p>
            </div>); })()}
        </div>))}
      {!rows.length && <p className="py-6 text-muted">No alerts yet. The CNN sweep runs every 15 minutes.</p>}
    </div>);
}

export function Plans({ token }: { token: string }) {
  const [rows, setRows] = useState<Plan[]>([]); const [msg, setMsg] = useState("");
  const load = () => get<Plan[]>(token, "/api/plans").then(setRows).catch(() => {});
  useEffect(() => { load(); }, [token]);
  async function act(id: string, a: "approve" | "reject") { try { await planAction(token, id, a); setMsg(`Plan ${a}d`); load(); } catch (e) { setMsg((e as Error).message); } }
  return (
    <div className="space-y-3">{msg && <p className="text-sm text-muted">{msg}</p>}
      {rows.map(p => (
        <div key={p.id} className="rounded-lg border border-white/15 p-4 text-sm">
          <div className="flex items-center justify-between"><b className="font-medium">{p.plan.summary ?? p.prompt}</b><span className="text-muted">{p.status.replace("_", " ")} · blast {p.blast_radius}</span></div>
          {p.plan.policy_violations?.length ? <p className="mt-2 text-red-300">Policy: {p.plan.policy_violations.map(v => v.message).join("; ")}</p> : null}
          {p.status === "pending_approval" && <div className="mt-3 flex gap-2"><Button onClick={() => act(p.id, "approve")}>Approve</Button><Button variant="danger" onClick={() => act(p.id, "reject")}>Reject</Button></div>}
        </div>))}
      {!rows.length && <p className="text-muted">No plans yet. Ask the Copilot to audit or optimize something.</p>}
    </div>);
}
