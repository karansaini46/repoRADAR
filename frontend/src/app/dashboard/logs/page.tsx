"use client";

import React, { useState, useEffect, useRef } from "react";
const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type ServiceName = "api" | "worker" | "scheduler";

export default function LogsPage() {
  const [service, setService] = useState<ServiceName>("worker");
  const [logs, setLogs] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [autoScroll, setAutoScroll] = useState(true);
  const scrollRef = useRef<HTMLPreElement>(null);

  useEffect(() => {
    const fetchLogs = async () => {
      try {
        const res = await fetch(`${API}/api/system/logs?service=${service}&lines=500`);
        if (!res.ok) throw new Error("Failed to fetch logs");
        const data = await res.json();
        setLogs(data.logs || "No logs available.");
      } catch (err) {
        console.error(err);
        setLogs("Error fetching logs. Ensure backend is running and logs are generated.");
      } finally {
        setLoading(false);
      }
    };

    fetchLogs();
    const interval = setInterval(fetchLogs, 3000);
    return () => clearInterval(interval);
  }, [service]);

  useEffect(() => {
    if (autoScroll && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs, autoScroll]);

  // A basic syntax highlighter for log levels
  const renderHighlightedLogs = (text: string) => {
    if (!text) return null;
    return text.split('\n').map((line, i) => {
      let colorClass = "text-neutral-300";
      if (line.includes("ERROR") || line.includes("Exception") || line.includes("Failed") || line.includes("Traceback")) {
        colorClass = "text-red-400 font-medium";
      } else if (line.includes("WARNING")) {
        colorClass = "text-yellow-400 font-medium";
      } else if (line.includes("INFO") || line.includes("SUCCESS")) {
        colorClass = "text-indigo-300";
      }
      return (
        <div key={i} className={`whitespace-pre-wrap ${colorClass}`}>
          {line}
        </div>
      );
    });
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto h-[calc(100vh-8rem)] flex flex-col">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">System Logs</h1>
          <p className="text-sm text-neutral-400 mt-1">
            Real-time stdout stream from background containers.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={service}
            onChange={(e) => {
              setService(e.target.value as ServiceName);
              setLoading(true);
            }}
            className="bg-white/5 border border-white/10 text-white text-sm rounded-lg focus:ring-indigo-500 focus:border-indigo-500 block p-2.5 outline-none"
          >
            <option value="worker">Worker (Background Tasks)</option>
            <option value="api">API (FastAPI)</option>
            <option value="scheduler">Scheduler (Cron Jobs)</option>
          </select>
          <label className="flex items-center gap-2 text-sm text-neutral-300 cursor-pointer bg-white/5 px-3 py-2 rounded-lg border border-white/10">
            <input 
              type="checkbox" 
              checked={autoScroll}
              onChange={(e) => setAutoScroll(e.target.checked)}
              className="rounded bg-black/50 border-white/20 text-indigo-500 focus:ring-indigo-500 focus:ring-offset-0 focus:ring-1" 
            />
            Auto-scroll
          </label>
        </div>
      </div>

      <div className="flex-1 bg-[#050505] border border-white/10 rounded-xl overflow-hidden flex flex-col relative shadow-2xl">
        {/* Terminal Header */}
        <div className="h-10 bg-white/5 border-b border-white/10 flex items-center px-4 gap-2 shrink-0">
          <div className="w-3 h-3 rounded-full bg-red-500/80"></div>
          <div className="w-3 h-3 rounded-full bg-yellow-500/80"></div>
          <div className="w-3 h-3 rounded-full bg-green-500/80"></div>
          <span className="ml-2 text-xs text-neutral-500 font-mono tracking-wider">
            root@{service}:/app/autoscan/logs/{service}.log
          </span>
          {loading && (
            <span className="ml-auto text-xs text-indigo-400 animate-pulse font-mono">Loading...</span>
          )}
        </div>

        {/* Terminal Body */}
        <pre 
          ref={scrollRef}
          className="flex-1 overflow-y-auto p-4 font-mono text-sm leading-relaxed custom-scrollbar relative"
          style={{ scrollBehavior: 'smooth' }}
        >
          {loading && !logs ? (
            <div className="text-neutral-500 flex items-center gap-2">
              <svg className="animate-spin h-4 w-4 text-indigo-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Establishing connection...
            </div>
          ) : (
            renderHighlightedLogs(logs)
          )}
        </pre>
      </div>
      
      <style dangerouslySetInnerHTML={{__html: `
        .custom-scrollbar::-webkit-scrollbar {
          width: 8px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: rgba(0,0,0,0.2);
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: rgba(255,255,255,0.1);
          border-radius: 4px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
          background: rgba(255,255,255,0.2);
        }
      `}} />
    </div>
  );
}
