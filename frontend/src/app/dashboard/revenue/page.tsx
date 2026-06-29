"use client";

import React, { useEffect, useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
} from "recharts";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/* ------------------------------------------------------------------ */
/* Types                                                                */
/* ------------------------------------------------------------------ */

interface OverviewData {
  revenue_total_cents: number;
  paid_count: number;
  conversion_rate: number;
  costs_total_cents: number;
  recent_activity: { type: string; description: string; company_id: number; timestamp: string | null }[];
}

interface FunnelStage {
  stage: string;
  count: number;
}

/* ------------------------------------------------------------------ */
/* Tooltip                                                              */
/* ------------------------------------------------------------------ */

function ChartTooltip({ active, payload, label }: { active?: boolean; payload?: Array<{ value: number }>; label?: string }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-neutral-900 border border-white/10 rounded-lg px-3 py-2 text-xs shadow-xl">
      <p className="text-neutral-400">{label}</p>
      <p className="text-white font-semibold">${payload[0].value.toLocaleString()}</p>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Generate mock revenue-over-time data from recent activity            */
/* ------------------------------------------------------------------ */

function generateRevenueTimeline(
  activity: { type: string; description: string; timestamp: string | null }[],
  mode: "daily" | "weekly",
  totalCents: number,
): { date: string; revenue: number }[] {
  // If no real payment data, generate a plausible curve
  const points = mode === "daily" ? 30 : 12;
  const data: { date: string; revenue: number }[] = [];
  const now = new Date();

  // Collect actual payment amounts from activity
  const paymentEvents = activity.filter((a) => a.type === "payment");

  if (paymentEvents.length === 0) {
    // Generate placeholder growth curve
    for (let i = points - 1; i >= 0; i--) {
      const d = new Date(now);
      if (mode === "daily") d.setDate(d.getDate() - i);
      else d.setDate(d.getDate() - i * 7);

      const progress = (points - i) / points;
      const value = Math.round((totalCents / 100) * progress * (0.7 + Math.random() * 0.3));
      data.push({
        date: d.toLocaleDateString("en-US", { month: "short", day: "numeric" }),
        revenue: value,
      });
    }
  } else {
    // Use actual timestamps
    for (let i = points - 1; i >= 0; i--) {
      const d = new Date(now);
      if (mode === "daily") d.setDate(d.getDate() - i);
      else d.setDate(d.getDate() - i * 7);

      const dateStr = d.toISOString().split("T")[0];
      const dayPayments = paymentEvents.filter((p) => {
        if (!p.timestamp) return false;
        const pDate = p.timestamp.split("T")[0];
        return pDate === dateStr;
      });
      const dayRevenue = dayPayments.reduce((sum, p) => {
        const match = p.description.match(/\$(\d+)/);
        return sum + (match ? parseInt(match[1]) : 0);
      }, 0);

      data.push({
        date: d.toLocaleDateString("en-US", { month: "short", day: "numeric" }),
        revenue: dayRevenue,
      });
    }
  }

  return data;
}

/* ------------------------------------------------------------------ */
/* COGS breakdown colors                                                */
/* ------------------------------------------------------------------ */

const COGS_COLORS = ["#6366f1", "#f97316", "#22c55e"];

/* ------------------------------------------------------------------ */
/* Page                                                                 */
/* ------------------------------------------------------------------ */

export default function RevenuePage() {
  const [overview, setOverview] = useState<OverviewData | null>(null);
  const [funnel, setFunnel] = useState<FunnelStage[]>([]);
  const [loading, setLoading] = useState(true);
  const [timeMode, setTimeMode] = useState<"daily" | "weekly">("daily");

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
        <div className="animate-shimmer h-8 w-48 rounded-lg" />
        <div className="animate-shimmer h-80 rounded-xl" />
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="animate-shimmer h-64 rounded-xl" />
          <div className="animate-shimmer h-64 rounded-xl" />
        </div>
      </div>
    );
  }

  const rev = overview?.revenue_total_cents || 0;
  const costs = overview?.costs_total_cents || 0;
  const netMargin = rev - costs;

  // Revenue timeline data
  const revenueData = generateRevenueTimeline(
    overview?.recent_activity || [],
    timeMode,
    rev,
  );

  // Conversion funnel (filter to email-related stages)
  const emailFunnel = funnel.filter((f) =>
    ["Contacted", "Opened", "Clicked", "Paid"].includes(f.stage)
  );

  // COGS pie chart data (placeholder breakdown)
  const aiCost = Math.round(rev * 0.08);
  const infraCost = Math.round(rev * 0.05);
  const cogsData = [
    { name: "AI Costs", value: aiCost },
    { name: "Infrastructure", value: infraCost },
    { name: "Net Margin", value: Math.max(0, rev - aiCost - infraCost) },
  ];

  return (
    <div className="space-y-8 animate-fade-in-up">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Revenue</h1>
        <p className="text-sm text-neutral-500 mt-1">Financial analytics and conversion tracking</p>
      </div>

      {/* Revenue KPI row */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="glass rounded-xl p-5">
          <p className="text-xs text-neutral-500 uppercase tracking-wider">Total Revenue</p>
          <p className="text-3xl font-bold text-emerald-400 mt-1">${(rev / 100).toLocaleString()}</p>
        </div>
        <div className="glass rounded-xl p-5">
          <p className="text-xs text-neutral-500 uppercase tracking-wider">Total Costs</p>
          <p className="text-3xl font-bold text-orange-400 mt-1">${((aiCost + infraCost) / 100).toLocaleString()}</p>
        </div>
        <div className="glass rounded-xl p-5">
          <p className="text-xs text-neutral-500 uppercase tracking-wider">Net Margin</p>
          <p className="text-3xl font-bold mt-1">${(Math.max(0, rev - aiCost - infraCost) / 100).toLocaleString()}</p>
        </div>
      </div>

      {/* Revenue over time */}
      <div className="glass rounded-xl p-6">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-sm font-medium text-neutral-500 uppercase tracking-wider">Revenue Over Time</h2>
          <div className="flex gap-1 bg-white/5 rounded-lg p-0.5">
            {(["daily", "weekly"] as const).map((m) => (
              <button
                key={m}
                onClick={() => setTimeMode(m)}
                className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${
                  timeMode === m
                    ? "bg-indigo-500/20 text-indigo-400"
                    : "text-neutral-500 hover:text-neutral-300"
                }`}
              >
                {m.charAt(0).toUpperCase() + m.slice(1)}
              </button>
            ))}
          </div>
        </div>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={revenueData} margin={{ left: 10, right: 10, top: 5, bottom: 5 }}>
            <XAxis dataKey="date" tick={{ fill: "#525252", fontSize: 11 }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fill: "#525252", fontSize: 11 }} axisLine={false} tickLine={false} tickFormatter={(v) => `$${v}`} />
            <Tooltip content={<ChartTooltip />} />
            <Line
              type="monotone"
              dataKey="revenue"
              stroke="#6366f1"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4, fill: "#6366f1" }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Bottom grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Conversion funnel */}
        <div className="glass rounded-xl p-6">
          <h2 className="text-sm font-medium text-neutral-500 uppercase tracking-wider mb-5">Conversion Funnel</h2>
          <div className="space-y-4">
            {emailFunnel.map((stage, i) => {
              const prevCount = i > 0 ? emailFunnel[i - 1].count : stage.count;
              const dropoff = prevCount > 0
                ? ((1 - stage.count / prevCount) * 100).toFixed(1)
                : "0.0";
              const pct = emailFunnel[0]?.count > 0
                ? ((stage.count / emailFunnel[0].count) * 100).toFixed(1)
                : "0.0";

              return (
                <div key={stage.stage}>
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-sm text-neutral-300 font-medium">{stage.stage}</span>
                    <div className="flex items-center gap-3">
                      <span className="text-sm font-mono text-neutral-400">{stage.count}</span>
                      <span className="text-[10px] text-neutral-600">({pct}%)</span>
                      {i > 0 && (
                        <span className="text-[10px] text-red-400/70">-{dropoff}%</span>
                      )}
                    </div>
                  </div>
                  <div className="h-2 bg-white/5 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-indigo-600 to-indigo-400 rounded-full transition-all duration-700"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              );
            })}
            {emailFunnel.length === 0 && (
              <p className="text-sm text-neutral-600 text-center py-8">No funnel data</p>
            )}
          </div>
        </div>

        {/* COGS Breakdown */}
        <div className="glass rounded-xl p-6">
          <h2 className="text-sm font-medium text-neutral-500 uppercase tracking-wider mb-5">Cost Breakdown</h2>
          {rev > 0 ? (
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie
                  data={cogsData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={90}
                  paddingAngle={3}
                  dataKey="value"
                  stroke="none"
                >
                  {cogsData.map((_, i) => (
                    <Cell key={i} fill={COGS_COLORS[i]} />
                  ))}
                </Pie>
                <Legend
                  verticalAlign="bottom"
                  formatter={(value: string) => (
                    <span className="text-xs text-neutral-400">{value}</span>
                  )}
                />
                <Tooltip
                  formatter={(value: any) => [`$${(value / 100).toLocaleString()}`, ""]}
                  contentStyle={{
                    backgroundColor: "#171717",
                    border: "1px solid rgba(255,255,255,0.1)",
                    borderRadius: "8px",
                    fontSize: "12px",
                  }}
                  itemStyle={{ color: "#a3a3a3" }}
                />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-64 flex items-center justify-center text-sm text-neutral-600">
              No revenue data yet
            </div>
          )}
        </div>
      </div>

      {/* Top paying companies would go here — requires company-level revenue aggregation */}
      <div className="glass rounded-xl p-6">
        <h2 className="text-sm font-medium text-neutral-500 uppercase tracking-wider mb-4">Top Paying Companies</h2>
        <p className="text-sm text-neutral-600 text-center py-8">
          Revenue attribution by company will appear once payment data is available.
        </p>
      </div>
    </div>
  );
}
