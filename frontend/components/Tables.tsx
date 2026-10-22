"use client";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { get, planAction } from "@/lib/api";

type Alert = { id: string; severity: string; title: string; source: string; confidence: number; status: string };
type Plan = { id: string; status: string; prompt: string; blast_radius: number; plan: { summary?: string; policy_violations?: { rule: string; message: string }[] } };

export function Alerts({ token }: { token: string }) {
  const [rows, setRows] = useState<Alert[]>([]);
  useEffect(() => { get<Alert[]>(token, "/api/alerts").then(setRows).catch(() => {}); }, [token]);
  return (
    <table className="w-full text-sm"><thead className="text-left text-muted"><tr><th className="py-2">Severity</th><th>Alert</th><th>Source</th><th>Confidence</th></tr></thead>
      <tbody>{rows.map(a => <tr key={a.id} className="border-t border-white/10"><td className="py-2">{a.severity}</td><td>{a.title}</td><td>{a.source}</td><td>{(a.confidence * 100).toFixed(0)}%</td></tr>)}
        {!rows.length && <tr><td colSpan={4} className="py-6 text-muted">No alerts yet. The CNN sweep runs every 15 minutes.</td></tr>}</tbody></table>);
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
