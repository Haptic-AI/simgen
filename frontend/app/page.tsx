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
const BLOG_URL = "https://www.hapticlabs.ai/blog/2026/04/06/from-cloud-gpus-to-creative-canvas?ref=https://simgen.hapticlabs.ai";
const GITHUB_URL = "https://github.com/Haptic-AI/simgen?ref=https://simgen.hapticlabs.ai";

const SHOWCASE_PROMPTS = [
  { prompt: "a pendulum swinging in slow motion", template: "pendulum" },
  { prompt: "a ball bouncing down stairs", template: "bouncing_ball" },
  { prompt: "a robot arm reaching for a target", template: "robot_arm" },
  { prompt: "a pole balancing on a cart", template: "cartpole" },
  { prompt: "a humanoid figure stumbling forward", template: "humanoid" },
  { prompt: "a chaotic double pendulum", template: "double_pendulum" },
  { prompt: "a tower of blocks collapsing", template: "falling_stack" },
  { prompt: "a ragdoll tumbling off a ledge", template: "ragdoll" },
  { prompt: "a spinning top wobbling on a table", template: "spinning_top" },
];

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

  const pollJob = async (jobId: string): Promise<Generation> => {
    while (true) {
      await new Promise((r) => setTimeout(r, 2000));
      const res = await fetch(`${API_URL}/job/${jobId}`);
      if (!res.ok) throw new Error(`Poll failed: ${res.status}`);
      const job = await res.json();

      if (job.status === "complete") return job.result;
      if (job.status === "error") throw new Error(job.error || "Generation failed");
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
      {/* Header */}
      <header className="border-b border-[var(--color-border)] px-8 py-5 flex items-center justify-between bg-[var(--color-surface)]" style={{ backdropFilter: 'blur(12px)' }}>
        <div className="flex items-center gap-4">
          <button
            onClick={() => setHistoryOpen(true)}
            className="p-2 text-[var(--color-text-muted)] hover:text-[var(--color-text)] transition-colors rounded-lg hover:bg-[var(--color-primary-light)]"
            title="Prompt history"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </button>
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-[var(--color-text)]">
              <span className="text-[var(--color-primary)]">Sim</span>
              <span className="text-[var(--color-accent)]">Gen</span>
            </h1>
            <p className="text-sm font-medium text-[var(--color-text-muted)] mt-0.5 tracking-wide">prompt-to-physics simulation</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {stats && stats.total_ratings > 0 && (
            <div className="text-xs text-[var(--color-text-muted)] bg-[var(--color-primary-light)] border border-[var(--color-border)] rounded-full px-3 py-1.5">
              Learning from{" "}
              <span className="text-[var(--color-primary)] font-medium">{stats.total_ratings}</span> ratings
            </div>
          )}
          {flowMode && (
            <button
              onClick={() => setFlowMode(false)}
              className="text-xs px-3 py-1.5 rounded-full bg-[var(--color-primary-light)] text-[var(--color-primary)] border border-[var(--color-primary)]/20 transition-colors hover:bg-[var(--color-primary)]/10"
            >
              Flow Mode
            </button>
          )}
          <a
            href={BLOG_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm font-medium text-[var(--color-text-muted)] hover:text-[var(--color-primary)] transition-colors px-3 py-1.5 rounded-lg hover:bg-[var(--color-primary-light)]"
          >
            Blog
          </a>
          <a
            href={GITHUB_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm font-medium text-[var(--color-text-muted)] hover:text-[var(--color-primary)] transition-colors px-3 py-1.5 rounded-lg hover:bg-[var(--color-primary-light)]"
          >
            GitHub
          </a>
          <button
            onClick={() => setShowStats(!showStats)}
            className="text-sm font-medium text-[var(--color-text-muted)] hover:text-[var(--color-text)] transition-colors px-3 py-1.5 rounded-lg hover:bg-[var(--color-primary-light)]"
          >
            {showStats ? "Hide insights" : "Insights"}
          </button>
        </div>
      </header>

      {showStats && stats && <StatsPanel stats={stats} />}

      {/* Journey breadcrumb */}
      {promptChain.length > 0 && (
        <div className="border-b border-[var(--color-border)] px-8 py-2 flex items-center gap-2 overflow-x-auto bg-[var(--color-bg-alt)]">
          <span className="text-sm text-[var(--color-text-faint)] shrink-0 uppercase tracking-wider font-semibold">Journey</span>
          {promptChain.map((p, i) => (
            <span key={i} className="text-sm shrink-0">
              {i > 0 && <span className="text-[var(--color-text-faint)] mx-1">&rarr;</span>}
              <span className={i === promptChain.length - 1 ? "text-[var(--color-primary)] font-medium" : "text-[var(--color-text-muted)]"}>
                {p.length > 30 ? p.slice(0, 30) + "..." : p}
              </span>
            </span>
          ))}
          {promptChain.length > 1 && (
            <button
              onClick={handleUndo}
              disabled={loading}
              className="text-xs text-[var(--color-text-faint)] hover:text-[var(--color-error)] transition-colors shrink-0 ml-2 disabled:opacity-30"
            >
              Undo
            </button>
          )}
        </div>
      )}

      <div ref={scrollRef} className="flex-1 overflow-y-auto px-8 py-8 space-y-8">
        {/* Loading state */}
        {loading && (
          <div className="flex flex-col items-center justify-center py-16 space-y-6">
            <div className="relative">
              <div className="w-12 h-12 border-2 border-[var(--color-primary)]/30 border-t-[var(--color-primary)] rounded-full animate-spin" />
            </div>
            <GenerationTimer
              running={loading}
              label={loadingLabel || (generations.length > 0 ? "Generating next round..." : "Creating 4 simulations...")}
            />
          </div>
        )}

        {error && (
          <div className="max-w-2xl mx-auto bg-[var(--color-error-light)] border border-[var(--color-error)]/20 rounded-[var(--radius-lg)] px-4 py-3 text-[var(--color-error)] text-xs">
            {error}
          </div>
        )}

        {/* Latest generation */}
        {generations.length > 0 && (
          <div>
            {generations[0].description && (
              <p className="max-w-4xl mx-auto text-xs text-[var(--color-text-muted)] mb-2 italic leading-relaxed">
                {generations[0].description}
              </p>
            )}
            {flowMode && !loading && (
              <p className="max-w-4xl mx-auto text-xs text-[var(--color-primary)]/60 mb-3">
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

        {/* Previous generations */}
        {generations.length > 1 && (
          <div className="max-w-4xl mx-auto">
            <button
              onClick={() => setShowPrevious(!showPrevious)}
              className="text-xs text-[var(--color-text-faint)] uppercase tracking-widest font-medium hover:text-[var(--color-text-muted)] transition-colors flex items-center gap-2"
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

        {/* Empty state — showcase all 9 templates */}
        {!loading && generations.length === 0 && (
          <div className="flex flex-col items-center justify-center py-16 text-[var(--color-text-muted)]">
            <div className="w-16 h-16 mb-6 rounded-2xl bg-[var(--color-surface)] border border-[var(--color-border)] flex items-center justify-center" style={{ boxShadow: 'var(--shadow-sm)' }}>
              <svg className="w-7 h-7 text-[var(--color-text-faint)]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
              </svg>
            </div>
            <p className="text-lg font-semibold text-[var(--color-text)]">Describe what you want to see</p>
            <p className="text-sm mt-2 text-[var(--color-text-muted)] max-w-md text-center leading-relaxed">
              Type a prompt below, or click any example to simulate instantly
            </p>

            <div className="grid grid-cols-3 gap-3 mt-8 max-w-2xl w-full">
              {SHOWCASE_PROMPTS.map((item) => (
                <button
                  key={item.template}
                  onClick={() => handleSubmit(item.prompt)}
                  className="text-left bg-[var(--color-surface)] border border-[var(--color-border)] rounded-[var(--radius-md)] px-4 py-3 hover:border-[var(--color-primary)] hover:bg-[var(--color-primary-light)] transition-all group"
                  style={{ boxShadow: 'var(--shadow-sm)' }}
                >
                  <p className="text-sm font-semibold text-[var(--color-text)] group-hover:text-[var(--color-primary)] transition-colors leading-snug">
                    {item.prompt}
                  </p>
                  <p className="text-xs text-[var(--color-text-faint)] mt-1.5 font-mono">{item.template}</p>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Bottom bar */}
      <div className="border-t border-[var(--color-border)] px-8 py-4 space-y-3 bg-[var(--color-surface)]" style={{ backdropFilter: 'blur(12px)' }}>
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
        <div className="max-w-2xl mx-auto flex items-center justify-center gap-3 text-xs text-[var(--color-text-faint)]">
          <span>Built by</span>
          <a href="https://www.hapticlabs.ai?ref=https://simgen.hapticlabs.ai" target="_blank" rel="noopener noreferrer" className="font-semibold text-[var(--color-text-muted)] hover:text-[var(--color-primary)] transition-colors">
            Haptic Labs
          </a>
          <span>&middot;</span>
          <a href={BLOG_URL} target="_blank" rel="noopener noreferrer" className="hover:text-[var(--color-primary)] transition-colors">
            Blog
          </a>
          <span>&middot;</span>
          <a href={GITHUB_URL} target="_blank" rel="noopener noreferrer" className="hover:text-[var(--color-primary)] transition-colors">
            GitHub
          </a>
        </div>
      </div>
    </main>
    </>
  );
}
