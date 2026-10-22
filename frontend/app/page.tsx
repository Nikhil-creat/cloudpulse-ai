"use client";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import ChatPanel from "@/components/ChatPanel";
import Overview from "@/components/Overview";
import Security from "@/components/Security";
import { Alerts, Plans } from "@/components/Tables";
import { login } from "@/lib/api";

const TABS = ["Overview", "Copilot", "Alerts", "Plans", "Security"] as const;

export default function Home() {
  const [token, setToken] = useState<string | null>(null);
  const [tab, setTab] = useState<(typeof TABS)[number]>("Overview");
  const [email, setEmail] = useState(""); const [pw, setPw] = useState(""); const [otp, setOtp] = useState(""); const [err, setErr] = useState("");
  const field = "h-10 rounded-md border border-white/20 bg-transparent px-3 text-sm";

  if (!token) return (
    <main className="mx-auto flex min-h-[70vh] max-w-sm flex-col justify-center gap-3 px-6">
      <h1 className="text-2xl font-medium tracking-tight">Sign in to CloudPulse</h1>
      <input aria-label="Email" placeholder="Email" value={email} onChange={e => setEmail(e.target.value)} className={field} />
      <input aria-label="Password" type="password" placeholder="Password" value={pw} onChange={e => setPw(e.target.value)} className={field} />
      <input aria-label="One-time code" placeholder="One-time code (if MFA is on)" value={otp} onChange={e => setOtp(e.target.value)} maxLength={6} className={field} />
      {err && <p className="text-sm text-red-300">{err}</p>}
      <Button onClick={async () => { try { setToken(await login(email, pw, otp || undefined)); } catch { setErr("Sign-in failed. Check your details and one-time code."); } }}>Sign in</Button>
    </main>);

  return (
    <main className="mx-auto max-w-6xl px-6 py-6">
      <div role="tablist" className="mb-6 flex gap-2 overflow-x-auto">
        {TABS.map(t => <button key={t} role="tab" aria-selected={tab === t} onClick={() => setTab(t)}
          className={`h-9 shrink-0 rounded-md border px-4 text-sm ${tab === t ? "border-white/70 bg-white/10" : "border-white/15 text-muted hover:text-white"}`}>{t}</button>)}
      </div>
      {tab === "Overview" && <Overview token={token} />}
      {tab === "Copilot" && <ChatPanel token={token} />}
      {tab === "Alerts" && <Alerts token={token} />}
      {tab === "Plans" && <Plans token={token} />}
      {tab === "Security" && <Security token={token} />}
    </main>);
}
