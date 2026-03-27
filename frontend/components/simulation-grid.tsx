"use client";

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
}

export default function SimulationGrid({ generation, apiUrl }: Props) {
  return (
    <div className="max-w-4xl mx-auto">
      <p className="text-sm text-gray-400 mb-4">
        <span className="text-gray-600">Prompt:</span> {generation.prompt}
      </p>
      <div className="grid grid-cols-2 gap-4">
        {generation.simulations.map((sim) => (
          <SimulationCard key={sim.id} simulation={sim} apiUrl={apiUrl} />
        ))}
      </div>
    </div>
  );
}
