"use client";

import { useState } from "react";
import FeedbackButtons from "./feedback-buttons";

interface Simulation {
  id: string;
  label: string;
  video_url: string;
  params: Record<string, number>;
}

interface Props {
  simulation: Simulation;
  apiUrl: string;
  onFeedback?: () => void;
  onVary?: (simulationId: string) => void;
  flowMode?: boolean;
}

export default function SimulationCard({ simulation, apiUrl, onFeedback, onVary, flowMode }: Props) {
  const [showParams, setShowParams] = useState(false);
  const videoSrc = `${apiUrl}${simulation.video_url}`;

  return (
    <div
      className={`bg-[var(--color-surface)] border rounded-[var(--radius-lg)] overflow-hidden group transition-all ${
        flowMode
          ? "border-[var(--color-border)] hover:border-[var(--color-primary)] cursor-pointer"
          : "border-[var(--color-border)]"
      }`}
      style={{ boxShadow: flowMode ? undefined : 'var(--shadow-sm)' }}
      onClick={flowMode && onVary ? () => onVary(simulation.id) : undefined}
    >
      <div className="relative aspect-video bg-[var(--color-accent)]">
        <video
          src={videoSrc}
          controls={!flowMode}
          loop
          muted
          autoPlay
          playsInline
          className="w-full h-full object-contain"
        />
        <div className="absolute top-2 left-2 bg-[var(--color-accent)]/80 text-sm text-white px-2 py-1 rounded-[var(--radius-sm)]">
          {simulation.label}
        </div>
        {flowMode && (
          <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity bg-[var(--color-accent)]/30">
            <div className="bg-[var(--color-primary)] text-[var(--color-primary-text)] text-sm font-medium px-4 py-2 rounded-[var(--radius-md)]" style={{ boxShadow: 'var(--shadow-md)' }}>
              Pick this one
            </div>
          </div>
        )}
        {!flowMode && onVary && (
          <button
            onClick={(e) => { e.stopPropagation(); onVary(simulation.id); }}
            className="absolute top-2 right-2 bg-[var(--color-primary)]/80 hover:bg-[var(--color-primary)] text-[var(--color-primary-text)] text-sm px-2.5 py-1 rounded-[var(--radius-sm)] opacity-0 group-hover:opacity-100 transition-opacity"
          >
            Iterate on this
          </button>
        )}
      </div>

      {!flowMode && (
        <>
          <div className="px-3 py-2 flex items-center justify-between">
            <FeedbackButtons simulationId={simulation.id} apiUrl={apiUrl} onFeedback={onFeedback} />
            <button
              onClick={() => setShowParams(!showParams)}
              className="text-sm text-[var(--color-text-muted)] hover:text-[var(--color-text)] transition-colors"
            >
              {showParams ? "Hide details" : "Technical details"}
            </button>
          </div>

          {showParams && (
            <div className="px-3 pb-3">
              <div className="bg-[var(--color-bg-alt)] rounded-[var(--radius-sm)] p-2 text-sm text-[var(--color-text-muted)] font-mono space-y-0.5">
                {Object.entries(simulation.params).map(([key, val]) => (
                  <div key={key}>
                    {key}: {typeof val === "number" ? val.toFixed(3) : String(val)}
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
