"""FastAPI app — prompt-to-simulation API."""

import uuid
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from backend.prompt_parser import parse_prompt
from backend.renderer import render_simulation

app = FastAPI(title="mjsim", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory state
simulations: dict[str, dict] = {}
feedback_store: dict[str, str] = {}


class GenerateRequest(BaseModel):
    prompt: str


class FeedbackRequest(BaseModel):
    simulation_id: str
    rating: str  # "up" or "down"


@app.post("/generate")
def generate(req: GenerateRequest):
    """Parse prompt with AI, render 4 simulation videos, return URLs."""
    # Parse prompt via Claude
    try:
        config = parse_prompt(req.prompt)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prompt parsing failed: {e}")

    template = config["template"]
    variations = config["variations"]
    generation_id = uuid.uuid4().hex[:8]

    results = []
    for i, variation in enumerate(variations):
        sim_id = f"{generation_id}_{i}"
        params = variation["params"]

        try:
            video_path = render_simulation(template, params, sim_id)
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Rendering failed for variation {i}: {e}",
            )

        sim_data = {
            "id": sim_id,
            "label": variation["label"],
            "video_url": f"/video/{sim_id}",
            "params": params,
            "template": template,
            "video_path": video_path,
            "created_at": datetime.utcnow().isoformat(),
        }
        simulations[sim_id] = sim_data
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


@app.get("/video/{sim_id}")
def get_video(sim_id: str):
    """Serve a rendered simulation video."""
    sim = simulations.get(sim_id)
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return FileResponse(sim["video_path"], media_type="video/mp4")


@app.post("/feedback")
def submit_feedback(req: FeedbackRequest):
    """Record thumbs up/down for a simulation."""
    if req.simulation_id not in simulations:
        raise HTTPException(status_code=404, detail="Simulation not found")
    feedback_store[req.simulation_id] = req.rating
    return {"success": True}


@app.get("/health")
def health():
    return {"status": "ok", "simulations_count": len(simulations)}
