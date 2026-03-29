"""MuJoCo simulation renderer — XML template → MP4 video.

Supports two rendering modes:
1. Passive physics (ragdoll) — our XML templates with parameter substitution
2. Policy-controlled (locomotion) — trained Brax PPO policy driving joint torques
"""

import os
import re
import shutil
import subprocess

import mujoco
import numpy as np

from backend.templates import TEMPLATE_SCHEMAS, get_template_xml

VIDEO_DIR = "/tmp/mjsim_videos"
WIDTH = 640
HEIGHT = 480
FPS = 30

os.makedirs(VIDEO_DIR, exist_ok=True)


def _apply_params(xml: str, params: dict, timestep: float) -> str:
    """Replace {{placeholder}} tokens in XML with parameter values."""
    xml = xml.replace("{{timestep}}", str(timestep))
    for key, value in params.items():
        xml = xml.replace(f"{{{{{key}}}}}", str(value))
    remaining = re.findall(r"\{\{(\w+)\}\}", xml)
    if remaining:
        raise ValueError(f"Unresolved template placeholders: {remaining}")
    return xml


def render_simulation(template_name: str, params: dict, sim_id: str, use_policy: str = None, theme: str = "studio") -> str:
    """
    Render a simulation to MP4.

    Args:
        template_name: Key in TEMPLATE_SCHEMAS
        params: Dict of parameter values
        sim_id: Unique simulation ID for the output filename
        use_policy: If set, use this locomotion policy instead of passive physics

    Returns:
        Path to the rendered MP4 file.
    """
    output_path = os.path.join(VIDEO_DIR, f"{sim_id}.mp4")

    # If a locomotion policy is requested, try GPU server first, then local
    if use_policy:
        try:
            _render_on_gpu_server(use_policy, params, output_path, theme=theme)
            return output_path
        except Exception as e1:
            print(f"GPU server rendering failed ({e1}), trying local...")
            try:
                frames = _render_with_policy(use_policy, params)
                _encode_mp4(frames, output_path)
                return output_path
            except Exception as e2:
                print(f"Local policy rendering failed ({e2}), falling back to passive physics")

    # Standard passive physics rendering
    frames = _render_passive(template_name, params)
    _encode_mp4(frames, output_path)
    return output_path


def _render_with_policy(policy_name: str, params: dict) -> list:
    """Render using a trained Brax locomotion policy."""
    import jax
    import jax.numpy as jnp
    import pickle
    from brax import envs
    from brax.training.agents.ppo import networks as ppo_nets

    policies_dir = os.path.join(os.path.dirname(__file__), "policies")
    policy_path = os.path.join(policies_dir, f"{policy_name}.pkl")

    with open(policy_path, "rb") as f:
        data = pickle.load(f)

    env_name = data.get("env_name", "humanoid")
    env = envs.get_environment(env_name)

    # Build inference function
    network = ppo_nets.make_ppo_networks(
        observation_size=env.observation_size,
        action_size=env.action_size,
    )
    make_inference = ppo_nets.make_inference_fn(network)
    inference_fn = make_inference(data["params"])
    jit_inference = jax.jit(inference_fn)
    jit_step = jax.jit(env.step)
    jit_reset = jax.jit(env.reset)

    # Run simulation with policy
    gravity_scale = params.get("gravity", 9.81) / 9.81
    duration = 15.0
    rng = jax.random.PRNGKey(int(hash(str(params)) % 2**31))
    state = jit_reset(rng)

    # Collect trajectory
    steps_per_frame = max(1, int(1.0 / (FPS * env.dt)))
    total_frames = int(duration * FPS)

    qpos_trajectory = []
    qvel_trajectory = []

    for _ in range(total_frames):
        for _ in range(steps_per_frame):
            act_rng, rng = jax.random.split(rng)
            act, _ = jit_inference(state.obs, act_rng)
            state = jit_step(state, act)

        ps = state.pipeline_state
        qpos_trajectory.append(np.array(jax.device_get(ps.q)))
        qvel_trajectory.append(np.array(jax.device_get(ps.qd)))

    # Render with MuJoCo using the Brax model
    # Get the underlying MuJoCo model from Brax
    sys = env.sys
    mj_model = sys.mj_model
    mj_data = mujoco.MjData(mj_model)

    # Apply gravity scaling
    mj_model.opt.gravity[2] = -9.81 * gravity_scale

    renderer = mujoco.Renderer(mj_model, height=HEIGHT, width=WIDTH)

    frames = []
    for qpos, qvel in zip(qpos_trajectory, qvel_trajectory):
        nq = min(len(qpos), mj_model.nq)
        nv = min(len(qvel), mj_model.nv)
        mj_data.qpos[:nq] = qpos[:nq]
        mj_data.qvel[:nv] = qvel[:nv]
        mujoco.mj_forward(mj_model, mj_data)
        renderer.update_scene(mj_data)
        frame = renderer.render()
        frames.append(frame.copy())

    renderer.close()
    return frames


def _render_on_gpu_server(policy_name: str, params: dict, output_path: str, theme: str = "studio"):
    """Send locomotion render request to the H100 GPU server via curl."""
    import json

    gpu_url = os.environ.get("GPU_RENDER_URL", "http://localhost:8100")
    req_data = json.dumps({
        "policy_name": policy_name,
        "params": params,
        "duration": 10.0,
        "fps": FPS,
        "width": WIDTH,
        "height": HEIGHT,
        "theme": theme,
    })

    result = subprocess.run(
        [
            "curl", "-s", "-f",
            "--max-time", "180",
            "--connect-timeout", "10",
            "-X", "POST",
            f"{gpu_url}/render",
            "-H", "Content-Type: application/json",
            "-d", req_data,
            "-o", output_path,
        ],
        capture_output=True,
        timeout=200,
    )

    if result.returncode != 0:
        stderr = result.stderr.decode()
        raise RuntimeError(f"GPU render failed (curl exit {result.returncode}): {stderr}")

    if not os.path.exists(output_path) or os.path.getsize(output_path) < 1000:
        raise RuntimeError("GPU render produced empty or invalid file")


def _render_passive(template_name: str, params: dict) -> list:
    """Render using passive physics (ragdoll mode)."""
    schema = TEMPLATE_SCHEMAS[template_name]
    xml_template = get_template_xml(template_name)

    full_params = {}
    for pname, pinfo in schema["params"].items():
        full_params[pname] = params.get(pname, pinfo["default"])

    timestep = schema["timestep"]
    duration = schema["sim_duration"]
    xml_str = _apply_params(xml_template, full_params, timestep)

    model = mujoco.MjModel.from_xml_string(xml_str)
    data = mujoco.MjData(model)

    # Apply initial conditions
    if template_name == "pendulum":
        joint_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, "hinge")
        if joint_id >= 0:
            data.qpos[model.jnt_qposadr[joint_id]] = full_params["initial_angle"]

    elif template_name == "cartpole":
        pole_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, "pole_hinge")
        if pole_id >= 0:
            data.qpos[model.jnt_qposadr[pole_id]] = full_params["initial_angle"]

    elif template_name == "robot_arm":
        shoulder_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, "shoulder")
        if shoulder_id >= 0:
            data.qpos[model.jnt_qposadr[shoulder_id]] = full_params["target_angle"]
        if model.nu >= 2:
            data.ctrl[0] = full_params["target_angle"] * full_params["speed"]
            data.ctrl[1] = full_params["target_angle"] * 0.5 * full_params["speed"]

    elif template_name == "humanoid":
        torso_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "torso")
        if torso_id >= 0 and abs(full_params["push_force"]) > 0:
            data.xfrc_applied[torso_id, 0] = full_params["push_force"]

    mujoco.mj_forward(model, data)

    cam_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_CAMERA, "main")
    cam_name = "main" if cam_id >= 0 else None

    renderer = mujoco.Renderer(model, height=HEIGHT, width=WIDTH)
    steps_per_frame = int(1.0 / (FPS * timestep))
    total_frames = int(duration * FPS)

    frames = []
    for _ in range(total_frames):
        for _ in range(steps_per_frame):
            mujoco.mj_step(model, data)

        if template_name == "humanoid" and data.time > 0.5:
            torso_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "torso")
            if torso_id >= 0:
                data.xfrc_applied[torso_id, :] = 0

        renderer.update_scene(data, camera=cam_name)
        frame = renderer.render()
        frames.append(frame.copy())

    renderer.close()
    return frames


def _encode_mp4(frames: list, output_path: str):
    """Encode frames to H.264 MP4."""
    if shutil.which("ffmpeg"):
        _encode_ffmpeg(frames, output_path)
    else:
        _encode_imageio(frames, output_path)


def _encode_ffmpeg(frames: list, output_path: str):
    h, w = frames[0].shape[:2]
    cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo", "-vcodec", "rawvideo",
        "-s", f"{w}x{h}", "-pix_fmt", "rgb24",
        "-r", str(FPS), "-i", "pipe:",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-preset", "ultrafast", "-crf", "23",
        "-movflags", "+faststart",
        output_path,
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    for frame in frames:
        proc.stdin.write(frame.tobytes())
    proc.stdin.close()
    proc.wait()
    if proc.returncode != 0:
        stderr = proc.stderr.read().decode()
        raise RuntimeError(f"ffmpeg failed: {stderr}")


def _encode_imageio(frames: list, output_path: str):
    import imageio.v3 as iio
    iio.imwrite(
        output_path, np.stack(frames),
        fps=FPS, codec="libx264", plugin="pyav",
    )
