"""MuJoCo simulation renderer — XML template → MP4 video."""

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
    # Check for any remaining placeholders and fill with defaults
    remaining = re.findall(r"\{\{(\w+)\}\}", xml)
    if remaining:
        raise ValueError(f"Unresolved template placeholders: {remaining}")
    return xml


def render_simulation(template_name: str, params: dict, sim_id: str) -> str:
    """
    Render a simulation to MP4.

    Args:
        template_name: Key in TEMPLATE_SCHEMAS
        params: Dict of parameter values
        sim_id: Unique simulation ID for the output filename

    Returns:
        Path to the rendered MP4 file.
    """
    schema = TEMPLATE_SCHEMAS[template_name]
    xml_template = get_template_xml(template_name)

    # Fill in defaults for any missing params
    full_params = {}
    for pname, pinfo in schema["params"].items():
        full_params[pname] = params.get(pname, pinfo["default"])

    timestep = schema["timestep"]
    duration = schema["sim_duration"]
    xml_str = _apply_params(xml_template, full_params, timestep)

    # Load model and create simulation
    model = mujoco.MjModel.from_xml_string(xml_str)
    data = mujoco.MjData(model)

    # Apply initial conditions for specific templates
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
        # Set control to target position
        if model.nu >= 2:
            data.ctrl[0] = full_params["target_angle"] * full_params["speed"]
            data.ctrl[1] = full_params["target_angle"] * 0.5 * full_params["speed"]

    elif template_name == "humanoid":
        # Apply push force to torso
        torso_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "torso")
        if torso_id >= 0 and abs(full_params["push_force"]) > 0:
            data.xfrc_applied[torso_id, 0] = full_params["push_force"]

    mujoco.mj_forward(model, data)

    # Determine camera
    cam_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_CAMERA, "main")
    cam_name = "main" if cam_id >= 0 else None

    # Render frames
    renderer = mujoco.Renderer(model, height=HEIGHT, width=WIDTH)
    steps_per_frame = int(1.0 / (FPS * timestep))
    total_frames = int(duration * FPS)

    frames = []
    for _ in range(total_frames):
        for _ in range(steps_per_frame):
            mujoco.mj_step(model, data)

        # For humanoid, only apply push for first 0.5 seconds
        if template_name == "humanoid" and data.time > 0.5:
            torso_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "torso")
            if torso_id >= 0:
                data.xfrc_applied[torso_id, :] = 0

        renderer.update_scene(data, camera=cam_name)
        frame = renderer.render()
        frames.append(frame.copy())

    renderer.close()

    # Encode to MP4 via ffmpeg
    output_path = os.path.join(VIDEO_DIR, f"{sim_id}.mp4")
    _encode_mp4(frames, output_path)

    return output_path


def _encode_mp4(frames: list[np.ndarray], output_path: str):
    """Encode frames to H.264 MP4. Uses ffmpeg if available, falls back to imageio."""
    if shutil.which("ffmpeg"):
        _encode_ffmpeg(frames, output_path)
    else:
        _encode_imageio(frames, output_path)


def _encode_ffmpeg(frames: list[np.ndarray], output_path: str):
    """Encode via system ffmpeg — produces H.264 MP4."""
    h, w = frames[0].shape[:2]

    cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-s", f"{w}x{h}",
        "-pix_fmt", "rgb24",
        "-r", str(FPS),
        "-i", "pipe:",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-preset", "ultrafast",
        "-crf", "23",
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


def _encode_imageio(frames: list[np.ndarray], output_path: str):
    """Encode via imageio + imageio-ffmpeg (bundled ffmpeg binary)."""
    import imageio.v3 as iio

    iio.imwrite(
        output_path,
        np.stack(frames),
        fps=FPS,
        codec="libx264",
        plugin="pyav",
    )
