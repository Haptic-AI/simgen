"use client";

import { useState } from "react";

interface Props {
  simulationId: string;
  apiUrl: string;
}

export default function FeedbackButtons({ simulationId, apiUrl }: Props) {
  const [rating, setRating] = useState<"up" | "down" | null>(null);

  const handleFeedback = async (value: "up" | "down") => {
    const newRating = rating === value ? null : value;
    setRating(newRating);
    if (newRating) {
      try {
        await fetch(`${apiUrl}/feedback`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ simulation_id: simulationId, rating: newRating }),
        });
      } catch {
        // Silent fail for feedback
      }
    }
  };

  return (
    <div className="flex gap-2">
      <button
        onClick={() => handleFeedback("up")}
        className={`p-1.5 rounded transition-colors ${
          rating === "up"
            ? "bg-green-900/50 text-green-400"
            : "text-gray-600 hover:text-gray-300"
        }`}
        title="Good simulation"
      >
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M14 9V5a3 3 0 00-3-3l-4 9v11h11.28a2 2 0 002-1.7l1.38-9a2 2 0 00-2-2.3H14z" />
          <path strokeLinecap="round" strokeLinejoin="round" d="M7 22H4a2 2 0 01-2-2v-7a2 2 0 012-2h3" />
        </svg>
      </button>
      <button
        onClick={() => handleFeedback("down")}
        className={`p-1.5 rounded transition-colors ${
          rating === "down"
            ? "bg-red-900/50 text-red-400"
            : "text-gray-600 hover:text-gray-300"
        }`}
        title="Bad simulation"
      >
        <svg className="w-4 h-4 rotate-180" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M14 9V5a3 3 0 00-3-3l-4 9v11h11.28a2 2 0 002-1.7l1.38-9a2 2 0 00-2-2.3H14z" />
          <path strokeLinecap="round" strokeLinejoin="round" d="M7 22H4a2 2 0 01-2-2v-7a2 2 0 012-2h3" />
        </svg>
      </button>
    </div>
  );
}
