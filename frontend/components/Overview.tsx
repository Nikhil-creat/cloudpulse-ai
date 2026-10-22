"use client";
import { useEffect, useState } from "react";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import dynamic from "next/dynamic";
import { get } from "@/lib/api";

const ClusterGraph = dynamic(() => import("@/components/ClusterGraph"), { ssr: false });
type Stats = { resources: number; monthly_cost_usd: number; open_alerts: number; pending_plans: number; llm_requests_24h: number; llm_cost_24h_usd: number; cache_hit_rate: number };
type Fc = { history: { day: string; cost: number }[]; forecast_7d: number[]; month_end_projection: number; anomaly_days: number[] };

export default function Overview({ token }: { token: string }) {
  const [s, setS] = useState<Stats | null>(null); const [f, setF] = useState<Fc | null>(null);
  useEffect(() => { get<Stats>(token, "/api/stats").then(setS).catch(() => {}); get<Fc>(token, "/api/finops/forecast").then(setF).catch(() => {}); }, [token]);
  const kpis: [string, string][] = s ? [
    ["Managed resources", String(s.resources)], ["Monthly cost", `$${s.monthly_cost_usd.toFixed(0)}`],
    ["Open alerts", String(s.open_alerts)], ["Plans awaiting approval", String(s.pending_plans)],
    ["LLM cache hit rate", `${(s.cache_hit_rate * 100).toFixed(0)}%`], ["LLM spend (24 h)", `$${s.llm_cost_24h_usd.toFixed(3)}`]] : [];
  const data = f ? [...f.history.map(h => ({ day: h.day.slice(5), cost: h.cost })), ...f.forecast_7d.map((c, i) => ({ day: `+${i + 1}d`, forecast: c }))] : [];
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-6">
        {kpis.map(([k, v]) => <div key={k} className="rounded-lg border border-white/15 p-3"><div className="text-xs text-muted">{k}</div><div className="mt-1 text-xl font-medium tracking-tight">{v}</div></div>)}
        {!s && <p className="col-span-full text-sm text-muted">Connect a cloud account to see live numbers.</p>}
      </div>
      <div className="grid gap-6 lg:grid-cols-2">
        <section className="rounded-lg border border-white/15 p-4">
          <h2 className="mb-1 text-sm text-muted">Daily cost and 7-day forecast{f && ` · month-end projection $${f.month_end_projection.toFixed(0)}`}</h2>
          <div className="h-64"><ResponsiveContainer><AreaChart data={data}>
            <CartesianGrid stroke="rgba(255,255,255,.08)" /><XAxis dataKey="day" stroke="#777" fontSize={11} /><YAxis stroke="#777" fontSize={11} />
            <Tooltip contentStyle={{ background: "#000", border: "1px solid #333" }} />
            <Area dataKey="cost" stroke="#fff" fill="rgba(255,255,255,.12)" /><Area dataKey="forecast" stroke="#f26b1d" strokeDasharray="4 3" fill="rgba(242,107,29,.12)" />
          </AreaChart></ResponsiveContainer></div>
        </section>
        <section className="rounded-lg border border-white/15 p-4"><h2 className="mb-1 text-sm text-muted">Cluster telemetry</h2><ClusterGraph /></section>
      </div>
    </div>);
}
