"""SQLite persistence for generations, simulations, and feedback."""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Optional

DB_PATH = os.environ.get("MJSIM_DB_PATH", "simgen.db")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def get_db():
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    """Create tables if they don't exist."""
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS generations (
                id TEXT PRIMARY KEY,
                prompt TEXT NOT NULL,
                template TEXT NOT NULL,
                description TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS simulations (
                id TEXT PRIMARY KEY,
                generation_id TEXT NOT NULL,
                label TEXT NOT NULL,
                template TEXT NOT NULL,
                params TEXT NOT NULL,
                video_path TEXT,
                rating TEXT,
                rated_at TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (generation_id) REFERENCES generations(id)
            );

            CREATE INDEX IF NOT EXISTS idx_simulations_rating ON simulations(rating);
            CREATE INDEX IF NOT EXISTS idx_simulations_template ON simulations(template);
            CREATE INDEX IF NOT EXISTS idx_generations_prompt ON generations(prompt);
        """)


def save_generation(generation_id: str, prompt: str, template: str, description: str):
    with get_db() as conn:
        conn.execute(
            "INSERT INTO generations (id, prompt, template, description, created_at) VALUES (?, ?, ?, ?, ?)",
            (generation_id, prompt, template, description, datetime.utcnow().isoformat()),
        )


def save_simulation(sim_id: str, generation_id: str, label: str, template: str, params: dict, video_path: str):
    with get_db() as conn:
        conn.execute(
            "INSERT INTO simulations (id, generation_id, label, template, params, video_path, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (sim_id, generation_id, label, template, json.dumps(params), video_path, datetime.utcnow().isoformat()),
        )


def save_rating(sim_id: str, rating: str):
    with get_db() as conn:
        conn.execute(
            "UPDATE simulations SET rating = ?, rated_at = ? WHERE id = ?",
            (rating, datetime.utcnow().isoformat(), sim_id),
        )


def get_simulation(sim_id: str) -> Optional[dict]:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM simulations WHERE id = ?", (sim_id,)).fetchone()
        return dict(row) if row else None


def get_top_rated(template: str = None, limit: int = 10) -> list[dict]:
    """Get top-rated simulations, optionally filtered by template."""
    with get_db() as conn:
        if template:
            rows = conn.execute(
                """SELECT s.*, g.prompt FROM simulations s
                   JOIN generations g ON s.generation_id = g.id
                   WHERE s.rating = 'up' AND s.template = ?
                   ORDER BY s.rated_at DESC LIMIT ?""",
                (template, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT s.*, g.prompt FROM simulations s
                   JOIN generations g ON s.generation_id = g.id
                   WHERE s.rating = 'up'
                   ORDER BY s.rated_at DESC LIMIT ?""",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]


def get_recent_feedback(limit: int = 20) -> list[dict]:
    """Get recent rated simulations for context."""
    with get_db() as conn:
        rows = conn.execute(
            """SELECT s.*, g.prompt FROM simulations s
               JOIN generations g ON s.generation_id = g.id
               WHERE s.rating IS NOT NULL
               ORDER BY s.rated_at DESC LIMIT ?""",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_stats() -> dict:
    """Get aggregate stats for the dashboard."""
    with get_db() as conn:
        total_gens = conn.execute("SELECT COUNT(*) FROM generations").fetchone()[0]
        total_sims = conn.execute("SELECT COUNT(*) FROM simulations").fetchone()[0]
        total_up = conn.execute("SELECT COUNT(*) FROM simulations WHERE rating = 'up'").fetchone()[0]
        total_down = conn.execute("SELECT COUNT(*) FROM simulations WHERE rating = 'down'").fetchone()[0]

        # Per-template stats
        template_rows = conn.execute(
            """SELECT template,
                      COUNT(*) as total,
                      SUM(CASE WHEN rating = 'up' THEN 1 ELSE 0 END) as upvotes,
                      SUM(CASE WHEN rating = 'down' THEN 1 ELSE 0 END) as downvotes
               FROM simulations
               GROUP BY template
               ORDER BY upvotes DESC"""
        ).fetchall()

        templates = [dict(r) for r in template_rows]

        # Top-rated params per template
        top_params = {}
        for t in templates:
            rows = conn.execute(
                """SELECT params, label FROM simulations
                   WHERE template = ? AND rating = 'up'
                   ORDER BY rated_at DESC LIMIT 5""",
                (t["template"],),
            ).fetchall()
            top_params[t["template"]] = [
                {"params": json.loads(r["params"]), "label": r["label"]} for r in rows
            ]

        # Unmatched prompts — prompts where all 4 sims got downvoted
        unmatched = conn.execute(
            """SELECT g.prompt, g.template, g.created_at
               FROM generations g
               WHERE NOT EXISTS (
                   SELECT 1 FROM simulations s
                   WHERE s.generation_id = g.id AND (s.rating = 'up' OR s.rating IS NULL)
               )
               ORDER BY g.created_at DESC LIMIT 10"""
        ).fetchall()

        return {
            "total_generations": total_gens,
            "total_simulations": total_sims,
            "total_upvotes": total_up,
            "total_downvotes": total_down,
            "total_ratings": total_up + total_down,
            "templates": templates,
            "top_rated_params": top_params,
            "unmatched_prompts": [dict(r) for r in unmatched],
        }
