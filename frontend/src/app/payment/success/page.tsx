"use client";

import React, { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";

/* ------------------------------------------------------------------ */
/* Inner component that uses useSearchParams (requires Suspense)       */
/* ------------------------------------------------------------------ */

function SuccessContent() {
  const searchParams = useSearchParams();
  const sessionId = searchParams.get("session_id");
  const [showCheck, setShowCheck] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => setShowCheck(true), 300);
    return () => clearTimeout(timer);
  }, []);

  return (
    <>
      {/* Animated checkmark */}
      <div
        className={`mx-auto w-20 h-20 rounded-full flex items-center justify-center mb-8 transition-all duration-700 ease-out ${
          showCheck
            ? "bg-emerald-500/10 scale-100 opacity-100"
            : "bg-emerald-500/5 scale-50 opacity-0"
        }`}
      >
        <svg
          className={`w-10 h-10 text-emerald-400 transition-all duration-500 delay-300 ${
            showCheck ? "scale-100 opacity-100" : "scale-0 opacity-0"
          }`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth="2.5"
            d="M5 13l4 4L19 7"
          />
        </svg>
      </div>

      {/* Text content */}
      <div
        className={`transition-all duration-700 delay-500 ${
          showCheck
            ? "translate-y-0 opacity-100"
            : "translate-y-4 opacity-0"
        }`}
      >
        <h1 className="text-3xl sm:text-4xl font-bold mb-3 tracking-tight">
          Payment Successful!
        </h1>
        <p className="text-neutral-400 text-lg mb-8 leading-relaxed">
          Thank you for your purchase. Your full vulnerability report is
          being delivered to your inbox right now.
        </p>

        {/* Info card */}
        <div className="glass rounded-2xl p-6 text-left space-y-4 mb-8">
          <div className="flex items-start gap-3">
            <div className="w-9 h-9 rounded-lg bg-indigo-500/10 flex items-center justify-center shrink-0 mt-0.5">
              <svg
                className="w-5 h-5 text-indigo-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                  d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
                />
              </svg>
            </div>
            <div>
              <h3 className="text-sm font-semibold text-neutral-200">
                Check Your Email
              </h3>
              <p className="text-xs text-neutral-500 mt-0.5">
                The full PDF report has been sent to the email address you
                provided during checkout. It includes a secure download link
                valid for 7 days.
              </p>
            </div>
          </div>

          <div className="flex items-start gap-3">
            <div className="w-9 h-9 rounded-lg bg-emerald-500/10 flex items-center justify-center shrink-0 mt-0.5">
              <svg
                className="w-5 h-5 text-emerald-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                  d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                />
              </svg>
            </div>
            <div>
              <h3 className="text-sm font-semibold text-neutral-200">
                What&apos;s Included
              </h3>
              <p className="text-xs text-neutral-500 mt-0.5">
                Full vulnerability analysis with exact file paths, PoC
                details, AI-verified severity ratings, and step-by-step
                remediation guidance.
              </p>
            </div>
          </div>
        </div>

        {/* Session reference */}
        {sessionId && (
          <p className="text-[11px] text-neutral-600 font-mono mb-6">
            Session: {sessionId.slice(0, 28)}…
          </p>
        )}

        {/* CTA */}
        <a
          href="/"
          className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-white/5 border border-white/10 text-sm font-medium text-neutral-300 hover:bg-white/10 hover:text-white transition-all"
        >
          <svg
            className="w-4 h-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="2"
              d="M10 19l-7-7m0 0l7-7m-7 7h18"
            />
          </svg>
          Back to Home
        </a>
      </div>
    </>
  );
}

/* ------------------------------------------------------------------ */
/* Loading fallback                                                     */
/* ------------------------------------------------------------------ */

function SuccessLoading() {
  return (
    <div className="flex flex-col items-center">
      <div className="w-20 h-20 rounded-full bg-emerald-500/5 animate-pulse mb-8" />
      <div className="h-8 w-64 animate-shimmer rounded-lg mb-3" />
      <div className="h-5 w-80 animate-shimmer rounded-lg" />
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Page component                                                       */
/* ------------------------------------------------------------------ */

export default function PaymentSuccessPage() {
  return (
    <div className="min-h-screen bg-[#0a0a0a] bg-grid flex flex-col">
      {/* Navigation */}
      <nav className="border-b border-white/5 bg-black/60 backdrop-blur-xl">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center">
          <a
            href="/"
            className="font-bold text-lg tracking-tight text-white flex items-center gap-2.5 hover:opacity-80 transition-opacity"
          >
            <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-indigo-500 to-indigo-700 flex items-center justify-center shadow-lg shadow-indigo-500/20">
              <svg
                className="w-4 h-4 text-white"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2.5"
                  d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
                />
              </svg>
            </div>
            AutoScan
          </a>
        </div>
      </nav>

      {/* Main Content */}
      <main className="flex-1 flex items-center justify-center px-6 py-20">
        <div className="max-w-lg w-full text-center">
          <Suspense fallback={<SuccessLoading />}>
            <SuccessContent />
          </Suspense>
        </div>
      </main>

      {/* Footer */}
      <footer className="py-6 text-center border-t border-white/5 text-neutral-600 text-xs">
        <p>
          © {new Date().getFullYear()} AutoScan Security. All rights reserved.
        </p>
      </footer>
    </div>
  );
}
