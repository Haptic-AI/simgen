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
        className="flex-1 bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl px-4 py-3 text-[var(--color-text)] placeholder-[var(--color-text-faint)] focus:outline-none focus:border-[var(--color-primary)] focus:ring-1 focus:ring-[var(--color-primary)]/20 disabled:opacity-50 text-sm transition-colors"
        style={{ boxShadow: 'var(--shadow-sm)' }}
      />
      <button
        onClick={handleSubmit}
        disabled={!prompt.trim() || loading}
        className="bg-[var(--color-primary)] hover:bg-[var(--color-primary-hover)] disabled:bg-[var(--color-border)] disabled:text-[var(--color-text-faint)] text-[var(--color-primary-text)] px-6 py-3 rounded-xl font-medium text-xs tracking-wide uppercase transition-colors"
        style={{ boxShadow: 'var(--shadow-sm)' }}
      >
        {loading ? "..." : "Simulate"}
      </button>
    </div>
  );
}
