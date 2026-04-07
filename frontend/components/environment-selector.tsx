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

const EMOJI: Record<string, string> = {
  earth: "",
  moon: "",
  mars: "",
  mercury: "",
  jupiter: "",
  zero_g: "",
};

export default function EnvironmentSelector({ environments, selected, onSelect }: Props) {
  return (
    <div className="flex gap-2 flex-wrap">
      {Object.entries(environments).map(([key, env]) => (
        <button
          key={key}
          onClick={() => onSelect(key)}
          className={`px-3 py-1.5 rounded-full text-sm font-medium transition-all ${
            selected === key
              ? "bg-indigo-600 text-white"
              : "bg-gray-900 text-gray-400 border border-gray-800 hover:border-gray-600 hover:text-gray-200"
          }`}
          title={env.description}
        >
          {env.label}
          {selected === key && (
            <span className="ml-1.5 text-indigo-200 font-normal">{env.gravity} m/s²</span>
          )}
        </button>
      ))}
    </div>
  );
}
