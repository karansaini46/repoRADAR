"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
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

interface VulnCompany {
  id: number;
  name: string;
  github_org: string;
  status: string;
  finding_count: number;
  severity_breakdown: Record<string, number>;
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
  const [vulnCompanies, setVulnCompanies] = useState<VulnCompany[]>([]);
  const [loading, setLoading] = useState(true);
  
  const [settings, setSettings] = useState<{auto_mode: boolean, scraping_interval_hours: number} | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [isStarting, setIsStarting] = useState(false);

  useEffect(() => {
    Promise.all([
      fetch(`${API}/api/dashboard/overview`).then((r) => r.ok ? r.json() : null),
      fetch(`${API}/api/dashboard/funnel`).then((r) => r.ok ? r.json() : null),
      fetch(`${API}/api/system/settings`).then((r) => r.ok ? r.json() : null),
      fetch(`${API}/api/dashboard/vulnerable-companies`).then((r) => r.ok ? r.json() : null),
    ])
      .then(([ov, fn, st, vc]) => {
        setOverview(ov);
        setFunnel(fn?.funnel || []);
        if (st) setSettings(st);
        setVulnCompanies(vc?.companies || []);
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

  const handleToggleAuto = async () => {
    if (!settings) return;
    const newSettings = { ...settings, auto_mode: !settings.auto_mode };
    setSettings(newSettings);
    setIsSaving(true);
    await fetch(`${API}/api/system/settings`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(newSettings),
    });
    setIsSaving(false);
  };

  const handleChangeInterval = async (val: string) => {
    if (!settings) return;
    const newSettings = { ...settings, scraping_interval_hours: parseInt(val) };
    setSettings(newSettings);
    setIsSaving(true);
    await fetch(`${API}/api/system/settings`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(newSettings),
    });
    setIsSaving(false);
  };

  const handleManualStart = async () => {
    setIsStarting(true);
    try {
      const res = await fetch(`${API}/api/system/manual-start`, { method: "POST" });
      if (res.ok) alert("Discovery engine started manually.");
      else alert("Failed to start engine.");
    } catch (e) {
      alert("Error starting engine.");
    }
    setIsStarting(false);
  };

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
            const content = (
              <div className="flex items-center gap-4 w-full">
                <span className={`text-xs w-24 text-right font-medium shrink-0 transition-colors ${
                  stage.stage === "Verified" ? "text-indigo-400 group-hover:text-indigo-300" : "text-neutral-400"
                }`}>
                  {stage.stage}
                </span>
                <div className="flex-1 h-8 bg-white/5 rounded-lg overflow-hidden relative">
                  <div
                    className={`h-full rounded-lg transition-all duration-700 ease-out flex items-center px-3 ${
                      stage.stage === "Verified" ? "brightness-110 group-hover:brightness-125 cursor-pointer" : ""
                    }`}
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

            if (stage.stage === "Verified") {
              return (
                <Link key={stage.stage} href="/dashboard/verified" className="block group">
                  {content}
                </Link>
              );
            }

            return (
              <div key={stage.stage} className="block">
                {content}
              </div>
            );
          })}
        </div>
      </div>

      {/* System Controls */}
      <div className="glass rounded-xl p-6">
        <h2 className="text-sm font-medium text-neutral-500 uppercase tracking-wider mb-5">Scraping & Automation Engine</h2>
        <div className="flex flex-col sm:flex-row sm:items-center gap-6">
          
          <div className="flex items-center justify-between sm:justify-start gap-4">
            <div>
              <p className="text-sm font-semibold text-neutral-200">Auto Mode</p>
              <p className="text-xs text-neutral-500">Run pipelines on schedule</p>
            </div>
            <button
              onClick={handleToggleAuto}
              disabled={isSaving}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                settings?.auto_mode ? "bg-emerald-500" : "bg-neutral-600"
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  settings?.auto_mode ? "translate-x-6" : "translate-x-1"
                }`}
              />
            </button>
          </div>

          <div className="h-px sm:h-10 w-full sm:w-px bg-white/10" />
          
          <div className="flex items-center justify-between sm:justify-start gap-4">
            <div>
              <p className="text-sm font-semibold text-neutral-200">Scraping Schedule</p>
              <p className="text-xs text-neutral-500">Interval for discovery</p>
            </div>
            <select
              value={settings?.scraping_interval_hours || 24}
              onChange={(e) => handleChangeInterval(e.target.value)}
              disabled={isSaving}
              className="bg-neutral-900 border border-white/10 rounded-lg text-sm px-3 py-1.5 text-neutral-200 focus:outline-none focus:border-emerald-500"
            >
              <option value="6">Every 6 Hours</option>
              <option value="12">Every 12 Hours</option>
              <option value="24">Every 24 Hours</option>
              <option value="48">Every 48 Hours</option>
            </select>
          </div>

          <div className="flex-1" />

          <button
            onClick={handleManualStart}
            disabled={isStarting}
            className="bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold py-2 px-5 rounded-lg transition-colors flex items-center justify-center gap-2"
          >
            {isStarting ? (
              <svg className="animate-spin h-4 w-4 text-white" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
            ) : (
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" /><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
            )}
            Start Manual Scrape
          </button>
        </div>
      </div>

      {/* Vulnerable Companies */}
      {vulnCompanies.length > 0 && (
        <div className="glass rounded-xl p-6">
          <div className="flex items-center justify-between mb-5">
            <h2 className="text-sm font-medium text-neutral-500 uppercase tracking-wider">Companies with Vulnerabilities</h2>
            <span className="text-xs text-red-400 font-medium bg-red-500/10 px-2.5 py-1 rounded-md border border-red-500/20">
              {vulnCompanies.reduce((sum, c) => sum + c.finding_count, 0)} total findings
            </span>
          </div>
          <div className="space-y-2">
            {vulnCompanies.map((vc) => (
              <Link
                key={vc.id}
                href={`/dashboard/companies/${vc.id}`}
                className="flex items-center justify-between p-4 rounded-lg bg-white/[0.02] hover:bg-white/[0.05] border border-white/5 hover:border-indigo-500/30 transition-all group"
              >
                <div className="flex items-center gap-4">
                  <div className="w-10 h-10 rounded-lg bg-red-500/10 flex items-center justify-center text-red-400 shrink-0">
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.75" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4.5c-.77-.833-2.694-.833-3.464 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z" />
                    </svg>
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-neutral-200 group-hover:text-white transition-colors">{vc.name}</p>
                    <p className="text-[11px] text-neutral-600 font-mono">{vc.github_org}</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <div className="flex flex-wrap gap-1.5">
                    {vc.severity_breakdown.CRITICAL && (
                      <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-red-500/15 text-red-400 border border-red-500/25">
                        {vc.severity_breakdown.CRITICAL} Critical
                      </span>
                    )}
                    {vc.severity_breakdown.HIGH && (
                      <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-orange-500/15 text-orange-400 border border-orange-500/25">
                        {vc.severity_breakdown.HIGH} High
                      </span>
                    )}
                    {vc.severity_breakdown.MEDIUM && (
                      <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-yellow-500/15 text-yellow-400 border border-yellow-500/25">
                        {vc.severity_breakdown.MEDIUM} Medium
                      </span>
                    )}
                    {vc.severity_breakdown.LOW && (
                      <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-neutral-500/15 text-neutral-400 border border-neutral-500/25">
                        {vc.severity_breakdown.LOW} Low
                      </span>
                    )}
                  </div>
                  <span className="text-lg font-bold text-neutral-200 font-mono min-w-[3rem] text-right">{vc.finding_count}</span>
                  <svg className="w-4 h-4 text-neutral-600 group-hover:text-indigo-400 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5l7 7-7 7" />
                  </svg>
                </div>
              </Link>
            ))}
          </div>
        </div>
      )}

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
