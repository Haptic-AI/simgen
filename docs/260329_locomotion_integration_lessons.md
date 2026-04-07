# 2026-03-29 — Locomotion Integration: Lessons Learned

## Summary

We trained a humanoid walking policy on the H100 and integrated it into SimGen.
The humanoid can now walk. Getting here required solving several real problems
that are worth documenting for the next session.

## What we did

### 1. Trained a walking policy (5 minutes on H100)

- **Framework:** Brax PPO (Proximal Policy Optimization)
- **Environment:** Brax's built-in `humanoid` (NOT our custom XML template)
- **Config:** 2048 parallel environments, 20M timesteps
- **Result:** Reward climbed from 90 (falling) → 5,091 (walking)
- **File:** `backend/policies/humanoid_walk.pkl` (1.3 MB)
- **H100 location:** `/mnt/chris-premium/simgen/policies/humanoid_walk.pkl`
- **Training script:** `/mnt/chris-premium/simgen/train_walk_v2.py`

### 2. Built a GPU render server on the H100

- **File:** `/mnt/chris-premium/simgen/gpu_render_server.py`
- **Port:** 8100 (accessed via SSH tunnel from local Mac)
- **What it does:** Receives a render request → runs the Brax policy → collects joint positions → renders with MuJoCo → encodes to MP4 with ffmpeg → returns the video

### 3. Integrated into the local backend

- **Detection:** `backend/locomotion.py` scans prompts for walking keywords
- **Routing:** `backend/renderer.py` sends locomotion renders to the GPU server
- **Fallback chain:** GPU server → local Brax (fails on Python 3.9) → passive ragdoll

## Problems we hit and how we solved them

### Problem 1: Python 3.9 can't import Brax/MJX

**Symptom:** `TypeError: unsupported operand type(s) for |: '_UnionGenericAlias' and 'types.GenericAlias'`

**Root cause:** `mujoco-mjx` uses Python 3.10+ union type syntax (`Type1 | Type2`) which doesn't work in Python 3.9.

**Solution:** Made all Brax imports lazy — only imported at render time, not at module load time. Then moved the actual rendering to the H100 (Python 3.10) via HTTP.

**Lesson:** Don't import GPU/ML libraries at the top of files that need to load on all platforms. Use lazy imports or split into separate services.

### Problem 2: MuJoCo headless rendering on the H100

**Symptom:** `mujoco.FatalError: an OpenGL platform library has not been loaded`

**Root cause:** The H100 server has no display. MuJoCo needs to be told to use EGL (headless GPU rendering) instead of looking for a window.

**Solution:** Set `MUJOCO_GL=egl` environment variable before starting the GPU render server. Added it to `start_gpu_server.sh`.

**Lesson:** Any headless MuJoCo rendering needs `MUJOCO_GL=egl` (Linux) or `MUJOCO_GL=osmesa` (fallback). This should be in every deployment script.

### Problem 3: ffmpeg pipe-to-stdout with movflags

**Symptom:** `BrokenPipeError: [Errno 32] Broken pipe`

**Root cause:** ffmpeg's `-movflags +faststart` requires seeking back to the beginning of the file to write the moov atom. You can't do that when writing to `pipe:1` (stdout).

**Solution:** Write to a temp file instead of piping to stdout. Return the temp file via FastAPI's `FileResponse`.

**Lesson:** Never use `-movflags +faststart` with pipe output. Write to file first, then serve.

### Problem 4: Humanoid walks out of frame

**Symptom:** Top-down checkerboard view with a tiny dot — the humanoid walked away from the fixed camera.

**Root cause:** Default MuJoCo camera is static. The Brax humanoid walks forward and out of view.

**Solution:** Use `mujoco.MjvCamera` with `type=mjCAMERA_TRACKING` and `trackbodyid=1` to follow the humanoid's torso. Set reasonable distance (4.0), azimuth (135°), and elevation (-20°).

**Lesson:** Any locomotion simulation MUST use a tracking camera. Static cameras only work for stationary scenes.

### Problem 5: Concurrent GPU renders crash the server

**Symptom:** 2 of 4 videos rendered, 2 got `Connection reset by peer`

**Root cause:** FastAPI's local backend sends 4 render requests sequentially, but the GPU server's single uvicorn worker can't handle a second request while the first is still rendering (GPU memory contention).

**Solution:** Added a `threading.Lock()` in the GPU render server to serialize all render requests. Only one render runs at a time.

**Lesson:** GPU rendering is inherently single-threaded per device. Serialize requests or use a proper job queue.

### Problem 6: Brax's humanoid is different from our XML template

**Symptom:** Walking videos look different from our ragdoll videos — different model, different proportions.

**Root cause:** The walking policy was trained on Brax's built-in humanoid model, not our custom `humanoid.xml`. They're different models with different joint structures.

**Current status:** We use Brax's model for locomotion and our XML template for passive physics. This creates a visual inconsistency.

**Future fix:** Either (a) retrain the policy on our custom model using MJX, or (b) replace our XML template with Brax's model for all humanoid simulations.

## Architecture as of 2026-03-29

```
Creator types "a person walking"
        ↓
Local backend (:8000) — Claude API parses prompt
        ↓
locomotion.py detects "walking" keyword → policy_name = "humanoid_walk"
        ↓
renderer.py tries GPU server first:
        ↓
SSH tunnel (localhost:8100 → H100:8100)
        ↓
GPU render server on H100:
  1. Loads Brax policy from pkl
  2. Runs 300 steps (10s × 30fps) with JAX JIT
  3. Collects qpos/qvel trajectory
  4. Renders each frame with MuJoCo (EGL headless)
  5. Tracking camera follows the humanoid
  6. ffmpeg encodes to MP4 (temp file)
  7. Returns MP4 via FileResponse
        ↓
If GPU server fails → falls back to passive ragdoll (our XML template)
```

## How to start the full system

```bash
# Terminal 1: SSH tunnel to H100
ssh -i $SSH_KEY -p $SSH_PORT -N -L 8100:localhost:8100 $SSH_USER@$GPU_SERVER_IP

# Terminal 2 (if GPU server not running): Start GPU render server on H100
ssh -i $SSH_KEY -p $SSH_PORT $SSH_USER@$GPU_SERVER_IP "bash /mnt/chris-premium/simgen/start_gpu_server.sh"

# Terminal 3: Local backend
cd /path/to/mujoco-cloud
ANTHROPIC_API_KEY=... python3 -m uvicorn backend.main:app --port 8000

# Terminal 4: Frontend
cd frontend && npx next dev -p 3000
```

## Performance

| Step | Time (first request) | Time (cached) |
|------|---------------------|---------------|
| Claude API prompt parsing | 2-3s | 2-3s |
| JAX JIT compilation | ~50s | 0s (cached) |
| Brax simulation (10s, 300 frames) | ~5s | ~5s |
| MuJoCo rendering (300 frames) | ~3s | ~3s |
| ffmpeg encoding | ~1s | ~1s |
| **Total per video** | **~60s** | **~10s** |
| **Total for 4 videos** | **~4 min** | **~40s** |

JIT compilation only happens once per server restart. After warmup, locomotion renders should take ~10s per video.

## What's next

1. **Warm up JIT on server start** — run a dummy render when the GPU server boots so the first real request isn't slow
2. **Consistent humanoid model** — either retrain on our XML or adopt Brax's model everywhere
3. **More policies** — train jump, stumble, push-recovery, run
4. **Camera control** — let creators pick camera angle (front, side, top-down, tracking)
5. **Gravity variation** — test the walking policy under Moon/Mars gravity (it may fall over — might need per-environment policies)
