"""GPU render server — runs on H100, renders locomotion policies to MP4.
Supports: humanoid_walk, humanoid_run, hopper.
JIT warms up all policies on startup so first request is fast."""

import os
import pickle
import subprocess
import tempfile
import time
import threading

import jax
import jax.numpy as jnp
import mujoco
import numpy as np
from brax import envs
from brax.training.agents.ppo import networks as ppo_nets
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

app = FastAPI(title="simgen-gpu-renderer")

POLICIES_DIR = "/mnt/chris-premium/simgen/policies"
_cache = {}
_render_lock = threading.Lock()

THEMES = {
    "studio": {"floor": [0.15, 0.15, 0.17], "sky1": [0.03, 0.03, 0.05], "sky2": [0.08, 0.08, 0.12]},
    "outdoor": {"floor": [0.35, 0.42, 0.28], "sky1": [0.45, 0.65, 0.85], "sky2": [0.75, 0.85, 0.95]},
    "industrial": {"floor": [0.3, 0.3, 0.32], "sky1": [0.2, 0.2, 0.22], "sky2": [0.35, 0.35, 0.38]},
    "desert": {"floor": [0.65, 0.55, 0.38], "sky1": [0.85, 0.6, 0.35], "sky2": [0.95, 0.8, 0.6]},
    "night": {"floor": [0.1, 0.1, 0.12], "sky1": [0.02, 0.02, 0.06], "sky2": [0.05, 0.05, 0.15]},
    "snow": {"floor": [0.85, 0.87, 0.9], "sky1": [0.6, 0.65, 0.7], "sky2": [0.8, 0.82, 0.85]},
}



def _load_policy(name):
    if name in _cache:
        return _cache[name]

    path = os.path.join(POLICIES_DIR, f"{name}.pkl")
    with open(path, "rb") as f:
        data = pickle.load(f)

    env_name = data.get("env_name", "humanoid")
    backend = data.get("backend", "generalized")

    if backend == "spring":
        env = envs.get_environment(env_name, backend="spring")
    else:
        env = envs.get_environment(env_name)

    network = ppo_nets.make_ppo_networks(
        observation_size=env.observation_size,
        action_size=env.action_size,
    )
    make_inference = ppo_nets.make_inference_fn(network)
    inference_fn = make_inference(data["params"])
    jit_inference = jax.jit(inference_fn)
    jit_step = jax.jit(env.step)
    jit_reset = jax.jit(env.reset)

    _cache[name] = {
        "env": env,
        "inference": jit_inference,
        "step": jit_step,
        "reset": jit_reset,
    }
    return _cache[name]


def _warmup_policy(name):
    """Run one step to trigger JIT compilation."""
    try:
        print(f"  Warming up {name}...", flush=True)
        t0 = time.time()
        policy = _load_policy(name)
        rng = jax.random.PRNGKey(0)
        state = policy["reset"](rng)
        act_rng, rng = jax.random.split(rng)
        act, _ = policy["inference"](state.obs, act_rng)
        state = policy["step"](state, act)
        # Force computation
        _ = float(state.reward)
        print(f"  {name}: warmed up in {time.time()-t0:.1f}s", flush=True)
    except Exception as e:
        print(f"  {name}: warmup failed: {e}", flush=True)


class RenderRequest(BaseModel):
    policy_name: str
    params: dict = {}
    duration: float = 10.0
    fps: int = 30
    width: int = 640
    height: int = 480
    theme: str = "studio"


@app.on_event("startup")
def startup():
    print("\nWarming up JIT for all policies...", flush=True)
    for f in os.listdir(POLICIES_DIR):
        if f.endswith(".pkl"):
            _warmup_policy(f.replace(".pkl", ""))
    print("Warmup complete!\n", flush=True)


@app.post("/render")
def render(req: RenderRequest):
    with _render_lock:
        return _do_render(req)


def _do_render(req: RenderRequest):
    t0 = time.time()

    try:
        policy = _load_policy(req.policy_name)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"Policy load failed: {e}"})

    env = policy["env"]
    jit_inference = policy["inference"]
    jit_step = policy["step"]
    jit_reset = policy["reset"]

    gravity_scale = req.params.get("gravity", 9.81) / 9.81
    seed = abs(hash(str(req.params))) % (2**31)

    rng = jax.random.PRNGKey(seed)
    state = jit_reset(rng)

    steps_per_frame = max(1, int(1.0 / (req.fps * env.dt)))
    total_frames = int(req.duration * req.fps)

    qpos_list = []
    qvel_list = []

    for _ in range(total_frames):
        for _ in range(steps_per_frame):
            act_rng, rng = jax.random.split(rng)
            act, _ = jit_inference(state.obs, act_rng)
            state = jit_step(state, act)
        ps = state.pipeline_state
        qpos_list.append(np.array(jax.device_get(ps.q)))
        qvel_list.append(np.array(jax.device_get(ps.qd)))

    sim_time = time.time() - t0
    print(f"Sim ({req.policy_name}): {sim_time:.1f}s", flush=True)

    # Render with tracking camera
    mj_model = env.sys.mj_model
    mj_data = mujoco.MjData(mj_model)
    mj_model.opt.gravity[2] = -9.81 * gravity_scale

    renderer = mujoco.Renderer(mj_model, height=req.height, width=req.width)

    cam = mujoco.MjvCamera()
    cam.type = mujoco.mjtCamera.mjCAMERA_TRACKING
    cam.trackbodyid = 1
    cam.distance = 3.0
    cam.azimuth = 150
    cam.elevation = -15
    cam.lookat[:] = [0, 0, 1.0]

    frames = []
    for qpos, qvel in zip(qpos_list, qvel_list):
        nq = min(len(qpos), mj_model.nq)
        nv = min(len(qvel), mj_model.nv)
        mj_data.qpos[:nq] = qpos[:nq]
        mj_data.qvel[:nv] = qvel[:nv]
        mujoco.mj_forward(mj_model, mj_data)
        renderer.update_scene(mj_data, camera=cam)
        frame = renderer.render()
        frames.append(frame.copy())

    renderer.close()

    # Encode MP4
    tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
    tmp.close()

    h, w = frames[0].shape[:2]
    cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo", "-vcodec", "rawvideo",
        "-s", f"{w}x{h}", "-pix_fmt", "rgb24",
        "-r", str(req.fps), "-i", "pipe:",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-preset", "ultrafast", "-crf", "23",
        "-movflags", "+faststart",
        tmp.name,
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    for frame in frames:
        proc.stdin.write(frame.tobytes())
    proc.stdin.close()
    proc.wait()

    if proc.returncode != 0:
        stderr = proc.stderr.read().decode()
        return JSONResponse(status_code=500, content={"error": f"ffmpeg: {stderr[-500:]}"})

    total_time = time.time() - t0
    fsize = os.path.getsize(tmp.name)
    print(f"Total: {total_time:.1f}s | {fsize/1024:.0f} KB", flush=True)

    return FileResponse(tmp.name, media_type="video/mp4", filename="simulation.mp4")


@app.get("/health")
def health():
    return {
        "status": "ok",
        "gpu": str(jax.devices()),
        "policies": os.listdir(POLICIES_DIR),
        "cached": list(_cache.keys()),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8100)
