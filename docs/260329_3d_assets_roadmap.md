# 2026-03-29 — 3D Assets Roadmap: From Colored Floors to Real Environments

## The Problem

MuJoCo renders physics beautifully but its visual fidelity is basic — solid colors,
simple shapes, gradient skyboxes. Creators want "warehouse", "park", "city street" —
not gray rectangles. Here's how to bridge that gap.

## Current State: Visual Themes (just shipped)

We have 6 visual themes (Studio, Outdoor, Industrial, Desert, Night, Snow) that
change floor color, sky gradient, and lighting. This is mood lighting, not environments.

## The Upgrade Path: Real 3D Assets in MuJoCo

### Level 1: MuJoCo Native Assets (free, immediate)

MuJoCo supports meshes (STL/OBJ), textures (PNG), and heightmaps natively in MJCF XML.

**What you can do today:**
```xml
<asset>
  <!-- Load a texture from a PNG file -->
  <texture name="concrete" type="2d" file="concrete.png"/>
  <material name="floor_mat" texture="concrete" texrepeat="10 10"/>

  <!-- Load a 3D mesh -->
  <mesh name="table" file="table.stl" scale="0.01 0.01 0.01"/>
</asset>

<worldbody>
  <geom type="plane" material="floor_mat" size="20 20 0.1"/>
  <body name="table" pos="2 0 0">
    <geom type="mesh" mesh="table" rgba="0.5 0.4 0.3 1"/>
  </body>
</worldbody>
```

**Where to get assets:**
- [TurboSquid](https://www.turbosquid.com) — thousands of free STL/OBJ models
- [Sketchfab](https://sketchfab.com) — search for "warehouse", "props", etc. Download as OBJ
- [Google Poly / Poly Haven](https://polyhaven.com) — free PBR textures (concrete, wood, grass, asphalt)
- [KitBash3D](https://kitbash3d.com) — environment kits

**Limitations:** MuJoCo meshes are collision shapes. Complex meshes (1M+ triangles)
will slow down physics. Use simplified collision meshes + visual-only high-detail meshes.

### Level 2: NVIDIA Isaac Sim / Omniverse Assets (free with account)

**NVIDIA Isaac Sim** includes a massive library of 3D environments and robots.
The assets are in USD (Universal Scene Description) format.

**How to get them:**
1. Create a free NVIDIA Developer account: https://developer.nvidia.com
2. Install NVIDIA Omniverse Launcher: https://www.nvidia.com/en-us/omniverse/
3. Open Isaac Sim → Assets panel → browse environments:
   - Warehouse (multiple layouts)
   - Office
   - Hospital
   - Factory floor
   - Outdoor terrain
4. Export as USD → convert to OBJ/STL for MuJoCo

**The conversion pipeline:**
```
Isaac Sim USD → Blender (import USD) → Export OBJ/STL → MuJoCo MJCF XML
```

**Tools:**
- `usd-core` Python package: `pip install usd-core`
- Blender (free): import USD, export OBJ
- `obj2mjcf`: community tool that converts OBJ → MJCF XML

**Key assets from Isaac Sim:**
| Asset | Use case |
|-------|----------|
| Simple Warehouse | Industrial floor, shelving, pallets |
| Office | Desks, chairs, cubicles |
| Factory | Conveyor belts, machinery |
| Hospital | Beds, corridors, equipment |

### Level 3: MuJoCo Menagerie (free, research-grade)

[MuJoCo Menagerie](https://github.com/google-deepmind/mujoco_menagerie) is Google DeepMind's
collection of high-quality robot models in MJCF format. Ready to use, no conversion needed.

```bash
pip install mujoco-menagerie
```

**Available models:**
- Unitree H1 / G1 humanoid robots
- Boston Dynamics Spot
- KUKA robot arms
- Shadow dexterous hand
- Franka Emika Panda
- Universal Robots UR5e
- Various quadrupeds

These could REPLACE our primitive humanoid with a realistic robot model.

### Level 4: NVIDIA Omniverse + MuJoCo (advanced)

NVIDIA recently added [MuJoCo support to Omniverse](https://developer.nvidia.com/blog/nvidia-adds-mujoco-support/).
This means you can run MuJoCo physics INSIDE Omniverse's photorealistic renderer.

**What this enables:**
- MuJoCo physics (accurate, fast) + Omniverse RTX rendering (photorealistic)
- Real-time ray tracing, global illumination, PBR materials
- The humanoid walks in a fully lit warehouse with realistic shadows

**Requirements:** NVIDIA GPU with RTX (your H100 qualifies), Omniverse installed.

**This is the endgame** — but it's a significant integration effort.

## Recommended Implementation Order

### Phase 1: Texture packs (1-2 hours)

Download free textures from Poly Haven and apply to our floor planes:
```
concrete_rough.png → Industrial theme
grass_field.png → Outdoor theme
sand_desert.png → Desert theme
asphalt_wet.png → Night theme
```

Store in `backend/assets/textures/`. Apply via `<texture>` in XML.

### Phase 2: Simple prop meshes (1 day)

Download 5-10 simple OBJ models (table, chair, cone, barrier, box stack)
and create "environment presets" that scatter them around the scene:
- Warehouse: boxes, pallets, shelving
- Park: bench, tree (simple), fence
- Street: car (simple), traffic cone, streetlight

### Phase 3: MuJoCo Menagerie robots (2-3 days)

Replace our primitive humanoid with a proper robot model from Menagerie.
Retrain walking policies on the new model using MJX on the H100.

### Phase 4: Isaac Sim environments (1 week)

Convert a few Isaac Sim environments to MJCF:
- Simple Warehouse → full warehouse floor with shelving
- Office → furniture and corridors
- Factory → industrial equipment

### Phase 5: Omniverse integration (2-4 weeks)

Full photorealistic rendering pipeline:
MuJoCo physics → Omniverse RTX rendering → MP4

## Quick Win: Texture Pack Setup

```bash
# Download free textures
mkdir -p backend/assets/textures
cd backend/assets/textures

# From Poly Haven (CC0 license):
# https://polyhaven.com/textures
# Download 1K versions of:
# - concrete_floor_worn_001
# - grass_field
# - sand_coast_01
# - asphalt_02
# - snow_02

# Each texture is a folder with diffuse, normal, roughness maps
# MuJoCo only uses the diffuse (color) map
```

Then update the XML templates to reference textures:
```xml
<texture name="floor_tex" type="2d" file="assets/textures/concrete_floor.png"/>
<material name="floor_mat" texture="floor_tex" texrepeat="8 8" reflectance="0.1"/>
<geom type="plane" material="floor_mat" size="20 20 0.1"/>
```

## Resources

- [MuJoCo MJCF Modeling Guide](https://mujoco.readthedocs.io/en/stable/modeling.html)
- [MuJoCo Menagerie](https://github.com/google-deepmind/mujoco_menagerie)
- [NVIDIA Isaac Sim](https://developer.nvidia.com/isaac-sim)
- [Poly Haven Free Textures](https://polyhaven.com/textures)
- [obj2mjcf converter](https://github.com/kevinzakka/obj2mjcf)
- [NVIDIA Omniverse + MuJoCo](https://developer.nvidia.com/blog/nvidia-adds-mujoco-support/)
- [Universal Scene Description (USD)](https://openusd.org)
