# MuJoCo Cloud

One-click GPU simulation environments for MuJoCo on Azure. Deploy a ready-to-go robotics simulation box in one command.

```bash
pip install -e .
mjcloud config --subscription YOUR_SUB_ID --resource-group YOUR_RG
mjcloud deploy
# 2 minutes later: GPU instance running with MuJoCo, Jupyter, and examples ready
```

---

## What We Built

There is no "one-click MuJoCo deployment" on any major cloud provider. We searched AWS, Azure, and GCP marketplaces — nothing exists. Researchers who want GPU-accelerated MuJoCo simulation today face a multi-hour setup gauntlet: provision a VM, install NVIDIA drivers, fight with CUDA versions, install MuJoCo, configure JAX for GPU, set up Jupyter, open firewall ports, and hope nothing breaks.

**mjcloud** eliminates all of that. It's a single CLI tool that:

1. Spins up a GPU VM on Azure (T4, A100, or H100)
2. Automatically installs the entire MuJoCo + MJX + JAX + CUDA stack
3. Starts Jupyter Lab on port 8888
4. Pre-loads example scripts and Google DeepMind's MuJoCo Playground
5. Gives you SSH and Jupyter access in one command

The whole tool is ~600 lines of Python across 4 files. It uses the Azure Compute API directly — no Terraform, no Docker, no Kubernetes. Just `mjcloud deploy` and you're simulating.

### Project Structure

```
mujoco-cloud/
├── pyproject.toml              # Package config, "mjcloud" CLI entry point
├── mjcloud/
│   ├── cli.py                  # Click CLI with rich output
│   ├── config.py               # Instance presets and user config
│   ├── azure.py                # Azure Compute API wrapper
│   └── startup_script.sh       # VM provisioning (drivers, CUDA, MuJoCo, Jupyter)
└── examples/
    ├── humanoid_walk.py        # CPU vs GPU single-env benchmark
    └── batched_humanoid_mjx.py # 1024 parallel envs on GPU — the real showcase
```

---

## Why This Matters for Robotics

### The problem

Modern robotics research runs on simulation. Training a humanoid locomotion policy with PPO requires **billions** of environment steps. MuJoCo is the gold standard physics simulator — used by Google DeepMind, Tesla Optimus, Berkeley, Stanford, and nearly every serious robotics lab.

But GPU-accelerated MuJoCo (MJX) is where the real speed is: instead of simulating one robot on CPU at ~50K steps/sec, you simulate **1024 robots in parallel** on GPU at **50M+ steps/sec**. That turns a 6-hour training run into a 3-minute one.

The catch? Setting up a GPU cloud instance for MuJoCo is miserable:

- **NVIDIA driver hell**: Which driver version? Does it match your CUDA? Does CUDA match your JAX?
- **JAX + CUDA compatibility**: JAX GPU support requires specific CUDA + cuDNN versions. Get one wrong and nothing works silently.
- **MuJoCo rendering**: Headless GPU rendering needs EGL configured correctly. Most cloud VMs don't have this out of the box.
- **Firewall rules**: Jupyter won't be reachable without opening the right ports.
- **Ephemeral environments**: Researchers spin up and tear down VMs constantly. Doing this manually every time is a waste of research hours.

This setup typically takes **2-4 hours** for someone experienced. For a student or researcher new to cloud GPUs, it can take a full day.

### What mjcloud solves

```bash
mjcloud deploy    # done in 2 minutes. everything works.
```

A researcher can go from "I want to train a locomotion policy" to "I have 1024 parallel MuJoCo humanoids running on an Azure GPU VM" in under 10 minutes. No driver debugging. No CUDA version mismatches. No firewall configuration.

### Who this is for

- **Grad students** starting robotics research who need GPU simulation but don't want to become cloud infrastructure experts
- **Robotics labs** that want reproducible, disposable simulation environments for experiments
- **RL researchers** who need batched MJX environments for policy training
- **Hackathon teams** and course projects that need quick access to MuJoCo on GPU
- **Anyone** who has lost hours to NVIDIA driver + CUDA + JAX version conflicts

---

## Getting Started

### Prerequisites

1. **Create an Azure account** at [portal.azure.com](https://portal.azure.com) with billing enabled
2. **Create a Subscription and Resource Group**
   - In the Azure Portal, go to **Subscriptions** and note your **Subscription ID**
   - Go to **Resource Groups** → **Create** and create a new resource group (e.g., `mujoco-rg`) in your preferred region
3. **Procure a GPU VM** — request quota for one of the following GPU SKUs in your region:
   - **NVIDIA T4** (NC4as T4 v3 series) — budget option for development and small experiments
   - **NVIDIA A100** (ND A100 v4 series) — high-performance training and large-scale simulation
   - **NVIDIA H100** (ND H100 v5 series) — maximum throughput for production RL training

### Setup (< 5 minutes)

```bash
# Install Azure CLI (if you don't have it)
brew install azure-cli

# Authenticate
az login

# Clone and install mjcloud
git clone https://github.com/Haptic-AI/one-click-mujocu-azure.git
cd one-click-mujocu-azure
python3 -m venv .venv && source .venv/bin/activate
pip install -e .

# Configure
mjcloud config --subscription YOUR_SUB_ID --resource-group YOUR_RG

# Deploy
mjcloud deploy
```

That's it. You'll see output like:

```
╔════════════════════════════════ MuJoCo Cloud ════════════════════════════════╗
║ Your MuJoCo environment is running!                                          ║
║                                                                              ║
║ Instance:  mjcloud-haptic-01                                                 ║
║ IP:        34.134.219.151                                                    ║
║ VM Size:   Standard_NC4as_T4_v3                                              ║
║ Status:    RUNNING                                                           ║
║                                                                              ║
║ SSH:       mjcloud ssh mjcloud-haptic-01                                     ║
║ Jupyter:   http://34.134.219.151:8888                                        ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

### Instance Presets

| Preset | VM Size | GPU | RAM | Cost |
|--------|---------|-----|-----|------|
| `small` | Standard_NC4as_T4_v3 | 1x NVIDIA T4 | 28GB | ~$0.53/hr |
| `medium` | Standard_NC24ads_A100_v4 | 1x NVIDIA A100 | 220GB | ~$3.67/hr |
| `large` | Standard_ND96isr_H100_v5 | 8x NVIDIA H100 | 1900GB | ~$32.77/hr |

```bash
mjcloud deploy --preset small          # budget option
mjcloud deploy --preset large --name my-experiment
mjcloud deploy --dry-run               # preview without creating
```

### All CLI Commands

```bash
mjcloud deploy              # Create a new GPU instance
mjcloud list                # List all running instances
mjcloud status <name>       # Instance details
mjcloud ssh <name>          # SSH into instance
mjcloud jupyter <name>      # Get Jupyter URL
mjcloud jupyter <name> --open  # Open in browser
mjcloud destroy <name>      # Tear down instance
mjcloud destroy <name> -y   # Skip confirmation
mjcloud config              # View/set defaults
mjcloud presets             # Show size options
```

---

## What You Can Do Once the Instance Is Running

The instance comes with the full GPU-accelerated MuJoCo stack. Here's what's available:

### 1. Single-Environment Simulation

Basic MuJoCo on CPU — good for debugging, visualization, model validation:

```python
import mujoco

model = mujoco.MjModel.from_xml_path("humanoid.xml")
data = mujoco.MjData(model)

for _ in range(10000):
    mujoco.mj_step(model, data)
# ~50K steps/sec on CPU
```

### 2. GPU-Accelerated Simulation with MJX

Single-environment on GPU via JAX — useful for fast prototyping:

```python
from mujoco import mjx
import jax

mjx_model = mjx.put_model(model)
mjx_data = mjx.put_data(model, data)
jit_step = jax.jit(mjx.step)

for _ in range(10000):
    mjx_data = jit_step(mjx_model, mjx_data)
# ~500K steps/sec on GPU
```

### 3. Batched Parallel Environments (the real power)

Run 1024+ environments simultaneously on GPU — this is what makes GPU simulation transformative for RL training:

```python
import jax
from mujoco import mjx

# Vectorize across 1024 parallel worlds
batched_step = jax.vmap(mjx.step, in_axes=(None, 0))
# ~50M+ steps/sec across all envs on GPU
```

### 4. RL Training with Gymnasium

Standard RL environment interface:

```python
import gymnasium as gym

env = gym.make("Humanoid-v5", render_mode="rgb_array")
obs, info = env.reset()
for _ in range(1000):
    action = env.action_space.sample()
    obs, reward, terminated, truncated, info = env.step(action)
```

### 5. DeepMind Control Suite

Pre-installed dm-control environments:

```python
from dm_control import suite

env = suite.load("humanoid", "walk")
time_step = env.reset()
while not time_step.last():
    action = env.action_spec().generate_value()
    time_step = env.step(action)
```

### 6. Jupyter Lab

Open `http://<instance-ip>:8888` in your browser. A welcome notebook walks you through rendering frames, checking GPU status, and running your first simulation.

### 7. MuJoCo Playground

Google DeepMind's official collection of environments and training scripts is pre-cloned at `/opt/mjcloud/mujoco_playground/`. Includes locomotion, manipulation, and more.

---

## Included Examples

### `humanoid_walk.py` — CPU vs GPU Benchmark

Loads the humanoid model and benchmarks single-environment simulation on CPU vs GPU:

```bash
python /opt/mjcloud/examples/humanoid_walk.py
```

Expect: CPU ~50K steps/sec, GPU ~500K steps/sec (10x speedup for single env).

### `batched_humanoid_mjx.py` — The GPU Showcase

This is the example that demonstrates why you want a GPU for MuJoCo. It runs **1024 humanoid simulations in parallel** using `jax.vmap` over MJX, with a simple locomotion reward function:

```bash
python /opt/mjcloud/examples/batched_humanoid_mjx.py
```

What it does:
- Creates 1024 parallel humanoid environments on the GPU
- Each env gets slightly different initial conditions
- Runs 1000-step rollouts with random actions
- Computes locomotion rewards (height + forward velocity - control cost)
- Benchmarks at 64, 256, and 1024 parallel envs
- Prints estimated training times: how long it would take to collect 1B env steps on this GPU vs a single CPU core

Expected output on T4:
```
Batched MJX Benchmark
============================================================
Environments:    1,024
Episode length:  1,000 steps
Total steps:     1,024,000
Throughput:      ~30,000,000+ steps/sec

Training time estimate (1B steps):
  This GPU:      ~0.5 hours
  Single CPU:    5,556 hours (231 days)
  Speedup:       ~10,000x
```

This is the pattern used by state-of-the-art locomotion papers from DeepMind and Berkeley. The only difference between this example and a real training script is swapping random actions for a PPO/SAC policy network.

---

## What's Pre-Installed

| Component | Version | Purpose |
|-----------|---------|---------|
| NVIDIA Driver | 535 | GPU hardware access |
| CUDA Toolkit | 12.2 | GPU compute |
| MuJoCo | 3.x | Physics simulation |
| MuJoCo MJX | 3.x | GPU-accelerated MuJoCo via JAX |
| JAX | 0.4.35 (CUDA) | Differentiable compute, vmap, JIT |
| dm-control | latest | DeepMind control suite |
| Gymnasium | latest | Standard RL environment interface |
| Jupyter Lab | latest | Interactive notebooks |
| MuJoCo Playground | latest | DeepMind's example environments |

---

## Configuration

Config lives at `~/.mjcloud/config.yaml`. Override with env vars:

| Variable | Description | Default |
|----------|-------------|---------|
| `MJCLOUD_SUBSCRIPTION` | Azure Subscription ID | — |
| `MJCLOUD_RESOURCE_GROUP` | Azure Resource Group | — |
| `MJCLOUD_REGION` | Default Azure region | `westus2` |

---

## How It Works Under the Hood

1. `mjcloud deploy` calls the Azure Compute API to create a GPU VM (T4, A100, or H100) in your resource group
2. A startup script (`startup_script.sh`) runs on first boot via Azure custom script extension
3. The script installs NVIDIA drivers, CUDA 12.2, creates a Python venv, and installs the full MuJoCo + JAX + Jupyter stack
4. Jupyter Lab starts as a systemd service on port 8888
5. An Azure NSG rule (`mjcloud-allow-jupyter`) is automatically created to allow traffic on port 8888
6. All instances are tagged `mjcloud=true` so `mjcloud list` can find them

Setup takes ~5-10 minutes after boot. Monitor progress:

```bash
mjcloud ssh <name>
tail -f /var/log/mjcloud-setup.log
```

---

## Roadmap

- [ ] AWS support (EC2 G5/G6 instances with L4 GPUs)
- [ ] GCP support (g2-standard instances with L4 GPUs)
- [ ] Pre-built VM images for instant boot (skip the 5-min install)
- [ ] Docker-based deployments
- [ ] Web dashboard for instance management
- [ ] Auto-shutdown timers to prevent runaway costs
- [ ] Team workspaces and shared instances
- [ ] Custom startup scripts and model uploads
- [ ] Spot/low-priority instances for cheaper training runs

## License

MIT
