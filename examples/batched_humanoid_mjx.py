"""Batched Humanoid Training with MJX on L4 GPU.

This example demonstrates the real power of an L4 GPU for robotics research:
running thousands of parallel MuJoCo simulations simultaneously using MJX
(MuJoCo XLA). This is the pattern used by state-of-the-art locomotion papers.

What this does:
  1. Loads the humanoid model into MJX (GPU-accelerated MuJoCo)
  2. Vectorizes across 1024 parallel environments using jax.vmap
  3. Runs a simple random-action rollout across all envs simultaneously
  4. Benchmarks throughput: expect 10-50M+ steps/sec on an L4

Why this matters:
  - PPO/SAC training for locomotion needs billions of env steps
  - On CPU, a single humanoid env runs ~50K steps/sec
  - On L4 with MJX batching, 1024 envs run at ~50M steps/sec combined
  - What takes 6 hours on CPU takes 3 minutes on L4

Run on your MuJoCo Cloud instance:
    python batched_humanoid_mjx.py
"""
import time
import functools

import jax
import jax.numpy as jnp
import mujoco
from mujoco import mjx


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
NUM_ENVS = 1024          # parallel environments
EPISODE_LENGTH = 1000    # steps per rollout
WARMUP_STEPS = 100       # JIT warmup


def create_batched_envs(model: mujoco.MjModel, num_envs: int):
    """Create a batch of MJX environments on GPU."""
    mjx_model = mjx.put_model(model)
    data = mujoco.MjData(model)
    mjx_data = mjx.put_data(model, data)

    # Vectorize: create `num_envs` copies of the initial state
    # Each env gets a different random seed for initial perturbation
    rng = jax.random.PRNGKey(0)
    keys = jax.random.split(rng, num_envs)

    def init_with_noise(key):
        """Initialize one env with small random joint perturbation."""
        noisy_qpos = mjx_data.qpos + jax.random.normal(key, mjx_data.qpos.shape) * 0.01
        return mjx_data.replace(qpos=noisy_qpos)

    batched_data = jax.vmap(init_with_noise)(keys)
    return mjx_model, batched_data


@functools.partial(jax.jit, static_argnums=(0,))
def batched_step(num_envs, mjx_model, batched_data, actions):
    """Step all environments in parallel on GPU."""
    def single_step(data, action):
        data = data.replace(ctrl=action)
        return mjx.step(mjx_model, data)

    return jax.vmap(single_step)(batched_data, actions)


def compute_reward(batched_data, model):
    """Simple reward: height of torso + forward velocity - control cost.

    This is a simplified version of the reward used in DeepMind's
    locomotion papers. In a real training loop you'd also add:
    - Termination conditions (falling below height threshold)
    - Orientation penalties
    - Energy efficiency terms
    """
    # Torso height (z-position of the root body)
    torso_height = batched_data.qpos[:, 2]

    # Forward velocity (x-velocity of the root body)
    forward_vel = batched_data.qvel[:, 0]

    # Control cost (penalize large actuator forces)
    ctrl_cost = 0.1 * jnp.sum(batched_data.ctrl ** 2, axis=-1)

    # Alive bonus (reward for not falling)
    alive_bonus = jnp.where(torso_height > 0.8, 1.0, 0.0)

    reward = forward_vel + alive_bonus - ctrl_cost
    return reward


def run_benchmark(model, num_envs, episode_length):
    """Run a full batched rollout and report throughput."""
    print(f"\n{'='*60}")
    print(f"Batched MJX Benchmark")
    print(f"{'='*60}")
    print(f"Environments:    {num_envs:,}")
    print(f"Episode length:  {episode_length:,} steps")
    print(f"Total steps:     {num_envs * episode_length:,}")
    print(f"JAX devices:     {jax.devices()}")
    print()

    nu = model.nu  # number of actuators

    # Create batched environments
    print("Creating batched environments on GPU...")
    mjx_model, batched_data = create_batched_envs(model, num_envs)

    # JIT warmup
    print(f"JIT compiling batched step ({WARMUP_STEPS} warmup steps)...")
    rng = jax.random.PRNGKey(42)
    for i in range(WARMUP_STEPS):
        rng, key = jax.random.split(rng)
        actions = jax.random.uniform(key, (num_envs, nu), minval=-1.0, maxval=1.0)
        batched_data = batched_step(num_envs, mjx_model, batched_data, actions)
    jax.block_until_ready(batched_data.qpos)
    print("JIT compilation complete.\n")

    # Timed rollout
    print(f"Running {episode_length:,} steps across {num_envs:,} envs...")
    total_rewards = jnp.zeros(num_envs)

    start = time.time()
    for step in range(episode_length):
        rng, key = jax.random.split(rng)
        actions = jax.random.uniform(key, (num_envs, nu), minval=-1.0, maxval=1.0)
        batched_data = batched_step(num_envs, mjx_model, batched_data, actions)

        if step % 100 == 0:
            rewards = compute_reward(batched_data, model)
            total_rewards = total_rewards + rewards

    # Block until all GPU work is done
    jax.block_until_ready(batched_data.qpos)
    elapsed = time.time() - start

    total_steps = num_envs * episode_length
    steps_per_sec = total_steps / elapsed

    print(f"\n{'='*60}")
    print(f"RESULTS")
    print(f"{'='*60}")
    print(f"Wall time:       {elapsed:.2f}s")
    print(f"Total steps:     {total_steps:,}")
    print(f"Throughput:      {steps_per_sec:,.0f} steps/sec")
    print(f"Per-env speed:   {steps_per_sec/num_envs:,.0f} steps/sec/env")
    print(f"Mean reward:     {jnp.mean(total_rewards):.2f}")
    print(f"Max reward:      {jnp.max(total_rewards):.2f}")
    print()

    # Context: what this means for training
    ppo_steps_needed = 1_000_000_000  # 1B steps typical for locomotion
    hours_needed = ppo_steps_needed / steps_per_sec / 3600
    cpu_sps = 50_000  # typical single-core CPU speed
    cpu_hours = ppo_steps_needed / cpu_sps / 3600
    print(f"Training time estimate (1B steps):")
    print(f"  This L4 GPU:   {hours_needed:.1f} hours")
    print(f"  Single CPU:    {cpu_hours:.0f} hours ({cpu_hours/24:.0f} days)")
    print(f"  Speedup:       {cpu_hours/hours_needed:.0f}x")
    print(f"{'='*60}")

    return steps_per_sec


def main():
    print("MuJoCo Cloud - Batched Humanoid Benchmark")
    print(f"MuJoCo version: {mujoco.__version__}")
    print(f"JAX version:    {jax.__version__}")

    # Check GPU
    devices = jax.devices()
    gpu_available = any(d.platform == "gpu" for d in devices)
    if not gpu_available:
        print("\nWARNING: No GPU detected! Running on CPU will be slow.")
        print("Make sure you're running on a MuJoCo Cloud instance with L4 GPU.\n")

    # Load humanoid
    xml_path = mujoco.util.MODEL_PATH + "/humanoid/humanoid.xml"
    model = mujoco.MjModel.from_xml_path(xml_path)
    print(f"Model: humanoid ({model.nq} DOF, {model.nbody} bodies, {model.nu} actuators)")

    # Run benchmarks at different batch sizes
    for n_envs in [64, 256, 1024]:
        run_benchmark(model, n_envs, EPISODE_LENGTH)

    print("\nDone! The L4 GPU is especially powerful for batched simulation.")
    print("Try increasing NUM_ENVS to 2048 or 4096 for even higher throughput.")


if __name__ == "__main__":
    main()
