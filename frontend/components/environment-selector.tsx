"use client";

interface Environment {
  label: string;
  description: string;
  gravity: number;
}

interface Props {
  environments: Record<string, Environment>;
  selected: string;
  onSelect: (env: string) => void;
}

export default function EnvironmentSelector({ environments, selected, onSelect }: Props) {
  return (
    <div className="flex gap-2 flex-wrap">
      {Object.entries(environments).map(([key, env]) => (
        <button
          key={key}
          onClick={() => onSelect(key)}
          className={`px-3 py-1.5 rounded-full text-sm font-medium transition-all ${
            selected === key
              ? "bg-[var(--color-primary)] text-[var(--color-primary-text)]"
              : "bg-[var(--color-surface)] text-[var(--color-text-muted)] border border-[var(--color-border)] hover:border-[var(--color-border-strong)] hover:text-[var(--color-text)]"
          }`}
          title={env.description}
        >
          {env.label}
          {selected === key && (
            <span className="ml-1.5 text-[var(--color-primary-text)]/70 font-normal">{env.gravity} m/s²</span>
          )}
        </button>
      ))}
    </div>
  );
}
