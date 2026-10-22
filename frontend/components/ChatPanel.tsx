"use client";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { planAction, streamChat } from "@/lib/api";

type Plan = { plan_id: string; summary: string; steps: { action: string; risk: string }[]; blast_radius: { score: number }; requires_admin: boolean };
type Msg = { role: "user" | "ai"; text: string; plan?: Plan; status?: string };

export default function ChatPanel({ token }: { token: string }) {
  const [msgs, setMsgs] = useState<Msg[]>([]); const [input, setInput] = useState(""); const [busy, setBusy] = useState(false);
  const patch = (fn: (m: Msg) => Msg) => setMsgs(ms => ms.map((m, i) => (i === ms.length - 1 ? fn(m) : m)));

  async function send() {
    if (!input.trim() || busy) return;
    const q = input; setInput(""); setBusy(true);
    setMsgs(m => [...m, { role: "user", text: q }, { role: "ai", text: "" }]);
    try {
      for await (const { event, data } of streamChat(token, q)) {
        if (event === "token") patch(m => ({ ...m, text: m.text + data }));
        if (event === "agent") patch(m => ({ ...m, status: `${data.node}: ${data.line}` }));
        if (event === "plan") patch(m => ({ ...m, text: data.summary, plan: data }));
        if (event === "error") patch(m => ({ ...m, text: `Error: ${data}` }));
      }
    } finally { setBusy(false); }
  }

  async function decide(id: string, a: "approve" | "reject") {
    try { await planAction(token, id, a); patch(m => ({ ...m, status: `Plan ${a}d` })); }
    catch (e) { patch(m => ({ ...m, status: (e as Error).message })); }
  }

  return (
    <div className="flex h-[28rem] flex-col rounded-lg border border-white/15">
      <div className="flex-1 space-y-3 overflow-y-auto p-4 text-sm">
        {msgs.length === 0 && <p className="text-muted">Ask: “Audit my S3 buckets and find idle EC2 instances.”</p>}
        {msgs.map((m, i) => (
          <div key={i} className={m.role === "user" ? "text-right" : ""}>
            <div className={`inline-block max-w-[85%] rounded-md px-3 py-2 text-left ${m.role === "user" ? "bg-white text-black" : "bg-white/5"}`}>
              {m.text || m.status || "…"}
              {m.plan && (
                <div className="mt-3 space-y-2 border-t border-white/10 pt-3">
                  {m.plan.steps.map((s, k) => <div key={k}>• {s.action} <span className="text-muted">({s.risk})</span></div>)}
                  <div className="text-muted">Blast radius score {m.plan.blast_radius.score}{m.plan.requires_admin && " · admin approval required"}</div>
                  <div className="flex gap-2">
                    <Button onClick={() => decide(m.plan!.plan_id, "approve")}>Approve</Button>
                    <Button variant="danger" onClick={() => decide(m.plan!.plan_id, "reject")}>Reject</Button>
                  </div>
                  {m.status && <div className="text-muted">{m.status}</div>}
                </div>)}
            </div>
          </div>))}
      </div>
      <div className="flex gap-2 border-t border-white/10 p-3">
        <input value={input} onChange={e => setInput(e.target.value)} onKeyDown={e => e.key === "Enter" && send()}
          placeholder="Ask CloudPulse Copilot…" className="h-10 flex-1 rounded-md border border-white/20 bg-transparent px-3 text-sm outline-none focus:border-white/60" />
        <Button onClick={send} disabled={busy}>Send</Button>
      </div>
    </div>);
}
