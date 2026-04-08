"use client";

interface TemplateStats {
  template: string;
  total: number;
  upvotes: number;
  downvotes: number;
}

interface Stats {
  total_generations: number;
  total_simulations: number;
  total_upvotes: number;
  total_downvotes: number;
  total_ratings: number;
  templates: TemplateStats[];
  top_rated_params: Record<string, { params: Record<string, number>; label: string }[]>;
  unmatched_prompts: { prompt: string; template: string }[];
}

interface Props {
  stats: Stats;
}

export default function StatsPanel({ stats }: Props) {
  return (
    <div className="border-b border-[var(--color-border)] bg-[var(--color-bg-alt)] px-6 py-5">
      <div className="max-w-4xl mx-auto">
        <h2 className="text-sm font-semibold text-[var(--color-text)] mb-4">Learning Insights</h2>

        <div className="grid grid-cols-4 gap-4 mb-5">
          <Stat label="Generations" value={stats.total_generations} />
          <Stat label="Simulations" value={stats.total_simulations} />
          <Stat label="Upvotes" value={stats.total_upvotes} color="text-[var(--color-success)]" />
          <Stat label="Downvotes" value={stats.total_downvotes} color="text-[var(--color-error)]" />
        </div>

        {stats.templates.length > 0 && (
          <div className="mb-5">
            <h3 className="text-sm font-medium text-[var(--color-text-muted)] mb-2 uppercase tracking-wider">Template Performance</h3>
            <div className="space-y-2">
              {stats.templates.map((t) => {
                const total = t.upvotes + t.downvotes;
                const pct = total > 0 ? Math.round((t.upvotes / total) * 100) : 0;
                return (
                  <div key={t.template} className="flex items-center gap-3 text-sm">
                    <span className="text-[var(--color-text)] w-28 font-mono">{t.template}</span>
                    <div className="flex-1 bg-[var(--color-border)] rounded-full h-2 overflow-hidden">
                      <div
                        className="bg-[var(--color-primary)] h-full rounded-full transition-all"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                    <span className="text-sm text-[var(--color-text-muted)] w-20 text-right">
                      {t.upvotes}/{total} liked
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {Object.entries(stats.top_rated_params).some(([, v]) => v.length > 0) && (
          <div className="mb-5">
            <h3 className="text-sm font-medium text-[var(--color-text-muted)] mb-2 uppercase tracking-wider">Top-Rated Configs</h3>
            <div className="space-y-1">
              {Object.entries(stats.top_rated_params).map(([template, configs]) =>
                configs.slice(0, 3).map((c, i) => (
                  <div key={`${template}-${i}`} className="text-sm text-[var(--color-text-muted)] font-mono bg-[var(--color-surface)] rounded-[var(--radius-sm)] px-2 py-1">
                    <span className="text-[var(--color-primary)]">{template}</span>
                    {" · "}
                    <span className="text-[var(--color-text)]">{c.label}</span>
                    {" · "}
                    {Object.entries(c.params).map(([k, v]) => `${k}=${typeof v === "number" ? v.toFixed(2) : v}`).join(", ")}
                  </div>
                ))
              )}
            </div>
          </div>
        )}

        {stats.unmatched_prompts.length > 0 && (
          <div>
            <h3 className="text-sm font-medium text-[var(--color-text-muted)] mb-2 uppercase tracking-wider">
              Prompts That Need Better Templates
            </h3>
            <div className="space-y-1">
              {stats.unmatched_prompts.map((p, i) => (
                <div key={i} className="text-sm text-[var(--color-text-muted)]">
                  &quot;{p.prompt}&quot;
                  <span className="text-[var(--color-text-faint)]"> — mapped to {p.template}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {stats.total_ratings === 0 && (
          <p className="text-sm text-[var(--color-text-faint)]">
            No ratings yet. Rate simulations with thumbs up/down to teach the system what you like.
          </p>
        )}
      </div>
    </div>
  );
}

function Stat({ label, value, color = "text-[var(--color-text)]" }: { label: string; value: number; color?: string }) {
  return (
    <div className="bg-[var(--color-surface)] rounded-[var(--radius-md)] px-3 py-2 border border-[var(--color-border)]" style={{ boxShadow: 'var(--shadow-sm)' }}>
      <div className={`text-lg font-semibold ${color}`}>{value}</div>
      <div className="text-sm text-[var(--color-text-muted)]">{label}</div>
    </div>
  );
}
