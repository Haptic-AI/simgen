"use client";

import { useState } from "react";
import PromptInput from "@/components/prompt-input";
import SimulationGrid from "@/components/simulation-grid";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Simulation {
  id: string;
  label: string;
  video_url: string;
  params: Record<string, number>;
}

interface Generation {
  generation_id: string;
  prompt: string;
  simulations: Simulation[];
}

export default function Home() {
  const [generations, setGenerations] = useState<Generation[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (prompt: string) => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_URL}/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || `Server error ${res.status}`);
      }
      const data: Generation = await res.json();
      setGenerations((prev) => [data, ...prev]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen flex flex-col">
      <header className="border-b border-gray-800 px-6 py-4">
        <h1 className="text-xl font-semibold tracking-tight">
          <span className="text-indigo-400">mj</span>sim
        </h1>
        <p className="text-sm text-gray-500 mt-1">prompt to physics simulation</p>
      </header>

      <div className="flex-1 overflow-y-auto px-6 py-8 space-y-8">
        {loading && (
          <div className="flex flex-col items-center justify-center py-20 space-y-4">
            <div className="w-10 h-10 border-2 border-indigo-400 border-t-transparent rounded-full animate-spin" />
            <p className="text-gray-400 text-sm">Simulating physics...</p>
          </div>
        )}

        {error && (
          <div className="max-w-2xl mx-auto bg-red-900/30 border border-red-800 rounded-lg px-4 py-3 text-red-300 text-sm">
            {error}
          </div>
        )}

        {generations.map((gen) => (
          <SimulationGrid key={gen.generation_id} generation={gen} apiUrl={API_URL} />
        ))}

        {!loading && generations.length === 0 && (
          <div className="flex flex-col items-center justify-center py-32 text-gray-600">
            <svg className="w-16 h-16 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
            </svg>
            <p className="text-lg">Describe a physics simulation to get started</p>
            <p className="text-sm mt-2 text-gray-700">e.g. &quot;a pendulum swinging in low gravity&quot;</p>
          </div>
        )}
      </div>

      <div className="border-t border-gray-800 px-6 py-4">
        <PromptInput onSubmit={handleSubmit} loading={loading} />
      </div>
    </main>
  );
}
