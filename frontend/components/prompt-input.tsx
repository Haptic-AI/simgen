"use client";

import { useState, KeyboardEvent } from "react";

interface Props {
  onSubmit: (prompt: string) => void;
  loading: boolean;
  placeholder?: string;
}

export default function PromptInput({ onSubmit, loading, placeholder }: Props) {
  const [prompt, setPrompt] = useState("");

  const handleSubmit = () => {
    const trimmed = prompt.trim();
    if (!trimmed || loading) return;
    onSubmit(trimmed);
    setPrompt("");
  };

  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="max-w-2xl mx-auto w-full flex gap-3">
      <input
        type="text"
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder || "Describe a scene..."}
        disabled={loading}
        className="flex-1 bg-white/[0.03] border border-white/[0.08] rounded-xl px-4 py-3 text-gray-100 placeholder-gray-500 focus:outline-none focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/20 disabled:opacity-50 text-sm transition-colors"
      />
      <button
        onClick={handleSubmit}
        disabled={!prompt.trim() || loading}
        className="bg-blue-500 hover:bg-blue-400 disabled:bg-white/[0.04] disabled:text-gray-600 text-white px-6 py-3 rounded-xl font-medium text-xs tracking-wide uppercase transition-colors"
      >
        {loading ? "..." : "Generate"}
      </button>
    </div>
  );
}
