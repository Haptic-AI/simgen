"use client";

interface Theme {
  label: string;
  description: string;
}

interface Props {
  themes: Record<string, Theme>;
  selected: string;
  onSelect: (theme: string) => void;
}

const COLORS: Record<string, string> = {
  studio: "bg-[var(--color-text-muted)]",
  outdoor: "bg-[var(--color-success)]",
  industrial: "bg-[var(--color-text-faint)]",
  desert: "bg-[var(--color-warning)]",
  night: "bg-[var(--color-accent)]",
  snow: "bg-[var(--color-bg-alt)]",
};

export default function ThemeSelector({ themes, selected, onSelect }: Props) {
  return (
    <div className="flex gap-2 flex-wrap">
      {Object.entries(themes).map(([key, theme]) => (
        <button
          key={key}
          onClick={() => onSelect(key)}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium transition-all ${
            selected === key
              ? "bg-[var(--color-primary)] text-[var(--color-primary-text)]"
              : "bg-[var(--color-surface)] text-[var(--color-text-muted)] border border-[var(--color-border)] hover:border-[var(--color-border-strong)] hover:text-[var(--color-text)]"
          }`}
          title={theme.description}
        >
          <span className={`w-2.5 h-2.5 rounded-full ${COLORS[key] || "bg-[var(--color-text-faint)]"}`} />
          {theme.label}
        </button>
      ))}
    </div>
  );
}
