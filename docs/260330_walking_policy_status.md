# 2026-03-30 — Walking Policy Status: What Works, What Doesn't, What's Next

## The Core Problem

**Brax's built-in humanoid doesn't walk — it crawls.**

The PPO-trained policy (reward 5,091) learned to maximize forward velocity by
flopping/crawling forward, not by walking upright. Average torso height is 0.72m
(should be 1.2m+). This is a known problem with the Brax humanoid's default
reward function.

## What We Tried

### Attempt 1: Brax PPO with default reward (humanoid_walk.pkl)
- **Result:** Crawling, not walking. Avg height 0.72m.
- **Why:** Default reward = forward_velocity - control_cost. No incentive to stand.
- **Training time:** 5 min on H100

### Attempt 2: Brax PPO with spring backend (humanoid_run.pkl)
- **Result:** Different crawling pattern. Still not upright.
- **Training time:** 5 min on H100

### Attempt 3: MuJoCo Playground HumanoidWalk
- **Result:** Training completed (100M steps, 22 min), reward 2→144, 9 checkpoints saved.
- **Problem:** Can't extract inference function from orbax checkpoint. Playground's training
  infrastructure is tightly coupled — restoring requires replaying the full training setup.
- **Blocker:** Brax 0.14.2 (latest) changes State format, making checkpoint restore crash.

### Attempt 4: Playground's --load_checkpoint_path flag
- **Result:** Process runs but gets stuck on JIT compilation for 75+ minutes.
- **Why:** Even with `num_timesteps=1`, it compiles the full 2048-env training graph.

## Root Causes

1. **Brax's humanoid reward doesn't incentivize upright posture.**
   The humanoid learns to move forward by any means — crawling is easier than walking.

2. **MuJoCo Playground checkpoints are not portable.**
   They use orbax format + tightly coupled wrappers. No simple `load_and_infer()` API.

3. **Python version fragmentation.**
   Mac: 3.9 (can't import Brax). H100: 3.10 (too old for latest Brax). 3.11 works
   but needed manual JAX CUDA setup.

## What Actually Works Right Now

- **Passive ragdoll physics** render correctly (pendulum, ball, cartpole, robot arm)
- **Humanoid with push_force** works (gets pushed and falls realistically)
- **Humanoid standing** works (briefly, then falls over as expected for a ragdoll)
- **GPU server on H100** works for rendering (curl-based client is reliable)
- **Visual themes** work (floor color, lighting mood)
- **Feedback loop** works (ratings → few-shot learning in Claude prompt)

## Recommended Next Steps (in priority order)

### Option A: Custom MJX training loop (best, 1-2 days)
Write a custom training loop (not Brax's) that uses MJX directly:
- Custom reward: `reward = 10 * alive_bonus + forward_velocity - control_cost`
  where `alive_bonus` requires torso height > 1.0m
- Train directly on our custom humanoid XML (not Brax's built-in model)
- Save raw JAX params (not orbax) → load directly for inference
- This bypasses all the Brax/Playground wrapper complexity

### Option B: dm_control locomotion suite (fastest, hours)
Use `dm_control`'s humanoid walker tasks which have proper locomotion behaviors:
- `suite.load('humanoid', 'walk')` — returns a walking humanoid environment
- These use classical control, not RL policies
- Limited configurability but guaranteed upright walking
- Would work locally on Mac (no GPU needed)

### Option C: Use a different model (Unitree H1)
MuJoCo Playground's H1 humanoid has properly tuned walking rewards.
If we can solve the checkpoint extraction problem, this would give us
a realistic bipedal robot walking (not a human, but much better than crawling).

### Option D: Motion capture replay
Load walking motion capture data (BVH/C3D format) and replay it on the humanoid.
No RL needed — just playback pre-recorded walking. Creative variations via
speed, stride length, and blending between clips.

Resources:
- CMU MoCap database (free): http://mocap.cs.cmu.edu/
- MuJoCo's `mj_setKeyframe` for motion playback
- dm_control's `locomotion.mocap` module

## Current Infrastructure State

```
H100 Server (azureuser@20.69.105.30:50000):
├── /mnt/chris-premium/simgen/
│   ├── policies/
│   │   ├── humanoid_walk.pkl (1.3MB — crawling, NOT walking)
│   │   ├── humanoid_run.pkl (crawling fast)
│   │   └── hopper.pkl (works but one-legged)
│   ├── playground_logs/HumanoidWalk-20260329-213746/
│   │   └── checkpoints/000088473600/ (orbax — can't extract easily)
│   ├── gpu_render_server.py (works, serves Brax policies)
│   ├── start_gpu_server.sh
│   └── train_*.py (various training scripts)
├── ~/mujoco_playground/ (Google DeepMind's repo, installed)
└── Python 3.10 (default) + 3.11 (with JAX CUDA)

Local Mac:
├── backend/ (FastAPI, SQLite, Claude API)
├── frontend/ (Next.js)
└── SSH tunnel (localhost:8100 → H100:8100)
```
