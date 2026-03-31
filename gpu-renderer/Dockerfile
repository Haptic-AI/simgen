FROM nvidia/cuda:12.4.0-runtime-ubuntu22.04

WORKDIR /app

# System deps for MuJoCo EGL rendering + ffmpeg
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.11 python3.11-dev python3-pip python3.11-venv \
    libegl1-mesa-dev libgl1-mesa-glx libgles2-mesa-dev \
    ffmpeg curl git \
    && rm -rf /var/lib/apt/lists/*

# Make python3.11 the default
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1 \
    && python3 -m ensurepip --upgrade

ENV MUJOCO_GL=egl

# Install Python deps
RUN python3 -m pip install --no-cache-dir \
    fastapi uvicorn[standard] \
    mujoco mujoco-mjx \
    jax[cuda12] \
    brax numpy Pillow

# Copy the render server + policies
COPY gpu_render_server.py .
COPY policies/ ./policies/

EXPOSE 8100

CMD ["python3", "-m", "uvicorn", "gpu_render_server:app", "--host", "0.0.0.0", "--port", "8100"]
