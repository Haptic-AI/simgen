"""Locomotion policy detector — maps prompt keywords to trained policies.

Policies trained on H100 via Brax PPO:
- humanoid_walk: Forward walking (reward: 5091)
- humanoid_run: Fast running (reward: 741)
- hopper: One-legged hopping (reward: 511)
"""

from __future__ import annotations

import os
from typing import Optional

POLICIES_DIR = os.path.join(os.path.dirname(__file__), "policies")

# Keyword → policy mapping (order matters — first match wins)
POLICY_MAP = [
    (["run", "sprint", "jog", "dash", "rush", "race", "fast"], "humanoid_run"),
    (["walk", "stroll", "stride", "march", "pace", "saunter", "amble", "wander"], "humanoid_walk"),
    (["hop", "bounce", "jump", "leap", "skip"], "hopper"),
    (["stand", "balance", "upright", "still", "statue", "pose"], "humanoid_walk"),
]


def get_available_policies() -> list:
    """List available trained policy names."""
    if not os.path.exists(POLICIES_DIR):
        return []
    return [f.replace(".pkl", "") for f in os.listdir(POLICIES_DIR) if f.endswith(".pkl")]


def has_locomotion_policy(prompt: str) -> Optional[str]:
    """Check if the prompt describes locomotion we have a policy for.

    Returns the policy name if available, None otherwise.
    Checks local files first, then falls back to keyword matching
    (for when policies live on a remote GPU renderer).
    """
    prompt_lower = prompt.lower()

    for keywords, policy_name in POLICY_MAP:
        for kw in keywords:
            if kw in prompt_lower:
                # Check local first
                policy_path = os.path.join(POLICIES_DIR, f"{policy_name}.pkl")
                if os.path.exists(policy_path):
                    return policy_name
                # If GPU_RENDER_URL is set, the policy may exist on the remote renderer
                if os.environ.get("GPU_RENDER_URL"):
                    return policy_name

    return None
