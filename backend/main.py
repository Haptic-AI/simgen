"""FastAPI app — prompt-to-simulation API."""

import os
import uuid
import threading
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from backend.db import init_db, save_generation, save_simulation, save_rating, get_simulation, get_stats
from backend.environments import ENVIRONMENTS
from backend.visual_themes import THEMES
from backend.locomotion import has_locomotion_policy
from backend.prompt_parser import parse_prompt
from backend.renderer import render_simulation

app = FastAPI(title="simgen", version="0.3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://simgen.hapticlabs.ai",
        "http://localhost:3000",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory job store
_jobs: dict = {}


@app.on_event("startup")
def startup():
    init_db()


class GenerateRequest(BaseModel):
    prompt: str
    environment: str = "earth"
    theme: str = "studio"


class VaryRequest(BaseModel):
    simulation_id: str
    prompt: str = ""
    environment: str = "earth"


class RejectAllRequest(BaseModel):
    generation_id: str
    reason: str = ""

class FeedbackRequest(BaseModel):
    simulation_id: str
    rating: str


def _run_generate(job_id: str, prompt: str, environment: str, theme: str):
    """Background worker for generation."""
    try:
        _jobs[job_id]["status"] = "parsing"
        config = parse_prompt(prompt, environment=environment)

        template = config["template"]
        variations = config["variations"]
        generation_id = job_id

        policy_name = None
        if template == "humanoid":
            policy_name = has_locomotion_policy(prompt)

        save_generation(generation_id, prompt, template, config.get("description", ""))

        _jobs[job_id]["status"] = "rendering"
        _jobs[job_id]["template"] = template
        _jobs[job_id]["description"] = config.get("description", "")
        _jobs[job_id]["total"] = len(variations)

        # Render all variations in parallel
        results = [None] * len(variations)
        completed = [0]

        def render_one(i, variation):
            sim_id = f"{generation_id}_{i}"
            params = variation["params"]
            video_path = render_simulation(template, params, sim_id, use_policy=policy_name, theme=theme)
            save_simulation(sim_id, generation_id, variation["label"], template, params, video_path)
            completed[0] += 1
            _jobs[job_id]["progress"] = completed[0]
            return {
                "id": sim_id,
                "label": variation["label"],
                "video_url": f"/video/{sim_id}",
                "params": params,
            }

        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = {pool.submit(render_one, i, v): i for i, v in enumerate(variations)}
            for future in as_completed(futures):
                i = futures[future]
                results[i] = future.result()

        _jobs[job_id]["status"] = "complete"
        _jobs[job_id]["progress"] = len(variations)
        _jobs[job_id]["result"] = {
            "generation_id": generation_id,
            "prompt": prompt,
            "template": template,
            "description": config.get("description", ""),
            "simulations": results,
        }

    except Exception as e:
        _jobs[job_id]["status"] = "error"
        _jobs[job_id]["error"] = str(e)
        traceback.print_exc()


def _run_vary(job_id: str, simulation_id: str, prompt: str, environment: str):
    """Background worker for vary."""
    from backend.prompt_parser import parse_prompt_with_base
    import json

    try:
        _jobs[job_id]["status"] = "parsing"

        base_sim = get_simulation(simulation_id)
        if not base_sim:
            raise ValueError("Simulation not found")

        base_params = json.loads(base_sim["params"]) if isinstance(base_sim["params"], str) else base_sim["params"]
        base_template = base_sim["template"]

        actual_prompt = prompt
        if not actual_prompt:
            from backend.db import get_db
            with get_db() as conn:
                row = conn.execute(
                    "SELECT prompt FROM generations WHERE id = ?",
                    (base_sim["generation_id"],),
                ).fetchone()
                actual_prompt = row["prompt"] if row else "continue iterating"

        config = parse_prompt_with_base(
            actual_prompt, base_template, base_params, base_sim["label"],
            environment=environment,
        )

        template = config["template"]
        variations = config["variations"]
        generation_id = job_id

        save_generation(generation_id, f"[vary] {actual_prompt}", template, config.get("description", ""))

        _jobs[job_id]["status"] = "rendering"
        _jobs[job_id]["template"] = template
        _jobs[job_id]["description"] = config.get("description", "")
        _jobs[job_id]["total"] = len(variations)

        results = []
        for i, variation in enumerate(variations):
            _jobs[job_id]["progress"] = i
            sim_id = f"{generation_id}_{i}"
            params = variation["params"]

            video_path = render_simulation(template, params, sim_id)
            save_simulation(sim_id, generation_id, variation["label"], template, params, video_path)

            results.append({
                "id": sim_id,
                "label": variation["label"],
                "video_url": f"/video/{sim_id}",
                "params": params,
            })

        _jobs[job_id]["status"] = "complete"
        _jobs[job_id]["progress"] = len(variations)
        _jobs[job_id]["result"] = {
            "generation_id": generation_id,
            "prompt": actual_prompt,
            "template": template,
            "description": config.get("description", ""),
            "simulations": results,
            "varied_from": simulation_id,
        }

    except Exception as e:
        _jobs[job_id]["status"] = "error"
        _jobs[job_id]["error"] = str(e)
        traceback.print_exc()


@app.post("/generate")
def generate(req: GenerateRequest):
    """Submit a generation job. Returns immediately with a job ID."""
    job_id = uuid.uuid4().hex[:8]
    _jobs[job_id] = {
        "status": "queued",
        "progress": 0,
        "total": 4,
        "created_at": datetime.utcnow().isoformat(),
        "prompt": req.prompt,
    }
    thread = threading.Thread(target=_run_generate, args=(job_id, req.prompt, req.environment, req.theme))
    thread.start()
    return {"job_id": job_id, "status": "queued"}


@app.post("/vary")
def vary(req: VaryRequest):
    """Submit a vary job. Returns immediately with a job ID."""
    job_id = uuid.uuid4().hex[:8]
    _jobs[job_id] = {
        "status": "queued",
        "progress": 0,
        "total": 4,
        "created_at": datetime.utcnow().isoformat(),
        "prompt": req.prompt,
    }
    thread = threading.Thread(target=_run_vary, args=(job_id, req.simulation_id, req.prompt, req.environment))
    thread.start()
    return {"job_id": job_id, "status": "queued"}


@app.get("/job/{job_id}")
def get_job(job_id: str):
    """Poll a job's status. Returns progress and result when complete."""
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    response = {
        "job_id": job_id,
        "status": job["status"],
        "progress": job.get("progress", 0),
        "total": job.get("total", 4),
    }

    if job["status"] == "complete":
        response["result"] = job["result"]
    elif job["status"] == "error":
        response["error"] = job.get("error", "Unknown error")
    elif job["status"] == "rendering":
        response["template"] = job.get("template", "")
        response["description"] = job.get("description", "")

    return response


@app.get("/video/{sim_id}")
def get_video(sim_id: str):
    """Serve a rendered simulation video."""
    sim = get_simulation(sim_id)
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return FileResponse(sim["video_path"], media_type="video/mp4")


@app.post("/feedback")
def submit_feedback(req: FeedbackRequest):
    sim = get_simulation(req.simulation_id)
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")
    save_rating(req.simulation_id, req.rating)
    return {"success": True}


@app.post("/reject-all")
def reject_all(req: RejectAllRequest):
    from backend.db import get_db
    with get_db() as conn:
        gen = conn.execute("SELECT * FROM generations WHERE id = ?", (req.generation_id,)).fetchone()
        if not gen:
            raise HTTPException(status_code=404, detail="Generation not found")
        conn.execute(
            "UPDATE simulations SET rating = 'down', rated_at = datetime('now') WHERE generation_id = ?",
            (req.generation_id,),
        )
        if req.reason:
            conn.execute(
                "UPDATE generations SET description = description || ' [REJECTED: ' || ? || ']' WHERE id = ?",
                (req.reason, req.generation_id),
            )
    return {"success": True}


@app.get("/history")
def history(limit: int = 50):
    from backend.db import get_db
    with get_db() as conn:
        rows = conn.execute(
            """SELECT g.id, g.prompt, g.template, g.created_at,
                      COUNT(s.id) as sim_count,
                      SUM(CASE WHEN s.rating = 'up' THEN 1 ELSE 0 END) as upvotes,
                      SUM(CASE WHEN s.rating = 'down' THEN 1 ELSE 0 END) as downvotes
               FROM generations g
               LEFT JOIN simulations s ON s.generation_id = g.id
               GROUP BY g.id
               ORDER BY g.created_at DESC
               LIMIT ?""",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


@app.get("/environments")
def list_environments():
    return {
        key: {"label": env["label"], "description": env["description"], "gravity": env["gravity"]}
        for key, env in ENVIRONMENTS.items()
    }


@app.get("/themes")
def list_themes():
    return {
        key: {"label": t["label"], "description": t["description"]}
        for key, t in THEMES.items()
    }


@app.get("/stats")
def stats():
    return get_stats()


@app.get("/health")
def health():
    s = get_stats()
    return {
        "status": "ok",
        "total_generations": s["total_generations"],
        "total_ratings": s["total_ratings"],
    }


@app.get("/status")
def status():
    import time
    import httpx

    checks = {}
    checks["backend"] = {"status": "ok", "pid": os.getpid()}

    try:
        s = get_stats()
        checks["database"] = {"status": "ok", "generations": s["total_generations"]}
    except Exception as e:
        checks["database"] = {"status": "error", "error": str(e)}

    t0 = time.time()
    try:
        import anthropic
        client = anthropic.Anthropic()
        client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=5,
            messages=[{"role": "user", "content": "ping"}],
        )
        checks["anthropic_api"] = {"status": "ok", "latency_ms": int((time.time() - t0) * 1000)}
    except Exception as e:
        checks["anthropic_api"] = {"status": "error", "error": str(e)}

    gpu_url = os.environ.get("GPU_RENDER_URL", "")
    if gpu_url:
        try:
            resp = httpx.get(f"{gpu_url}/health", timeout=5)
            gpu_data = resp.json()
            checks["gpu_renderer"] = {
                "status": "ok",
                "url": gpu_url,
                "gpu": gpu_data.get("gpu", "unknown"),
                "policies": gpu_data.get("cached", []),
            }
        except Exception as e:
            checks["gpu_renderer"] = {"status": "error", "url": gpu_url, "error": str(e)}
    else:
        checks["gpu_renderer"] = {"status": "not_configured"}

    all_ok = all(c.get("status") == "ok" for c in checks.values())
    return {"overall": "ok" if all_ok else "degraded", "services": checks}
