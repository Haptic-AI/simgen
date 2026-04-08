"use client";

import { useState, useEffect, useRef } from "react";

interface Props {
  running: boolean;
  label?: string;
}

export default function GenerationTimer({ running, label }: Props) {
  const [elapsed, setElapsed] = useState(0);
  const startRef = useRef<number | null>(null);
  const frameRef = useRef<number | null>(null);

  useEffect(() => {
    if (running) {
      startRef.current = Date.now();
      setElapsed(0);
      const tick = () => {
        if (startRef.current) {
          setElapsed(Date.now() - startRef.current);
        }
        frameRef.current = requestAnimationFrame(tick);
      };
      frameRef.current = requestAnimationFrame(tick);
    } else {
      if (frameRef.current) cancelAnimationFrame(frameRef.current);
    }
    return () => {
      if (frameRef.current) cancelAnimationFrame(frameRef.current);
    };
  }, [running]);

  const secs = Math.floor(elapsed / 1000);
  const ms = Math.floor((elapsed % 1000) / 10);
  const mins = Math.floor(secs / 60);
  const displaySecs = secs % 60;

  return (
    <div className="flex flex-col items-center gap-2">
      <div className="flex items-center gap-3">
        {running && (
          <div className="w-2 h-2 rounded-full bg-[var(--color-primary)] animate-pulse" />
        )}
        <span className="font-mono text-2xl tabular-nums tracking-tight text-[var(--color-text)]">
          {mins > 0 && <>{mins}<span className="text-[var(--color-text-faint)]">m </span></>}
          {displaySecs.toString().padStart(2, "0")}
          <span className="text-[var(--color-text-faint)]">.</span>
          <span className="text-[var(--color-text-muted)] text-lg">{ms.toString().padStart(2, "0")}</span>
          <span className="text-[var(--color-text-faint)] text-sm ml-1">s</span>
        </span>
      </div>
      <p className="text-xs text-[var(--color-text-muted)]">
        {running
          ? label || "Generating 4 simulations..."
          : elapsed > 0
            ? `Completed in ${mins > 0 ? `${mins}m ` : ""}${displaySecs}s`
            : ""}
      </p>
    </div>
  );
}
