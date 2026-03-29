"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import PromptInput from "@/components/prompt-input";
import SimulationGrid from "@/components/simulation-grid";
import StatsPanel from "@/components/stats-panel";
import EnvironmentSelector from "@/components/environment-selector";
import HistorySidebar from "@/components/history-sidebar";
import ThemeSelector from "@/components/theme-selector";

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
  description?: string;
  simulations: Simulation[];
  environment?: string;
}

interface Stats {
  total_generations: number;
  total_simulations: number;
  total_upvotes: number;
  total_downvotes: number;
  total_ratings: number;
  templates: { template: string; total: number; upvotes: number; downvotes: number }[];
  top_rated_params: Record<string, { params: Record<string, number>; label: string }[]>;
  unmatched_prompts: { prompt: string; template: string }[];
}

interface Environment {
  label: string;
  description: string;
  gravity: number;
}

export default function Home() {
  const [generations, setGenerations] = useState<Generation[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [stats, setStats] = useState<Stats | null>(null);
  const [showStats, setShowStats] = useState(false);
  const [environment, setEnvironment] = useState("earth");
  const [environments, setEnvironments] = useState<Record<string, Environment>>({});
  const [theme, setTheme] = useState("studio");
  const [themes, setThemes] = useState<Record<string, { label: string; description: string }>>({});
  const [flowMode, setFlowMode] = useState(false);
  const [promptChain, setPromptChain] = useState<string[]>([]);
  const [historyOpen, setHistoryOpen] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/stats`);
      if (res.ok) setStats(await res.json());
    } catch {}
  }, []);

  useEffect(() => {
    fetchStats();
    fetch(`${API_URL}/environments`)
      .then((r) => r.json())
      .then(setEnvironments)
      .catch(() => {});
    fetch(`${API_URL}/themes`)
      .then((r) => r.json())
      .then(setThemes)
      .catch(() => {});
  }, [fetchStats]);

  // Scroll to top when new generation arrives
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTo({ top: 0, behavior: "smooth" });
    }
  }, [generations.length]);

  const handleSubmit = async (prompt: string) => {
    setLoading(true);
    setError(null);
    setPromptChain((prev) => [...prev, prompt]);
    try {
      const res = await fetch(`${API_URL}/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt, environment, theme }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || `Server error ${res.status}`);
      }
      const data: Generation = await res.json();
      data.environment = environment;
      setGenerations((prev) => [data, ...prev]);
      if (!flowMode) setFlowMode(true);
      fetchStats();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  };

  const handleVary = async (simulationId: string, appendPrompt?: string) => {
    setLoading(true);
    setError(null);
    if (appendPrompt) {
      setPromptChain((prev) => [...prev, appendPrompt]);
    }
    try {
      const res = await fetch(`${API_URL}/vary`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          simulation_id: simulationId,
          prompt: appendPrompt || "",
          environment,
        }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || `Server error ${res.status}`);
      }
      const data: Generation = await res.json();
      data.environment = environment;
      setGenerations((prev) => [data, ...prev]);
      fetchStats();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  };

  // Flow mode: thumbs up auto-triggers vary on that simulation
  const handleFlowSelect = async (simulationId: string) => {
    // First, record the upvote
    try {
      await fetch(`${API_URL}/feedback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ simulation_id: simulationId, rating: "up" }),
      });
    } catch {}
    fetchStats();
    // Then auto-vary
    await handleVary(simulationId);
  };

  const handleRejectAll = async (generationId: string, reason: string) => {
    try {
      await fetch(`${API_URL}/reject-all`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ generation_id: generationId, reason }),
      });
      fetchStats();
    } catch {}

    // Find the original prompt and auto-retry with lessons learned
    const gen = generations.find((g) => g.generation_id === generationId);
    if (gen) {
      const retryPrompt = reason
        ? `${gen.prompt} (previous attempt failed: ${reason})`
        : gen.prompt;
      await handleSubmit(retryPrompt);
    }
  };

  const handleUndo = () => {
    if (generations.length > 1) {
      setGenerations((prev) => prev.slice(1));
      setPromptChain((prev) => prev.slice(0, -1));
    }
  };

  const handleFeedbackGiven = () => {
    fetchStats();
  };

  const handleSelectPrompt = (prompt: string) => {
    handleSubmit(prompt);
  };

  return (
    <>
    <HistorySidebar
      apiUrl={API_URL}
      open={historyOpen}
      onClose={() => setHistoryOpen(false)}
      onSelectPrompt={handleSelectPrompt}
      refreshKey={generations.length}
    />
    <main className="min-h-screen flex flex-col">
      <header className="border-b border-gray-800 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button
            onClick={() => setHistoryOpen(true)}
            className="p-2 text-gray-500 hover:text-gray-300 transition-colors rounded-lg hover:bg-gray-900"
            title="Prompt history"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </button>
          <div>
            <h1 className="text-xl font-semibold tracking-tight">
              <span className="text-indigo-400">sim</span>gen
            </h1>
            <p className="text-sm text-gray-500 mt-1">describe a scene, get a simulation</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {stats && stats.total_ratings > 0 && (
            <div className="text-sm text-gray-500 bg-gray-900 border border-gray-800 rounded-full px-3 py-1.5">
              Learning from{" "}
              <span className="text-indigo-400 font-medium">{stats.total_ratings}</span> ratings
            </div>
          )}
          {flowMode && (
            <button
              onClick={() => setFlowMode(false)}
              className={`text-sm px-3 py-1.5 rounded-full transition-colors ${
                flowMode
                  ? "bg-indigo-600 text-white"
                  : "bg-gray-900 text-gray-400 border border-gray-800"
              }`}
            >
              Flow Mode
            </button>
          )}
          <button
            onClick={() => setShowStats(!showStats)}
            className="text-sm text-gray-500 hover:text-gray-300 transition-colors"
          >
            {showStats ? "Hide insights" : "Insights"}
          </button>
        </div>
      </header>

      {showStats && stats && <StatsPanel stats={stats} />}

      {/* Prompt chain breadcrumb */}
      {promptChain.length > 0 && (
        <div className="border-b border-gray-800/50 px-6 py-2 flex items-center gap-2 overflow-x-auto">
          <span className="text-sm text-gray-600 shrink-0">Journey:</span>
          {promptChain.map((p, i) => (
            <span key={i} className="text-sm shrink-0">
              {i > 0 && <span className="text-gray-700 mx-1">&rarr;</span>}
              <span className={i === promptChain.length - 1 ? "text-indigo-400" : "text-gray-500"}>
                {p.length > 30 ? p.slice(0, 30) + "..." : p}
              </span>
            </span>
          ))}
          {promptChain.length > 1 && (
            <button
              onClick={handleUndo}
              disabled={loading}
              className="text-sm text-gray-600 hover:text-red-400 transition-colors shrink-0 ml-2 disabled:opacity-30"
            >
              Undo
            </button>
          )}
        </div>
      )}

      <div ref={scrollRef} className="flex-1 overflow-y-auto px-6 py-8 space-y-8">
        {loading && (
          <div className="flex flex-col items-center justify-center py-20 space-y-4">
            <div className="w-10 h-10 border-2 border-indigo-400 border-t-transparent rounded-full animate-spin" />
            <p className="text-gray-400 text-sm">
              {generations.length > 0 ? "Generating next round..." : "Creating your simulation..."}
              {stats && stats.total_ratings > 0 && (
                <span className="block text-gray-600 mt-1">
                  Tuned by {stats.total_ratings} past ratings
                </span>
              )}
            </p>
          </div>
        )}

        {error && (
          <div className="max-w-2xl mx-auto bg-red-900/30 border border-red-800 rounded-lg px-4 py-3 text-red-300 text-sm">
            {error}
          </div>
        )}

        {/* Latest generation — show prominently in flow mode */}
        {generations.length > 0 && (
          <div>
            {generations[0].description && (
              <p className="max-w-4xl mx-auto text-sm text-gray-600 mb-1 italic">
                {generations[0].description}
              </p>
            )}
            {flowMode && !loading && (
              <p className="max-w-4xl mx-auto text-sm text-indigo-400/70 mb-3">
                Pick your favorite — it auto-generates 4 more variations
              </p>
            )}
            <SimulationGrid
              generation={generations[0]}
              apiUrl={API_URL}
              onFeedback={handleFeedbackGiven}
              onVary={flowMode ? handleFlowSelect : (id) => handleVary(id)}
              onRejectAll={handleRejectAll}
              flowMode={flowMode}
            />
          </div>
        )}

        {/* Previous generations — collapsed in flow mode */}
        {generations.length > 1 && (
          <div className="space-y-6 opacity-50">
            <p className="max-w-4xl mx-auto text-sm text-gray-600 uppercase tracking-wider">
              Previous rounds ({generations.length - 1})
            </p>
            {generations.slice(1).map((gen) => (
              <div key={gen.generation_id}>
                <SimulationGrid
                  generation={gen}
                  apiUrl={API_URL}
                  onFeedback={handleFeedbackGiven}
                  onVary={(id) => handleVary(id)}
                  onRejectAll={handleRejectAll}
                />
              </div>
            ))}
          </div>
        )}

        {!loading && generations.length === 0 && (
          <div className="flex flex-col items-center justify-center py-28 text-gray-600">
            <svg className="w-14 h-14 mb-5 text-gray-700" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
            </svg>
            <p className="text-lg text-gray-400">Describe what you want to see</p>
            <p className="text-sm mt-2 text-gray-700 max-w-md text-center">
              &quot;a figure standing on a cliff edge&quot; &middot; &quot;a ball bouncing down stairs&quot; &middot; &quot;a pendulum in slow motion&quot;
            </p>
            {stats && stats.total_ratings > 0 && (
              <p className="text-sm mt-6 text-indigo-400/50">
                {stats.total_ratings} ratings collected &middot; system is learning your style
              </p>
            )}
          </div>
        )}
      </div>

      <div className="border-t border-gray-800 px-6 py-4 space-y-3">
        <div className="max-w-2xl mx-auto space-y-2">
          {Object.keys(environments).length > 0 && (
            <EnvironmentSelector
              environments={environments}
              selected={environment}
              onSelect={setEnvironment}
            />
          )}
          {Object.keys(themes).length > 0 && (
            <ThemeSelector
              themes={themes}
              selected={theme}
              onSelect={setTheme}
            />
          )}
        </div>
        <PromptInput
          onSubmit={flowMode && generations.length > 0
            ? (prompt) => {
                // In flow mode, append prompt refines the latest generation
                const latestSims = generations[0]?.simulations;
                if (latestSims?.length > 0) {
                  handleVary(latestSims[0].id, prompt);
                } else {
                  handleSubmit(prompt);
                }
              }
            : handleSubmit
          }
          loading={loading}
          placeholder={flowMode && generations.length > 0
            ? "Add direction (e.g. 'make it slower', 'more dramatic')..."
            : "Describe a scene..."
          }
        />
      </div>
    </main>
    </>
  );
}
