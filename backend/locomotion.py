"""Locomotion policy loader — detects when a trained walking policy should be used.

The actual Brax imports happen lazily in renderer.py at render time,
not at module load time, to avoid Python 3.9 compatibility issues with mjx.
"""

from __future__ import annotations

import os
from typing import Optional

POLICIES_DIR = os.path.join(os.path.dirname(__file__), "policies")


def get_available_policies() -> list:
    """List available trained policy names."""
    if not os.path.exists(POLICIES_DIR):
        return []
    return [
        f.replace(".pkl", "")
        for f in os.listdir(POLICIES_DIR)
        if f.endswith(".pkl")
    ]


def has_locomotion_policy(prompt: str) -> Optional[str]:
    """Check if the prompt describes locomotion that we have a policy for.

    Returns the policy name if available, None otherwise.
    """
    prompt_lower = prompt.lower()

    locomotion_keywords = [
        "walk", "stroll", "stride", "march", "pace", "saunter", "amble",
        "run", "sprint", "jog", "dash", "rush",
        "stand", "balance", "upright",
    ]

    for kw in locomotion_keywords:
        if kw in prompt_lower:
            policy_path = os.path.join(POLICIES_DIR, "humanoid_walk.pkl")
            if os.path.exists(policy_path):
                return "humanoid_walk"

    return None
