"""Locomotion policy loader — runs trained Brax walking policies in simulation.

Loads a trained PPO policy from a pickle file and provides a function to
render a policy-controlled humanoid simulation to video frames.
"""

from __future__ import annotations

import os
import pickle
from typing import Optional

import jax
import jax.numpy as jnp
import numpy as np
import mujoco
from brax import envs
from brax.training.agents.ppo import train as ppo_module
from brax.training.agents.ppo import networks as ppo_networks

POLICIES_DIR = os.path.join(os.path.dirname(__file__), "policies")

_loaded_policies = {}


def _load_policy(policy_name: str):
    """Load a trained policy from disk. Cached after first load."""
    if policy_name in _loaded_policies:
        return _loaded_policies[policy_name]

    path = os.path.join(POLICIES_DIR, f"{policy_name}.pkl")
    if not os.path.exists(path):
        return None

    with open(path, "rb") as f:
        data = pickle.load(f)

    env_name = data.get("env_name", "humanoid")
    env = envs.get_environment(env_name)

    # Rebuild the network and inference function
    network = ppo_networks.make_ppo_networks(
        observation_size=env.observation_size,
        action_size=env.action_size,
        preprocess_observations_fn=ppo_networks.make_inference_fn(
            ppo_networks.running_statistics.normalize
        ) if hasattr(ppo_networks, 'make_inference_fn') else None,
    )

    # Try the simpler approach — use the train function to get make_inference_fn
    # then just apply params
    _loaded_policies[policy_name] = {
        "params": data["params"],
        "env": env,
        "env_name": env_name,
    }
    return _loaded_policies[policy_name]


def get_available_policies() -> list[str]:
    """List available trained policy names."""
    if not os.path.exists(POLICIES_DIR):
        return []
    return [
        f.replace(".pkl", "")
        for f in os.listdir(POLICIES_DIR)
        if f.endswith(".pkl")
    ]


def has_locomotion_policy(action: str) -> Optional[str]:
    """Check if we have a policy that can handle the requested action.

    Returns the policy name if available, None otherwise.
    """
    action_lower = action.lower()

    walk_keywords = ["walk", "stroll", "stride", "march", "pace", "saunter", "amble"]
    run_keywords = ["run", "sprint", "jog", "dash", "rush"]
    stand_keywords = ["stand", "balance", "upright", "still"]

    for kw in walk_keywords + run_keywords + stand_keywords:
        if kw in action_lower:
            if os.path.exists(os.path.join(POLICIES_DIR, "humanoid_walk.pkl")):
                return "humanoid_walk"

    return None


def render_with_policy(
    policy_name: str,
    duration: float = 15.0,
    fps: int = 30,
    width: int = 640,
    height: int = 480,
    gravity_scale: float = 1.0,
) -> list[np.ndarray]:
    """Render a policy-controlled simulation to frames.

    Uses Brax's built-in humanoid model (not our custom XML template)
    because the policy was trained on this specific model.

    Returns list of RGB numpy arrays.
    """
    policy_data = _load_policy(policy_name)
    if policy_data is None:
        raise ValueError(f"Policy '{policy_name}' not found in {POLICIES_DIR}")

    env = policy_data["env"]
    params = policy_data["params"]

    # Run the simulation in Brax to get state trajectories
    rng = jax.random.PRNGKey(42)
    state = jax.jit(env.reset)(rng)

    # We need to rebuild inference — use a simpler approach
    # Just run the environment with the trained params using Brax's pipeline
    from brax.training.agents.ppo import networks as ppo_nets

    network = ppo_nets.make_ppo_networks(
        observation_size=env.observation_size,
        action_size=env.action_size,
    )
    make_inference = ppo_nets.make_inference_fn(network)
    inference_fn = make_inference(params)
    jit_inference = jax.jit(inference_fn)

    # Collect Brax pipeline states
    steps_per_frame = max(1, int(1.0 / (fps * env.dt)))
    total_frames = int(duration * fps)

    states = []
    for frame_idx in range(total_frames):
        for _ in range(steps_per_frame):
            act_rng, rng = jax.random.split(rng)
            act, _ = jit_inference(state.obs, act_rng)
            state = jax.jit(env.step)(state, act)
        states.append(state)

    # Now render using MuJoCo's renderer with Brax's model
    # Get the MuJoCo model from Brax's environment
    try:
        mj_model = env.sys.mj_model
    except AttributeError:
        # Brax generalized pipeline — need to get the model differently
        from brax.io import mjcf
        mj_model = mujoco.MjModel.from_xml_string(env.sys.xml_string) if hasattr(env.sys, 'xml_string') else None

    if mj_model is None:
        # Fallback: use Brax's built-in rendering
        from brax.io import image
        frames = []
        for state in states:
            # Brax has its own renderer
            frame = image.render_array(env.sys, state.pipeline_state, width=width, height=height)
            frames.append(frame)
        return frames

    # Use MuJoCo native rendering
    mj_data = mujoco.MjData(mj_model)

    # Apply gravity scaling
    if gravity_scale != 1.0:
        mj_model.opt.gravity[2] = -9.81 * gravity_scale

    renderer = mujoco.Renderer(mj_model, height=height, width=width)

    frames = []
    for state in states:
        # Extract qpos/qvel from Brax state and set in MuJoCo
        pipeline_state = state.pipeline_state
        qpos = np.array(jax.device_get(pipeline_state.q))
        qvel = np.array(jax.device_get(pipeline_state.qd))

        mj_data.qpos[:len(qpos)] = qpos
        mj_data.qvel[:len(qvel)] = qvel
        mujoco.mj_forward(mj_model, mj_data)

        renderer.update_scene(mj_data)
        frame = renderer.render()
        frames.append(frame.copy())

    renderer.close()
    return frames
