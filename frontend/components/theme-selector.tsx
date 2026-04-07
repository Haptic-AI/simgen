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
  studio: "bg-gray-700",
  outdoor: "bg-green-700",
  industrial: "bg-zinc-600",
  desert: "bg-amber-700",
  night: "bg-slate-900",
  snow: "bg-slate-200",
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
              ? "bg-indigo-600 text-white"
              : "bg-gray-900 text-gray-400 border border-gray-800 hover:border-gray-600 hover:text-gray-200"
          }`}
          title={theme.description}
        >
          <span className={`w-2.5 h-2.5 rounded-full ${COLORS[key] || "bg-gray-500"}`} />
          {theme.label}
        </button>
      ))}
    </div>
  );
}
