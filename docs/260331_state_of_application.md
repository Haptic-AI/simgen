# 2026-03-31 — State of SimGen

## What Is SimGen

A prompt-to-physics-simulation app for creators. Describe a scene in plain English, get 4 MuJoCo simulation videos back. Rate them. The system learns your style. Iterate until perfect.

**Repo:** https://github.com/Haptic-AI/simgen
**Branch:** `main` (Claude-built), `alt/vercel` (v0-built alternative)

## What's Working

| Feature | Status |
|---------|--------|
| FastAPI backend + Next.js frontend | Working |
| Claude API prompt parsing with physics guardrails | Working |
| 5 MuJoCo templates (pendulum, ball, arm, cartpole, humanoid) | Working |
| Self-learning feedback loop (SQLite + ratings → Claude few-shot) | Working |
| Environment presets (Earth, Moon, Mars, Mercury, Jupiter, Zero-G) | Working |
| Visual themes (Studio, Outdoor, Industrial, Desert, Night, Snow) | Working |
| Flow Mode (pick favorite → auto-iterate) | Working |
| Prompt chaining + undo | Working |
| "None of these worked" reject-all + auto-retry | Working |
| History sidebar (past prompts, click to re-run) | Working |
| GPU render server on H100 (Brax policies) | Working |
| 3 trained policies (humanoid_walk, humanoid_run, hopper) | Trained (crawling, not upright) |
| Dockerized (3 containers + docker-compose) | Built, untested in production |
| Comprehensive docs (7 docs covering everything) | Written |

## What's NOT Working

| Problem | Root Cause |
|---------|------------|
| **Humanoid walks upright** | Brax's default reward optimizes forward velocity, humanoid learns to crawl. MuJoCo Playground trained a proper policy (reward 2→144) but orbax checkpoint can't be extracted due to wrapper incompatibility. |
| **Visual themes on GPU renders** | Brax model has its own textures that override our theme settings |
| **Speed for walking prompts** | 2-4 min per generation (JIT compilation + sequential GPU renders) |

## Usage Data (from testing)

- 32 generations, 128 simulations rendered
- 21 ratings: 5 upvotes, 16 downvotes
- Creator preference: low gravity, zero push, floating/graceful motion
- Top liked: "Weightless Serenity" (gravity=0.3), "Zero-G Meditation", "Floating Grace"
- Top unmatched prompt: "human walking" — the #1 thing that doesn't work

## Architecture

```
Mac (local dev):
  frontend/ (Next.js :3000) → backend/ (FastAPI :8000) → Claude API
                                  ↓ (walking prompts)
                           SSH tunnel :8100
                                  ↓
H100 (Azure $GPU_SERVER_IP:$SSH_PORT):
  gpu_render_server.py (:8100) → Brax policy → MuJoCo render → ffmpeg → MP4
```

## How to Run

```bash
# Clone
git clone https://github.com/Haptic-AI/simgen.git
cd simgen

# Backend
pip install fastapi uvicorn mujoco numpy Pillow anthropic imageio av
ANTHROPIC_API_KEY=... python3 -m uvicorn backend.main:app --port 8000

# Frontend
cd frontend && npm install && npx next dev -p 3000

# GPU server (optional — for walking prompts)
ssh -i $SSH_KEY -p $SSH_PORT -N -L 8100:localhost:8100 $SSH_USER@$GPU_SERVER_IP
# Then on H100: bash /mnt/chris-premium/simgen/start_gpu_server.sh

# Docker (alternative)
cp .env.example .env  # add ANTHROPIC_API_KEY
docker compose up --build
```

## H100 Server State

```
ssh -i $SSH_KEY -p $SSH_PORT $SSH_USER@$GPU_SERVER_IP

/mnt/chris-premium/simgen/
├── policies/                    # Trained Brax policies (crawling)
│   ├── humanoid_walk.pkl
│   ├── humanoid_run.pkl
│   └── hopper.pkl
├── gpu_render_server.py         # FastAPI render server
├── start_gpu_server.sh          # Startup script (MUJOCO_GL=egl)
├── train_walk_v2.py             # Brax PPO training script
├── train_walk_v3.py             # Improved training (still crawls)
├── train_playground.py          # MuJoCo Playground training
└── playground_logs/
    └── HumanoidWalk-20260329-213746/
        └── checkpoints/000088473600/  # Orbax checkpoint (can't extract)

~/mujoco_playground/             # Google DeepMind repo (installed)

Python 3.10 (default), 3.11 (with JAX CUDA — used for Playground)
```

## Priority List for Next Session

| # | Task | Why | Effort |
|---|------|-----|--------|
| 1 | **Fix upright walking** — try dm_control locomotion OR custom MJX training with height reward | Everything depends on this | Hours-days |
| 2 | Apply visual themes to GPU renders | Creators see checkerboard, not their theme | 1 hour |
| 3 | Speed: reduce to <1 min per generation | 2-4 min kills creative flow | Half day |
| 4 | Real textures from Poly Haven | Colored floors → textured floors | Half day |
| 5 | Video download button | Creators need to save work | 1 hour |
| 6 | Multi-user for 100-creator activation | Single-user DB won't scale | 2-3 days |

## Key Files

```
backend/
  main.py              # FastAPI: /generate, /vary, /video, /feedback, /reject-all, /stats, /history, /environments, /themes
  renderer.py          # MuJoCo render + GPU server proxy (curl-based)
  prompt_parser.py     # Claude API with physics rules + feedback context
  db.py                # SQLite persistence
  templates.py         # 5 template schemas
  environments.py      # 6 gravity presets
  visual_themes.py     # 6 visual themes
  physics_rules.py     # Real-world physics knowledge for AI referee
  locomotion.py        # Keyword → policy mapping
  policies/            # Trained .pkl files
  templates/           # MuJoCo XML files

frontend/
  app/page.tsx         # Main page: flow mode, prompt chain, history
  components/
    prompt-input.tsx
    simulation-grid.tsx    # 2x2 grid + reject-all
    simulation-card.tsx    # Video + "Iterate on this" + "Pick this one"
    feedback-buttons.tsx
    environment-selector.tsx
    theme-selector.tsx
    stats-panel.tsx
    history-sidebar.tsx

gpu-renderer/          # Docker context for H100
docs/                  # 7 comprehensive docs
docker-compose.yml     # 3-container orchestration
```

## Product Vision

**Midjourney = dream without limits. SimGen = discover what's beautiful within the limits of reality.**

Two personas:
- **Creator** — prompts, iterates, rates. Never sees physics params. Constrained by reality (that's the feature).
- **Admin** — collects lessons across all creators, improves the model, closes capability gaps.

The flywheel: more creators → more ratings → better model → simpler prompts → more creators.
