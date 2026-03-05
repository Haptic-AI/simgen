import { useState, useEffect, useRef } from "react";

const TARGET_SCORE = 0.85;

const MOCK_ITERATIONS = [
  { iteration: 1, score: 0.23, promoted: true, mode: "incremental", elapsed_seconds: 87,
    breakdown: { ssim: 0.18, color: 0.31, brightness: 0.45, motion: 0.12, duration: 0.80 },
    gaps: ["CRITICAL: Low SSIM - geometry mismatch", "HIGH: Color histogram wrong - walls too neutral", "HIGH: Motion too fast"]
  },
  { iteration: 2, score: 0.34, promoted: true, mode: "incremental", elapsed_seconds: 91,
    breakdown: { ssim: 0.28, color: 0.44, brightness: 0.52, motion: 0.24, duration: 0.85 },
    gaps: ["HIGH: Upper walls too bright", "HIGH: Floor color too light", "MEDIUM: Missing shelving"]
  },
  { iteration: 3, score: 0.41, promoted: true, mode: "incremental", elapsed_seconds: 95,
    breakdown: { ssim: 0.35, color: 0.56, brightness: 0.61, motion: 0.32, duration: 0.90 },
    gaps: ["HIGH: Ceiling height wrong - too low", "MEDIUM: Lighting too flat", "MEDIUM: Camera too high"]
  },
  { iteration: 4, score: 0.39, promoted: false, mode: "incremental", elapsed_seconds: 88,
    breakdown: { ssim: 0.31, color: 0.50, brightness: 0.58, motion: 0.29, duration: 0.88 },
    gaps: ["HIGH: Over-corrected ceiling - now too tall", "HIGH: Ambient too dark", "MEDIUM: Props missing"]
  },
  { iteration: 5, score: 0.47, promoted: true, mode: "radical_rethink", elapsed_seconds: 102,
    breakdown: { ssim: 0.42, color: 0.62, brightness: 0.68, motion: 0.38, duration: 0.92 },
    gaps: ["MEDIUM: Wall color bands need fine-tuning", "MEDIUM: Shelving geometry incomplete", "LOW: Shadow softness"]
  },
];

const SCORE_COLORS = {
  excellent: "#00ff88",
  good: "#88ff44",
  mediocre: "#ffcc00",
  poor: "#ff6622",
  critical: "#ff2244"
};

function scoreColor(s) {
  if (s >= 0.85) return SCORE_COLORS.excellent;
  if (s >= 0.65) return SCORE_COLORS.good;
  if (s >= 0.45) return SCORE_COLORS.mediocre;
  if (s >= 0.25) return SCORE_COLORS.poor;
  return SCORE_COLORS.critical;
}

function ScoreBar({ label, value, weight }) {
  return (
    <div style={{ marginBottom: 6 }}>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11,
                    color: "#aaa", marginBottom: 2 }}>
        <span>{label} <span style={{ color: "#555" }}>×{weight}</span></span>
        <span style={{ color: scoreColor(value) }}>{(value*100).toFixed(1)}%</span>
      </div>
      <div style={{ height: 6, background: "#1a1a1a", borderRadius: 3, overflow: "hidden" }}>
        <div style={{
          height: "100%", width: `${value*100}%`,
          background: `linear-gradient(90deg, ${scoreColor(value)}88, ${scoreColor(value)})`,
          borderRadius: 3, transition: "width 0.6s ease"
        }} />
      </div>
    </div>
  );
}

function IterationCard({ iter, isBest, isActive }) {
  const [expanded, setExpanded] = useState(false);
  const bd = iter.breakdown || {};

  return (
    <div onClick={() => setExpanded(!expanded)} style={{
      background: isActive ? "#0d1f0d" : isBest ? "#0d1a0d" : "#0e0e0f",
      border: `1px solid ${isActive ? "#00ff88" : isBest ? "#336633" : "#1e1e22"}`,
      borderRadius: 8, padding: "10px 14px", marginBottom: 8, cursor: "pointer",
      transition: "all 0.2s",
      boxShadow: isActive ? "0 0 12px #00ff8844" : isBest ? "0 0 6px #33663322" : "none"
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        {/* Iter number */}
        <div style={{
          width: 36, height: 36, borderRadius: "50%",
          background: isActive ? "#00ff8822" : "#111",
          border: `2px solid ${isActive ? "#00ff88" : scoreColor(iter.score)}`,
          display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: 13, fontWeight: 700, color: isActive ? "#00ff88" : scoreColor(iter.score),
          flexShrink: 0
        }}>
          {iter.iteration}
        </div>

        {/* Score bar */}
        <div style={{ flex: 1 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center",
                        marginBottom: 4 }}>
            <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
              <span style={{ fontSize: 12, color: "#666",
                fontFamily: "monospace",
                background: iter.mode === "radical_rethink" ? "#330a00" : "#111",
                color: iter.mode === "radical_rethink" ? "#ff6622" : "#555",
                padding: "1px 6px", borderRadius: 3 }}>
                {iter.mode === "radical_rethink" ? "⚡ RETHINK" : "→ INCR"}
              </span>
              {iter.promoted && (
                <span style={{ fontSize: 10, color: "#00ff88", background: "#00ff8822",
                               padding: "1px 6px", borderRadius: 3 }}>✓ PROMOTED</span>
              )}
            </div>
            <span style={{ fontSize: 11, color: "#555" }}>{iter.elapsed_seconds}s</span>
          </div>
          <div style={{ height: 8, background: "#111", borderRadius: 4, overflow: "hidden" }}>
            <div style={{
              height: "100%", width: `${iter.score*100}%`,
              background: `linear-gradient(90deg, ${scoreColor(iter.score)}66, ${scoreColor(iter.score)})`,
              borderRadius: 4, transition: "width 0.8s ease"
            }} />
          </div>
        </div>

        {/* Score number */}
        <div style={{ fontSize: 20, fontWeight: 800, color: scoreColor(iter.score),
                      fontFamily: "monospace", minWidth: 52, textAlign: "right" }}>
          {(iter.score*100).toFixed(1)}
        </div>
      </div>

      {/* Expanded detail */}
      {expanded && (
        <div style={{ marginTop: 12, paddingTop: 12, borderTop: "1px solid #1a1a1a" }}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <div>
              <div style={{ fontSize: 10, color: "#444", marginBottom: 6, textTransform: "uppercase",
                            letterSpacing: 1 }}>Score Breakdown</div>
              <ScoreBar label="SSIM" value={bd.ssim||0} weight="0.25" />
              <ScoreBar label="Color" value={bd.color||0} weight="0.22" />
              <ScoreBar label="Brightness" value={bd.brightness||0} weight="0.18" />
              <ScoreBar label="Motion" value={bd.motion||0} weight="0.20" />
              <ScoreBar label="Duration" value={bd.duration||0} weight="0.15" />
            </div>
            <div>
              <div style={{ fontSize: 10, color: "#444", marginBottom: 6, textTransform: "uppercase",
                            letterSpacing: 1 }}>Top Gaps</div>
              {(iter.gaps||[]).map((g, i) => (
                <div key={i} style={{
                  fontSize: 10, color: g.startsWith("CRITICAL") ? "#ff2244" :
                                       g.startsWith("HIGH") ? "#ff6622" :
                                       g.startsWith("MEDIUM") ? "#ffcc00" : "#aaa",
                  marginBottom: 5, lineHeight: 1.4
                }}>
                  {g.substring(0, 90)}{g.length > 90 ? "..." : ""}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function SparkLine({ data, width = 200, height = 40 }) {
  if (!data.length) return null;
  const max = Math.max(...data, TARGET_SCORE);
  const pts = data.map((v, i) => {
    const x = (i / Math.max(data.length-1, 1)) * width;
    const y = height - (v / max) * height;
    return `${x},${y}`;
  }).join(" ");
  const targetY = height - (TARGET_SCORE / max) * height;

  return (
    <svg width={width} height={height} style={{ overflow: "visible" }}>
      <line x1={0} y1={targetY} x2={width} y2={targetY}
            stroke="#00ff8844" strokeWidth={1} strokeDasharray="4,4" />
      <polyline points={pts} fill="none" stroke="#00ff88" strokeWidth={2}
                strokeLinejoin="round" strokeLinecap="round" />
      {data.map((v, i) => (
        <circle key={i}
          cx={(i / Math.max(data.length-1, 1)) * width}
          cy={height - (v / max) * height}
          r={3} fill={scoreColor(v)} />
      ))}
    </svg>
  );
}

export default function SimDashboard() {
  const [iterations, setIterations] = useState(MOCK_ITERATIONS);
  const [isRunning, setIsRunning] = useState(false);
  const [activeIter, setActiveIter] = useState(null);
  const [phase, setPhase] = useState("idle"); // idle | simulating | scoring | refining
  const timerRef = useRef(null);

  const bestIter = iterations.reduce((b, i) => i.score > (b?.score||0) ? i : b, null);
  const scores = iterations.map(i => i.score);
  const lastScore = scores[scores.length-1] || 0;
  const trend = scores.length > 1 ? lastScore - scores[scores.length-2] : 0;

  // Simulate live progress
  const startLoop = () => {
    if (isRunning) return;
    setIsRunning(true);
    const nextIter = iterations.length + 1;
    setActiveIter(nextIter);

    const phases = ["simulating", "scoring", "refining"];
    let pi = 0;
    setPhase(phases[0]);

    timerRef.current = setInterval(() => {
      pi++;
      if (pi < phases.length) {
        setPhase(phases[pi]);
      } else {
        // Add synthetic iteration
        const prevBest = Math.max(...scores);
        const newScore = Math.min(prevBest + Math.random() * 0.12 - 0.02, 0.99);
        const promoted = newScore > prevBest;
        setIterations(prev => [...prev, {
          iteration: nextIter,
          score: Math.round(newScore * 10000) / 10000,
          promoted,
          mode: prev.length >= 7 && newScore < 0.6 ? "radical_rethink" : "incremental",
          elapsed_seconds: 85 + Math.floor(Math.random() * 30),
          breakdown: {
            ssim: Math.min(newScore + (Math.random()-0.5)*0.1, 1),
            color: Math.min(newScore + (Math.random()-0.5)*0.1, 1),
            brightness: Math.min(newScore + (Math.random()-0.5)*0.15, 1),
            motion: Math.min(newScore + (Math.random()-0.5)*0.1, 1),
            duration: Math.min(0.85 + Math.random()*0.1, 1)
          },
          gaps: promoted ? ["LOW: Fine-tune shadow softness", "LOW: Slight vignette adjustment"] :
                           ["HIGH: Color still slightly off", "MEDIUM: Motion profile variance"]
        }]);
        setIsRunning(false);
        setActiveIter(null);
        setPhase("idle");
        clearInterval(timerRef.current);
      }
    }, 2500);
  };

  useEffect(() => () => clearInterval(timerRef.current), []);

  const phaseLabel = {
    idle: "READY",
    simulating: "⚙ RUNNING SIM",
    scoring: "📊 SCORING",
    refining: "🧠 LLM REFINE"
  };

  return (
    <div style={{
      background: "#080809", minHeight: "100vh", color: "#ccc",
      fontFamily: "'JetBrains Mono', 'Fira Mono', 'Courier New', monospace",
      padding: 24
    }}>
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <div style={{ display: "flex", alignItems: "baseline", gap: 14, marginBottom: 4 }}>
          <h1 style={{ margin: 0, fontSize: 22, fontWeight: 800, color: "#fff",
                       letterSpacing: "-0.5px" }}>
            HELIOS<span style={{ color: "#00ff88" }}>_</span>SIM
          </h1>
          <span style={{ fontSize: 11, color: "#444", textTransform: "uppercase",
                         letterSpacing: 2 }}>Self-Learning Loop</span>
          <div style={{
            marginLeft: "auto", fontSize: 11, padding: "3px 10px", borderRadius: 4,
            background: isRunning ? "#0d2010" : "#111",
            border: `1px solid ${isRunning ? "#00ff88" : "#222"}`,
            color: isRunning ? "#00ff88" : "#555"
          }}>
            {isRunning ? (
              <span>● {phaseLabel[phase]}</span>
            ) : lastScore >= TARGET_SCORE ? (
              <span style={{ color: "#00ff88" }}>🎯 TARGET ACHIEVED</span>
            ) : (
              <span>{phaseLabel["idle"]}</span>
            )}
          </div>
        </div>
        <div style={{ height: 1, background: "linear-gradient(90deg, #00ff8833, transparent)" }} />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1fr", gap: 12, marginBottom: 20 }}>
        {/* Best score */}
        <div style={{ background: "#0d1f0d", border: "1px solid #1a3a1a",
                      borderRadius: 8, padding: 16 }}>
          <div style={{ fontSize: 10, color: "#444", textTransform: "uppercase",
                        letterSpacing: 1, marginBottom: 4 }}>Best Score</div>
          <div style={{ fontSize: 32, fontWeight: 800, color: scoreColor(bestIter?.score||0),
                        lineHeight: 1 }}>
            {((bestIter?.score||0)*100).toFixed(1)}
            <span style={{ fontSize: 14, color: "#555" }}>%</span>
          </div>
          <div style={{ fontSize: 10, color: "#555", marginTop: 4 }}>
            iter {bestIter?.iteration||0} / target {TARGET_SCORE*100}%
          </div>
          <div style={{ marginTop: 8, height: 4, background: "#111", borderRadius: 2 }}>
            <div style={{
              height: "100%", width: `${(bestIter?.score||0)/TARGET_SCORE*100}%`,
              maxWidth: "100%",
              background: "linear-gradient(90deg, #00ff8844, #00ff88)",
              borderRadius: 2
            }} />
          </div>
        </div>

        {/* Iterations */}
        <div style={{ background: "#0f0f12", border: "1px solid #1e1e22",
                      borderRadius: 8, padding: 16 }}>
          <div style={{ fontSize: 10, color: "#444", textTransform: "uppercase",
                        letterSpacing: 1, marginBottom: 4 }}>Iterations</div>
          <div style={{ fontSize: 32, fontWeight: 800, color: "#fff", lineHeight: 1 }}>
            {iterations.length}
            <span style={{ fontSize: 14, color: "#555" }}>/{20}</span>
          </div>
          <div style={{ fontSize: 10, color: "#555", marginTop: 4 }}>
            {iterations.filter(i=>i.promoted).length} promoted
          </div>
        </div>

        {/* Trend */}
        <div style={{ background: "#0f0f12", border: "1px solid #1e1e22",
                      borderRadius: 8, padding: 16 }}>
          <div style={{ fontSize: 10, color: "#444", textTransform: "uppercase",
                        letterSpacing: 1, marginBottom: 4 }}>Score Trend</div>
          <div style={{ marginTop: 4 }}>
            <SparkLine data={scores} width={140} height={40} />
          </div>
          <div style={{ fontSize: 10, color: trend >= 0 ? "#00ff88" : "#ff4444",
                        marginTop: 2 }}>
            {trend >= 0 ? "↗" : "↘"} {trend >= 0 ? "+" : ""}{(trend*100).toFixed(1)}% last iter
          </div>
        </div>

        {/* LLM status */}
        <div style={{ background: "#0f0f12", border: "1px solid #1e1e22",
                      borderRadius: 8, padding: 16 }}>
          <div style={{ fontSize: 10, color: "#444", textTransform: "uppercase",
                        letterSpacing: 1, marginBottom: 4 }}>LLM Refiner</div>
          <div style={{ fontSize: 12, color: "#888", marginBottom: 2 }}>Qwen2.5-Coder-14B</div>
          <div style={{ fontSize: 10, color: "#555" }}>localhost:8000</div>
          <div style={{ marginTop: 8, display: "flex", gap: 4 }}>
            {["incr","incr","incr","incr","rethink"].map((m,i) => (
              <div key={i} style={{
                width: 20, height: 20, borderRadius: 3,
                background: m === "rethink" ? "#ff662233" : "#00ff8822",
                border: `1px solid ${m === "rethink" ? "#ff6622" : "#00ff8844"}`,
                fontSize: 8, display: "flex", alignItems: "center", justifyContent: "center",
                color: m === "rethink" ? "#ff6622" : "#00ff88"
              }}>
                {m === "rethink" ? "⚡" : "→"}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Main content */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 320px", gap: 16 }}>

        {/* Iteration list */}
        <div>
          <div style={{ fontSize: 10, color: "#444", textTransform: "uppercase",
                        letterSpacing: 1, marginBottom: 10 }}>
            Iteration History — click to expand
          </div>
          {[...iterations].reverse().map(iter => (
            <IterationCard
              key={iter.iteration}
              iter={iter}
              isBest={iter.iteration === bestIter?.iteration}
              isActive={iter.iteration === activeIter}
            />
          ))}

          {isRunning && (
            <div style={{
              background: "#0d1f0d", border: "1px solid #00ff88",
              borderRadius: 8, padding: "10px 14px", marginBottom: 8,
              animation: "pulse 1.5s ease-in-out infinite"
            }}>
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <div style={{
                  width: 36, height: 36, borderRadius: "50%",
                  border: "2px solid #00ff88",
                  display: "flex", alignItems: "center", justifyContent: "center",
                  fontSize: 13, fontWeight: 700, color: "#00ff88"
                }}>
                  {iterations.length + 1}
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 11, color: "#00ff88", marginBottom: 6 }}>
                    {phaseLabel[phase]}
                  </div>
                  <div style={{ height: 6, background: "#111", borderRadius: 3, overflow: "hidden" }}>
                    <div style={{
                      height: "100%", width: "60%",
                      background: "linear-gradient(90deg, #00ff8844, #00ff88)",
                      borderRadius: 3,
                      animation: "loading 1.2s ease-in-out infinite"
                    }} />
                  </div>
                </div>
                <div style={{ fontSize: 20, fontWeight: 800, color: "#333",
                              fontFamily: "monospace" }}>
                  ???
                </div>
              </div>
            </div>
          )}

          <style>{`
            @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.7} }
            @keyframes loading {
              0%{transform:translateX(-100%)} 100%{transform:translateX(200%)}
            }
          `}</style>
        </div>

        {/* Right panel */}
        <div>
          {/* Control */}
          <div style={{ background: "#0f0f12", border: "1px solid #1e1e22",
                        borderRadius: 8, padding: 16, marginBottom: 12 }}>
            <div style={{ fontSize: 10, color: "#444", textTransform: "uppercase",
                          letterSpacing: 1, marginBottom: 12 }}>Loop Control</div>

            <button
              onClick={startLoop}
              disabled={isRunning || lastScore >= TARGET_SCORE}
              style={{
                width: "100%", padding: "10px 0",
                background: isRunning ? "#0a1a0a" : lastScore >= TARGET_SCORE ? "#0a1a0a" : "#00ff8822",
                border: `1px solid ${isRunning ? "#334" : lastScore >= TARGET_SCORE ? "#1a3a1a" : "#00ff88"}`,
                borderRadius: 6, color: isRunning ? "#555" : lastScore >= TARGET_SCORE ? "#00ff88" : "#00ff88",
                fontSize: 13, fontWeight: 700, cursor: isRunning ? "not-allowed" : "pointer",
                transition: "all 0.2s"
              }}
            >
              {lastScore >= TARGET_SCORE ? "🎯 TARGET ACHIEVED" :
               isRunning ? "◌ Running..." : "▶ Run Next Iteration"}
            </button>

            <div style={{ marginTop: 10, display: "grid", gridTemplateColumns: "1fr 1fr",
                          gap: 6 }}>
              <button style={{
                padding: "6px 0", background: "#111", border: "1px solid #222",
                borderRadius: 5, color: "#666", fontSize: 10, cursor: "pointer"
              }}>
                ⚡ Force Rethink
              </button>
              <button style={{
                padding: "6px 0", background: "#111", border: "1px solid #222",
                borderRadius: 5, color: "#666", fontSize: 10, cursor: "pointer"
              }}>
                📤 Publish Best
              </button>
            </div>
          </div>

          {/* Best prompt preview */}
          <div style={{ background: "#0f0f12", border: "1px solid #1e1e22",
                        borderRadius: 8, padding: 16, marginBottom: 12 }}>
            <div style={{ fontSize: 10, color: "#444", textTransform: "uppercase",
                          letterSpacing: 1, marginBottom: 8 }}>Best Prompt Preview</div>
            <div style={{
              fontSize: 9.5, color: "#667", lineHeight: 1.6,
              maxHeight: 180, overflow: "hidden",
              maskImage: "linear-gradient(180deg, #fff 60%, transparent)"
            }}>
              Helios patrol robot conducts a slow 180-degree surveillance sweep inside a large 
              industrial warehouse. Camera at 0.48m height, FOV 95°. Scene: 30×20×8m warehouse. 
              Dark corrugated ceiling rgba(0.22,0.23,0.25). 8 fluorescent fixtures, cool white 
              diffuse 1.8 intensity, castshadow=true. Upper walls rust-brown rgba(0.32,0.15,0.06), 
              mid amber-yellow rgba(0.88,0.56,0.04), lower white brick...
            </div>
          </div>

          {/* Reference stats */}
          <div style={{ background: "#0f0f12", border: "1px solid #1e1e22",
                        borderRadius: 8, padding: 16 }}>
            <div style={{ fontSize: 10, color: "#444", textTransform: "uppercase",
                          letterSpacing: 1, marginBottom: 10 }}>Reference Video</div>
            {[
              ["Duration", "33s @ 30fps"],
              ["Resolution", "1280×720"],
              ["Camera height", "0.48m AGL"],
              ["Yaw rate", "5.5°/sec"],
              ["Scene", "30×20×8m"],
              ["Lighting", "8× fluorescent"],
              ["Brightness", "0.44 (norm)"],
            ].map(([k,v]) => (
              <div key={k} style={{ display: "flex", justifyContent: "space-between",
                                    fontSize: 10, marginBottom: 5,
                                    borderBottom: "1px solid #111", paddingBottom: 4 }}>
                <span style={{ color: "#555" }}>{k}</span>
                <span style={{ color: "#888" }}>{v}</span>
              </div>
            ))}
            <div style={{ marginTop: 8, fontSize: 10, color: "#444",
                          textAlign: "center" }}>
              ─── TARGET ── {TARGET_SCORE*100}% match ───
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
