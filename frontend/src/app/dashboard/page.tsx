"use client";

import React, { useEffect, useState } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/* ------------------------------------------------------------------ */
/* Types                                                                */
/* ------------------------------------------------------------------ */

interface OverviewData {
  companies_by_status: Record<string, number>;
  revenue_total_cents: number;
  paid_count: number;
  conversion_rate: number;
  avg_report_price: number;
  top_finding_types: { type: string; count: number }[];
  costs_total_cents: number;
  recent_activity: {
    type: string;
    description: string;
    company_id: number;
    timestamp: string | null;
  }[];
}

interface FunnelStage {
  stage: string;
  count: number;
}

/* ------------------------------------------------------------------ */
/* Animated number                                                      */
/* ------------------------------------------------------------------ */

function AnimNum({ value, prefix = "", suffix = "" }: { value: number; prefix?: string; suffix?: string }) {
  const [d, setD] = useState(0);
  useEffect(() => {
    const dur = 700;
    const start = Date.now();
    const step = () => {
      const p = Math.min((Date.now() - start) / dur, 1);
      setD(Math.round((1 - Math.pow(1 - p, 3)) * value));
      if (p < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }, [value]);
  return <>{prefix}{d.toLocaleString()}{suffix}</>;
}

/* ------------------------------------------------------------------ */
/* Skeleton                                                             */
/* ------------------------------------------------------------------ */

function Sk({ className = "" }: { className?: string }) {
  return <div className={`animate-shimmer rounded-lg ${className}`} />;
}

/* ------------------------------------------------------------------ */
/* Funnel bar colors                                                    */
/* ------------------------------------------------------------------ */

const FUNNEL_COLORS = [
  "#6366f1", "#818cf8", "#a78bfa", "#c084fc",
  "#e879f9", "#f472b6", "#fb7185", "#f97316", "#22c55e",
];

/* ------------------------------------------------------------------ */
/* Custom Tooltip                                                       */
/* ------------------------------------------------------------------ */

function ChartTooltip({ active, payload, label }: { active?: boolean; payload?: Array<{ value: number }>; label?: string }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-neutral-900 border border-white/10 rounded-lg px-3 py-2 text-xs shadow-xl">
      <p className="text-neutral-400">{label}</p>
      <p className="text-white font-semibold">{payload[0].value}</p>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Page                                                                 */
/* ------------------------------------------------------------------ */

export default function DashboardPage() {
  const [overview, setOverview] = useState<OverviewData | null>(null);
  const [funnel, setFunnel] = useState<FunnelStage[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      fetch(`${API}/api/dashboard/overview`).then((r) => r.ok ? r.json() : null),
      fetch(`${API}/api/dashboard/funnel`).then((r) => r.ok ? r.json() : null),
    ])
      .then(([ov, fn]) => {
        setOverview(ov);
        setFunnel(fn?.funnel || []);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="space-y-6">
        <Sk className="h-8 w-48" />
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => <Sk key={i} className="h-28" />)}
        </div>
        <Sk className="h-64" />
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <Sk className="h-80" />
          <Sk className="h-80" />
        </div>
      </div>
    );
  }

  const rev = overview?.revenue_total_cents || 0;
  const maxFunnel = Math.max(...funnel.map((f) => f.count), 1);

  return (
    <div className="space-y-8 animate-fade-in-up">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-sm text-neutral-500 mt-1">Pipeline overview and key metrics</p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        {[
          {
            label: "Total Revenue",
            value: `$${(rev / 100).toLocaleString(undefined, { minimumFractionDigits: 0 })}`,
            icon: <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.75" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>,
            color: "text-emerald-400 bg-emerald-500/10",
          },
          {
            label: "Paid Reports",
            value: overview?.paid_count || 0,
            icon: <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.75" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>,
            color: "text-indigo-400 bg-indigo-500/10",
          },
          {
            label: "Conversion Rate",
            value: `${((overview?.conversion_rate || 0) * 100).toFixed(1)}%`,
            icon: <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.75" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" /></svg>,
            color: "text-purple-400 bg-purple-500/10",
          },
          {
            label: "Avg Report Price",
            value: `$${((overview?.avg_report_price || 0) / 100).toFixed(0)}`,
            icon: <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.75" d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" /></svg>,
            color: "text-amber-400 bg-amber-500/10",
          },
        ].map((kpi, i) => (
          <div key={i} className="glass rounded-xl p-5 flex items-start gap-4 transition-transform hover:scale-[1.02]">
            <div className={`w-10 h-10 rounded-lg ${kpi.color} flex items-center justify-center shrink-0`}>
              {kpi.icon}
            </div>
            <div>
              <p className="text-xs text-neutral-500 font-medium uppercase tracking-wider">{kpi.label}</p>
              <p className="text-2xl font-bold mt-0.5">{typeof kpi.value === "number" ? <AnimNum value={kpi.value} /> : kpi.value}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Pipeline Funnel */}
      <div className="glass rounded-xl p-6">
        <h2 className="text-sm font-medium text-neutral-500 uppercase tracking-wider mb-5">Pipeline Funnel</h2>
        <div className="space-y-3">
          {funnel.map((stage, i) => {
            const pct = maxFunnel > 0 ? (stage.count / maxFunnel) * 100 : 0;
            return (
              <div key={stage.stage} className="flex items-center gap-4">
                <span className="text-xs text-neutral-400 w-24 text-right font-medium shrink-0">
                  {stage.stage}
                </span>
                <div className="flex-1 h-8 bg-white/5 rounded-lg overflow-hidden relative">
                  <div
                    className="h-full rounded-lg transition-all duration-700 ease-out flex items-center px-3"
                    style={{
                      width: `${Math.max(pct, 2)}%`,
                      backgroundColor: FUNNEL_COLORS[i] || FUNNEL_COLORS[0],
                      animationDelay: `${i * 80}ms`,
                    }}
                  >
                    <span className="text-xs font-semibold text-white drop-shadow-sm">
                      {stage.count}
                    </span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Bottom Grid: Top Findings + Activity Feed */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Top Finding Types Chart */}
        <div className="glass rounded-xl p-6">
          <h2 className="text-sm font-medium text-neutral-500 uppercase tracking-wider mb-4">Top Finding Types</h2>
          {(overview?.top_finding_types?.length || 0) > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart
                data={overview!.top_finding_types}
                layout="vertical"
                margin={{ left: 80, right: 20, top: 5, bottom: 5 }}
              >
                <XAxis type="number" tick={{ fill: "#525252", fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis dataKey="type" type="category" tick={{ fill: "#a3a3a3", fontSize: 11 }} axisLine={false} tickLine={false} width={80} />
                <Tooltip content={<ChartTooltip />} cursor={{ fill: "rgba(255,255,255,0.03)" }} />
                <Bar dataKey="count" radius={[0, 6, 6, 0]} maxBarSize={24}>
                  {overview!.top_finding_types.map((_, i) => (
                    <Cell key={i} fill={FUNNEL_COLORS[i % FUNNEL_COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-48 flex items-center justify-center text-sm text-neutral-600">
              No findings data yet
            </div>
          )}
        </div>

        {/* Recent Activity Feed */}
        <div className="glass rounded-xl p-6">
          <h2 className="text-sm font-medium text-neutral-500 uppercase tracking-wider mb-4">Recent Activity</h2>
          <div className="space-y-1">
            {(overview?.recent_activity?.length || 0) > 0 ? (
              overview!.recent_activity.map((ev, i) => (
                <div key={i} className="flex items-start gap-3 py-2.5 border-b border-white/5 last:border-0">
                  <div className={`w-7 h-7 rounded-md flex items-center justify-center shrink-0 mt-0.5 ${
                    ev.type === "payment" ? "bg-emerald-500/10 text-emerald-400" : "bg-blue-500/10 text-blue-400"
                  }`}>
                    {ev.type === "payment" ? (
                      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8V7m0 1v8m0 0v1" /></svg>
                    ) : (
                      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" /></svg>
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-neutral-200 truncate">{ev.description}</p>
                    <p className="text-[11px] text-neutral-600 mt-0.5">
                      {ev.timestamp ? new Date(ev.timestamp).toLocaleString() : "—"}
                    </p>
                  </div>
                </div>
              ))
            ) : (
              <div className="h-48 flex items-center justify-center text-sm text-neutral-600">
                No recent activity
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
