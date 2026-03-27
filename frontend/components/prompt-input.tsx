"use client";

import { useState, KeyboardEvent } from "react";

interface Props {
  onSubmit: (prompt: string) => void;
  loading: boolean;
}

export default function PromptInput({ onSubmit, loading }: Props) {
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
        placeholder="Describe a physics simulation..."
        disabled={loading}
        className="flex-1 bg-gray-900 border border-gray-700 rounded-lg px-4 py-3 text-gray-100 placeholder-gray-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 disabled:opacity-50 text-sm"
      />
      <button
        onClick={handleSubmit}
        disabled={!prompt.trim() || loading}
        className="bg-indigo-600 hover:bg-indigo-500 disabled:bg-gray-800 disabled:text-gray-600 text-white px-6 py-3 rounded-lg font-medium text-sm transition-colors"
      >
        {loading ? "..." : "Generate"}
      </button>
    </div>
  );
}
