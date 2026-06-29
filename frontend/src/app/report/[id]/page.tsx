"use client";

import React, { useEffect, useState } from "react";

/* ------------------------------------------------------------------ */
/* Types                                                                */
/* ------------------------------------------------------------------ */

interface SeverityCounts {
  critical: number;
  high: number;
  medium: number;
  low: number;
}

interface PreviewFinding {
  id: number;
  title: string;
  file_path: string;
  severity: string;
  scanner: string;
}

interface ReportData {
  report_id: number;
  company: { id: number; name: string; github_org: string };
  severity_counts: SeverityCounts;
  total_findings: number;
  preview_findings: PreviewFinding[];
  price_dollars: number;
  price_cents: number;
  risk_estimate: { min_usd: number; max_usd: number };
  report_tier: string;
}

/* ------------------------------------------------------------------ */
/* Helpers                                                              */
/* ------------------------------------------------------------------ */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function severityColor(sev: string) {
  switch (sev?.toLowerCase()) {
    case "critical":
      return {
        bg: "bg-red-500/10",
        border: "border-red-500/20",
        text: "text-red-500",
        label: "text-red-400",
        badge: "bg-red-500/20 text-red-400 border-red-500/30",
        dot: "bg-red-500",
      };
    case "high":
      return {
        bg: "bg-orange-500/10",
        border: "border-orange-500/20",
        text: "text-orange-500",
        label: "text-orange-400",
        badge: "bg-orange-500/20 text-orange-400 border-orange-500/30",
        dot: "bg-orange-500",
      };
    case "medium":
      return {
        bg: "bg-yellow-500/10",
        border: "border-yellow-500/20",
        text: "text-yellow-500",
        label: "text-yellow-400",
        badge: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
        dot: "bg-yellow-500",
      };
    default:
      return {
        bg: "bg-white/5",
        border: "border-white/10",
        text: "text-neutral-400",
        label: "text-neutral-500",
        badge: "bg-white/10 text-neutral-400 border-white/10",
        dot: "bg-neutral-500",
      };
  }
}

function formatCurrency(val: number) {
  if (val >= 1_000_000)
    return `$${(val / 1_000_000).toFixed(1)}M`;
  if (val >= 1_000)
    return `$${(val / 1_000).toFixed(0)}K`;
  return `$${val.toFixed(0)}`;
}

/* ------------------------------------------------------------------ */
/* Skeleton loader                                                      */
/* ------------------------------------------------------------------ */

function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`animate-shimmer rounded-lg ${className}`} />;
}

function LoadingSkeleton() {
  return (
    <div className="min-h-screen bg-[#0a0a0a] bg-grid">
      {/* Nav skeleton */}
      <nav className="border-b border-white/5 bg-black/50 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <Skeleton className="w-32 h-6" />
          <Skeleton className="w-40 h-4" />
        </div>
      </nav>
      <main className="max-w-6xl mx-auto px-6 py-16 grid grid-cols-1 lg:grid-cols-3 gap-12">
        <div className="lg:col-span-2 space-y-8">
          <Skeleton className="w-3/4 h-12" />
          <Skeleton className="w-full h-6" />
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[1, 2, 3, 4].map((i) => (
              <Skeleton key={i} className="h-24" />
            ))}
          </div>
          <Skeleton className="w-full h-40" />
          <Skeleton className="w-full h-40" />
        </div>
        <div>
          <Skeleton className="h-96" />
        </div>
      </main>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Animated counter                                                     */
/* ------------------------------------------------------------------ */

function AnimatedNumber({ value, delay = 0 }: { value: number; delay?: number }) {
  const [display, setDisplay] = useState(0);

  useEffect(() => {
    const timer = setTimeout(() => {
      const duration = 800;
      const start = Date.now();
      const step = () => {
        const elapsed = Date.now() - start;
        const progress = Math.min(elapsed / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3);
        setDisplay(Math.round(eased * value));
        if (progress < 1) requestAnimationFrame(step);
      };
      requestAnimationFrame(step);
    }, delay);
    return () => clearTimeout(timer);
  }, [value, delay]);

  return <span>{display}</span>;
}

/* ------------------------------------------------------------------ */
/* Main Page Component                                                  */
/* ------------------------------------------------------------------ */

export default function ReportPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const [reportId, setReportId] = useState<string | null>(null);
  const [data, setData] = useState<ReportData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [checkoutLoading, setCheckoutLoading] = useState(false);

  // Resolve params
  useEffect(() => {
    params.then((p) => setReportId(p.id));
  }, [params]);

  // Fetch report data
  useEffect(() => {
    if (!reportId) return;
    setLoading(true);

    fetch(`${API_BASE}/api/reports/${reportId}/preview`)
      .then((res) => {
        if (!res.ok) throw new Error("Report not found");
        return res.json();
      })
      .then((json) => {
        setData(json);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, [reportId]);

  /* ----- Checkout handler -----  */
  async function handleCheckout() {
    if (!data) return;
    setCheckoutLoading(true);

    try {
      const res = await fetch(`${API_BASE}/api/checkout`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          report_id: data.report_id,
          email: "",  // Will be collected by Stripe Checkout
        }),
      });

      if (!res.ok) throw new Error("Failed to create checkout session");
      const json = await res.json();
      if (json.checkout_url) {
        window.location.href = json.checkout_url;
      }
    } catch {
      setCheckoutLoading(false);
    }
  }

  /* ----- Loading state ----- */
  if (loading) return <LoadingSkeleton />;

  /* ----- Error state ----- */
  if (error || !data) {
    return (
      <div className="min-h-screen bg-[#0a0a0a] bg-grid flex items-center justify-center">
        <div className="text-center glass rounded-2xl p-12 max-w-md">
          <div className="w-16 h-16 rounded-full bg-red-500/10 flex items-center justify-center mx-auto mb-6">
            <svg className="w-8 h-8 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z" />
            </svg>
          </div>
          <h2 className="text-xl font-semibold mb-2">Report Not Found</h2>
          <p className="text-neutral-400 text-sm">
            This report may not exist or has been removed.
          </p>
        </div>
      </div>
    );
  }

  const { company, severity_counts, total_findings, preview_findings, price_dollars, risk_estimate } = data;

  /* ---------------------------------------------------------------- */
  /* Render                                                             */
  /* ---------------------------------------------------------------- */
  return (
    <div className="min-h-screen bg-[#0a0a0a] bg-grid text-neutral-50 selection:bg-indigo-500/30">
      {/* ===== Navigation ===== */}
      <nav className="border-b border-white/5 bg-black/60 backdrop-blur-xl sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="font-bold text-lg tracking-tight text-white flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-indigo-500 to-indigo-700 flex items-center justify-center shadow-lg shadow-indigo-500/20">
              <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
              </svg>
            </div>
            AutoScan
          </div>
          <div className="text-sm text-neutral-500 font-medium hidden sm:block">
            Vulnerability Intelligence Report
          </div>
        </div>
      </nav>

      {/* ===== Main Content ===== */}
      <main className="max-w-6xl mx-auto px-6 py-12 md:py-20 grid grid-cols-1 lg:grid-cols-3 gap-12 lg:gap-16">
        {/* ---------- Left Column: Report Details ---------- */}
        <div className="lg:col-span-2 space-y-10">
          {/* Hero */}
          <div className="animate-fade-in-up">
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-xs font-medium mb-5">
              <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-pulse" />
              Report Ready
            </div>
            <h1 className="text-3xl sm:text-4xl md:text-5xl font-bold tracking-tight mb-4 leading-[1.1]">
              Security Report for{" "}
              <span className="text-gradient">{company.name}</span>
            </h1>
            <p className="text-base sm:text-lg text-neutral-400 leading-relaxed max-w-2xl">
              Our automated scanning engines have analyzed your public
              repositories and identified{" "}
              <span className="text-white font-semibold">{total_findings} security vulnerabilities</span>{" "}
              that may expose your infrastructure to risk.
            </p>
          </div>

          {/* Risk banner */}
          {risk_estimate.max_usd > 0 && (
            <div className="animate-fade-in-up-delay-1 glass rounded-xl p-5 flex items-center gap-4">
              <div className="w-10 h-10 rounded-lg bg-red-500/10 flex items-center justify-center shrink-0">
                <svg className="w-5 h-5 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <div>
                <div className="text-sm font-medium text-neutral-200">
                  Estimated Risk Exposure
                </div>
                <div className="text-xs text-neutral-400 mt-0.5">
                  Potential financial impact:{" "}
                  <span className="text-red-400 font-semibold">
                    {formatCurrency(risk_estimate.min_usd)} – {formatCurrency(risk_estimate.max_usd)}
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Severity Breakdown */}
          <div className="animate-fade-in-up-delay-2">
            <h3 className="text-sm font-medium text-neutral-500 uppercase tracking-wider mb-4">
              Severity Breakdown
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {(
                [
                  ["critical", severity_counts.critical],
                  ["high", severity_counts.high],
                  ["medium", severity_counts.medium],
                  ["low", severity_counts.low],
                ] as const
              ).map(([sev, count], i) => {
                const c = severityColor(sev);
                return (
                  <div
                    key={sev}
                    className={`${c.bg} border ${c.border} rounded-xl p-5 flex flex-col items-center justify-center transition-transform hover:scale-[1.03] hover:shadow-lg`}
                  >
                    <span className={`text-4xl font-bold ${c.text} animate-count-up`} style={{ animationDelay: `${i * 100 + 200}ms` }}>
                      <AnimatedNumber value={count} delay={i * 100 + 200} />
                    </span>
                    <span className={`text-[10px] ${c.label} uppercase tracking-widest mt-1.5 font-semibold`}>
                      {sev}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Finding Previews */}
          <div className="animate-fade-in-up-delay-3 space-y-4">
            <h3 className="text-sm font-medium text-neutral-500 uppercase tracking-wider mb-4">
              Vulnerability Previews
            </h3>

            {preview_findings.map((finding, i) => {
              const c = severityColor(finding.severity);
              return (
                <div
                  key={finding.id}
                  className="glass rounded-xl p-5 relative overflow-hidden group transition-all hover:border-white/10"
                >
                  <div className="flex flex-wrap items-center gap-2.5 mb-3">
                    <span className={`px-2.5 py-0.5 rounded-md text-[11px] font-semibold border ${c.badge}`}>
                      {finding.severity}
                    </span>
                    <span className="font-mono text-xs text-neutral-500 truncate max-w-[200px]">
                      {finding.file_path}
                    </span>
                    <span className="ml-auto text-[10px] text-neutral-600 font-mono uppercase">
                      {finding.scanner}
                    </span>
                  </div>

                  <h4 className="text-base font-medium text-white mb-3">
                    {finding.title}
                  </h4>

                  {/* Redacted code block */}
                  <div className="bg-black/50 p-4 rounded-lg font-mono text-xs text-neutral-600 select-none blur-[3px] group-hover:blur-[5px] transition-all leading-relaxed">
                    <p>const config = require(&apos;./sensitive-config&apos;);</p>
                    <p>const credential = &quot;████████████████████████&quot;;</p>
                    <p>// ... {Math.floor(Math.random() * 20 + 5)} more lines redacted</p>
                  </div>

                  {/* Lock overlay */}
                  <div className="absolute inset-0 flex items-center justify-center bg-[#0a0a0a]/30 backdrop-blur-[1px] opacity-0 group-hover:opacity-100 transition-all duration-300">
                    <div className="bg-black/80 text-white px-5 py-2.5 rounded-full text-sm font-medium border border-white/10 shadow-2xl flex items-center gap-2.5 animate-float">
                      <svg className="w-4 h-4 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                      </svg>
                      Unlock to view full details
                    </div>
                  </div>
                </div>
              );
            })}

            {preview_findings.length === 0 && (
              <div className="glass rounded-xl p-8 text-center text-neutral-500 text-sm">
                Finding previews will appear here once analysis is complete.
              </div>
            )}
          </div>
        </div>

        {/* ---------- Right Column: Checkout Card ---------- */}
        <div className="relative animate-fade-in-up-delay-4">
          <div className="sticky top-24 space-y-5">
            {/* Main CTA Card */}
            <div className="glass rounded-2xl p-7 shadow-2xl shadow-indigo-500/5 animate-pulse-glow">
              <h2 className="text-2xl font-bold mb-1.5">Unlock Full Report</h2>
              <p className="text-sm text-neutral-400 mb-6 leading-relaxed">
                Get immediate access to the full technical analysis, reproduction steps, and AI-driven remediation guidance.
              </p>

              <div className="flex items-baseline gap-2.5 mb-7">
                <span className="text-5xl font-extrabold tracking-tight">
                  ${Math.floor(price_dollars)}
                </span>
                <span className="text-neutral-500 font-medium text-lg">USD</span>
              </div>

              <button
                id="checkout-button"
                onClick={handleCheckout}
                disabled={checkoutLoading}
                className="w-full bg-gradient-to-r from-indigo-600 to-indigo-500 hover:from-indigo-500 hover:to-indigo-400 disabled:opacity-60 disabled:cursor-not-allowed text-white font-semibold py-4 px-5 rounded-xl shadow-lg shadow-indigo-600/25 transition-all active:scale-[0.98] flex justify-center items-center gap-2.5 cursor-pointer"
              >
                {checkoutLoading ? (
                  <>
                    <svg className="animate-spin w-5 h-5" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                    Redirecting to Stripe…
                  </>
                ) : (
                  <>
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
                    </svg>
                    Pay with Stripe
                  </>
                )}
              </button>

              {/* Value props */}
              <div className="mt-7 space-y-3">
                {[
                  "Detailed vulnerability analysis & PoC",
                  "Exact file paths and line numbers",
                  "AI-driven remediation steps",
                  "Downloadable PDF report",
                  "Delivered to your inbox in seconds",
                ].map((text, i) => (
                  <div key={i} className="flex items-center gap-3 text-sm text-neutral-300">
                    <svg className="w-4.5 h-4.5 text-emerald-400 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M5 13l4 4L19 7" />
                    </svg>
                    {text}
                  </div>
                ))}
              </div>

              {/* Security badge */}
              <div className="mt-7 pt-5 border-t border-white/5">
                <div className="flex items-center justify-center gap-2 text-[11px] text-neutral-500">
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                  </svg>
                  Secure payment processed by Stripe
                </div>
              </div>
            </div>

            {/* Tier badge */}
            {data.report_tier && data.report_tier !== "standard" && (
              <div className="glass rounded-xl p-4 text-center">
                <span className="text-xs font-semibold uppercase tracking-widest text-indigo-400">
                  {data.report_tier} tier
                </span>
              </div>
            )}
          </div>
        </div>
      </main>

      {/* ===== Trust Signals Section ===== */}
      <section className="border-t border-white/5 bg-black/40 py-20">
        <div className="max-w-6xl mx-auto px-6">
          <div className="text-center mb-14">
            <h2 className="text-3xl font-bold mb-4">Why Trust AutoScan?</h2>
            <p className="text-neutral-400 max-w-2xl mx-auto text-base leading-relaxed">
              AutoScan is an enterprise-grade vulnerability intelligence
              platform. Our proprietary engines analyze public codebases to
              alert companies to critical risks before malicious actors can
              exploit them.
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-6">
            {[
              {
                icon: (
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                  </svg>
                ),
                color: "text-blue-400 bg-blue-500/10",
                title: "Zero False Positives",
                desc: "Every finding is verified using AI context analysis to ensure you only pay for actionable intelligence.",
              },
              {
                icon: (
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                ),
                color: "text-purple-400 bg-purple-500/10",
                title: "Immediate Delivery",
                desc: "Your full PDF report is delivered securely via an encrypted link within seconds of payment.",
              },
              {
                icon: (
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                  </svg>
                ),
                color: "text-teal-400 bg-teal-500/10",
                title: "Private & Confidential",
                desc: "We do not disclose our findings to third parties. Purchasing this report grants you exclusive access.",
              },
            ].map((card, i) => (
              <div
                key={i}
                className="glass rounded-xl p-6 glass-hover transition-all duration-300 hover:-translate-y-1"
              >
                <div className={`w-12 h-12 rounded-lg ${card.color} flex items-center justify-center mb-4`}>
                  {card.icon}
                </div>
                <h3 className="text-lg font-semibold mb-2">{card.title}</h3>
                <p className="text-sm text-neutral-400 leading-relaxed">
                  {card.desc}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ===== About Section ===== */}
      <section className="border-t border-white/5 py-16">
        <div className="max-w-3xl mx-auto px-6 text-center">
          <h2 className="text-2xl font-bold mb-4">About AutoScan</h2>
          <p className="text-neutral-400 leading-relaxed">
            AutoScan continuously monitors public GitHub repositories to
            identify leaked credentials, dependency vulnerabilities, insecure
            code patterns, and infrastructure misconfigurations. Our reports
            combine multi-scanner analysis with AI verification to deliver
            the highest-quality vulnerability intelligence available.
          </p>
        </div>
      </section>

      {/* ===== Footer ===== */}
      <footer className="py-8 text-center border-t border-white/5 text-neutral-600 text-sm">
        <p>© {new Date().getFullYear()} AutoScan Security. All rights reserved.</p>
      </footer>
    </div>
  );
}
