# HELIOS WAREHOUSE SIM — END-TO-END WORKFLOW
## Self-Learning MuJoCo Simulation Pipeline

---

## WHAT WAS BUILT

```
Reference Video (helios_demo.mp4)
        ↓ analyzed → ground truth spec
BASELINE_PROMPT (warehouse interior, camera params, lighting)
        ↓
┌─────────────────────────────────────────────────────────┐
│              SELF-LEARNING LOOP (sim_loop.py)           │
│                                                         │
│  prompt_to_video.py → score_video() → diagnose_gaps()  │
│           ↑                                    ↓       │
│    rule_based_refine()          Qwen2.5-14B LLM        │
│           ↑────────────────────────────────────        │
│                                                         │
│  Loop until score ≥ 0.85 OR iteration ≥ 20             │
└─────────────────────────────────────────────────────────┘
        ↓ winner
  publish to Ziggeo (1920×1080 @ 60fps, 300s)
```

---

## QUICK START (3 commands)

```bash
# 1. Start the LLM server (already done per your setup)
bash 00_setup/start_llm.sh

# 2. Run the self-learning loop
cd ~/  # wherever prompt_to_video.py lives
python3 sim_loop.py

# 3. Monitor progress
tail -f /mnt/sim_outputs/loop_log.jsonl | python3 -c "
import sys, json
for line in sys.stdin:
    r = json.loads(line)
    print(f'Iter {r[\"iteration\"]:02d} | Score: {r[\"score\"]:.4f} | Promoted: {r[\"promoted\"]}')
"
```

---

## FILE MAP

```
sim_loop.py                  ← MAIN LOOP — run this
mcp_tools/mcp_server.py      ← MCP server (Claude Code / Claude Desktop)
claude_mcp_config.json       ← Wire MCP into Claude Desktop
SimDashboard.jsx             ← React UI for monitoring
CLAUDE_AGENT_PROMPT.md       ← Full Claude agent instructions
/mnt/sim_outputs/            ← Generated videos land here
/mnt/sim_outputs/loop_log.jsonl ← Iteration history
/mnt/sim_outputs/WINNING_PROMPT.txt ← Auto-saved when target hit
```

---

## HOW THE LOOP WORKS

### Scoring (5 dimensions)
| Dimension | Weight | Method |
|---|---|---|
| SSIM | 25% | Structural similarity, 6 frame pairs |
| Color histogram | 22% | HSV histogram cosine similarity |
| Brightness | 18% | Mean luminance match |
| Motion profile | 20% | Inter-frame difference curve |
| Duration | 15% | Duration match to 33s |

### Refinement Strategy
- **Iterations 1–4:** Incremental — fix top 3 gaps via LLM
- **Plateau (3 iter no improvement):** Radical rethink — full prompt rewrite
- **Iteration 10+ with score < 0.65:** Force radical rethink
- **LLM unavailable:** Rule-based gap→fix table (runs offline)

### Escalation Ladder
```
Score < 0.30  → Check sim pipeline, simplify prompt
Score 0.30–0.50 → Fix geometry & color first
Score 0.50–0.65 → Fix lighting & motion
Score 0.65–0.85 → Fine-tune props, shadows, texture
Score ≥ 0.85  → 🎯 PUBLISH to Ziggeo 1080p60 300s
```

---

## REFERENCE VIDEO GROUND TRUTH

From frame analysis of helios_demo.mp4:

- **Warehouse:** 30×20×8m, industrial interior
- **Ceiling:** Dark corrugated metal + exposed black I-beams
- **Walls (3 bands):**
  - Upper: dark rust-brown `rgba(0.32, 0.15, 0.06)`
  - Mid: bright amber-yellow `rgba(0.88, 0.56, 0.04)`
  - Lower: white brick wainscoting `rgba(0.92, 0.92, 0.90)`
- **Floor:** Dark grey concrete `rgba(0.24, 0.26, 0.28)` with tile grid
- **Lighting:** 8 fluorescent ceiling fixtures, cool white, soft shadows
- **Camera:** First-person POV, 0.48m AGL, 95° FOV
- **Motion:** 5.5°/sec rightward yaw, 180° over 33 seconds
- **Props:** Orange shelving (right wall), pallets, boxes, foam rolls on floor

---

## MCP INTEGRATION (Claude Code / Claude Desktop)

Add to `~/.claude/mcp_config.json`:
```json
{
  "mcpServers": {
    "helios-sim": {
      "command": "python3",
      "args": ["/path/to/mcp_tools/mcp_server.py"]
    }
  }
}
```

Then Claude has access to:
- `mcp__analyze_video` — score any video vs reference
- `mcp__refine_prompt` — call Qwen LLM for prompt improvement
- `mcp__run_simulation` — execute prompt_to_video.py
- `mcp__publish_to_ziggeo` — publish winner
- `mcp__update_loop_log` — log iteration records

---

## CLAUDE AGENT INVOCATION

To have Claude run the loop autonomously, use the prompt in `CLAUDE_AGENT_PROMPT.md`.

Key instruction to give Claude:
> "You are SimDirector. Run the Helios warehouse simulation self-learning loop.
> Start with the baseline prompt, use mcp__run_simulation to generate videos,
> mcp__analyze_video to score them, mcp__refine_prompt to improve the prompt,
> and repeat until score ≥ 0.85. Then publish the winner to Ziggeo at 1080p60."

---

## RESUME AFTER INTERRUPTION

```bash
python3 sim_loop.py --resume
# Picks up from highest-scoring logged prompt
```

---

*Pipeline v1.0 — Built for Helios / SimReady Warehouse Project*
