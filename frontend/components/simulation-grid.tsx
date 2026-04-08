"use client";

import { useState } from "react";
import SimulationCard from "./simulation-card";

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

interface Props {
  generation: Generation;
  apiUrl: string;
  onFeedback?: () => void;
  onVary?: (simulationId: string) => void;
  onRejectAll?: (generationId: string, reason: string) => void;
  flowMode?: boolean;
}

export default function SimulationGrid({ generation, apiUrl, onFeedback, onVary, onRejectAll, flowMode }: Props) {
  const [rejected, setRejected] = useState(false);
  const [showRejectInput, setShowRejectInput] = useState(false);
  const [rejectReason, setRejectReason] = useState("");

  const handleReject = () => {
    if (onRejectAll) {
      onRejectAll(generation.generation_id, rejectReason);
      setRejected(true);
      setShowRejectInput(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto">
      <p className="text-sm text-[var(--color-text-muted)] mb-4">
        <span className="text-[var(--color-text-faint)]">Prompt:</span> {generation.prompt}
      </p>
      <div className={`grid grid-cols-2 gap-4 ${rejected ? "opacity-30" : ""}`}>
        {generation.simulations.map((sim) => (
          <SimulationCard
            key={sim.id}
            simulation={sim}
            apiUrl={apiUrl}
            onFeedback={onFeedback}
            onVary={onVary}
            flowMode={flowMode && !rejected}
          />
        ))}
      </div>

      {rejected ? (
        <div className="mt-3 text-center">
          <p className="text-sm text-[var(--color-error)]/70">Rejected — the system will avoid this pattern</p>
        </div>
      ) : (
        <div className="mt-3 flex items-center justify-center gap-3">
          {!showRejectInput ? (
            <div className="relative flex items-center gap-1.5 group/info">
              <button
                onClick={() => setShowRejectInput(true)}
                className="text-sm text-[var(--color-text-faint)] hover:text-[var(--color-error)] transition-colors px-3 py-1.5 rounded-[var(--radius-sm)] border border-transparent hover:border-[var(--color-error)]/20"
              >
                None of these worked
              </button>
              <div className="relative">
                <svg className="w-3.5 h-3.5 text-[var(--color-text-faint)] hover:text-[var(--color-text-muted)] cursor-help transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-64 bg-[var(--color-surface)] border border-[var(--color-border)] rounded-[var(--radius-md)] px-3 py-2 text-sm text-[var(--color-text-muted)] opacity-0 invisible group-hover/info:opacity-100 group-hover/info:visible transition-all z-10" style={{ boxShadow: 'var(--shadow-lg)' }}>
                  <p className="font-medium text-[var(--color-text)] mb-1">What happens when you reject:</p>
                  <ul className="space-y-0.5 text-[var(--color-text-muted)]">
                    <li>1. All 4 simulations are marked as failures</li>
                    <li>2. You can tell us what went wrong</li>
                    <li>3. The system immediately retries with your feedback</li>
                    <li>4. Future prompts will avoid similar results</li>
                  </ul>
                  <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-[var(--color-surface)]"></div>
                </div>
              </div>
            </div>
          ) : (
            <div className="flex items-center gap-2 max-w-lg w-full">
              <input
                type="text"
                value={rejectReason}
                onChange={(e) => setRejectReason(e.target.value)}
                placeholder="What went wrong? (optional)"
                className="flex-1 bg-[var(--color-surface)] border border-[var(--color-error)]/30 rounded-[var(--radius-sm)] px-3 py-1.5 text-sm text-[var(--color-text)] placeholder-[var(--color-text-faint)] focus:outline-none focus:border-[var(--color-error)]"
                onKeyDown={(e) => e.key === "Enter" && handleReject()}
                autoFocus
              />
              <button
                onClick={handleReject}
                className="text-sm bg-[var(--color-error-light)] text-[var(--color-error)] hover:bg-[var(--color-error)]/15 px-3 py-1.5 rounded-[var(--radius-sm)] transition-colors"
              >
                Reject all
              </button>
              <button
                onClick={() => setShowRejectInput(false)}
                className="text-sm text-[var(--color-text-faint)] hover:text-[var(--color-text-muted)] px-2 py-1.5"
              >
                Cancel
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
