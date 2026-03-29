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
    <div className="border-b border-gray-800 bg-gray-900/50 px-6 py-5">
      <div className="max-w-4xl mx-auto">
        <h2 className="text-sm font-semibold text-gray-300 mb-4">Learning Insights</h2>

        <div className="grid grid-cols-4 gap-4 mb-5">
          <Stat label="Generations" value={stats.total_generations} />
          <Stat label="Simulations" value={stats.total_simulations} />
          <Stat label="Upvotes" value={stats.total_upvotes} color="text-green-400" />
          <Stat label="Downvotes" value={stats.total_downvotes} color="text-red-400" />
        </div>

        {stats.templates.length > 0 && (
          <div className="mb-5">
            <h3 className="text-sm font-medium text-gray-500 mb-2 uppercase tracking-wider">Template Performance</h3>
            <div className="space-y-2">
              {stats.templates.map((t) => {
                const total = t.upvotes + t.downvotes;
                const pct = total > 0 ? Math.round((t.upvotes / total) * 100) : 0;
                return (
                  <div key={t.template} className="flex items-center gap-3 text-sm">
                    <span className="text-gray-300 w-28 font-mono">{t.template}</span>
                    <div className="flex-1 bg-gray-800 rounded-full h-2 overflow-hidden">
                      <div
                        className="bg-indigo-500 h-full rounded-full transition-all"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                    <span className="text-sm text-gray-500 w-20 text-right">
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
            <h3 className="text-sm font-medium text-gray-500 mb-2 uppercase tracking-wider">Top-Rated Configs</h3>
            <div className="space-y-1">
              {Object.entries(stats.top_rated_params).map(([template, configs]) =>
                configs.slice(0, 3).map((c, i) => (
                  <div key={`${template}-${i}`} className="text-sm text-gray-400 font-mono bg-gray-950 rounded px-2 py-1">
                    <span className="text-indigo-400">{template}</span>
                    {" · "}
                    <span className="text-gray-300">{c.label}</span>
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
            <h3 className="text-sm font-medium text-gray-500 mb-2 uppercase tracking-wider">
              Prompts That Need Better Templates
            </h3>
            <div className="space-y-1">
              {stats.unmatched_prompts.map((p, i) => (
                <div key={i} className="text-sm text-gray-500">
                  &quot;{p.prompt}&quot;
                  <span className="text-gray-700"> — mapped to {p.template}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {stats.total_ratings === 0 && (
          <p className="text-sm text-gray-600">
            No ratings yet. Rate simulations with thumbs up/down to teach the system what you like.
          </p>
        )}
      </div>
    </div>
  );
}

function Stat({ label, value, color = "text-gray-100" }: { label: string; value: number; color?: string }) {
  return (
    <div className="bg-gray-950 rounded-lg px-3 py-2">
      <div className={`text-lg font-semibold ${color}`}>{value}</div>
      <div className="text-sm text-gray-500">{label}</div>
    </div>
  );
}
