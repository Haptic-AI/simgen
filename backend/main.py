"""FastAPI app — prompt-to-simulation API."""

import uuid

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from backend.db import init_db, save_generation, save_simulation, save_rating, get_simulation, get_stats
from backend.environments import ENVIRONMENTS
from backend.locomotion import has_locomotion_policy
from backend.prompt_parser import parse_prompt
from backend.renderer import render_simulation

app = FastAPI(title="simgen", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    init_db()


class GenerateRequest(BaseModel):
    prompt: str
    environment: str = "earth"


class VaryRequest(BaseModel):
    simulation_id: str
    prompt: str = ""
    environment: str = "earth"


class RejectAllRequest(BaseModel):
    generation_id: str
    reason: str = ""  # optional free-text from creator


class FeedbackRequest(BaseModel):
    simulation_id: str
    rating: str  # "up" or "down"


@app.post("/generate")
def generate(req: GenerateRequest):
    """Parse prompt with AI, render 4 simulation videos, return URLs."""
    try:
        config = parse_prompt(req.prompt, environment=req.environment)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prompt parsing failed: {e}")

    template = config["template"]
    variations = config["variations"]
    generation_id = uuid.uuid4().hex[:8]

    # Check if a locomotion policy should be used
    policy_name = None
    if template == "humanoid":
        policy_name = has_locomotion_policy(req.prompt)

    # Persist generation
    save_generation(generation_id, req.prompt, template, config.get("description", ""))

    results = []
    for i, variation in enumerate(variations):
        sim_id = f"{generation_id}_{i}"
        params = variation["params"]

        try:
            video_path = render_simulation(template, params, sim_id, use_policy=policy_name)
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Rendering failed for variation {i}: {e}",
            )

        # Persist simulation
        save_simulation(sim_id, generation_id, variation["label"], template, params, video_path)

        results.append({
            "id": sim_id,
            "label": variation["label"],
            "video_url": f"/video/{sim_id}",
            "params": params,
        })

    return {
        "generation_id": generation_id,
        "prompt": req.prompt,
        "template": template,
        "description": config.get("description", ""),
        "simulations": results,
    }


@app.post("/vary")
def vary(req: VaryRequest):
    """Take a liked simulation and generate 4 variations around its params."""
    from backend.prompt_parser import parse_prompt_with_base

    base_sim = get_simulation(req.simulation_id)
    if not base_sim:
        raise HTTPException(status_code=404, detail="Simulation not found")

    import json
    base_params = json.loads(base_sim["params"]) if isinstance(base_sim["params"], str) else base_sim["params"]
    base_template = base_sim["template"]

    # Get the original prompt if none provided
    prompt = req.prompt
    if not prompt:
        from backend.db import get_db
        with get_db() as conn:
            row = conn.execute(
                "SELECT prompt FROM generations WHERE id = ?",
                (base_sim["generation_id"],),
            ).fetchone()
            prompt = row["prompt"] if row else "continue iterating"

    try:
        config = parse_prompt_with_base(
            prompt, base_template, base_params, base_sim["label"],
            environment=req.environment,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Variation failed: {e}")

    template = config["template"]
    variations = config["variations"]
    generation_id = uuid.uuid4().hex[:8]

    save_generation(generation_id, f"[vary] {prompt}", template, config.get("description", ""))

    results = []
    for i, variation in enumerate(variations):
        sim_id = f"{generation_id}_{i}"
        params = variation["params"]

        try:
            video_path = render_simulation(template, params, sim_id)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Rendering failed: {e}")

        save_simulation(sim_id, generation_id, variation["label"], template, params, video_path)
        results.append({
            "id": sim_id,
            "label": variation["label"],
            "video_url": f"/video/{sim_id}",
            "params": params,
        })

    return {
        "generation_id": generation_id,
        "prompt": prompt,
        "template": template,
        "description": config.get("description", ""),
        "simulations": results,
        "varied_from": req.simulation_id,
    }


@app.get("/video/{sim_id}")
def get_video(sim_id: str):
    """Serve a rendered simulation video."""
    sim = get_simulation(sim_id)
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return FileResponse(sim["video_path"], media_type="video/mp4")


@app.post("/feedback")
def submit_feedback(req: FeedbackRequest):
    """Record thumbs up/down for a simulation — persisted to SQLite."""
    sim = get_simulation(req.simulation_id)
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")
    save_rating(req.simulation_id, req.rating)
    return {"success": True}


@app.post("/reject-all")
def reject_all(req: RejectAllRequest):
    """Creator rejected all 4 — total miss. Downvote all sims and log the reason."""
    from backend.db import get_db
    with get_db() as conn:
        # Verify generation exists
        gen = conn.execute("SELECT * FROM generations WHERE id = ?", (req.generation_id,)).fetchone()
        if not gen:
            raise HTTPException(status_code=404, detail="Generation not found")

        # Downvote all simulations in this generation
        conn.execute(
            "UPDATE simulations SET rating = 'down', rated_at = datetime('now') WHERE generation_id = ?",
            (req.generation_id,),
        )

        # Store the rejection reason on the generation
        if req.reason:
            conn.execute(
                "UPDATE generations SET description = description || ' [REJECTED: ' || ? || ']' WHERE id = ?",
                (req.reason, req.generation_id),
            )

    return {"success": True, "message": "All variations rejected — the system will learn from this."}


@app.get("/environments")
def list_environments():
    """List available environment presets."""
    return {
        key: {"label": env["label"], "description": env["description"], "gravity": env["gravity"]}
        for key, env in ENVIRONMENTS.items()
    }


@app.get("/stats")
def stats():
    """Dashboard stats: template performance, top params, unmatched prompts."""
    return get_stats()


@app.get("/health")
def health():
    s = get_stats()
    return {
        "status": "ok",
        "total_generations": s["total_generations"],
        "total_ratings": s["total_ratings"],
    }
