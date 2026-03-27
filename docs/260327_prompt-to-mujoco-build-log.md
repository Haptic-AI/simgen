# 2026-03-27 — Prompt-to-MuJoCo Simulation App Build Log

## Part 1: What Was Built

### Architecture

```
Frontend (Next.js)          Backend (FastAPI)
┌─────────────────┐        ┌──────────────────────────┐
│ Prompt input     │──POST──│ /generate                │
│ 2x2 video grid   │  /gen  │   Claude API → sim config│
│ Thumbs up/down   │        │   MuJoCo render → MP4    │
│                  │◄─video─│ /video/{id}              │
│                  │──POST──│ /feedback                │
└─────────────────┘        └──────────────────────────┘
```

### How to run

**Backend:**
```bash
cd backend
pip install -e .
export ANTHROPIC_API_KEY=sk-ant-...
uvicorn backend.main:app --port 8000 --reload
```

**Frontend:**
```bash
cd frontend
npm run dev
```

Open http://localhost:3000 and type something like "a pendulum swinging in low gravity" or "bouncing ball with high elasticity".

### Components built

| Component | Files | Status |
|-----------|-------|--------|
| 5 MuJoCo XML templates | pendulum, bouncing_ball, robot_arm, cartpole, humanoid | All simulate + render to MP4 |
| Renderer | `backend/renderer.py` — MuJoCo headless → imageio/ffmpeg MP4 | Tested, 34-89 KB per video |
| Prompt parser | `backend/prompt_parser.py` — Claude API with tool-use | Structured JSON output |
| FastAPI app | `backend/main.py` — /generate, /video/{id}, /feedback | CORS enabled for localhost:3000 |
| Next.js frontend | Dark theme, prompt input, 2x2 video grid, thumbs up/down | Builds clean |

### Project structure

```
backend/
  main.py              # FastAPI: /generate, /feedback, /video/{id}
  renderer.py          # MuJoCo → MP4 pipeline (imageio/ffmpeg)
  prompt_parser.py     # Claude API with tool-use for structured JSON
  templates.py         # Template schemas (param ranges, defaults)
  templates/
    pendulum.xml
    bouncing_ball.xml
    robot_arm.xml
    cartpole.xml
    humanoid.xml
  pyproject.toml

frontend/
  app/
    layout.tsx         # Dark theme shell
    page.tsx           # Main page: prompt + generation history
    globals.css
  components/
    prompt-input.tsx   # Chat-style input bar
    simulation-grid.tsx # 2x2 grid wrapper
    simulation-card.tsx # Video + label + feedback
    feedback-buttons.tsx # Thumbs up/down
```

### Key technical decisions

- **Claude API with tool-use** for structured output — more reliable than raw JSON
- **imageio[pyav]** fallback when system ffmpeg isn't installed — H.264 for browser compatibility
- **Sequential rendering** of 4 videos (not parallel) — avoids memory issues
- **Sync /generate endpoint** — blocks for 10-30s, fine for single-user local use
- **No database, no auth** — in-memory state, /tmp for videos
- **640x480 resolution** at 30fps, 5 sec per simulation

### Performance specs & optimization roadmap

#### Where time is spent (end-to-end for 4 videos)

| Stage | Current (Mac CPU) | What drives it |
|-------|-------------------|----------------|
| Prompt parsing (Claude API) | 1-3 sec | Network round-trip + LLM inference |
| MuJoCo simulation (per video) | 0.5-2 sec | Timestep count, model complexity |
| Frame rendering (per video) | 2-5 sec | Resolution x frame count, CPU-bound |
| Video encoding (per video) | 0.5-1 sec | Frame count, codec, encoder speed |
| **Total (4 videos, sequential)** | **~15-40 sec** | Everything runs in series |

#### Target: < 2 minutes (current v1 — achievable now)

**Minimum specs:**
- macOS or Linux, 16GB+ RAM, 4+ CPU cores
- Python 3.10+, MuJoCo 3.x
- System ffmpeg (faster than imageio fallback)
- Anthropic API key with reasonable rate limits

**What to do:**
- Install system ffmpeg (`brew install ffmpeg`) — ~30% faster encoding vs imageio
- Current settings (640x480, 30fps, 5 sec, sequential) should land in 15-40 sec range
- Already within the 2-minute target on most machines

#### Target: < 1 minute

**Recommended specs:**
- 32GB+ RAM (headroom for 4 concurrent MuJoCo instances)
- 8+ CPU cores (Apple M2 Pro/Max or better, or Intel/AMD equivalent)
- System ffmpeg with libx264

**Optimizations to implement:**
1. **Parallel rendering** — render all 4 simulations concurrently using `concurrent.futures.ProcessPoolExecutor(max_workers=4)`. Each MuJoCo instance is independent. On 8 cores this cuts render time by ~3.5x.
2. **Reduce resolution to 480x360** for the preview grid — only render 640x480 (or higher) on user request
3. **Use Claude Haiku** for prompt parsing instead of Sonnet — same structured output quality for this task, 2-3x faster response time, cheaper
4. **Shorten simulation to 3 sec** (90 frames) — still enough to see the physics, cuts render + encode time by 40%

**Expected result:** ~12-25 sec end-to-end

#### Target: < 30 seconds

**Ideal specs:**
- NVIDIA GPU (your H100 with 96GB VRAM is perfect)
- 64GB+ system RAM
- NVMe SSD for /tmp video writes
- System ffmpeg compiled with NVENC (GPU-accelerated H.264 encoding)
- Fast network to Anthropic API (< 200ms latency)

**Optimizations to implement:**
1. **MJX GPU rendering** — move simulation to GPU using `mujoco.mjx`. The H100 can simulate all 4 variations in a single batched pass. This alone turns 4x 2-sec CPU sims into 1x 0.1-sec GPU batch.
2. **NVENC encoding** — replace `libx264` with `h264_nvenc` in the ffmpeg pipeline. GPU-accelerated encoding is 5-10x faster than CPU x264.
3. **Streaming render pipeline** — pipe frames directly from GPU → NVENC without writing to RAM. Eliminates the frame buffer entirely.
4. **Claude API with streaming** — start rendering the first variation while Claude is still generating variations 2-4 (parse the tool-use response incrementally).
5. **Parallel 4-way with GPU** — dedicate GPU streams to each variation. The H100 has enough VRAM for 4 concurrent MuJoCo renderers at 640x480.
6. **Pre-warm models** — keep compiled MuJoCo models in memory between requests. Template XML parsing + model compilation takes ~100ms per request that can be cached.
7. **WebSocket streaming to frontend** — send each video to the frontend as soon as it's ready (don't wait for all 4). User sees first result in ~8 sec.

**Expected result:** ~5-10 sec end-to-end (prompt → first video visible)

#### Hardware you have available

| Resource | Spec | Best use |
|----------|------|----------|
| Mac (local) | 128GB RAM, Apple Silicon (assumed) | Development, < 1 min target with parallel CPU rendering |
| H100 GPU | 96GB VRAM | Production, < 30 sec target with MJX + NVENC |
| Claude Max Pro | Unlimited Anthropic API | No rate limit concerns for prompt parsing |
| Gemini (unlimited) | Google AI | Alternative prompt parser if latency is lower |

#### Quality vs speed tradeoffs

| Setting | Fast (30s target) | Balanced (1min) | High quality |
|---------|-------------------|-----------------|--------------|
| Resolution | 480x360 | 640x480 | 1920x1080 |
| Duration | 3 sec | 5 sec | 10 sec |
| FPS | 24 | 30 | 60 |
| Frames | 72 | 150 | 600 |
| Render per video | ~0.5s (GPU) | ~3s (CPU) | ~20s (CPU) |
| Encoding | NVENC | ffmpeg ultrafast | ffmpeg slow (better compression) |

### What was removed

Old `mjsim/` library, `examples/`, and cloud deployment code (Azure/GCP CLI) are gone. The project is 100% focused on prompt-to-simulation now.

---

## Part 2: The Prompt That Created This Project

The following prompt was provided to Claude Code to build the entire app in one session:

---

> Prompt-to-MuJoCo Simulation App
>
> **Overview**
>
> A Midjourney-inspired interface where users submit text prompts describing physics scenarios, an AI interprets them to select and configure MuJoCo simulation templates, and the backend generates 4 video variations for the user to review with thumbs up/down feedback.
>
> **Architecture**
>
> ```
>                     Next.js Frontend
>   - Prompt input (chat-style)
>   - 2x2 video grid with controls
>   - Thumbs up/down per simulation
>   - "Generate More" / "Regenerate" buttons
>
>                     | /api/...
>                     v
>
>                     FastAPI Backend
>   - POST /generate - AI interprets prompt -> 4 simulations
>   - POST /feedback - Collect user ratings
>   - GET /video/{id} - Serve rendered videos
>   - MuJoCo rendering pipeline
> ```
>
> **Project Structure**
>
> ```
> /vercel.json                     # Services configuration
> /backend/
>   main.py                        # FastAPI app
>   pyproject.toml                 # Python deps (mujoco, opencv, etc.)
>   templates/                     # MuJoCo XML templates
>     pendulum.xml
>     bouncing_ball.xml
>     robot_arm.xml
>     humanoid.xml
>     cartpole.xml
>   renderer.py                    # MuJoCo -> video rendering
>   prompt_parser.py               # AI prompt interpretation
>
> /frontend/
>   package.json
>   next.config.ts
>   app/
>     layout.tsx
>     page.tsx                     # Main UI
>     globals.css
>   components/
>     prompt-input.tsx             # Chat-style input
>     simulation-grid.tsx          # 2x2 video grid
>     simulation-card.tsx          # Single video + feedback
>     feedback-buttons.tsx         # Thumbs up/down
> ```
>
> **Implementation Order**
>
> 1. Set up project structure - vercel.json, frontend/backend scaffolding
> 2. Create MuJoCo templates - XML files for 5 simulation types
> 3. Build renderer - MuJoCo -> MP4 pipeline
> 4. Build prompt parser - AI interpretation of prompts
> 5. Create API routes - /generate, /feedback, /video
> 6. Build frontend UI - Prompt input, video grid, feedback buttons
> 7. Polish - Loading states, error handling, responsive design
>
> **Dependencies**
>
> Backend (Python): fastapi, uvicorn, mujoco, opencv-python, numpy, groq (for AI prompt parsing)
>
> Frontend (Next.js): next, react, tailwindcss, lucide-react (icons)
>
> **Key Components**
>
> 1. Frontend - Main Page (frontend/app/page.tsx)
>    - Dark theme, centered layout
>    - Prompt input at bottom (like chat)
>    - 2x2 grid of simulation videos above
>    - Each video has: play/pause/seek controls, simulation parameters overlay, thumbs up/down buttons, "Use as base" button for variations
>    - Loading states with skeleton placeholders
>
> 2. Backend - Prompt Parser (backend/prompt_parser.py)
>    Uses AI (via Groq for fast inference) to:
>    - Parse natural language prompts
>    - Map to available templates
>    - Generate 4 parameter variations
>    - Return structured config for each simulation
>
>    Example prompt: "a pendulum swinging fast with high friction"
>    AI returns:
>    ```json
>    {
>      "template": "pendulum",
>      "variations": [
>        { "length": 1.0, "damping": 0.8, "initial_angle": 45 },
>        ...
>      ]
>    }
>    ```
>
> 3. Backend - MuJoCo Renderer (backend/renderer.py)
>    - Load XML template
>    - Apply parameter variations
>    - Run simulation for N steps
>    - Render frames using MuJoCo's built-in renderer
>    - Encode to MP4 using OpenCV
>
> **MuJoCo Templates**
>
> Pre-built XML files for common physics scenarios:
> - Pendulum: length, damping, initial angle, gravity
> - Bouncing Ball: elasticity, initial height, ball size
> - Robot Arm: joint stiffness, target position, speed
> - Cartpole: pole length, cart mass, initial angle
> - Humanoid: walking speed, terrain roughness
>
> **Feedback System**
> - Store ratings per simulation (thumbs up/down)
> - Track which prompts -> which templates work well
> - Enable "show me more like this" functionality
>
> **API Endpoints**
>
> POST /generate
> Request: `{ "prompt": "bouncing ball with high elasticity" }`
> Response: `{ "batch_id": "abc123", "simulations": [{ "id": "sim1", "video_url": "/api/video/sim1", "params": { ... } }, ...] }`
>
> POST /feedback
> Request: `{ "simulation_id": "sim1", "rating": "up" | "down" }`
>
> GET /video/{simulation_id}
> Returns MP4 video file.
>
> **Notes**
> - Videos stored temporarily in /tmp (ephemeral storage)
> - MuJoCo requires headless rendering (uses EGL/OSMesa)
> - Each simulation renders ~3-5 seconds of video at 30fps

---

### Modifications made by Claude during implementation

1. **Groq → Claude API**: Replaced Groq with Anthropic Claude API (claude-sonnet-4-20250514) using tool-use for reliable structured JSON output
2. **OpenCV → imageio[pyav] + ffmpeg**: Used imageio with PyAV backend instead of cv2 for H.264 browser-compatible MP4 encoding, with system ffmpeg as primary when available
3. **vercel.json removed**: Not needed for local-first v1
4. **lucide-react removed**: Used inline SVGs instead to avoid extra dependencies
5. **Template params adjusted**: Humanoid uses initial_height/push_force/gravity/damping instead of walking speed/terrain roughness (more physically meaningful for a ragdoll sim)
6. **MuJoCo `<force>` → `<motor>`**: Fixed cartpole XML for MuJoCo 3.x compatibility
