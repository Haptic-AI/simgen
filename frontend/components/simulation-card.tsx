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
      className={`bg-gray-900 border rounded-lg overflow-hidden group transition-all ${
        flowMode
          ? "border-gray-800 hover:border-indigo-500 cursor-pointer hover:shadow-lg hover:shadow-indigo-500/10"
          : "border-gray-800"
      }`}
      onClick={flowMode && onVary ? () => onVary(simulation.id) : undefined}
    >
      <div className="relative aspect-video bg-black">
        <video
          src={videoSrc}
          controls={!flowMode}
          loop
          muted
          autoPlay
          playsInline
          className="w-full h-full object-contain"
        />
        <div className="absolute top-2 left-2 bg-black/70 text-sm text-gray-300 px-2 py-1 rounded">
          {simulation.label}
        </div>
        {flowMode && (
          <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity bg-black/30">
            <div className="bg-indigo-600 text-white text-sm font-medium px-4 py-2 rounded-lg shadow-lg">
              Pick this one
            </div>
          </div>
        )}
        {!flowMode && onVary && (
          <button
            onClick={(e) => { e.stopPropagation(); onVary(simulation.id); }}
            className="absolute top-2 right-2 bg-indigo-600/80 hover:bg-indigo-500 text-white text-sm px-2.5 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity"
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
              className="text-sm text-gray-500 hover:text-gray-300 transition-colors"
            >
              {showParams ? "Hide details" : "Technical details"}
            </button>
          </div>

          {showParams && (
            <div className="px-3 pb-3">
              <div className="bg-gray-950 rounded p-2 text-sm text-gray-400 font-mono space-y-0.5">
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
