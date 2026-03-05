#!/usr/bin/env python3
"""
sim_loop.py — Helios Warehouse Simulation Self-Learning Loop
Runs autonomously: generate → evaluate → refine → repeat until target score

Usage:
    python3 sim_loop.py
    python3 sim_loop.py --max-iter 20 --target-score 0.85 --start-iter 1
    python3 sim_loop.py --resume  # picks up from loop_log.jsonl

Architecture:
    1. Start with BASELINE_PROMPT
    2. Run simulation via prompt_to_video.py
    3. Score output vs reference video
    4. Call Qwen LLM to refine prompt based on gaps
    5. Repeat — keeping best prompt/video
    6. Publish winner to Ziggeo at full quality
"""
import os
import sys
import json
import time
import argparse
import requests
import subprocess
import cv2
import numpy as np
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional

# ─── CONFIG ───────────────────────────────────────────────────────────────────
REFERENCE_VIDEO  = "/mnt/user-data/uploads/helios_demo.mp4"
SIM_OUTPUT_DIR   = "/mnt/sim_outputs"
LOG_FILE         = f"{SIM_OUTPUT_DIR}/loop_log.jsonl"
LLM_URL          = "http://localhost:8000/v1/chat/completions"
LLM_MODEL        = "Qwen/Qwen2.5-Coder-14B-Instruct"
TARGET_SCORE     = 0.85
MAX_ITERATIONS   = 20
PLATEAU_WINDOW   = 3      # iterations without improvement → escalate
MIN_DISK_GB      = 5.0

BASELINE_PROMPT = """Helios patrol robot conducts a slow 180-degree surveillance sweep inside a 
large industrial warehouse. Camera mounted at height 0.48m, horizontal FOV 95 degrees, no robot 
body visible in frame — pure first-person POV shot.

SCENE DIMENSIONS: 30m long x 20m wide x 8m ceiling height.

CEILING: dark corrugated galvanized metal panels, rgba 0.22 0.23 0.25 1, with exposed black 
steel I-beams running perpendicular every 3m, beam rgba 0.08 0.08 0.09 1.

LIGHTING: 8 fluorescent tube fixtures mounted to ceiling beams in two parallel rows (4 per row), 
each fixture 1.2m long, diffuse rgba 0.92 0.96 1.0 1, intensity 1.8, castshadow true, ambient 
light rgba 0.28 0.30 0.34 1. Fixtures spaced 4m apart along X-axis at Y offsets -4m and +4m.

WALLS: 
  - Upper band (height 3m to 8m): dark rust-brown painted metal panels, rgba 0.32 0.15 0.06 1
  - Mid band (height 1.2m to 3m): bright amber-yellow painted panels, rgba 0.88 0.56 0.04 1  
  - Lower wainscoting (height 0m to 1.2m): white painted brick, rgba 0.92 0.92 0.90 1
  - Horizontal divider strip between mid and lower: dark grey, rgba 0.25 0.27 0.28 1, height 0.08m

FLOOR: dark grey concrete with subtle square tile grid (1.5m spacing), floor rgba 0.24 0.26 0.28 1, 
tile grout rgba 0.18 0.19 0.21 1, slight roughness texture.
Yellow safety tape stripes along perimeter 0.5m from walls, stripe width 0.1m.

RIGHT WALL SHELVING (X=14m, running from Z=-6m to Z=+6m):
  - Orange powder-coated steel uprights every 1.5m, rgba 0.85 0.42 0.02 1, height 2.4m
  - 4 horizontal shelf levels at heights 0.4m, 0.9m, 1.5m, 2.1m
  - Shelf decking: orange-painted plywood, rgba 0.75 0.38 0.05 1
  - Contents: cardboard boxes (rgba 0.72 0.58 0.35 1) and purple storage boxes (rgba 0.45 0.15 0.55 1)
  - Wooden pallets on floor beneath shelves, rgba 0.65 0.50 0.28 1

FLOOR PROPS:
  - Two white foam/paper rolls on floor at position (0, 3, 0.06), cylinder radius 0.06m length 0.4m
  - Additional scattered small boxes near far wall corners

CAMERA MOTION:
  - Start position: xyz 0.0 -6.0 0.48, facing direction +X (yaw=0)
  - Motion: yaw rotation rightward at 5.5 degrees per second
  - Total rotation: 180 degrees over 33 seconds
  - Linear motion: very slight forward creep at 0.03 m/s
  - Add subtle camera vibration: amplitude 0.003m at 2Hz (idle motor hum simulation)
  - Camera height: fixed at 0.48m AGL

RENDER QUALITY: 
  - Shadow mapping enabled, shadow softness 2
  - Ambient occlusion approximated via darken near wall-floor intersections
  - No HUD overlays, no MuJoCo debug overlays
  - Anti-aliasing 4x MSAA"""

# ─── DATA STRUCTURES ──────────────────────────────────────────────────────────

@dataclass
class IterationResult:
    iteration: int
    prompt: str
    video_path: Optional[str]
    score: float
    score_breakdown: dict
    gaps: list
    promoted: bool
    ziggeo_url: Optional[str]
    elapsed_seconds: float
    timestamp: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))


# ─── VIDEO SCORING ────────────────────────────────────────────────────────────

def score_video(gen_path: str, ref_path: str = REFERENCE_VIDEO) -> tuple[float, dict]:
    """Returns (overall_score 0-1, breakdown_dict)."""
    if not os.path.exists(gen_path):
        return 0.0, {"error": "video not found"}

    def read_frames(path, n=12):
        cap = cv2.VideoCapture(path)
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps   = cap.get(cv2.CAP_PROP_FPS) or 30
        frames = []
        for i in range(n):
            cap.set(cv2.CAP_PROP_POS_FRAMES, int((i / n) * total))
            ret, f = cap.read()
            if ret:
                frames.append(cv2.resize(f, (320, 180)))
        cap.release()
        return frames, fps, total

    gf, gfps, gtotal = read_frames(gen_path)
    rf, rfps, rtotal = read_frames(ref_path)
    if not gf or not rf:
        return 0.0, {"error": "frame read failed"}

    # 1. Color histogram similarity
    def hist(frames):
        hs = []
        for f in frames:
            h = cv2.calcHist([cv2.cvtColor(f, cv2.COLOR_BGR2HSV)], [0,1], None, [18,16], [0,180,0,256])
        cv2.normalize(h, h)
        hs.append(h.flatten())
        avg = np.mean(hs, axis=0)
        avg /= (np.linalg.norm(avg) + 1e-8)
        return avg

    gh, rh = hist(gf), hist(rf)
    color_score = float(np.dot(gh, rh))

    # 2. Brightness match
    gb = np.mean([cv2.cvtColor(f, cv2.COLOR_BGR2GRAY).mean()/255 for f in gf])
    rb = np.mean([cv2.cvtColor(f, cv2.COLOR_BGR2GRAY).mean()/255 for f in rf])
    bright_score = 1.0 - min(abs(gb-rb)/0.3, 1.0)

    # 3. Structural similarity (SSIM approximation)
    ssim_scores = []
    for g, r in zip(gf[:6], rf[:6]):
        gg = cv2.cvtColor(g, cv2.COLOR_BGR2GRAY).astype(float)
        rr = cv2.cvtColor(r, cv2.COLOR_BGR2GRAY).astype(float)
        u1, u2 = gg.mean(), rr.mean()
        s1, s2 = gg.std(), rr.std()
        s12 = np.mean((gg-u1)*(rr-u2))
        C1, C2 = (0.01*255)**2, (0.03*255)**2
        ssim = ((2*u1*u2+C1)*(2*s12+C2)) / ((u1**2+u2**2+C1)*(s1**2+s2**2+C2))
        ssim_scores.append(max(0.0, float(ssim)))
    ssim = np.mean(ssim_scores) if ssim_scores else 0.0

    # 4. Motion profile match
    def motion(frames):
        d = [cv2.absdiff(frames[i], frames[i-1]).mean() for i in range(1, len(frames))]
        return np.array(d) if d else np.array([0.0])

    gm, rm = motion(gf), motion(rf)
    n = min(len(gm), len(rm))
    if n > 0:
        gn = gm[:n] / (gm[:n].max()+1e-8)
        rn = rm[:n] / (rm[:n].max()+1e-8)
        motion_score = float(1.0 - np.mean(np.abs(gn-rn)))
    else:
        motion_score = 0.5

    # 5. Duration match
    gdur = gtotal/(gfps or 30)
    rdur = rtotal/(rfps or 30)
    dur_score = 1.0 - min(abs(gdur-rdur)/rdur, 1.0)

    # Weighted composite
    breakdown = {
        "ssim": round(ssim, 4),
        "color": round(color_score, 4),
        "brightness": round(bright_score, 4),
        "motion": round(motion_score, 4),
        "duration": round(dur_score, 4),
        "gen_brightness": round(gb, 3),
        "ref_brightness": round(rb, 3),
        "gen_duration_sec": round(gdur, 1),
    }
    overall = round(
        0.25*ssim + 0.22*color_score + 0.18*bright_score + 0.20*motion_score + 0.15*dur_score,
        4
    )
    return overall, breakdown


def diagnose_gaps(score: float, breakdown: dict, iteration: int) -> list[str]:
    """Return top 3 priority gaps from score breakdown."""
    gaps = []
    s = breakdown

    if s.get("ssim", 1.0) < 0.4:
        gaps.append(f"CRITICAL: Low structural similarity (SSIM={s['ssim']:.2f}) — "
                    "environment geometry doesn't match warehouse layout, "
                    "fix: enforce 30x20x8m dimensions, correct wall band heights")

    if s.get("color", 1.0) < 0.6:
        gaps.append(f"HIGH: Color histogram mismatch (score={s['color']:.2f}) — "
                    "dominant colors wrong; fix: amber-yellow mid-wall rgba(0.88,0.56,0.04), "
                    "dark rust upper rgba(0.32,0.15,0.06), grey floor rgba(0.24,0.26,0.28)")

    if s.get("brightness", 1.0) < 0.6:
        diff = s.get("gen_brightness", 0) - s.get("ref_brightness", 0.45)
        direction = "too bright" if diff > 0 else "too dark"
        gaps.append(f"HIGH: Brightness {direction} (gen={s.get('gen_brightness',0):.2f}, "
                    f"ref={s.get('ref_brightness',0):.2f}); fix: "
                    + ("reduce ambient light to rgba 0.28 0.30 0.34" if diff > 0
                       else "increase ceiling fixture intensity to 1.8, add 8 fixtures"))

    if s.get("motion", 1.0) < 0.6:
        gaps.append(f"HIGH: Camera motion profile mismatch (score={s['motion']:.2f}) — "
                    "fix: smooth yaw rotation at exactly 5.5 deg/sec rightward for 33s, "
                    "add subtle 2Hz vibration amplitude 0.003m, camera height 0.48m AGL")

    if s.get("duration", 1.0) < 0.7:
        gaps.append(f"MEDIUM: Duration mismatch (gen={s.get('gen_duration_sec',0):.1f}s vs ref=33s) — "
                    "set simulation duration to 35 seconds")

    # Always add a specificity gap early
    if iteration <= 3:
        gaps.append("MEDIUM: Add missing props — orange metal shelving right wall, "
                    "white foam rolls on floor center, wooden pallets in corners, "
                    "purple storage boxes on shelves, cardboard boxes")

    if len(gaps) == 0:
        gaps.append(f"LOW: Fine-tune overall (score={score:.2f}) — "
                    "increase texture detail, improve shadow softness, add slight lens vignette")

    return gaps[:3]


# ─── LLM REFINEMENT ───────────────────────────────────────────────────────────

def refine_prompt_via_llm(current_prompt: str, gaps: list, iteration: int,
                           mode: str = "incremental") -> str:
    """Call Qwen to refine prompt. Falls back to rule-based if LLM unavailable."""

    system = """You are a MuJoCo simulation expert. Refine the given prompt to fix specific gaps.
Output ONLY the improved prompt text — no explanations, no markdown, no headers.
Be precise: use exact meter dimensions, exact RGBA values (0.0-1.0), exact degree values."""

    gap_text = "\n".join(f"{i+1}. {g}" for i, g in enumerate(gaps))

    if mode == "radical_rethink":
        user = f"""RADICAL RETHINK NEEDED after {iteration} failed iterations.
Completely rewrite this MuJoCo prompt from scratch. Priority order:
1. Camera: first-person POV, 0.48m height, 95° FOV, 5.5°/sec rightward yaw for 33 seconds
2. Lighting: 8 ceiling fluorescent fixtures, cool white diffuse, castshadow=true, soft ambient
3. Environment: 30×20×8m warehouse, 3-band walls (rust/amber/brick), dark grey floor
4. Props: orange shelving right wall, scattered boxes, foam rolls on floor

Gaps to fix:
{gap_text}

Old prompt (DO NOT reuse structure, start fresh):
{current_prompt[:500]}...

Output only the new prompt:"""
    else:
        user = f"""Fix these specific gaps in the MuJoCo prompt (iteration {iteration}):
{gap_text}

Current prompt:
{current_prompt}

Output only the improved prompt:"""

    try:
        resp = requests.post(
            LLM_URL,
            headers={"Content-Type": "application/json"},
            json={
                "model": LLM_MODEL,
                "max_tokens": 1200,
                "temperature": 0.6 if mode == "incremental" else 0.85,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user}
                ]
            },
            timeout=90
        )
        resp.raise_for_status()
        refined = resp.json()["choices"][0]["message"]["content"].strip()
        print(f"  ✓ LLM refined prompt ({len(refined)} chars)")
        return refined
    except Exception as e:
        print(f"  ⚠ LLM unavailable ({e}), applying rule-based refinement")
        return rule_based_refine(current_prompt, gaps)


def rule_based_refine(prompt: str, gaps: list) -> str:
    """Fallback: apply known gap→fix rules directly to prompt text."""
    refined = prompt

    for gap in gaps:
        gap_lower = gap.lower()

        if "too bright" in gap_lower:
            refined = refined.replace("intensity 1.8", "intensity 1.2")
            refined = refined.replace("ambient light rgba 0.28", "ambient light rgba 0.18")

        elif "too dark" in gap_lower:
            refined = refined.replace("intensity 1.2", "intensity 1.8")
            refined += "\nINSTRUCTION: Increase ambient intensity. Add 2 additional ceiling fixtures."

        if "color" in gap_lower and "mismatch" in gap_lower:
            if "rgba 0.88 0.56 0.04" not in refined:
                refined += "\nFORCE mid-wall rgba 0.88 0.56 0.04 1 (bright amber-yellow)"
                refined += "\nFORCE upper-wall rgba 0.32 0.15 0.06 1 (dark rust-brown)"

        if "duration" in gap_lower:
            if "duration 35" not in refined and "35 seconds" not in refined:
                refined += "\nSIMULATION DURATION: exactly 35 seconds"

        if "camera motion" in gap_lower or "motion profile" in gap_lower:
            refined += "\nCAMERA OVERRIDE: yaw_rate 5.5 deg/sec rightward, height 0.48m, " \
                       "smooth rotation, 2Hz vibration 0.003m amplitude"

        if "props" in gap_lower or "shelving" in gap_lower:
            refined += ("\nREQUIRED PROPS: orange metal shelving (4 tiers) full length of right wall, "
                       "wooden pallets beneath shelves, purple storage boxes and cardboard on shelves, "
                       "2 white foam rolls at floor center (0, 3, 0.06)")

    return refined


# ─── SIMULATION RUNNER ────────────────────────────────────────────────────────

def run_simulation(prompt: str, output_path: str, duration: int = 35,
                   resolution: str = "1280,720", fps: int = 30) -> dict:
    """Run prompt_to_video.py and return result dict."""
    os.makedirs(SIM_OUTPUT_DIR, exist_ok=True)

    # Save prompt to temp file
    pfile = f"/tmp/prompt_{int(time.time())}.txt"
    with open(pfile, "w") as f:
        f.write(prompt)

    start = time.time()

    # Try --prompt-file first, then inline --prompt
    for cmd in [
        ["python3", "prompt_to_video.py", "--prompt-file", pfile,
         "--destination", "local", "--duration", str(duration),
         "--resolution", resolution, "--fps", str(fps), "--output", output_path],
        ["python3", "prompt_to_video.py", "--prompt", prompt,
         "--destination", "local", "--duration", str(duration),
         "--resolution", resolution, "--fps", str(fps)],
    ]:
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            if result.returncode == 0:
                break
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Timeout", "elapsed": time.time()-start}
        except Exception as e:
            return {"success": False, "error": str(e), "elapsed": time.time()-start}

    elapsed = time.time() - start
    os.unlink(pfile) if os.path.exists(pfile) else None

    return {
        "success": result.returncode == 0,
        "video_path": output_path if os.path.exists(output_path) else None,
        "elapsed": round(elapsed, 1),
        "stdout": result.stdout[-1500:],
        "stderr": result.stderr[-500:],
        "returncode": result.returncode
    }


def publish_final(video_path: str, score: float, best_prompt: str):
    """Publish the best video at full quality to Ziggeo."""
    print(f"\n🏆 TARGET SCORE ACHIEVED! Publishing final 1080p60 video to Ziggeo...")

    final_path = f"{SIM_OUTPUT_DIR}/helios_final_1080p60.mp4"
    cmd = [
        "python3", "prompt_to_video.py",
        "--prompt", best_prompt,
        "--destination", "ziggeo",
        "--duration", "300",
        "--resolution", "1920,1080",
        "--fps", "60"
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
        print(f"  {'✓' if result.returncode==0 else '✗'} Final publish complete")
        print(result.stdout[-500:])
    except Exception as e:
        print(f"  ✗ Final publish failed: {e}")
        print(f"  → Best video available at: {video_path}")


def check_disk_space() -> float:
    """Returns free GB at /mnt."""
    stat = os.statvfs("/mnt")
    return stat.f_frsize * stat.f_bavail / (1024**3)


def cleanup_old_videos(keep_n: int = 5):
    """Delete lowest-scoring videos to free disk space."""
    log_entries = []
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE) as f:
            for line in f:
                try:
                    log_entries.append(json.loads(line))
                except:
                    pass

    # Sort by score, keep top N
    sorted_entries = sorted(log_entries, key=lambda x: x.get("score", 0))
    to_delete = sorted_entries[:-keep_n]
    for entry in to_delete:
        vp = entry.get("video_path")
        if vp and os.path.exists(vp) and not entry.get("promoted_final"):
            os.unlink(vp)
            print(f"  🗑 Deleted low-score video: {vp} (score={entry.get('score',0):.3f})")


# ─── MAIN LOOP ────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Helios Warehouse Self-Learning Sim Loop")
    parser.add_argument("--max-iter", type=int, default=MAX_ITERATIONS)
    parser.add_argument("--target-score", type=float, default=TARGET_SCORE)
    parser.add_argument("--start-iter", type=int, default=1)
    parser.add_argument("--resume", action="store_true", help="Resume from best logged prompt")
    args = parser.parse_args()

    os.makedirs(SIM_OUTPUT_DIR, exist_ok=True)

    best_score = 0.0
    best_prompt = BASELINE_PROMPT
    best_video = None
    no_improvement_count = 0
    current_prompt = BASELINE_PROMPT

    print("=" * 70)
    print("  HELIOS WAREHOUSE SIMULATION — SELF-LEARNING LOOP")
    print(f"  Target: {args.target_score:.0%} | Max iterations: {args.max_iter}")
    print(f"  Reference: {REFERENCE_VIDEO}")
    print(f"  Output dir: {SIM_OUTPUT_DIR}")
    print("=" * 70)

    # Resume if requested
    if args.resume and os.path.exists(LOG_FILE):
        with open(LOG_FILE) as f:
            entries = [json.loads(l) for l in f if l.strip()]
        if entries:
            best_entry = max(entries, key=lambda x: x.get("score", 0))
            best_score = best_entry.get("score", 0)
            current_prompt = best_entry.get("prompt", BASELINE_PROMPT)
            best_prompt = current_prompt
            args.start_iter = max(e.get("iteration", 0) for e in entries) + 1
            print(f"  Resuming from iteration {args.start_iter}, best score: {best_score:.4f}")

    for iteration in range(args.start_iter, args.max_iter + 1):
        iter_start = time.time()
        print(f"\n{'─'*70}")
        print(f"  ITERATION {iteration:02d} / {args.max_iter}")
        print(f"  Current best score: {best_score:.4f}")
        print(f"  Disk free: {check_disk_space():.1f} GB")
        print(f"{'─'*70}")

        # Disk space guard
        if check_disk_space() < MIN_DISK_GB:
            print(f"  ⚠ Low disk space! Cleaning up...")
            cleanup_old_videos(keep_n=3)

        # Output path
        output_path = f"{SIM_OUTPUT_DIR}/iter_{iteration:03d}.mp4"

        # Run simulation
        print(f"\n  [1/4] Running simulation...")
        print(f"  Prompt preview: {current_prompt[:120]}...")
        sim_result = run_simulation(
            prompt=current_prompt,
            output_path=output_path,
            duration=35,
            resolution="1280,720",
            fps=30
        )

        if not sim_result["success"] or not sim_result.get("video_path"):
            print(f"  ✗ Simulation failed (rc={sim_result.get('returncode')})")
            print(f"  stderr: {sim_result.get('stderr', '')[:300]}")
            print(f"  stdout: {sim_result.get('stdout', '')[:300]}")

            # Still try to score if video exists from partial run
            if not os.path.exists(output_path):
                print(f"  → Skipping scoring, applying minor refinement")
                gaps = ["CRITICAL: Simulation pipeline failed — check prompt syntax, "
                        "simplify scene description, reduce prop count"]
                mode = "incremental"
                score, breakdown = 0.0, {"error": "sim_failed"}
            else:
                sim_result["video_path"] = output_path
                print(f"  → Partial video found, scoring anyway")

        # Score the video
        if sim_result.get("video_path") and os.path.exists(sim_result["video_path"]):
            print(f"\n  [2/4] Scoring output vs reference...")
            score, breakdown = score_video(sim_result["video_path"])
            print(f"  Score: {score:.4f}")
            print(f"  Breakdown: ssim={breakdown.get('ssim',0):.3f} | "
                  f"color={breakdown.get('color',0):.3f} | "
                  f"brightness={breakdown.get('brightness',0):.3f} | "
                  f"motion={breakdown.get('motion',0):.3f} | "
                  f"duration={breakdown.get('duration',0):.3f}")
        else:
            score, breakdown = 0.0, {"error": "no_video"}

        # Diagnose gaps
        print(f"\n  [3/4] Diagnosing gaps...")
        gaps = diagnose_gaps(score, breakdown, iteration)
        for i, g in enumerate(gaps):
            print(f"  Gap {i+1}: {g[:100]}...")

        # Promote if improved
        promoted = score > best_score
        if promoted:
            best_score = score
            best_prompt = current_prompt
            best_video = sim_result.get("video_path")
            no_improvement_count = 0
            print(f"\n  ✅ NEW BEST! Score: {score:.4f} → promoted")
        else:
            no_improvement_count += 1
            print(f"\n  → No improvement (no_improvement_count={no_improvement_count})")

        # Determine refinement mode
        if no_improvement_count >= PLATEAU_WINDOW and iteration >= 5:
            mode = "radical_rethink"
            print(f"  ⚡ PLATEAU DETECTED — switching to radical rethink mode")
            no_improvement_count = 0  # reset after escalation
        elif iteration >= 10 and score < 0.65:
            mode = "radical_rethink"
            print(f"  ⚡ Score below 0.65 at iter 10+ — radical rethink")
        else:
            mode = "incremental"

        # Log this iteration
        elapsed = time.time() - iter_start
        log_entry = {
            "iteration": iteration,
            "prompt": current_prompt,
            "score": score,
            "breakdown": breakdown,
            "gaps": gaps,
            "video_path": sim_result.get("video_path"),
            "promoted": promoted,
            "best_score": best_score,
            "elapsed_seconds": round(elapsed, 1),
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "mode": mode
        }
        with open(LOG_FILE, "a") as f:
            f.write(json.dumps(log_entry) + "\n")

        # Print iteration summary
        print(f"\n  ── Iteration {iteration} Summary ──")
        print(f"  Score: {score:.4f} | Best: {best_score:.4f} | "
              f"{'✅ PROMOTED' if promoted else '→ Not promoted'}")
        print(f"  Elapsed: {elapsed:.0f}s")

        # Check exit conditions
        if score >= args.target_score:
            print(f"\n{'='*70}")
            print(f"  🎯 TARGET ACHIEVED! Score {score:.4f} >= {args.target_score}")
            print(f"  Best video: {best_video}")
            print(f"{'='*70}")
            publish_final(best_video, best_score, best_prompt)

            # Save winning prompt
            with open(f"{SIM_OUTPUT_DIR}/WINNING_PROMPT.txt", "w") as f:
                f.write(best_prompt)
            print(f"\n  Winning prompt saved to {SIM_OUTPUT_DIR}/WINNING_PROMPT.txt")
            return

        # Refine prompt for next iteration
        print(f"\n  [4/4] Refining prompt via LLM ({mode} mode)...")
        # Use best prompt as base for refinement (not last failed prompt)
        base_for_refinement = best_prompt if best_score > 0.3 else current_prompt
        current_prompt = refine_prompt_via_llm(
            current_prompt=base_for_refinement,
            gaps=gaps,
            iteration=iteration,
            mode=mode
        )

    # Max iterations reached
    print(f"\n{'='*70}")
    print(f"  Max iterations ({args.max_iter}) reached.")
    print(f"  Best score achieved: {best_score:.4f} (target: {args.target_score})")
    print(f"  Best video: {best_video}")
    print(f"{'='*70}")

    if best_video and os.path.exists(best_video):
        publish_final(best_video, best_score, best_prompt)
        with open(f"{SIM_OUTPUT_DIR}/BEST_PROMPT.txt", "w") as f:
            f.write(best_prompt)


if __name__ == "__main__":
    main()
