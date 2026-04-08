"use client";

import { useState, useEffect, useCallback } from "react";

interface HistoryItem {
  id: string;
  prompt: string;
  template: string;
  created_at: string;
  sim_count: number;
  upvotes: number;
  downvotes: number;
}

interface Props {
  apiUrl: string;
  open: boolean;
  onClose: () => void;
  onSelectPrompt: (prompt: string) => void;
  refreshKey?: number;
}

export default function HistorySidebar({ apiUrl, open, onClose, onSelectPrompt, refreshKey }: Props) {
  const [history, setHistory] = useState<HistoryItem[]>([]);

  const fetchHistory = useCallback(async () => {
    try {
      const res = await fetch(`${apiUrl}/history`);
      if (res.ok) setHistory(await res.json());
    } catch {}
  }, [apiUrl]);

  useEffect(() => {
    if (open) fetchHistory();
  }, [open, fetchHistory, refreshKey]);

  const formatTime = (iso: string) => {
    const d = new Date(iso + "Z");
    const now = new Date();
    const diff = now.getTime() - d.getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return "just now";
    if (mins < 60) return `${mins}m ago`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}h ago`;
    return `${Math.floor(hrs / 24)}d ago`;
  };

  return (
    <>
      {/* Overlay */}
      {open && (
        <div
          className="fixed inset-0 bg-[var(--color-accent)]/20 z-40"
          style={{ backdropFilter: 'blur(2px)' }}
          onClick={onClose}
        />
      )}

      {/* Sidebar */}
      <div
        className={`fixed top-0 left-0 h-full w-80 bg-[var(--color-bg)] border-r border-[var(--color-border-strong)] z-50 transform transition-transform duration-200 ${
          open ? "translate-x-0" : "-translate-x-full"
        }`}
        style={{ boxShadow: open ? 'var(--shadow-lg)' : 'none' }}
      >
        <div className="flex items-center justify-between px-4 py-4 border-b border-[var(--color-border)]">
          <h2 className="text-sm font-semibold text-[var(--color-text)]">Prompt History</h2>
          <button
            onClick={onClose}
            className="text-[var(--color-text-muted)] hover:text-[var(--color-text)] transition-colors"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="overflow-y-auto h-[calc(100%-57px)] px-2 py-2">
          {history.length === 0 && (
            <p className="text-sm text-[var(--color-text-faint)] text-center py-8">No prompts yet</p>
          )}

          {history.map((item) => {
            const total = item.upvotes + item.downvotes;
            const displayPrompt = item.prompt.replace(/^\[vary\]\s*/, "");

            return (
              <button
                key={item.id}
                onClick={() => {
                  onSelectPrompt(displayPrompt);
                  onClose();
                }}
                className="w-full text-left px-3 py-2.5 rounded-[var(--radius-md)] hover:bg-[var(--color-primary-light)] transition-colors group mb-1"
              >
                <p className="text-sm text-[var(--color-text)] group-hover:text-[var(--color-primary)] transition-colors line-clamp-2">
                  {displayPrompt}
                </p>
                <div className="flex items-center gap-2 mt-1">
                  <span className="text-sm text-[var(--color-text-faint)]">{formatTime(item.created_at)}</span>
                  <span className="text-sm text-[var(--color-text-faint)]">{item.template}</span>
                  {total > 0 && (
                    <span className="text-sm">
                      <span className="text-[var(--color-success)]">{item.upvotes}</span>
                      <span className="text-[var(--color-text-faint)]">/</span>
                      <span className="text-[var(--color-error)]">{item.downvotes}</span>
                    </span>
                  )}
                </div>
              </button>
            );
          })}
        </div>
      </div>
    </>
  );
}
