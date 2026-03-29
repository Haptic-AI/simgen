"""Template schemas — defines available simulation types and their parameter ranges."""

import os

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")

TEMPLATE_SCHEMAS = {
    "pendulum": {
        "description": "Simple pendulum swinging under gravity",
        "params": {
            "length": {"min": 0.2, "max": 3.0, "default": 1.0, "unit": "meters"},
            "damping": {"min": 0.0, "max": 5.0, "default": 0.1, "unit": "Ns/m"},
            "initial_angle": {"min": -3.14, "max": 3.14, "default": 1.57, "unit": "radians"},
            "gravity": {"min": 0.5, "max": 30.0, "default": 9.81, "unit": "m/s^2"},
        },
        "sim_duration": 15.0,
        "timestep": 0.002,
    },
    "bouncing_ball": {
        "description": "Ball bouncing on a surface with configurable elasticity",
        "params": {
            "elasticity": {"min": 0.1, "max": 0.99, "default": 0.8, "unit": "coefficient"},
            "initial_height": {"min": 0.5, "max": 5.0, "default": 2.0, "unit": "meters"},
            "ball_size": {"min": 0.05, "max": 0.5, "default": 0.1, "unit": "meters"},
            "gravity": {"min": 0.5, "max": 30.0, "default": 9.81, "unit": "m/s^2"},
        },
        "sim_duration": 15.0,
        "timestep": 0.002,
    },
    "robot_arm": {
        "description": "2-link robot arm reaching toward a target",
        "params": {
            "stiffness": {"min": 1.0, "max": 50.0, "default": 10.0, "unit": "N/rad"},
            "damping": {"min": 0.1, "max": 10.0, "default": 1.0, "unit": "Ns/rad"},
            "target_angle": {"min": -2.0, "max": 2.0, "default": 1.0, "unit": "radians"},
            "speed": {"min": 0.5, "max": 5.0, "default": 1.0, "unit": "multiplier"},
        },
        "sim_duration": 15.0,
        "timestep": 0.002,
    },
    "cartpole": {
        "description": "Classic cart-pole balancing problem",
        "params": {
            "pole_length": {"min": 0.3, "max": 2.0, "default": 0.6, "unit": "meters"},
            "cart_mass": {"min": 0.5, "max": 5.0, "default": 1.0, "unit": "kg"},
            "initial_angle": {"min": -0.5, "max": 0.5, "default": 0.1, "unit": "radians"},
            "gravity": {"min": 0.5, "max": 30.0, "default": 9.81, "unit": "m/s^2"},
        },
        "sim_duration": 15.0,
        "timestep": 0.002,
    },
    "humanoid": {
        "description": "Humanoid figure in a dramatic pose or falling",
        "params": {
            "initial_height": {"min": 0.8, "max": 2.0, "default": 1.3, "unit": "meters"},
            "push_force": {"min": -200.0, "max": 200.0, "default": 0.0, "unit": "N"},
            "gravity": {"min": 0.5, "max": 30.0, "default": 9.81, "unit": "m/s^2"},
            "damping": {"min": 0.0, "max": 5.0, "default": 0.5, "unit": "Ns/m"},
        },
        "sim_duration": 15.0,
        "timestep": 0.002,
    },
}


def get_template_xml(template_name: str) -> str:
    """Load a MuJoCo XML template by name."""
    path = os.path.join(TEMPLATES_DIR, f"{template_name}.xml")
    with open(path) as f:
        return f.read()


def get_schema_description() -> str:
    """Generate a human-readable description of all templates for the AI prompt."""
    lines = []
    for name, schema in TEMPLATE_SCHEMAS.items():
        lines.append(f"\n## {name}")
        lines.append(f"Description: {schema['description']}")
        lines.append("Parameters:")
        for pname, pinfo in schema["params"].items():
            lines.append(
                f"  - {pname}: {pinfo['min']} to {pinfo['max']} "
                f"(default: {pinfo['default']}, unit: {pinfo['unit']})"
            )
    return "\n".join(lines)
