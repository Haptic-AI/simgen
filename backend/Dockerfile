FROM python:3.12-slim

WORKDIR /app

# MuJoCo needs GL libs for headless rendering
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx libosmesa6 libglfw3 curl ffmpeg \
    && rm -rf /var/lib/apt/lists/*

ENV MUJOCO_GL=osmesa

RUN pip install --no-cache-dir \
    fastapi uvicorn[standard] mujoco numpy Pillow anthropic imageio av

# Copy entire project (backend imports use backend.* prefix)
COPY backend/ ./backend/

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
