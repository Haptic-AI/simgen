"use client";

import { useState, useEffect, useCallback } from "react";

interface ServiceStatus {
  status: string;
  [key: string]: unknown;
}

interface SystemStatus {
  overall: string;
  services: {
    backend: ServiceStatus;
    database: ServiceStatus;
    anthropic_api: ServiceStatus;
    gpu_renderer: ServiceStatus;
  };
}

interface Props {
  apiUrl: string;
}

export default function StatusWidget({ apiUrl }: Props) {
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [collapsed, setCollapsed] = useState(true);

  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch(`${apiUrl}/status`);
      if (res.ok) setStatus(await res.json());
    } catch {
      setStatus(null);
    }
  }, [apiUrl]);

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 30000);
    return () => clearInterval(interval);
  }, [fetchStatus]);

  const dot = (ok: boolean) => (
    <span className={`inline-block w-1.5 h-1.5 rounded-full ${ok ? "bg-green-400" : "bg-red-400"}`} />
  );

  if (!status) return null;

  const allOk = status.overall === "ok";
  const gpu = status.services.gpu_renderer;
  const policies = (gpu?.policies as string[]) || [];

  return (
    <div className="fixed top-4 right-4 z-30">
      {/* Collapsed: just a dot */}
      {collapsed ? (
        <button
          onClick={() => setCollapsed(false)}
          className="flex items-center gap-2 bg-gray-900/90 backdrop-blur border border-gray-800 rounded-lg px-3 py-2 hover:border-gray-700 transition-colors"
          title="System status"
        >
          <span className={`w-2 h-2 rounded-full ${allOk ? "bg-green-400" : "bg-amber-400 animate-pulse"}`} />
          <span className="text-xs text-gray-500">Status</span>
        </button>
      ) : (
        <div className="bg-gray-900/95 backdrop-blur border border-gray-800 rounded-xl w-64 shadow-xl">
          <div className="flex items-center justify-between px-3 py-2.5 border-b border-gray-800/50">
            <div className="flex items-center gap-2">
              <span className={`w-2 h-2 rounded-full ${allOk ? "bg-green-400" : "bg-amber-400 animate-pulse"}`} />
              <span className="text-xs font-medium text-gray-300">System Status</span>
            </div>
            <button
              onClick={() => setCollapsed(true)}
              className="text-gray-600 hover:text-gray-400 transition-colors"
            >
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <div className="px-3 py-2 space-y-1.5">
            <StatusRow label="Backend API" ok={status.services.backend?.status === "ok"} dot={dot} />
            <StatusRow label="Database" ok={status.services.database?.status === "ok"} dot={dot}
              detail={`${(status.services.database as Record<string, unknown>)?.generations || 0} generations`} />
            <StatusRow label="Claude API" ok={status.services.anthropic_api?.status === "ok"} dot={dot}
              detail={status.services.anthropic_api?.status === "ok"
                ? `${(status.services.anthropic_api as Record<string, unknown>)?.latency_ms}ms`
                : String((status.services.anthropic_api as Record<string, unknown>)?.error || "")} />
            <StatusRow label="GPU Renderer" ok={gpu?.status === "ok"} dot={dot}
              detail={gpu?.status === "ok" ? String((gpu as Record<string, unknown>)?.gpu || "") : ""} />
          </div>

          {policies.length > 0 && (
            <div className="px-3 py-2 border-t border-gray-800/50">
              <p className="text-[10px] uppercase tracking-wider text-gray-600 mb-1.5">Trained Policies</p>
              <div className="flex flex-wrap gap-1">
                {policies.map((p) => (
                  <span key={p} className="text-[10px] bg-gray-800 text-gray-400 px-1.5 py-0.5 rounded">
                    {p}
                  </span>
                ))}
              </div>
            </div>
          )}

          <div className="px-3 py-1.5 border-t border-gray-800/50">
            <button
              onClick={fetchStatus}
              className="text-[10px] text-gray-600 hover:text-gray-400 transition-colors"
            >
              Refresh
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function StatusRow({ label, ok, dot, detail }: {
  label: string;
  ok: boolean;
  dot: (ok: boolean) => React.ReactNode;
  detail?: string;
}) {
  return (
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-2">
        {dot(ok)}
        <span className="text-xs text-gray-400">{label}</span>
      </div>
      {detail && (
        <span className={`text-[10px] ${ok ? "text-gray-600" : "text-red-400"}`}>
          {detail.length > 20 ? detail.slice(0, 20) + "..." : detail}
        </span>
      )}
    </div>
  );
}
