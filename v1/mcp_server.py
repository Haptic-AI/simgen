#!/usr/bin/env python3
"""
MCP Server — Helios Warehouse Simulation Self-Learning Loop
Exposes tools: analyze_video, refine_prompt, run_simulation, publish_to_ziggeo, update_loop_log
"""
import json
import sys
import os
import subprocess
import time
import hashlib
import requests
from pathlib import Path
from typing import Any

# ─── CONFIG ───────────────────────────────────────────────────────────────────
LLM_BASE_URL = "http://localhost:8000/v1"
LLM_MODEL    = "Qwen/Qwen2.5-Coder-14B-Instruct"
REFERENCE_VIDEO = "/mnt/user-data/uploads/helios_demo.mp4"
SIM_OUTPUT_DIR  = "/mnt/sim_outputs"
LOG_FILE        = "/mnt/sim_outputs/loop_log.jsonl"

# ─── TOOL REGISTRY ────────────────────────────────────────────────────────────
TOOLS = {
    "mcp__analyze_video": {
        "description": "Score a generated simulation video against the reference video using perceptual metrics",
        "inputSchema": {
            "type": "object",
            "properties": {
                "video_path": {"type": "string", "description": "Path to the generated video"},
                "reference_path": {"type": "string", "description": "Path to reference video (default: helios_demo.mp4)"},
                "metrics": {"type": "array", "items": {"type": "string"}, "description": "Metrics to compute"}
            },
            "required": ["video_path"]
        }
    },
    "mcp__refine_prompt": {
        "description": "Call local Qwen LLM to improve a MuJoCo simulation prompt based on identified gaps",
        "inputSchema": {
            "type": "object",
            "properties": {
                "current_prompt": {"type": "string"},
                "gaps": {"type": "array", "items": {"type": "string"}},
                "reference_description": {"type": "string"},
                "iteration": {"type": "integer"},
                "mode": {"type": "string", "enum": ["incremental", "radical_rethink", "component_build"]}
            },
            "required": ["current_prompt", "gaps"]
        }
    },
    "mcp__run_simulation": {
        "description": "Execute the full prompt→MuJoCo→video pipeline",
        "inputSchema": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string"},
                "duration": {"type": "integer", "default": 35},
                "resolution": {"type": "string", "default": "1280,720"},
                "fps": {"type": "integer", "default": 30},
                "output_path": {"type": "string"},
                "destination": {"type": "string", "enum": ["local", "ziggeo"], "default": "local"}
            },
            "required": ["prompt"]
        }
    },
    "mcp__publish_to_ziggeo": {
        "description": "Publish a video to Ziggeo with metadata tags",
        "inputSchema": {
            "type": "object",
            "properties": {
                "video_path": {"type": "string"},
                "title": {"type": "string"},
                "tags": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["video_path", "title"]
        }
    },
    "mcp__update_loop_log": {
        "description": "Append an iteration record to the self-learning loop log",
        "inputSchema": {
            "type": "object",
            "properties": {
                "iteration": {"type": "integer"},
                "prompt": {"type": "string"},
                "score": {"type": "number"},
                "gaps": {"type": "array"},
                "video_path": {"type": "string"},
                "ziggeo_url": {"type": "string"},
                "promoted": {"type": "boolean"}
            },
            "required": ["iteration", "score"]
        }
    }
}

# ─── TOOL IMPLEMENTATIONS ─────────────────────────────────────────────────────

def analyze_video(params: dict) -> dict:
    """Compare generated video to reference using frame-level metrics."""
    import cv2
    import numpy as np

    video_path = params["video_path"]
    ref_path   = params.get("reference_path", REFERENCE_VIDEO)

    if not os.path.exists(video_path):
        return {"error": f"Video not found: {video_path}", "overall": 0.0}

    def extract_frames(path, n=10):
        cap = cv2.VideoCapture(path)
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps   = cap.get(cv2.CAP_PROP_FPS)
        frames = []
        for i in range(n):
            cap.set(cv2.CAP_PROP_POS_FRAMES, int((i / n) * total))
            ret, frame = cap.read()
            if ret:
                frames.append(cv2.resize(frame, (320, 180)))
        cap.release()
        return frames, fps, total

    gen_frames, gen_fps, gen_total = extract_frames(video_path)
    ref_frames, ref_fps, ref_total = extract_frames(ref_path)

    if not gen_frames or not ref_frames:
        return {"error": "Could not read frames", "overall": 0.0}

    # Color histogram match
    def hist_score(frames):
        hists = []
        for f in frames:
            hsv = cv2.cvtColor(f, cv2.COLOR_BGR2HSV)
            h = cv2.calcHist([hsv], [0, 1], None, [18, 16], [0, 180, 0, 256])
            cv2.normalize(h, h)
            hists.append(h.flatten())
        return np.mean(hists, axis=0)

    gen_hist = hist_score(gen_frames)
    ref_hist = hist_score(ref_frames)
    color_match = float(np.dot(gen_hist, ref_hist) / (np.linalg.norm(gen_hist) * np.linalg.norm(ref_hist) + 1e-8))

    # Brightness match
    gen_bright = np.mean([np.mean(cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)) / 255.0 for f in gen_frames])
    ref_bright = np.mean([np.mean(cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)) / 255.0 for f in ref_frames])
    brightness_match = 1.0 - min(abs(gen_bright - ref_bright) / 0.3, 1.0)

    # SSIM (first matching frame pair)
    ssim_scores = []
    for gf, rf in zip(gen_frames[:5], ref_frames[:5]):
        gray_g = cv2.cvtColor(gf, cv2.COLOR_BGR2GRAY).astype(float)
        gray_r = cv2.cvtColor(rf, cv2.COLOR_BGR2GRAY).astype(float)
        mu1, mu2 = gray_g.mean(), gray_r.mean()
        sig1, sig2 = gray_g.std(), gray_r.std()
        sig12 = np.mean((gray_g - mu1) * (gray_r - mu2))
        C1, C2 = (0.01*255)**2, (0.03*255)**2
        ssim = ((2*mu1*mu2+C1)*(2*sig12+C2)) / ((mu1**2+mu2**2+C1)*(sig1**2+sig2**2+C2))
        ssim_scores.append(max(0.0, float(ssim)))
    ssim = np.mean(ssim_scores) if ssim_scores else 0.0

    # Duration match
    gen_dur = gen_total / gen_fps if gen_fps else 0
    ref_dur = ref_total / ref_fps if ref_fps else 33
    duration_match = 1.0 - min(abs(gen_dur - ref_dur) / ref_dur, 1.0)

    # Motion profile (inter-frame difference as proxy for camera velocity)
    def motion_profile(frames):
        diffs = []
        for i in range(1, len(frames)):
            diff = cv2.absdiff(frames[i], frames[i-1])
            diffs.append(np.mean(diff))
        return np.array(diffs) if diffs else np.array([0.0])

    gen_motion = motion_profile(gen_frames)
    ref_motion = motion_profile(ref_frames)
    min_len = min(len(gen_motion), len(ref_motion))
    if min_len > 0:
        gm = gen_motion[:min_len] / (gen_motion[:min_len].max() + 1e-8)
        rm = ref_motion[:min_len] / (ref_motion[:min_len].max() + 1e-8)
        motion_match = float(1.0 - np.mean(np.abs(gm - rm)))
    else:
        motion_match = 0.5

    # Weighted composite
    overall = (
        0.25 * ssim +
        0.20 * color_match +
        0.20 * brightness_match +
        0.20 * motion_match +
        0.15 * duration_match
    )

    return {
        "ssim": round(ssim, 4),
        "color_match": round(color_match, 4),
        "brightness_match": round(brightness_match, 4),
        "motion_match": round(motion_match, 4),
        "duration_match": round(duration_match, 4),
        "overall": round(overall, 4),
        "gen_brightness": round(gen_bright, 3),
        "ref_brightness": round(ref_bright, 3),
        "gen_duration_sec": round(gen_dur, 1),
        "ref_duration_sec": round(ref_dur, 1)
    }


def refine_prompt(params: dict) -> dict:
    """Call local Qwen LLM to improve the simulation prompt."""
    current_prompt = params["current_prompt"]
    gaps           = params.get("gaps", [])
    iteration      = params.get("iteration", 1)
    mode           = params.get("mode", "incremental")

    system_msg = """You are a MuJoCo simulation expert and creative director. Your job is to refine 
text prompts that drive a Python pipeline (prompt_to_video.py) which converts natural language 
descriptions into MuJoCo XML scenes, runs physics simulation, and renders video with ffmpeg.

The prompt controls:
- Scene geometry (walls, floor, ceiling dimensions and materials)
- Lighting setup (light positions, colors, intensities, shadow parameters)
- Camera trajectory (position, orientation, motion path, FOV)  
- Asset placement (shelving, boxes, pallets, props)
- Texture assignments (RGBA values or texture file references)
- Robot motion parameters (velocity, angular rate, path)

When refining a prompt, output ONLY the improved prompt text. Be specific with:
- Exact dimensions in meters
- RGB color values for materials (0.0-1.0 range)
- Camera parameters (fov_deg, position xyz, euler angles)
- Motion parameters (angular_velocity_deg_per_sec, linear_velocity_m_per_sec)
- Light parameters (pos xyz, diffuse rgb, specular, castshadow)
Do NOT include explanations, headers, or markdown. Output the refined prompt only."""

    gap_str = "\n".join(f"- {g}" for g in gaps) if gaps else "- General quality improvement"

    if mode == "radical_rethink":
        user_msg = f"""The current simulation prompt is NOT producing good results after {iteration} iterations.
Completely restructure it. Focus FIRST on getting camera motion and lighting correct, then add environment.

CURRENT PROMPT:
{current_prompt}

IDENTIFIED PROBLEMS:
{gap_str}

TARGET: A 33-second first-person POV video of an industrial warehouse interior.
The camera pans right at 5.5 deg/sec from a height of 0.48m.
Warehouse: 30m x 20m x 8m, dark ceiling, amber/yellow walls, grey floor, orange shelving.

Output only the completely rewritten prompt."""

    elif mode == "component_build":
        component = params.get("component", "environment")
        user_msg = f"""Build a minimal prompt that ONLY focuses on the {component} component.
Strip everything else. Make the {component} perfect first.

CURRENT PROMPT:
{current_prompt}

Output only the focused component prompt."""

    else:  # incremental
        user_msg = f"""Improve this MuJoCo simulation prompt. Fix ONLY these specific gaps (in priority order):
{gap_str}

CURRENT PROMPT:
{current_prompt}

Make targeted improvements. Keep what's working. Output only the improved prompt."""

    try:
        resp = requests.post(
            f"{LLM_BASE_URL}/chat/completions",
            headers={"Content-Type": "application/json"},
            json={
                "model": LLM_MODEL,
                "max_tokens": 1000,
                "temperature": 0.7,
                "messages": [
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": user_msg}
                ]
            },
            timeout=60
        )
        resp.raise_for_status()
        data = resp.json()
        refined = data["choices"][0]["message"]["content"].strip()
        return {
            "refined_prompt": refined,
            "mode": mode,
            "gaps_targeted": gaps,
            "llm_tokens_used": data.get("usage", {})
        }
    except Exception as e:
        # Fallback: return the current prompt with gap annotations
        return {
            "refined_prompt": current_prompt,
            "error": str(e),
            "fallback": True
        }


def run_simulation(params: dict) -> dict:
    """Execute prompt_to_video.py pipeline."""
    prompt      = params["prompt"]
    duration    = params.get("duration", 35)
    resolution  = params.get("resolution", "1280,720")
    fps         = params.get("fps", 30)
    destination = params.get("destination", "local")
    output_path = params.get("output_path")

    if not output_path:
        ts = int(time.time())
        output_path = f"{SIM_OUTPUT_DIR}/sim_{ts}.mp4"

    os.makedirs(SIM_OUTPUT_DIR, exist_ok=True)

    # Write prompt to temp file to avoid shell escaping issues
    prompt_file = f"/tmp/sim_prompt_{int(time.time())}.txt"
    with open(prompt_file, "w") as f:
        f.write(prompt)

    cmd = [
        "python3", "prompt_to_video.py",
        "--prompt-file", prompt_file,
        "--destination", destination,
        "--duration", str(duration),
        "--resolution", resolution,
        "--fps", str(fps),
        "--output", output_path
    ]

    # Also try the original single --prompt flag as fallback
    cmd_alt = [
        "python3", "prompt_to_video.py",
        "--prompt", prompt,
        "--destination", destination,
        "--duration", str(duration),
        "--resolution", resolution,
        "--fps", str(fps),
    ]

    start = time.time()
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=600
        )
        elapsed = time.time() - start

        if result.returncode != 0:
            # Try alternate invocation
            result = subprocess.run(
                cmd_alt, capture_output=True, text=True, timeout=600
            )

        # Parse ziggeo token from stdout if destination=ziggeo
        ziggeo_url = None
        if "ziggeo" in result.stdout.lower():
            for line in result.stdout.split("\n"):
                if "ziggeo.com" in line or "token" in line.lower():
                    ziggeo_url = line.strip()
                    break

        return {
            "video_path": output_path if os.path.exists(output_path) else None,
            "success": result.returncode == 0,
            "elapsed_seconds": round(elapsed, 1),
            "stdout": result.stdout[-2000:],
            "stderr": result.stderr[-1000:],
            "ziggeo_url": ziggeo_url
        }
    except subprocess.TimeoutExpired:
        return {"error": "Simulation timed out after 600s", "success": False}
    except Exception as e:
        return {"error": str(e), "success": False}
    finally:
        if os.path.exists(prompt_file):
            os.unlink(prompt_file)


def publish_to_ziggeo(params: dict) -> dict:
    """Publish video to Ziggeo via prompt_to_video.py."""
    video_path = params["video_path"]
    title      = params.get("title", "Helios Warehouse Simulation")
    tags       = params.get("tags", [])

    if not os.path.exists(video_path):
        return {"error": f"Video not found: {video_path}"}

    cmd = [
        "python3", "prompt_to_video.py",
        "--input-video", video_path,
        "--destination", "ziggeo",
        "--title", title,
        "--tags", ",".join(tags)
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        ziggeo_url = None
        for line in result.stdout.split("\n"):
            if "ziggeo.com" in line:
                ziggeo_url = line.strip()
        return {
            "success": result.returncode == 0,
            "ziggeo_url": ziggeo_url,
            "stdout": result.stdout[-1000:]
        }
    except Exception as e:
        return {"error": str(e)}


def update_loop_log(params: dict) -> dict:
    """Append iteration record to JSONL log."""
    os.makedirs(SIM_OUTPUT_DIR, exist_ok=True)
    record = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        **params
    }
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(record) + "\n")
    return {"logged": True, "log_file": LOG_FILE}


# ─── MCP JSON-RPC PROTOCOL ────────────────────────────────────────────────────

def handle_request(request: dict) -> dict:
    method = request.get("method", "")
    params = request.get("params", {})
    req_id = request.get("id")

    def ok(result):
        return {"jsonrpc": "2.0", "id": req_id, "result": result}

    def err(code, msg):
        return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": msg}}

    if method == "initialize":
        return ok({
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "helios-sim-mcp", "version": "1.0.0"}
        })

    elif method == "tools/list":
        tool_list = [
            {"name": name, "description": spec["description"], "inputSchema": spec["inputSchema"]}
            for name, spec in TOOLS.items()
        ]
        return ok({"tools": tool_list})

    elif method == "tools/call":
        tool_name = params.get("name", "")
        tool_args = params.get("arguments", {})

        dispatch = {
            "mcp__analyze_video":    analyze_video,
            "mcp__refine_prompt":    refine_prompt,
            "mcp__run_simulation":   run_simulation,
            "mcp__publish_to_ziggeo": publish_to_ziggeo,
            "mcp__update_loop_log":  update_loop_log,
        }

        if tool_name not in dispatch:
            return err(-32601, f"Unknown tool: {tool_name}")

        try:
            result = dispatch[tool_name](tool_args)
            return ok({"content": [{"type": "text", "text": json.dumps(result, indent=2)}]})
        except Exception as e:
            return err(-32603, f"Tool execution error: {str(e)}")

    return err(-32601, f"Method not found: {method}")


def main():
    """Run MCP server over stdio."""
    sys.stderr.write("Helios Sim MCP Server started\n")
    sys.stderr.flush()

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
            response = handle_request(request)
            print(json.dumps(response), flush=True)
        except json.JSONDecodeError as e:
            error = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": f"Parse error: {e}"}}
            print(json.dumps(error), flush=True)


if __name__ == "__main__":
    main()
