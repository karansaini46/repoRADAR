"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/* ------------------------------------------------------------------ */
/* Types                                                                */
/* ------------------------------------------------------------------ */

interface Finding {
  id: number;
  type: string;
  severity: string;
  title: string;
  description: string | null;
  file_path: string | null;
  line_no: number | null;
  scanner_name: string;
  verified: boolean | null;
  is_false_positive: boolean | null;
  ai_explanation: string | null;
  ai_recommendation: string | null;
  created_at: string | null;
  repo_name: string;
  repo_full_name: string;
  company_id: number;
  company_name: string;
}

const SEV_STYLES: Record<string, string> = {
  critical: "bg-red-500/15 text-red-400 border-red-500/25",
  high: "bg-orange-500/15 text-orange-400 border-orange-500/25",
  medium: "bg-yellow-500/15 text-yellow-400 border-yellow-500/25",
  low: "bg-neutral-500/15 text-neutral-400 border-neutral-500/25",
};

/* ------------------------------------------------------------------ */
/* Page                                                                 */
/* ------------------------------------------------------------------ */

export default function VerifiedFindingsPage() {
  const [findings, setFindings] = useState<Finding[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedFindingId, setExpandedFindingId] = useState<number | null>(null);

  useEffect(() => {
    fetch(`${API}/api/dashboard/verified-findings`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (d?.findings) {
          setFindings(d.findings);
        }
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="animate-shimmer h-8 w-64 rounded-lg" />
        <div className="animate-shimmer h-96 rounded-xl" />
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in-up">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm text-neutral-500">
        <Link href="/dashboard" className="hover:text-neutral-300 transition-colors">Dashboard</Link>
        <span>/</span>
        <span className="text-neutral-300">Verified Findings</span>
      </div>

      <div>
        <h1 className="text-2xl font-bold tracking-tight">Verified Findings</h1>
        <p className="text-sm text-neutral-500 mt-1">
          All vulnerabilities that have been successfully verified by AI across {findings.length} findings.
        </p>
      </div>

      <div className="glass rounded-xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-white/5 bg-white/[0.02]">
                <th className="py-3 px-4 text-left text-xs font-medium text-neutral-500 uppercase tracking-wider">Company</th>
                <th className="py-3 px-4 text-left text-xs font-medium text-neutral-500 uppercase tracking-wider">Repository</th>
                <th className="py-3 px-4 text-left text-xs font-medium text-neutral-500 uppercase tracking-wider">Severity</th>
                <th className="py-3 px-4 text-left text-xs font-medium text-neutral-500 uppercase tracking-wider">Title</th>
                <th className="py-3 px-4 text-left text-xs font-medium text-neutral-500 uppercase tracking-wider">Scanner</th>
              </tr>
            </thead>
            <tbody>
              {findings.map((f) => (
                <React.Fragment key={f.id}>
                  <tr
                    className="border-b border-white/5 hover:bg-white/[0.02] transition-colors cursor-pointer"
                    onClick={() => setExpandedFindingId(expandedFindingId === f.id ? null : f.id)}
                  >
                    <td className="py-3 px-4">
                      <Link
                        href={`/dashboard/companies/${f.company_id}`}
                        className="text-indigo-400 hover:text-indigo-300 transition-colors"
                        onClick={(e) => e.stopPropagation()}
                      >
                        {f.company_name}
                      </Link>
                    </td>
                    <td className="py-3 px-4 text-neutral-300 max-w-[200px] truncate">
                      <a
                        href={`https://github.com/${f.repo_full_name}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="hover:text-white transition-colors"
                        onClick={(e) => e.stopPropagation()}
                      >
                        {f.repo_name}
                      </a>
                    </td>
                    <td className="py-3 px-4">
                      <span className={`px-2 py-0.5 rounded-md text-[10px] font-semibold uppercase border ${SEV_STYLES[f.severity?.toLowerCase()] || SEV_STYLES.low}`}>
                        {f.severity}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-neutral-200 max-w-xs truncate flex items-center gap-2">
                      <svg
                        className={`w-4 h-4 text-neutral-500 transition-transform ${expandedFindingId === f.id ? "rotate-90" : ""}`}
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5l7 7-7 7" />
                      </svg>
                      {f.title}
                    </td>
                    <td className="py-3 px-4 text-xs text-neutral-400">{f.scanner_name}</td>
                  </tr>
                  {expandedFindingId === f.id && (
                    <tr className="border-b border-white/5 bg-black/20">
                      <td colSpan={5} className="p-6">
                        <div className="space-y-4 max-w-3xl">
                          {f.description && (
                            <div>
                              <h4 className="text-xs font-semibold text-neutral-400 uppercase tracking-wider mb-2">Original Description</h4>
                              <div className="text-sm text-neutral-300 p-3 rounded-lg bg-white/5 font-mono whitespace-pre-wrap">
                                {f.description}
                              </div>
                            </div>
                          )}

                          {/* GitHub Source Link */}
                          {f.file_path && (
                            <div>
                              <h4 className="text-xs font-semibold text-neutral-400 uppercase tracking-wider mb-2 flex items-center gap-2">
                                <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                                  <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z" />
                                </svg>
                                Source Location
                              </h4>
                              <a
                                href={`https://github.com/${f.repo_full_name || ""}/blob/HEAD/${f.file_path}${f.line_no ? `#L${f.line_no}` : ""}`}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="flex items-center gap-3 p-3 rounded-lg bg-white/5 border border-white/10 hover:border-indigo-500/30 hover:bg-white/[0.07] transition-all group"
                              >
                                <div className="flex-1 min-w-0">
                                  <p className="text-sm text-indigo-400 font-mono truncate group-hover:text-indigo-300 transition-colors">
                                    {f.file_path}
                                    {f.line_no ? `:${f.line_no}` : ""}
                                  </p>
                                  <p className="text-[11px] text-neutral-600 mt-0.5">
                                    {f.repo_full_name || "unknown"}
                                  </p>
                                </div>
                                <span className="px-3 py-1.5 text-xs font-medium rounded-lg bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 group-hover:bg-indigo-500/20 transition-colors shrink-0">
                                  View on GitHub →
                                </span>
                              </a>
                            </div>
                          )}

                          {f.ai_explanation && (
                            <div>
                              <h4 className="text-xs font-semibold text-indigo-400 uppercase tracking-wider mb-2 flex items-center gap-2">
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
                                </svg>
                                AI Analysis
                              </h4>
                              <div className="text-sm text-neutral-200 p-4 rounded-lg border border-indigo-500/20 bg-indigo-500/5 leading-relaxed whitespace-pre-wrap">
                                {f.ai_explanation}
                              </div>
                            </div>
                          )}

                          {f.ai_recommendation && (
                            <div>
                              <h4 className="text-xs font-semibold text-emerald-400 uppercase tracking-wider mb-2 flex items-center gap-2">
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                                </svg>
                                Recommended Fix
                              </h4>
                              <div className="text-sm text-neutral-200 p-4 rounded-lg border border-emerald-500/20 bg-emerald-500/5 leading-relaxed whitespace-pre-wrap">
                                {f.ai_recommendation}
                              </div>
                            </div>
                          )}

                          {f.is_false_positive && (
                            <div className="mt-2 text-sm text-amber-500 font-medium">
                              Note: This finding was flagged as a potential false positive by the AI verifier.
                            </div>
                          )}
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              ))}
              {findings.length === 0 && (
                <tr>
                  <td colSpan={5} className="py-12 text-center text-neutral-600">
                    No verified findings yet
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
