# MuJoCo Cloud

One-click GPU simulation environments for MuJoCo. No one-click MuJoCo cloud deployment exists on any major provider today — this project fills that gap.

`mjcloud` is a CLI tool that spins up an NVIDIA L4 GPU instance on GCP with MuJoCo, Jupyter, and example models pre-installed. Think "Vercel for MuJoCo simulation" — deploy a ready-to-go simulation environment in one command.

## Project Structure

```
mujoco-cloud/
├── pyproject.toml          # Package config, "mjcloud" CLI entry point
├── setup.py                # Compat shim for older pip versions
├── README.md
├── mjcloud/
│   ├── __init__.py
│   ├── cli.py              # Click CLI: deploy, list, ssh, jupyter, destroy, status, config, presets
│   ├── config.py           # Presets (small/medium/large), config file (~/.mjcloud/config.yaml)
│   ├── gcp.py              # GCP Compute Engine: create/list/delete instances, firewall rules
│   └── startup_script.sh   # VM provisioning: NVIDIA drivers, CUDA, MuJoCo, MJX, JAX, Jupyter
└── examples/
    └── humanoid_walk.py    # CPU vs GPU benchmark (pre-loaded on the VM)
```

## Quickstart

```bash
# Install
pip install -e .

# Configure your GCP project
mjcloud config --project YOUR_GCP_PROJECT_ID

# Deploy a simulation environment
mjcloud deploy

# Once running, open Jupyter or SSH in
mjcloud jupyter <instance-name> --open
mjcloud ssh <instance-name>

# Clean up when done
mjcloud destroy <instance-name>
```

## Prerequisites

1. A GCP account with billing enabled
2. `gcloud` CLI installed and authenticated (`gcloud auth application-default login`)
3. GPU quota for `g2-standard-*` instances in your project

## Instance Presets

| Preset | Machine | GPU | RAM | Approx Cost |
|--------|---------|-----|-----|-------------|
| small | g2-standard-4 | 1x L4 | 16GB | ~$0.70/hr |
| medium | g2-standard-8 | 1x L4 | 32GB | ~$0.98/hr |
| large | g2-standard-16 | 1x L4 | 64GB | ~$1.53/hr |

```bash
mjcloud deploy --preset large
mjcloud presets  # show all presets
```

## What's Pre-Installed on Every Instance

- **MuJoCo 3.x** with native Python bindings
- **MuJoCo XLA (MJX)** for GPU-accelerated simulation (millions of steps/sec)
- **JAX** with CUDA 12.2 support
- **Jupyter Lab** on port 8888 (auto-starts as a systemd service)
- **dm-control** and **Gymnasium[mujoco]** for RL environments
- **MuJoCo Playground** examples from Google DeepMind
- A **welcome notebook** that walks through your first simulation
- **humanoid_walk.py** benchmark: CPU vs GPU comparison

## CLI Commands

```bash
mjcloud deploy              # Create a new GPU instance with MuJoCo
mjcloud deploy --preset large --name my-sim   # Customize size and name
mjcloud deploy --dry-run    # Preview without creating

mjcloud list                # List all instances
mjcloud status <name>       # Instance details
mjcloud ssh <name>          # SSH into instance (via gcloud)
mjcloud jupyter <name>      # Print Jupyter URL
mjcloud jupyter <name> --open  # Open Jupyter in browser
mjcloud destroy <name>      # Delete instance
mjcloud destroy <name> -y   # Skip confirmation

mjcloud config              # View current configuration
mjcloud config --project X  # Set GCP project
mjcloud config --zone Y     # Set default zone
mjcloud presets             # Show available instance presets
```

## Configuration

Config is stored in `~/.mjcloud/config.yaml`. Environment variable overrides:

| Variable | Description | Default |
|----------|-------------|---------|
| `MJCLOUD_PROJECT` | GCP project ID | — |
| `GOOGLE_CLOUD_PROJECT` | GCP project ID (fallback) | — |
| `MJCLOUD_ZONE` | Default zone | `us-central1-a` |

## How It Works

1. `mjcloud deploy` creates a GCE `g2-standard-8` instance with an NVIDIA L4 GPU
2. A startup script (`startup_script.sh`) runs on first boot:
   - Installs NVIDIA drivers (535) + CUDA 12.2
   - Creates a Python venv at `/opt/mjcloud/venv`
   - Installs MuJoCo, MJX, JAX (CUDA), dm-control, Gymnasium, Jupyter
   - Clones MuJoCo Playground examples
   - Creates a welcome Jupyter notebook
   - Starts Jupyter Lab as a systemd service on port 8888
3. A firewall rule (`mjcloud-allow-jupyter`) opens port 8888 for your instances
4. All instances are labeled `mjcloud=true` for easy tracking

Setup takes ~5-10 minutes after the VM boots. Monitor progress:

```bash
mjcloud ssh <name>
tail -f /var/log/mjcloud-setup.log
```

## Roadmap

- [ ] AWS support (EC2 G5/G6 instances)
- [ ] Azure support
- [ ] Docker-based deployments for faster boot times
- [ ] Pre-built VM images (skip the 5-min install)
- [ ] Web dashboard for managing instances
- [ ] Cost estimation and auto-shutdown timers
- [ ] Team/org support with shared instances
- [ ] Custom startup scripts and model uploads

## License

MIT
