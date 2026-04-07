"""Environment presets — real-world physics baked into named configs.

Creators pick "Earth" or "Mars" instead of typing gravity=3.72.
"""

ENVIRONMENTS = {
    "earth": {
        "label": "Earth",
        "description": "Standard Earth conditions — what we all know",
        "gravity": 9.81,
        "damping": 0.5,
        "air_density": 1.225,
    },
    "moon": {
        "label": "Moon",
        "description": "1/6th gravity — everything floats longer, falls slower",
        "gravity": 1.62,
        "damping": 0.05,
        "air_density": 0.0,
    },
    "mars": {
        "label": "Mars",
        "description": "38% Earth gravity — between Earth and Moon",
        "gravity": 3.72,
        "damping": 0.15,
        "air_density": 0.020,
    },
    "mercury": {
        "label": "Mercury",
        "description": "38% Earth gravity, no atmosphere — similar to Mars but harsher",
        "gravity": 3.70,
        "damping": 0.02,
        "air_density": 0.0,
    },
    "jupiter": {
        "label": "Jupiter",
        "description": "2.5x Earth gravity — everything is heavy, falls fast",
        "gravity": 24.79,
        "damping": 2.0,
        "air_density": 0.16,
    },
    "zero_g": {
        "label": "Zero-G",
        "description": "Weightlessness — space station, orbit",
        "gravity": 0.01,
        "damping": 0.0,
        "air_density": 0.0,
    },
}

DEFAULT_ENVIRONMENT = "earth"


def get_environment(name: str) -> dict:
    """Get environment config by name, defaulting to Earth."""
    return ENVIRONMENTS.get(name.lower(), ENVIRONMENTS[DEFAULT_ENVIRONMENT])


def get_environment_descriptions() -> str:
    """Human-readable list for the AI prompt."""
    lines = []
    for key, env in ENVIRONMENTS.items():
        lines.append(f"- **{env['label']}** (`{key}`): {env['description']} (gravity={env['gravity']} m/s²)")
    return "\n".join(lines)
