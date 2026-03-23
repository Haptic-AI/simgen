#!/bin/bash
# MuJoCo Cloud - VM Startup Script
# Installs NVIDIA drivers, MuJoCo, JAX, Jupyter on a fresh Ubuntu 22.04 VM
set -euo pipefail

LOG_FILE="/var/log/mjcloud-setup.log"
SETUP_MARKER="/opt/mjcloud/.setup-complete"

exec > >(tee -a "$LOG_FILE") 2>&1
echo "=== MuJoCo Cloud setup started at $(date) ==="

# Skip if already set up
if [ -f "$SETUP_MARKER" ]; then
    echo "Setup already complete, starting services..."
    systemctl start jupyter
    exit 0
fi

mkdir -p /opt/mjcloud

# System updates
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y python3-pip python3-venv git wget curl tmux htop

# Install NVIDIA drivers + CUDA toolkit
# GCP L4 instances use the latest NVIDIA drivers
apt-get install -y linux-headers-$(uname -r)
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
distribution=$(. /etc/os-release; echo $ID$VERSION_ID)

# Install NVIDIA driver
apt-get install -y nvidia-driver-535 nvidia-utils-535

# Install CUDA toolkit 12.2
wget -q https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-keyring_1.1-1_all.deb
dpkg -i cuda-keyring_1.1-1_all.deb
apt-get update -y
apt-get install -y cuda-toolkit-12-2

# Set up environment
cat >> /etc/environment << 'ENVEOF'
MUJOCO_GL=egl
CUDA_HOME=/usr/local/cuda-12.2
PATH=/usr/local/cuda-12.2/bin:$PATH
LD_LIBRARY_PATH=/usr/local/cuda-12.2/lib64:$LD_LIBRARY_PATH
ENVEOF

export MUJOCO_GL=egl
export CUDA_HOME=/usr/local/cuda-12.2
export PATH=/usr/local/cuda-12.2/bin:$PATH
export LD_LIBRARY_PATH=/usr/local/cuda-12.2/lib64:${LD_LIBRARY_PATH:-}

# Create mjcloud Python environment
python3 -m venv /opt/mjcloud/venv
source /opt/mjcloud/venv/bin/activate

# Install MuJoCo and simulation stack
pip install --upgrade pip
pip install \
    mujoco>=3.2 \
    mujoco-mjx>=3.2 \
    jax[cuda12]==0.4.35 \
    flax \
    optax \
    dm-control \
    gymnasium[mujoco] \
    jupyterlab \
    ipywidgets \
    matplotlib \
    mediapy \
    tqdm \
    rich

# Clone MuJoCo playground examples
git clone --depth 1 https://github.com/google-deepmind/mujoco_playground.git /opt/mjcloud/mujoco_playground 2>/dev/null || true

# Create welcome notebook
mkdir -p /opt/mjcloud/notebooks
cat > /opt/mjcloud/notebooks/welcome.ipynb << 'NBEOF'
{
 "cells": [
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "# Welcome to MuJoCo Cloud\n",
    "\n",
    "Your GPU-accelerated MuJoCo simulation environment is ready.\n",
    "\n",
    "## Quick Start"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "import mujoco\n",
    "import numpy as np\n",
    "print(f'MuJoCo version: {mujoco.__version__}')\n",
    "\n",
    "# Load the humanoid model\n",
    "model = mujoco.MjModel.from_xml_path(mujoco.util.MODEL_PATH + '/humanoid/humanoid.xml')\n",
    "data = mujoco.MjData(model)\n",
    "\n",
    "# Step the simulation\n",
    "for i in range(1000):\n",
    "    mujoco.mj_step(model, data)\n",
    "\n",
    "print(f'Simulated 1000 steps. Final time: {data.time:.3f}s')\n",
    "print(f'Center of mass height: {data.subtree_com[0][2]:.3f}m')"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "# Render a frame\n",
    "import mediapy\n",
    "\n",
    "renderer = mujoco.Renderer(model, height=480, width=640)\n",
    "mujoco.mj_forward(model, data)\n",
    "renderer.update_scene(data)\n",
    "mediapy.show_image(renderer.render())"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "# Check GPU availability for MJX (JAX-accelerated MuJoCo)\n",
    "import jax\n",
    "print(f'JAX devices: {jax.devices()}')\n",
    "print(f'GPU available: {any(d.platform == \"gpu\" for d in jax.devices())}')"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## Next Steps\n",
    "\n",
    "- Explore `/opt/mjcloud/mujoco_playground/` for advanced examples\n",
    "- Try MJX for GPU-accelerated simulation (millions of steps/sec)\n",
    "- Run `gymnasium` environments with MuJoCo backend\n",
    "- Check `/opt/mjcloud/examples/` for starter scripts"
   ]
  }
 ],
 "metadata": {
  "kernelspec": {
   "display_name": "Python 3",
   "language": "python",
   "name": "python3"
  },
  "language_info": {
   "name": "python",
   "version": "3.10.12"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 4
}
NBEOF

# Copy example scripts
mkdir -p /opt/mjcloud/examples
cat > /opt/mjcloud/examples/humanoid_walk.py << 'PYEOF'
"""MuJoCo Humanoid Walking Example - GPU Accelerated with MJX."""
import mujoco
from mujoco import mjx
import jax
import jax.numpy as jnp
import time

def main():
    # Load humanoid model
    model = mujoco.MjModel.from_xml_path(
        mujoco.util.MODEL_PATH + "/humanoid/humanoid.xml"
    )
    data = mujoco.MjData(model)

    # CPU simulation benchmark
    start = time.time()
    n_steps = 10_000
    for _ in range(n_steps):
        mujoco.mj_step(model, data)
    cpu_time = time.time() - start
    print(f"CPU: {n_steps} steps in {cpu_time:.2f}s ({n_steps/cpu_time:.0f} steps/sec)")

    # GPU simulation with MJX
    mjx_model = mjx.put_model(model)
    mjx_data = mjx.put_data(model, data)

    jit_step = jax.jit(mjx.step)

    # Warmup
    mjx_data = jit_step(mjx_model, mjx_data)
    jax.block_until_ready(mjx_data.qpos)

    # Benchmark
    start = time.time()
    for _ in range(n_steps):
        mjx_data = jit_step(mjx_model, mjx_data)
    jax.block_until_ready(mjx_data.qpos)
    gpu_time = time.time() - start
    print(f"GPU: {n_steps} steps in {gpu_time:.2f}s ({n_steps/gpu_time:.0f} steps/sec)")
    print(f"Speedup: {cpu_time/gpu_time:.1f}x")

if __name__ == "__main__":
    main()
PYEOF

# Configure Jupyter Lab
mkdir -p /root/.jupyter
cat > /root/.jupyter/jupyter_lab_config.py << 'JCEOF'
c.ServerApp.ip = '0.0.0.0'
c.ServerApp.port = 8888
c.ServerApp.open_browser = False
c.ServerApp.allow_root = True
c.ServerApp.token = ''
c.ServerApp.password = ''
c.ServerApp.allow_origin = '*'
c.ServerApp.root_dir = '/opt/mjcloud/notebooks'
JCEOF

# Create systemd service for Jupyter
cat > /etc/systemd/system/jupyter.service << 'SVCEOF'
[Unit]
Description=MuJoCo Cloud Jupyter Lab
After=network.target

[Service]
Type=simple
ExecStart=/opt/mjcloud/venv/bin/jupyter lab --config=/root/.jupyter/jupyter_lab_config.py
Environment=MUJOCO_GL=egl
Environment=PATH=/opt/mjcloud/venv/bin:/usr/local/cuda-12.2/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
Environment=LD_LIBRARY_PATH=/usr/local/cuda-12.2/lib64
WorkingDirectory=/opt/mjcloud/notebooks
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SVCEOF

systemctl daemon-reload
systemctl enable jupyter
systemctl start jupyter

# Mark setup complete
touch "$SETUP_MARKER"
echo "=== MuJoCo Cloud setup completed at $(date) ==="
