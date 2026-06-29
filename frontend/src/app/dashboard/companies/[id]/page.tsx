"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/* ------------------------------------------------------------------ */
/* Types                                                                */
/* ------------------------------------------------------------------ */

interface CompanyDetail {
  company: {
    id: number; name: string; github_org: string; website: string | null;
    description: string | null; employee_count: number | null;
    funding_status: string | null; qualification_score: number | null;
    enrichment_score: number | null; tech_stack: string[] | null;
    status: string | null; impact_score: number | null;
    estimated_risk_min_usd: number | null; estimated_risk_max_usd: number | null;
    report_price_cents: number | null; report_tier: string | null;
    created_at: string | null; updated_at: string | null;
  };
  repositories: { id: number; name: string; full_name: string; language: string | null; stars: number; finding_count: number; status: string | null; last_scanned_at: string | null }[];
  findings: { id: number; type: string; severity: string; title: string; description: string | null; file_path: string | null; line_no: number | null; scanner: string; verified: boolean | null; ai_explanation: string | null; ai_recommendation: string | null; created_at: string | null }[];
  contacts: { id: number; email: string; first_name: string | null; last_name: string | null; position: string | null; score: number | null; is_verified: boolean | null }[];
  emails: { id: number; subject: string; contact_id: number; sequence_num: number; sent_at: string | null; opened_at: string | null; clicked_at: string | null; events: { event_type: string; created_at: string | null }[] }[];
  payments: { id: number; report_id: number; amount_cents: number; status: string; stripe_session_id: string; created_at: string | null }[];
  reports: { id: number; created_at: string | null; full_report_path: string | null }[];
  revenue_cents: number;
}

const TABS = ["Overview", "Findings", "Outreach", "Payments"] as const;
type Tab = typeof TABS[number];

const SEV_STYLES: Record<string, string> = {
  critical: "bg-red-500/15 text-red-400 border-red-500/25",
  high: "bg-orange-500/15 text-orange-400 border-orange-500/25",
  medium: "bg-yellow-500/15 text-yellow-400 border-yellow-500/25",
  low: "bg-neutral-500/15 text-neutral-400 border-neutral-500/25",
};

/* ------------------------------------------------------------------ */
/* Page                                                                 */
/* ------------------------------------------------------------------ */

export default function CompanyDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const [companyId, setCompanyId] = useState<string | null>(null);
  const [data, setData] = useState<CompanyDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<Tab>("Overview");
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  useEffect(() => { params.then((p) => setCompanyId(p.id)); }, [params]);

  useEffect(() => {
    if (!companyId) return;
    setLoading(true);
    fetch(`${API}/api/companies/${companyId}`)
      .then((r) => r.ok ? r.json() : null)
      .then((d) => { setData(d); setLoading(false); })
      .catch(() => setLoading(false));
  }, [companyId]);

  async function doAction(action: string) {
    if (!companyId) return;
    setActionLoading(action);
    try {
      if (action === "rescan") {
        await fetch(`${API}/api/companies/${companyId}/actions/rescan`, { method: "POST" });
      } else if (action === "resend") {
        await fetch(`${API}/api/companies/${companyId}/actions/resend-email`, { method: "POST" });
      } else if (action === "skip") {
        await fetch(`${API}/api/companies/${companyId}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ skip: true }),
        });
      }
    } finally {
      setActionLoading(null);
    }
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="animate-shimmer h-8 w-64 rounded-lg" />
        <div className="animate-shimmer h-32 rounded-xl" />
        <div className="animate-shimmer h-96 rounded-xl" />
      </div>
    );
  }

  if (!data) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-neutral-500">Company not found</p>
      </div>
    );
  }

  const c = data.company;

  return (
    <div className="space-y-6 animate-fade-in-up">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm text-neutral-500">
        <Link href="/dashboard/companies" className="hover:text-neutral-300 transition-colors">Companies</Link>
        <span>/</span>
        <span className="text-neutral-300">{c.name || c.github_org}</span>
      </div>

      {/* Header Card */}
      <div className="glass rounded-xl p-6">
        <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4">
          <div className="space-y-2">
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold">{c.name || c.github_org}</h1>
              <span className={`px-2 py-0.5 rounded-md text-[10px] font-semibold uppercase tracking-wider border ${
                c.status === "PAID" ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" :
                c.status === "SKIP" ? "bg-red-500/10 text-red-400 border-red-500/20" :
                "bg-indigo-500/10 text-indigo-400 border-indigo-500/20"
              }`}>{c.status || "NEW"}</span>
            </div>
            <div className="flex flex-wrap items-center gap-4 text-sm text-neutral-400">
              {c.github_org && (
                <a href={`https://github.com/${c.github_org}`} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1.5 hover:text-white transition-colors font-mono">
                  <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/></svg>
                  {c.github_org}
                </a>
              )}
              {c.website && (
                <a href={c.website} target="_blank" rel="noopener noreferrer" className="hover:text-white transition-colors">{c.website}</a>
              )}
              {c.employee_count && <span>{c.employee_count} employees</span>}
              {c.qualification_score !== null && (
                <span className="font-mono">Score: {c.qualification_score?.toFixed(1)}</span>
              )}
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex flex-wrap gap-2">
            {[
              { key: "rescan", label: "Re-scan", color: "bg-indigo-500/10 text-indigo-400 border-indigo-500/20 hover:bg-indigo-500/20" },
              { key: "resend", label: "Resend Email", color: "bg-blue-500/10 text-blue-400 border-blue-500/20 hover:bg-blue-500/20" },
              { key: "skip", label: "Mark Skip", color: "bg-red-500/10 text-red-400 border-red-500/20 hover:bg-red-500/20" },
            ].map((btn) => (
              <button
                key={btn.key}
                onClick={() => doAction(btn.key)}
                disabled={actionLoading === btn.key}
                className={`px-3 py-1.5 text-xs font-medium rounded-lg border transition-colors disabled:opacity-50 ${btn.color}`}
              >
                {actionLoading === btn.key ? "…" : btn.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-white/5 pb-0">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2.5 text-sm font-medium rounded-t-lg transition-colors ${
              tab === t
                ? "bg-white/5 text-white border-b-2 border-indigo-500"
                : "text-neutral-500 hover:text-neutral-300"
            }`}
          >
            {t}
            {t === "Findings" && <span className="ml-1.5 text-[10px] text-neutral-600">({data.findings.length})</span>}
            {t === "Outreach" && <span className="ml-1.5 text-[10px] text-neutral-600">({data.emails.length})</span>}
            {t === "Payments" && <span className="ml-1.5 text-[10px] text-neutral-600">({data.payments.length})</span>}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="animate-fade-in-up">
        {/* ===== Overview Tab ===== */}
        {tab === "Overview" && (
          <div className="space-y-6">
            {/* Summary cards */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="glass rounded-xl p-4 text-center">
                <p className="text-2xl font-bold">{data.findings.length}</p>
                <p className="text-[10px] text-neutral-500 uppercase tracking-wider mt-1">Findings</p>
              </div>
              <div className="glass rounded-xl p-4 text-center">
                <p className="text-2xl font-bold">{data.repositories.length}</p>
                <p className="text-[10px] text-neutral-500 uppercase tracking-wider mt-1">Repos</p>
              </div>
              <div className="glass rounded-xl p-4 text-center">
                <p className="text-2xl font-bold text-emerald-400">
                  ${(data.revenue_cents / 100).toFixed(0)}
                </p>
                <p className="text-[10px] text-neutral-500 uppercase tracking-wider mt-1">Revenue</p>
              </div>
              <div className="glass rounded-xl p-4 text-center">
                <p className="text-2xl font-bold">{data.contacts.length}</p>
                <p className="text-[10px] text-neutral-500 uppercase tracking-wider mt-1">Contacts</p>
              </div>
            </div>

            {/* Tech stack */}
            {c.tech_stack && c.tech_stack.length > 0 && (
              <div className="glass rounded-xl p-5">
                <h3 className="text-xs font-medium text-neutral-500 uppercase tracking-wider mb-3">Tech Stack</h3>
                <div className="flex flex-wrap gap-2">
                  {c.tech_stack.map((t, i) => (
                    <span key={i} className="px-2.5 py-1 rounded-md bg-white/5 text-xs text-neutral-300 border border-white/10">{t}</span>
                  ))}
                </div>
              </div>
            )}

            {/* Repositories */}
            <div className="glass rounded-xl p-5">
              <h3 className="text-xs font-medium text-neutral-500 uppercase tracking-wider mb-3">Repositories</h3>
              <div className="space-y-2">
                {data.repositories.map((r) => (
                  <div key={r.id} className="flex items-center justify-between py-2 border-b border-white/5 last:border-0">
                    <div>
                      <p className="text-sm font-medium text-neutral-200">{r.name}</p>
                      <p className="text-[11px] text-neutral-600 font-mono">{r.language || "—"} · ★ {r.stars}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-mono text-neutral-400">{r.finding_count} findings</p>
                      <p className="text-[10px] text-neutral-600">{r.last_scanned_at ? new Date(r.last_scanned_at).toLocaleDateString() : "Not scanned"}</p>
                    </div>
                  </div>
                ))}
                {data.repositories.length === 0 && <p className="text-sm text-neutral-600 text-center py-4">No repositories</p>}
              </div>
            </div>
          </div>
        )}

        {/* ===== Findings Tab ===== */}
        {tab === "Findings" && (
          <div className="glass rounded-xl overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-white/5">
                    <th className="py-3 px-4 text-left text-xs font-medium text-neutral-500 uppercase tracking-wider">Severity</th>
                    <th className="py-3 px-4 text-left text-xs font-medium text-neutral-500 uppercase tracking-wider">Title</th>
                    <th className="py-3 px-4 text-left text-xs font-medium text-neutral-500 uppercase tracking-wider">File</th>
                    <th className="py-3 px-4 text-left text-xs font-medium text-neutral-500 uppercase tracking-wider">Scanner</th>
                    <th className="py-3 px-4 text-center text-xs font-medium text-neutral-500 uppercase tracking-wider">Verified</th>
                  </tr>
                </thead>
                <tbody>
                  {data.findings.map((f) => (
                    <tr key={f.id} className="border-b border-white/5 hover:bg-white/[0.02] transition-colors">
                      <td className="py-3 px-4">
                        <span className={`px-2 py-0.5 rounded-md text-[10px] font-semibold uppercase border ${SEV_STYLES[f.severity?.toLowerCase()] || SEV_STYLES.low}`}>
                          {f.severity}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-neutral-200 max-w-xs truncate">{f.title}</td>
                      <td className="py-3 px-4 font-mono text-[11px] text-neutral-500 max-w-[200px] truncate">{f.file_path || "—"}</td>
                      <td className="py-3 px-4 text-xs text-neutral-400">{f.scanner}</td>
                      <td className="py-3 px-4 text-center">
                        {f.verified ? (
                          <span className="text-emerald-400">✓</span>
                        ) : (
                          <span className="text-neutral-600">—</span>
                        )}
                      </td>
                    </tr>
                  ))}
                  {data.findings.length === 0 && (
                    <tr><td colSpan={5} className="py-12 text-center text-neutral-600">No findings</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* ===== Outreach Tab ===== */}
        {tab === "Outreach" && (
          <div className="space-y-3">
            {data.emails.map((em) => (
              <div key={em.id} className="glass rounded-xl p-5">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="text-sm font-medium text-neutral-200">{em.subject}</p>
                    <p className="text-[11px] text-neutral-500 mt-1">Sequence #{em.sequence_num}</p>
                  </div>
                  <div className="flex items-center gap-3">
                    {em.clicked_at ? (
                      <span className="px-2 py-0.5 rounded-md text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">Clicked</span>
                    ) : em.opened_at ? (
                      <span className="px-2 py-0.5 rounded-md text-[10px] font-semibold bg-blue-500/10 text-blue-400 border border-blue-500/20">Opened</span>
                    ) : (
                      <span className="px-2 py-0.5 rounded-md text-[10px] font-semibold bg-neutral-500/10 text-neutral-400 border border-neutral-500/20">Sent</span>
                    )}
                  </div>
                </div>
                <div className="mt-3 flex flex-wrap gap-4 text-[11px] text-neutral-500">
                  <span>Sent: {em.sent_at ? new Date(em.sent_at).toLocaleString() : "—"}</span>
                  {em.opened_at && <span className="text-blue-400">Opened: {new Date(em.opened_at).toLocaleString()}</span>}
                  {em.clicked_at && <span className="text-emerald-400">Clicked: {new Date(em.clicked_at).toLocaleString()}</span>}
                </div>
                {em.events.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-white/5">
                    <p className="text-[10px] text-neutral-600 uppercase tracking-wider mb-1.5">Events</p>
                    <div className="flex flex-wrap gap-2">
                      {em.events.map((ev, i) => (
                        <span key={i} className="px-2 py-0.5 rounded bg-white/5 text-[10px] text-neutral-500">
                          {ev.event_type} — {ev.created_at ? new Date(ev.created_at).toLocaleTimeString() : ""}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ))}
            {data.emails.length === 0 && (
              <div className="glass rounded-xl p-12 text-center text-neutral-600 text-sm">No outreach emails sent</div>
            )}
          </div>
        )}

        {/* ===== Payments Tab ===== */}
        {tab === "Payments" && (
          <div className="glass rounded-xl overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-white/5">
                    <th className="py-3 px-4 text-left text-xs font-medium text-neutral-500 uppercase tracking-wider">Date</th>
                    <th className="py-3 px-4 text-right text-xs font-medium text-neutral-500 uppercase tracking-wider">Amount</th>
                    <th className="py-3 px-4 text-center text-xs font-medium text-neutral-500 uppercase tracking-wider">Status</th>
                    <th className="py-3 px-4 text-left text-xs font-medium text-neutral-500 uppercase tracking-wider">Stripe Session</th>
                  </tr>
                </thead>
                <tbody>
                  {data.payments.map((p) => (
                    <tr key={p.id} className="border-b border-white/5">
                      <td className="py-3 px-4 text-neutral-300">{p.created_at ? new Date(p.created_at).toLocaleDateString() : "—"}</td>
                      <td className="py-3 px-4 text-right font-mono text-neutral-200">${(p.amount_cents / 100).toFixed(2)}</td>
                      <td className="py-3 px-4 text-center">
                        <span className={`px-2 py-0.5 rounded-md text-[10px] font-semibold uppercase border ${
                          p.status === "paid" ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" :
                          p.status === "refunded" ? "bg-red-500/10 text-red-400 border-red-500/20" :
                          "bg-amber-500/10 text-amber-400 border-amber-500/20"
                        }`}>{p.status}</span>
                      </td>
                      <td className="py-3 px-4 font-mono text-[11px] text-neutral-600 max-w-[200px] truncate">{p.stripe_session_id}</td>
                    </tr>
                  ))}
                  {data.payments.length === 0 && (
                    <tr><td colSpan={4} className="py-12 text-center text-neutral-600">No payments</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
