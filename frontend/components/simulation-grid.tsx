"use client";

import { useState, useRef } from "react";
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
      <p className="text-sm text-gray-400 mb-4">
        <span className="text-gray-500">Prompt:</span> {generation.prompt}
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
          <p className="text-sm text-red-400/70">Rejected — the system will avoid this pattern</p>
        </div>
      ) : (
        <div className="mt-3 flex items-center justify-center gap-3">
          {!showRejectInput ? (
            <div className="relative flex items-center gap-1.5 group/info">
              <button
                onClick={() => setShowRejectInput(true)}
                className="text-sm text-gray-600 hover:text-red-400 transition-colors px-3 py-1.5 rounded border border-transparent hover:border-red-900/50"
              >
                None of these worked
              </button>
              <div className="relative">
                <svg className="w-3.5 h-3.5 text-gray-700 hover:text-gray-400 cursor-help transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-64 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-300 opacity-0 invisible group-hover/info:opacity-100 group-hover/info:visible transition-all shadow-lg z-10">
                  <p className="font-medium text-gray-200 mb-1">What happens when you reject:</p>
                  <ul className="space-y-0.5 text-gray-400">
                    <li>1. All 4 simulations are marked as failures</li>
                    <li>2. You can tell us what went wrong</li>
                    <li>3. The system immediately retries with your feedback</li>
                    <li>4. Future prompts will avoid similar results</li>
                  </ul>
                  <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-gray-800"></div>
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
                className="flex-1 bg-gray-900 border border-red-900/50 rounded px-3 py-1.5 text-sm text-gray-300 placeholder-gray-600 focus:outline-none focus:border-red-500"
                onKeyDown={(e) => e.key === "Enter" && handleReject()}
                autoFocus
              />
              <button
                onClick={handleReject}
                className="text-sm bg-red-900/30 text-red-400 hover:bg-red-900/50 px-3 py-1.5 rounded transition-colors"
              >
                Reject all
              </button>
              <button
                onClick={() => setShowRejectInput(false)}
                className="text-sm text-gray-600 hover:text-gray-400 px-2 py-1.5"
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
