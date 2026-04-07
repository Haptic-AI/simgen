# 2026-03-28 — Locomotion Policy: Making the Humanoid Walk

## The Problem

Our humanoid template is a ragdoll — it has joints, limbs, and mass but no brain.
Every "walking" prompt produces a figure that falls flat because there's no controller
telling each joint what to do. A real human stands and walks by firing hundreds of muscle
adjustments per second. We need to train an AI "brain" for our humanoid.

## The Solution

Use **MuJoCo Playground** (Google DeepMind's open-source framework) to train a locomotion
policy via reinforcement learning (PPO). The policy learns to walk by trial and error
across thousands of parallel simulations on GPU.

**Training time estimate on H100 (96GB VRAM): ~3-5 minutes.**

## How It Works

```
1. MuJoCo Playground sets up 8192 parallel humanoid environments on GPU (MJX)
2. PPO algorithm tries random joint actions → humanoid falls
3. Reward signal: stay upright + move forward + minimize energy
4. After millions of attempts (across parallel envs): humanoid learns to walk
5. Save the trained policy as an ONNX model
6. In SimGen: load the ONNX policy → at each timestep, policy outputs joint torques → humanoid walks
```

## Architecture

### Current flow (ragdoll):
```
Prompt → Claude picks params → MuJoCo simulates passive physics → humanoid falls → MP4
```

### New flow (with locomotion):
```
Prompt → Claude picks params + locomotion style → MuJoCo simulates WITH policy controlling joints → humanoid walks → MP4
```

## Implementation Plan

### Phase 1: Train on H100 (Day 1)

**H100 server:** `ssh -i $SSH_KEY -p $SSH_PORT $SSH_USER@$GPU_SERVER_IP`

```bash
# 1. Install MuJoCo Playground
pip install mujoco-playground

# 2. Train a humanoid walking policy (~3-5 min on H100)
python -m playground.train_jax_ppo \
  --env_name HumanoidWalk \
  --num_envs 8192 \
  --max_steps 50_000_000 \
  --checkpoint_dir /home/azureuser/simgen_policies/

# 3. Export best checkpoint to ONNX
python -m playground.export_onnx \
  --checkpoint /home/azureuser/simgen_policies/best.pkl \
  --output /home/azureuser/simgen_policies/humanoid_walk.onnx
```

**What we'll train:**
| Policy | Description | Use case |
|--------|-------------|----------|
| humanoid_walk | Basic forward walking | "a person walking down the street" |
| humanoid_stand | Active balance (stays upright) | "a person standing still" |
| humanoid_run | Fast locomotion | "a person running" |

### Phase 2: Integrate into SimGen backend

New file: `backend/locomotion.py`
- Load ONNX policy at startup
- During simulation: at each timestep, feed joint positions → policy outputs torques → apply to MuJoCo
- Parameters the creator controls: walk speed, direction, style (via reward shaping)

Updated `backend/renderer.py`:
- Detect if template has a locomotion policy available
- If yes: run policy-controlled simulation instead of passive physics
- Policy runs at 50Hz, simulation at 500Hz (10 physics steps per policy step)

Updated `backend/physics_rules.py`:
- Remove "humanoid CANNOT walk" limitation
- Add new capabilities: walk, run, stand actively, turn

### Phase 3: Expand policies

Once the pipeline works, train additional policies:
- **humanoid_jump** — vertical jump with landing
- **humanoid_stumble** — controlled loss of balance + recovery
- **humanoid_push_recovery** — get pushed, regain balance
- **humanoid_sit_stand** — sit down and stand up transitions

Each policy is a separate ONNX file, ~5 min to train on H100.

## What the Creator Experiences

Before:
- "a person walking" → ragdoll falls flat → frustration

After:
- "a person walking" → humanoid actually walks forward → creator iterates on speed, style, environment
- "a person walking on the moon" → same walking policy, 1/6th gravity → slow floating steps
- "a person running then stumbling" → chain two policies → run → stumble transition

## Technical Details

### MuJoCo Playground stack
- **MJX**: MuJoCo on XLA/GPU — runs 8192+ parallel physics sims
- **JAX**: Automatic differentiation + JIT compilation
- **PPO**: Proximal Policy Optimization — the standard RL algorithm for locomotion
- **ONNX Runtime**: Cross-platform inference at 50Hz

### Reward function for walking (standard)
```
reward = forward_velocity          # move forward
       + alive_bonus              # stay upright (torso height > 0.8m)
       - 0.1 * control_cost      # minimize energy (don't flail)
       - 0.01 * joint_deviation  # smooth motion
```

### H100 training specs
- GPU: NVIDIA H100 80GB (we have 96GB variant)
- Training: 8192 parallel environments
- Steps: 50M environment steps
- Time: ~3-5 minutes
- Output: JAX model parameters → export to ONNX (~5MB file)

## Dependencies to Install on H100

```bash
pip install mujoco-playground  # or clone from GitHub
pip install jax[cuda12]
pip install mujoco-mjx
pip install onnxruntime-gpu
pip install brax
```

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| MuJoCo Playground humanoid model differs from our template | Use their model as-is for locomotion, keep ours for ragdoll |
| ONNX export not straightforward | Fall back to JAX JIT inference directly |
| Policy doesn't generalize to different gravity | Train separate policies per environment, or use domain randomization |
| Policy file too large to load per-request | Load once at startup, reuse across requests |

## Training Results (2026-03-28)

**Completed on H100 (96GB VRAM) in 314 seconds (~5 minutes).**

```
Steps:          0 | Reward:     90.5   (falling over)
Steps:  5,017,600 | Reward:    584.9   (learning to stay upright)
Steps: 10,035,200 | Reward:  3,104.0   (walking forward)
Steps: 15,052,800 | Reward:  3,124.7   (refining gait)
Steps: 20,070,400 | Reward:  5,090.9   (solid walking policy)
```

- **Policy file:** `backend/policies/humanoid_walk.pkl` (1.3 MB)
- **Framework:** Brax PPO with generalized physics pipeline
- **Config:** 2048 parallel environments, 20M timesteps, batch_size=512
- **H100 server:** `ssh -i $SSH_KEY -p $SSH_PORT $SSH_USER@$GPU_SERVER_IP`
- **Training script:** `/mnt/chris-premium/simgen/train_walk_v2.py`

### Integration status

The trained policy uses Brax's built-in humanoid model (which is different from our
custom `humanoid.xml` template). To integrate:

1. **Option A (simpler):** Use Brax's humanoid model directly for locomotion prompts.
   Replace our passive ragdoll with Brax's model + policy for any walking/running prompt.
   Keep our ragdoll template for passive physics (falling, getting pushed).

2. **Option B (harder):** Retrain on our custom humanoid XML using MJX directly
   (not Brax's built-in model). This requires writing a custom MJX training loop.

**Recommended:** Option A for v1. Ship it, validate with creators, then invest in
Option B if the model mismatch causes issues.

### Integration completed (2026-03-28/29)

**Architecture:** Split rendering across local Mac and H100 GPU.

```
Creator prompt "a person walking"
        ↓
Local backend (Mac, :8000) detects locomotion keywords in prompt
        ↓
Sends render request via SSH tunnel → H100 GPU server (:8100)
        ↓
H100 runs Brax PPO policy (8100 env steps) → MuJoCo renders frames → ffmpeg encodes MP4
        ↓
MP4 streamed back to local backend → served to frontend
        ↓
Non-walking prompts (pendulum, ball, etc.) still render locally on Mac CPU
```

**Files created/modified:**
- `backend/locomotion.py` — detects locomotion keywords, returns policy name
- `backend/renderer.py` — added `_render_on_gpu_server()` for H100 rendering, fallback chain: GPU server → local Brax → passive physics
- `backend/physics_rules.py` — updated: humanoid CAN now walk/run/stride
- `backend/main.py` — wires locomotion detection into generate endpoint
- H100: `/mnt/chris-premium/simgen/gpu_render_server.py` — FastAPI server that loads policy, runs simulation, renders frames, encodes MP4

**How to run:**
```bash
# 1. Start SSH tunnel to H100 (in a separate terminal)
ssh -i $SSH_KEY -p $SSH_PORT -N -L 8100:localhost:8100 $SSH_USER@$GPU_SERVER_IP

# 2. Start GPU render server on H100 (already running, but if needed)
ssh -i $SSH_KEY -p $SSH_PORT $SSH_USER@$GPU_SERVER_IP "cd /mnt/chris-premium/simgen && nohup python3 gpu_render_server.py > gpu_server.log 2>&1 &"

# 3. Start local backend
ANTHROPIC_API_KEY=... python3 -m uvicorn backend.main:app --port 8000

# 4. Start frontend
cd frontend && npm run dev
```

**Why the split architecture:**
- Python 3.9 on Mac can't import Brax/MJX (needs 3.10+ for union type syntax)
- H100 has Python 3.10+, CUDA, and 96GB VRAM — the right place for GPU rendering
- SSH tunnel is secure and doesn't require opening Azure firewall ports
- Passive physics (pendulum, ball, cartpole) still render locally — fast, no GPU needed

## Success Criteria

- [ ] Humanoid walks forward for 15 seconds without falling
- [ ] Walking looks natural (not shuffling or jerking)
- [ ] Works across Earth, Moon, Mars gravity
- [ ] Creator can prompt "a person walking" and get a walking simulation
- [ ] Total generation time stays under 2 minutes

## Resources

- [MuJoCo Playground GitHub](https://github.com/google-deepmind/mujoco_playground)
- [MuJoCo Playground Paper](https://arxiv.org/html/2502.08844v1)
- [Brax: Differentiable Physics Engine](https://github.com/google/brax)
- [MJX Documentation](https://mujoco.readthedocs.io/en/stable/mjx.html)
- [LocoMuJoCo Benchmark](https://github.com/robfiras/loco-mujoco)
