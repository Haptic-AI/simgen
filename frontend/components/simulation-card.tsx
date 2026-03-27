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
}

export default function SimulationCard({ simulation, apiUrl }: Props) {
  const [showParams, setShowParams] = useState(false);
  const videoSrc = `${apiUrl}${simulation.video_url}`;

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-lg overflow-hidden group">
      <div className="relative aspect-video bg-black">
        <video
          src={videoSrc}
          controls
          loop
          muted
          autoPlay
          playsInline
          className="w-full h-full object-contain"
        />
        <div className="absolute top-2 left-2 bg-black/70 text-xs text-gray-300 px-2 py-1 rounded">
          {simulation.label}
        </div>
      </div>

      <div className="px-3 py-2 flex items-center justify-between">
        <FeedbackButtons simulationId={simulation.id} apiUrl={apiUrl} />
        <button
          onClick={() => setShowParams(!showParams)}
          className="text-xs text-gray-500 hover:text-gray-300 transition-colors"
        >
          {showParams ? "Hide params" : "Show params"}
        </button>
      </div>

      {showParams && (
        <div className="px-3 pb-3">
          <div className="bg-gray-950 rounded p-2 text-xs text-gray-400 font-mono space-y-0.5">
            {Object.entries(simulation.params).map(([key, val]) => (
              <div key={key}>
                {key}: {typeof val === "number" ? val.toFixed(3) : String(val)}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
