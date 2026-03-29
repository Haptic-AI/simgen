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
          className="fixed inset-0 bg-black/40 z-40"
          onClick={onClose}
        />
      )}

      {/* Sidebar */}
      <div
        className={`fixed top-0 left-0 h-full w-80 bg-gray-950 border-r border-gray-800 z-50 transform transition-transform duration-200 ${
          open ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex items-center justify-between px-4 py-4 border-b border-gray-800">
          <h2 className="text-sm font-semibold text-gray-200">Prompt History</h2>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-300 transition-colors"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="overflow-y-auto h-[calc(100%-57px)] px-2 py-2">
          {history.length === 0 && (
            <p className="text-sm text-gray-600 text-center py-8">No prompts yet</p>
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
                className="w-full text-left px-3 py-2.5 rounded-lg hover:bg-gray-900 transition-colors group mb-1"
              >
                <p className="text-sm text-gray-300 group-hover:text-indigo-400 transition-colors line-clamp-2">
                  {displayPrompt}
                </p>
                <div className="flex items-center gap-2 mt-1">
                  <span className="text-sm text-gray-600">{formatTime(item.created_at)}</span>
                  <span className="text-sm text-gray-700">{item.template}</span>
                  {total > 0 && (
                    <span className="text-sm">
                      <span className="text-green-500">{item.upvotes}</span>
                      <span className="text-gray-700">/</span>
                      <span className="text-red-500">{item.downvotes}</span>
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
