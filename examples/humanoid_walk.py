"""MuJoCo Humanoid Walking - CPU vs GPU benchmark.

This example loads the humanoid model and benchmarks MuJoCo simulation
on CPU vs GPU (using MJX with JAX).

Run on your MuJoCo Cloud instance:
    python humanoid_walk.py
"""
import mujoco
from mujoco import mjx
import jax
import jax.numpy as jnp
import time
import numpy as np


def render_frames(model, data, n_frames=60):
    """Render simulation frames and save as video."""
    try:
        import mediapy
    except ImportError:
        print("Install mediapy for video rendering: pip install mediapy")
        return

    renderer = mujoco.Renderer(model, height=480, width=640)
    frames = []

    mujoco.mj_resetData(model, data)
    for i in range(n_frames):
        for _ in range(10):  # 10 substeps per frame
            mujoco.mj_step(model, data)
        renderer.update_scene(data)
        frames.append(renderer.render())

    mediapy.write_video("humanoid_sim.mp4", frames, fps=30)
    print(f"Saved {n_frames} frames to humanoid_sim.mp4")


def benchmark_cpu(model, data, n_steps=10_000):
    """Benchmark CPU simulation."""
    mujoco.mj_resetData(model, data)
    start = time.time()
    for _ in range(n_steps):
        mujoco.mj_step(model, data)
    elapsed = time.time() - start
    return n_steps / elapsed


def benchmark_gpu(model, data, n_steps=10_000):
    """Benchmark GPU simulation with MJX."""
    mjx_model = mjx.put_model(model)
    mjx_data = mjx.put_data(model, data)

    jit_step = jax.jit(mjx.step)

    # Warmup JIT compilation
    mjx_data = jit_step(mjx_model, mjx_data)
    jax.block_until_ready(mjx_data.qpos)

    # Benchmark
    mujoco.mj_resetData(model, data)
    mjx_data = mjx.put_data(model, data)

    start = time.time()
    for _ in range(n_steps):
        mjx_data = jit_step(mjx_model, mjx_data)
    jax.block_until_ready(mjx_data.qpos)
    elapsed = time.time() - start

    return n_steps / elapsed


def main():
    print("MuJoCo Cloud - Humanoid Benchmark")
    print("=" * 40)
    print(f"MuJoCo version: {mujoco.__version__}")

    # Load model
    xml_path = mujoco.util.MODEL_PATH + "/humanoid/humanoid.xml"
    model = mujoco.MjModel.from_xml_path(xml_path)
    data = mujoco.MjData(model)
    print(f"Model: humanoid ({model.nq} DOF, {model.nbody} bodies)")

    # CPU benchmark
    print("\nBenchmarking CPU...")
    cpu_sps = benchmark_cpu(model, data)
    print(f"  CPU: {cpu_sps:,.0f} steps/sec")

    # GPU benchmark
    print("\nBenchmarking GPU (MJX)...")
    devices = jax.devices()
    print(f"  JAX devices: {devices}")
    gpu_sps = benchmark_gpu(model, data)
    print(f"  GPU: {gpu_sps:,.0f} steps/sec")
    print(f"  Speedup: {gpu_sps/cpu_sps:.1f}x")

    # Render
    print("\nRendering simulation video...")
    mujoco.mj_resetData(model, data)
    render_frames(model, data)


if __name__ == "__main__":
    main()
