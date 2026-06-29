"use client";

import React, { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { useSearchParams, useRouter } from "next/navigation";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/* ------------------------------------------------------------------ */
/* Types                                                                */
/* ------------------------------------------------------------------ */

interface CompanyRow {
  id: number;
  name: string;
  github_org: string;
  website: string | null;
  score: number | null;
  status: string;
  employee_count: number | null;
  finding_count: number;
  report_price_cents: number | null;
  report_tier: string | null;
  outreach_status: string;
  revenue_cents: number;
  created_at: string | null;
}

interface CompanyList {
  companies: CompanyRow[];
  total: number;
  page: number;
  limit: number;
  pages: number;
}

/* ------------------------------------------------------------------ */
/* Status badge                                                         */
/* ------------------------------------------------------------------ */

const STATUS_STYLES: Record<string, string> = {
  NEW: "bg-neutral-500/10 text-neutral-400 border-neutral-500/20",
  QUALIFIED: "bg-blue-500/10 text-blue-400 border-blue-500/20",
  ENRICHED: "bg-cyan-500/10 text-cyan-400 border-cyan-500/20",
  SCANNED: "bg-purple-500/10 text-purple-400 border-purple-500/20",
  REPORTED: "bg-indigo-500/10 text-indigo-400 border-indigo-500/20",
  CONTACTED: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  PAID: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
  SKIP: "bg-red-500/10 text-red-400 border-red-500/20",
};

function StatusBadge({ status }: { status: string }) {
  const style = STATUS_STYLES[status] || STATUS_STYLES.NEW;
  return (
    <span className={`px-2 py-0.5 rounded-md text-[10px] font-semibold uppercase tracking-wider border ${style}`}>
      {status}
    </span>
  );
}

function OutreachBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    none: "text-neutral-600",
    sent: "text-amber-400",
    opened: "text-blue-400",
    clicked: "text-emerald-400",
  };
  return <span className={`text-xs font-medium ${styles[status] || styles.none}`}>{status}</span>;
}

/* ------------------------------------------------------------------ */
/* Page                                                                 */
/* ------------------------------------------------------------------ */

function CompaniesContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const [data, setData] = useState<CompanyList | null>(null);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [search, setSearch] = useState(searchParams.get("search") || "");
  const [statusFilter, setStatusFilter] = useState(searchParams.get("status") || "");

  const page = parseInt(searchParams.get("page") || "1", 10);
  const limit = parseInt(searchParams.get("limit") || "25", 10);

  const fetchData = useCallback(() => {
    setLoading(true);
    const params = new URLSearchParams();
    params.set("page", String(page));
    params.set("limit", String(limit));
    if (statusFilter) params.set("status", statusFilter);
    if (search) params.set("search", search);

    fetch(`${API}/api/companies?${params}`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        setData(d);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [page, limit, statusFilter, search]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  function navigate(overrides: Record<string, string>) {
    const params = new URLSearchParams(searchParams.toString());
    Object.entries(overrides).forEach(([k, v]) => {
      if (v) params.set(k, v);
      else params.delete(k);
    });
    router.push(`/dashboard/companies?${params}`);
  }

  function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    navigate({ search, page: "1" });
  }

  function toggleSelect(id: number) {
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  }

  function toggleAll() {
    if (!data) return;
    if (selected.size === data.companies.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(data.companies.map((c) => c.id)));
    }
  }

  async function bulkAction(action: string) {
    if (selected.size === 0) return;
    for (const id of selected) {
      if (action === "skip") {
        await fetch(`${API}/api/companies/${id}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ skip: true }),
        });
      } else if (action === "rescan") {
        await fetch(`${API}/api/companies/${id}/actions/rescan`, { method: "POST" });
      }
    }
    setSelected(new Set());
    fetchData();
  }

  function exportCSV() {
    if (!data) return;
    const headers = ["Name", "GitHub Org", "Score", "Status", "Findings", "Price", "Outreach", "Revenue"];
    const rows = data.companies.map((c) => [
      c.name, c.github_org, c.score || 0, c.status, c.finding_count,
      `$${((c.report_price_cents || 0) / 100).toFixed(0)}`,
      c.outreach_status, `$${(c.revenue_cents / 100).toFixed(0)}`,
    ]);
    const csv = [headers, ...rows].map((r) => r.join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "companies_export.csv";
    a.click();
    URL.revokeObjectURL(url);
  }

  const companies = data?.companies || [];

  return (
    <div className="space-y-6 animate-fade-in-up">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Companies</h1>
          <p className="text-sm text-neutral-500 mt-1">
            {data?.total || 0} companies in pipeline
          </p>
        </div>

        {/* Bulk actions */}
        {selected.size > 0 && (
          <div className="flex items-center gap-2">
            <span className="text-xs text-neutral-400">{selected.size} selected</span>
            <button onClick={() => bulkAction("skip")} className="px-3 py-1.5 text-xs font-medium rounded-lg bg-red-500/10 text-red-400 border border-red-500/20 hover:bg-red-500/20 transition-colors">
              Mark Skip
            </button>
            <button onClick={() => bulkAction("rescan")} className="px-3 py-1.5 text-xs font-medium rounded-lg bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 hover:bg-indigo-500/20 transition-colors">
              Trigger Scan
            </button>
            <button onClick={exportCSV} className="px-3 py-1.5 text-xs font-medium rounded-lg bg-white/5 text-neutral-300 border border-white/10 hover:bg-white/10 transition-colors">
              Export CSV
            </button>
          </div>
        )}
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-3">
        <form onSubmit={handleSearch} className="flex-1 flex gap-2">
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search companies..."
            className="flex-1 bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder-neutral-600 focus:outline-none focus:border-indigo-500/50 transition-colors"
          />
          <button type="submit" className="px-4 py-2 text-sm font-medium rounded-lg bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 hover:bg-indigo-500/20 transition-colors">
            Search
          </button>
        </form>
        <select
          value={statusFilter}
          onChange={(e) => navigate({ status: e.target.value, page: "1" })}
          className="bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-neutral-300 focus:outline-none focus:border-indigo-500/50 transition-colors"
        >
          <option value="">All statuses</option>
          {["NEW", "QUALIFIED", "ENRICHED", "SCANNED", "REPORTED", "CONTACTED", "PAID", "SKIP"].map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
      </div>

      {/* Table */}
      <div className="glass rounded-xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-white/5">
                <th className="py-3 px-4 text-left">
                  <input type="checkbox" onChange={toggleAll} checked={selected.size === companies.length && companies.length > 0} className="rounded border-white/20 bg-transparent" />
                </th>
                <th className="py-3 px-4 text-left text-xs font-medium text-neutral-500 uppercase tracking-wider">Company</th>
                <th className="py-3 px-4 text-left text-xs font-medium text-neutral-500 uppercase tracking-wider">Score</th>
                <th className="py-3 px-4 text-left text-xs font-medium text-neutral-500 uppercase tracking-wider">Status</th>
                <th className="py-3 px-4 text-right text-xs font-medium text-neutral-500 uppercase tracking-wider">Findings</th>
                <th className="py-3 px-4 text-right text-xs font-medium text-neutral-500 uppercase tracking-wider">Price</th>
                <th className="py-3 px-4 text-center text-xs font-medium text-neutral-500 uppercase tracking-wider">Outreach</th>
                <th className="py-3 px-4 text-right text-xs font-medium text-neutral-500 uppercase tracking-wider">Revenue</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <tr key={i} className="border-b border-white/5">
                    {Array.from({ length: 8 }).map((_, j) => (
                      <td key={j} className="py-3 px-4"><div className="animate-shimmer h-4 rounded w-16" /></td>
                    ))}
                  </tr>
                ))
              ) : companies.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-16 text-center text-neutral-600">No companies found</td>
                </tr>
              ) : (
                companies.map((c) => (
                  <tr
                    key={c.id}
                    className="border-b border-white/5 hover:bg-white/[0.02] transition-colors cursor-pointer"
                    onClick={() => router.push(`/dashboard/companies/${c.id}`)}
                  >
                    <td className="py-3 px-4" onClick={(e) => e.stopPropagation()}>
                      <input type="checkbox" checked={selected.has(c.id)} onChange={() => toggleSelect(c.id)} className="rounded border-white/20 bg-transparent" />
                    </td>
                    <td className="py-3 px-4">
                      <div>
                        <p className="font-medium text-neutral-200">{c.name}</p>
                        <p className="text-[11px] text-neutral-600 font-mono">{c.github_org}</p>
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      <span className="font-mono text-sm text-neutral-300">{c.score?.toFixed(1) ?? "—"}</span>
                    </td>
                    <td className="py-3 px-4"><StatusBadge status={c.status} /></td>
                    <td className="py-3 px-4 text-right font-mono text-neutral-300">{c.finding_count}</td>
                    <td className="py-3 px-4 text-right font-mono text-neutral-300">
                      {c.report_price_cents ? `$${(c.report_price_cents / 100).toFixed(0)}` : "—"}
                    </td>
                    <td className="py-3 px-4 text-center"><OutreachBadge status={c.outreach_status} /></td>
                    <td className="py-3 px-4 text-right">
                      {c.revenue_cents > 0 ? (
                        <span className="font-mono text-emerald-400">${(c.revenue_cents / 100).toFixed(0)}</span>
                      ) : (
                        <span className="text-neutral-600">—</span>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {data && data.pages > 1 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-white/5">
            <p className="text-xs text-neutral-500">
              Page {data.page} of {data.pages} ({data.total} total)
            </p>
            <div className="flex gap-1.5">
              <button
                disabled={data.page <= 1}
                onClick={() => navigate({ page: String(data.page - 1) })}
                className="px-3 py-1.5 text-xs font-medium rounded-lg bg-white/5 border border-white/10 text-neutral-400 hover:bg-white/10 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
              >
                Previous
              </button>
              <button
                disabled={data.page >= data.pages}
                onClick={() => navigate({ page: String(data.page + 1) })}
                className="px-3 py-1.5 text-xs font-medium rounded-lg bg-white/5 border border-white/10 text-neutral-400 hover:bg-white/10 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default function CompaniesPage() {
  return (
    <React.Suspense fallback={
      <div className="space-y-6">
        <div className="animate-shimmer h-8 w-48 rounded-lg" />
        <div className="animate-shimmer h-96 rounded-xl" />
      </div>
    }>
      <CompaniesContent />
    </React.Suspense>
  );
}

