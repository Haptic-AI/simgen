# 2026-03-27 — SimGen Bake-Off: main vs alt/vercel

## What we have

Two complete implementations of the same product — prompt-to-MuJoCo physics simulation — built with different architectures. Both live in the same repo at [Haptic-AI/simgen](https://github.com/Haptic-AI/simgen).

### Branch: `main` (Claude version)

| Layer | Technology | Notes |
|-------|-----------|-------|
| Frontend | Next.js + Tailwind (hand-built) | Minimal dark UI, 4 components |
| AI | Claude API (Sonnet, tool-use) | Structured JSON via tool-use |
| Rendering | MuJoCo CPU + imageio/ffmpeg | Runs locally, no GPU needed |
| Backend | FastAPI (Python) | Single process, sync endpoints |
| Deployment | Local only | `uvicorn` + `npm run dev` |
| Templates | 5 XML files with `{{placeholder}}` substitution | pendulum, bouncing_ball, robot_arm, cartpole, humanoid |

**Strengths:** Simple, self-contained, runs on any Mac/Linux box. No cloud dependency beyond the Anthropic API key. All 5 templates verified rendering to MP4.

**Weaknesses:** CPU rendering is slower (~15-40s for 4 videos). No history sidebar. No "Vary" single simulation. Minimal UI polish.

### Branch: `alt/vercel` (v0/Vercel version)

| Layer | Technology | Notes |
|-------|-----------|-------|
| Frontend | Next.js + shadcn/ui + Tailwind (v0-generated) | Rich UI: history sidebar, skeleton loaders, health badge |
| AI | Gemini 2.0 Flash | Prompt parsing only |
| Rendering | MuJoCo + MJX on H100 GPU | GPU-accelerated, 4 parallel workers |
| Backend | FastAPI on Azure H100 | 4 uvicorn workers, EGL rendering |
| Deployment | Vercel (frontend) + Azure H100 (compute) | Split architecture |
| Templates | 5 templates built into `server.py` | Same 5 simulation types |

**Strengths:** Production-grade UI (shadcn components, history panel, vary/regenerate per-sim). GPU rendering via MJX will be dramatically faster. Designed for Vercel deployment out of the box. `start.sh` handles H100 setup automatically.

**Weaknesses:** Requires H100 server running and accessible. More moving parts (Vercel + Azure + Gemini). Haven't verified E2E yet.

## The bake-off plan

### Step 1: Get `main` up and running

```bash
git checkout main
cd backend && pip install -e .
export ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY
uvicorn backend.main:app --port 8000 --reload &
cd ../frontend && npm install && npm run dev
```

Open http://localhost:3000, run 3-5 prompts, note:
- Time from prompt submit → videos visible
- Video quality (resolution, smoothness, visual appeal)
- UI feel (responsiveness, loading states, friction)
- Template variety (does AI pick good templates + params?)

### Step 2: Get `alt/vercel` up and running

```bash
git checkout alt/vercel

# H100 server
scp -r backend/ $SSH_USER@$GPU_SERVER_IP:~/simgen/
ssh $SSH_USER@$GPU_SERVER_IP "cd ~/simgen/backend && chmod +x start.sh && ./start.sh"

# Frontend (local or Vercel)
npm install
GOOGLE_API_KEY=$GOOGLE_API_KEY MUJOCO_SERVER_URL=http://$GPU_SERVER_IP:8000 npm run dev
```

Open http://localhost:3000, run the same 3-5 prompts, note same criteria.

### Step 3: Compare and decide

| Criteria | main (Claude) | alt/vercel (v0) | Winner |
|----------|--------------|-----------------|--------|
| Time to first video | ___ sec | ___ sec | |
| Total generation time (4 videos) | ___ sec | ___ sec | |
| Video quality | /5 | /5 | |
| UI polish | /5 | /5 | |
| Template/param quality | /5 | /5 | |
| Setup complexity | /5 | /5 | |
| Cost per generation | $____ | $____ | |
| **Overall** | | | |

### What to look for

- **Speed:** alt/vercel should crush main on render time (H100 GPU vs Mac CPU). But does the network latency to Azure eat that advantage?
- **AI quality:** Does Claude (tool-use) or Gemini (Flash) produce better simulation configs? Try the same prompt on both and compare parameter choices.
- **UI:** The v0 version has history, vary, and richer components. Is that actually useful in practice, or is the minimal main UI sufficient?
- **Reliability:** Which one fails less? Template errors, API timeouts, video encoding issues?

### After the bake-off

The winning path becomes the foundation. Specific pieces from the losing path can be cherry-picked:
- If `main` wins on AI quality → swap Gemini for Claude in the alt/vercel frontend
- If `alt/vercel` wins on UI → port shadcn components back to main
- If `alt/vercel` wins on speed → move main's backend to the H100

The goal is one unified path forward, not two parallel codebases.
