"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import PromptInput from "@/components/prompt-input";
import SimulationGrid from "@/components/simulation-grid";
import StatsPanel from "@/components/stats-panel";
import EnvironmentSelector from "@/components/environment-selector";
import HistorySidebar from "@/components/history-sidebar";
import ThemeSelector from "@/components/theme-selector";
import GenerationTimer from "@/components/generation-timer";
import StatusWidget from "@/components/status-widget";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "";

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
  const [showPrevious, setShowPrevious] = useState(false);
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

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTo({ top: 0, behavior: "smooth" });
    }
  }, [generations.length]);

  // Poll a job until complete
  const pollJob = async (jobId: string): Promise<Generation> => {
    while (true) {
      await new Promise((r) => setTimeout(r, 2000));
      const res = await fetch(`${API_URL}/job/${jobId}`);
      if (!res.ok) throw new Error(`Poll failed: ${res.status}`);
      const job = await res.json();

      if (job.status === "complete") return job.result;
      if (job.status === "error") throw new Error(job.error || "Generation failed");
      // Update progress label
      if (job.status === "rendering" && job.progress !== undefined) {
        setLoadingLabel(`Rendering video ${job.progress + 1} of ${job.total}...`);
      } else if (job.status === "parsing") {
        setLoadingLabel("Interpreting your prompt...");
      }
    }
  };

  const [loadingLabel, setLoadingLabel] = useState("");

  const handleSubmit = async (prompt: string) => {
    setLoading(true);
    setError(null);
    setLoadingLabel("Submitting...");
    setPromptChain((prev) => [...prev, prompt]);
    try {
      // Submit job — returns immediately
      const res = await fetch(`${API_URL}/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt, environment, theme }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || `Server error ${res.status}`);
      }
      const { job_id } = await res.json();

      // Poll until done
      const data: Generation = await pollJob(job_id);
      data.environment = environment;
      setGenerations((prev) => [data, ...prev]);
      if (!flowMode) setFlowMode(true);
      fetchStats();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
      setLoadingLabel("");
    }
  };

  const handleVary = async (simulationId: string, appendPrompt?: string) => {
    setLoading(true);
    setError(null);
    setLoadingLabel("Submitting...");
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
      const { job_id } = await res.json();

      const data: Generation = await pollJob(job_id);
      data.environment = environment;
      setGenerations((prev) => [data, ...prev]);
      fetchStats();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
      setLoadingLabel("");
    }
  };

  const handleFlowSelect = async (simulationId: string) => {
    try {
      await fetch(`${API_URL}/feedback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ simulation_id: simulationId, rating: "up" }),
      });
    } catch {}
    fetchStats();
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
    <StatusWidget apiUrl={API_URL} />
    <main className="min-h-screen flex flex-col">
      {/* Header — Material-inspired clean header */}
      <header className="border-b border-white/[0.06] px-8 py-5 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button
            onClick={() => setHistoryOpen(true)}
            className="p-2 text-gray-500 hover:text-gray-300 transition-colors rounded-lg hover:bg-white/[0.04]"
            title="Prompt history"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </button>
          <div>
            <h1 className="text-2xl font-light tracking-tight">
              <span className="font-semibold text-blue-400">Sim</span>
              <span className="text-gray-300">Gen</span>
            </h1>
            <p className="text-xs text-gray-500 mt-0.5 tracking-wide">prompt-to-physics simulation</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {stats && stats.total_ratings > 0 && (
            <div className="text-xs text-gray-500 bg-white/[0.03] border border-white/[0.06] rounded-full px-3 py-1.5">
              Learning from{" "}
              <span className="text-blue-400 font-medium">{stats.total_ratings}</span> ratings
            </div>
          )}
          {flowMode && (
            <button
              onClick={() => setFlowMode(false)}
              className="text-xs px-3 py-1.5 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20 transition-colors hover:bg-blue-500/20"
            >
              Flow Mode
            </button>
          )}
          <button
            onClick={() => setShowStats(!showStats)}
            className="text-xs text-gray-500 hover:text-gray-300 transition-colors px-3 py-1.5 rounded-lg hover:bg-white/[0.04]"
          >
            {showStats ? "Hide insights" : "Insights"}
          </button>
        </div>
      </header>

      {showStats && stats && <StatsPanel stats={stats} />}

      {/* Journey breadcrumb */}
      {promptChain.length > 0 && (
        <div className="border-b border-white/[0.04] px-8 py-2 flex items-center gap-2 overflow-x-auto">
          <span className="text-xs text-gray-600 shrink-0 uppercase tracking-wider">Journey</span>
          {promptChain.map((p, i) => (
            <span key={i} className="text-xs shrink-0">
              {i > 0 && <span className="text-gray-700 mx-1">&rarr;</span>}
              <span className={i === promptChain.length - 1 ? "text-blue-400" : "text-gray-500"}>
                {p.length > 30 ? p.slice(0, 30) + "..." : p}
              </span>
            </span>
          ))}
          {promptChain.length > 1 && (
            <button
              onClick={handleUndo}
              disabled={loading}
              className="text-xs text-gray-600 hover:text-red-400 transition-colors shrink-0 ml-2 disabled:opacity-30"
            >
              Undo
            </button>
          )}
        </div>
      )}

      <div ref={scrollRef} className="flex-1 overflow-y-auto px-8 py-8 space-y-8">
        {/* Loading state with timer */}
        {loading && (
          <div className="flex flex-col items-center justify-center py-16 space-y-6">
            <div className="relative">
              <div className="w-12 h-12 border-2 border-blue-500/30 border-t-blue-400 rounded-full animate-spin" />
            </div>
            <GenerationTimer
              running={loading}
              label={loadingLabel || (generations.length > 0 ? "Generating next round..." : "Creating 4 simulations...")}
            />
          </div>
        )}

        {error && (
          <div className="max-w-2xl mx-auto bg-red-500/5 border border-red-500/20 rounded-xl px-4 py-3 text-red-300 text-xs">
            {error}
          </div>
        )}

        {/* Latest generation */}
        {generations.length > 0 && (
          <div>
            {generations[0].description && (
              <p className="max-w-4xl mx-auto text-xs text-gray-500 mb-2 italic leading-relaxed">
                {generations[0].description}
              </p>
            )}
            {flowMode && !loading && (
              <p className="max-w-4xl mx-auto text-xs text-blue-400/60 mb-3">
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

        {/* Previous generations — collapsed */}
        {generations.length > 1 && (
          <div className="max-w-4xl mx-auto">
            <button
              onClick={() => setShowPrevious(!showPrevious)}
              className="text-xs text-gray-600 uppercase tracking-widest font-medium hover:text-gray-400 transition-colors flex items-center gap-2"
            >
              <svg className={`w-3 h-3 transition-transform ${showPrevious ? "rotate-90" : ""}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
              </svg>
              Previous rounds ({generations.length - 1})
            </button>
            {showPrevious && (
              <div className="space-y-6 mt-4 opacity-40">
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
          </div>
        )}

        {/* Empty state */}
        {!loading && generations.length === 0 && (
          <div className="flex flex-col items-center justify-center py-32 text-gray-600">
            <div className="w-16 h-16 mb-6 rounded-2xl bg-white/[0.03] border border-white/[0.06] flex items-center justify-center">
              <svg className="w-7 h-7 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
              </svg>
            </div>
            <p className="text-base font-light text-gray-400">Describe what you want to see</p>
            <p className="text-xs mt-3 text-gray-600 max-w-sm text-center leading-relaxed">
              &quot;a figure standing on a cliff edge&quot; &middot; &quot;a ball bouncing down stairs&quot; &middot; &quot;a pendulum in slow motion&quot;
            </p>
          </div>
        )}
      </div>

      {/* Bottom bar — Material-style input area */}
      <div className="border-t border-white/[0.06] px-8 py-4 space-y-3 bg-[#0f1115]/80 backdrop-blur">
        {/* Environment and theme selectors — hidden for now
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
        */}
        <PromptInput
          onSubmit={flowMode && generations.length > 0
            ? (prompt) => {
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
