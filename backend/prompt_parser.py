"""AI prompt parser — translates creative prompts into simulation configs.

Designed for filmmakers and creators, not physicists. Claude acts as a
creative director who understands both artistic intent and physics.
The system learns from user feedback over time.
"""

import json
import os

import anthropic

from backend.environments import ENVIRONMENTS, get_environment, get_environment_descriptions
from backend.physics_rules import PHYSICS_RULES
from backend.templates import TEMPLATE_SCHEMAS, get_schema_description

client = anthropic.Anthropic()

SYSTEM_PROMPT = """You are SimGen's creative simulation director AND physics referee.

Your dual role:
1. CREATIVE DIRECTOR — translate artistic vision into beautiful simulations
2. PHYSICS REFEREE — ensure every simulation is grounded in real-world physics

When someone says "a dancer leaping gracefully," you create something beautiful
AND physically honest. A real human can jump ~2 feet, an athlete ~3 feet.
You don't make them fly — you make reality look stunning.

## Available simulation templates
{schema}

## Environment presets
The user selects an environment that defines the physics rules. Use its gravity
and damping as the BASE. The environment IS the creative canvas — Earth is grounded,
Moon lets things float, Jupiter makes everything heavy.
{environments}

Current environment: **{current_env}** (gravity={env_gravity} m/s²)

{physics_rules}

## Rules
- Pick the single best template for the user's creative vision
- Generate exactly 4 cinematic variations as a SPECTRUM from realistic to stylized:
  1. REALISTIC — exactly what this looks like in the real world
  2. CINEMATIC — slightly enhanced for visual drama
  3. STYLIZED — noticeably enhanced but still grounded
  4. PUSHING LIMITS — most extreme version that's still physically coherent
- Use the environment's gravity as the base — NEVER override it unless the creator explicitly asks
- If they want effects that break the current environment's physics, SUGGEST a different environment in the description (e.g., "Try Moon for more float time")
- Labels should be CINEMATIC and DESCRIPTIVE — NOT technical jargon
- All parameter values MUST be within the specified min/max ranges
- In the "description" field, briefly explain any physics constraints you applied and suggest alternatives if the prompt was pushing limits
{feedback_context}"""

TOOL_SCHEMA = {
    "name": "configure_simulation",
    "description": "Configure a MuJoCo simulation based on the user's creative vision",
    "input_schema": {
        "type": "object",
        "properties": {
            "template": {
                "type": "string",
                "enum": list(TEMPLATE_SCHEMAS.keys()),
                "description": "The simulation template to use",
            },
            "description": {
                "type": "string",
                "description": "Creative description of how the prompt was interpreted — speak to the artist, not the engineer",
            },
            "variations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "label": {
                            "type": "string",
                            "description": "Cinematic label like 'Graceful Arc' or 'Violent Tumble' — NOT technical like 'High Damping'",
                        },
                        "params": {
                            "type": "object",
                            "description": "Parameter values for this variation",
                            "additionalProperties": {"type": "number"},
                        },
                    },
                    "required": ["label", "params"],
                },
                "minItems": 4,
                "maxItems": 4,
                "description": "Exactly 4 cinematic variations — like 4 different takes of a scene",
            },
        },
        "required": ["template", "description", "variations"],
    },
}


def _build_feedback_context() -> str:
    """Query the DB for rated simulations and build context for Claude."""
    try:
        from backend.db import get_top_rated, get_recent_feedback
    except Exception:
        return ""

    top_rated = get_top_rated(limit=15)
    recent_down = [f for f in get_recent_feedback(limit=20) if f.get("rating") == "down"]

    if not top_rated and not recent_down:
        return ""

    lines = ["\n\n## Learning from creator feedback\n"]
    lines.append("This creator has rated past simulations. Lean toward styles and parameters "
                 "they've upvoted. Avoid patterns they've downvoted.\n")

    if top_rated:
        lines.append("### Liked (create more like these):")
        for sim in top_rated[:10]:
            params = json.loads(sim["params"]) if isinstance(sim["params"], str) else sim["params"]
            lines.append(f'- "{sim["prompt"]}" → {sim["template"]}, '
                         f'"{sim["label"]}" — {json.dumps(params)}')

    if recent_down:
        lines.append("\n### Disliked (avoid these patterns):")
        for sim in recent_down[:5]:
            params = json.loads(sim["params"]) if isinstance(sim["params"], str) else sim["params"]
            lines.append(f'- "{sim["prompt"]}" → {sim["template"]}, '
                         f'"{sim["label"]}" — {json.dumps(params)}')

    return "\n".join(lines)


def parse_prompt(user_prompt: str, environment: str = "earth") -> dict:
    """
    Parse a creative prompt into simulation configs.

    Args:
        user_prompt: Natural language scene description from the creator
        environment: Environment preset name (earth, mars, moon, etc.)

    Returns:
        {
            "template": "humanoid",
            "description": "A dramatic hero moment...",
            "variations": [
                {"label": "Graceful Descent", "params": {...}},
                ...
            ]
        }
    """
    env = get_environment(environment)
    schema_desc = get_schema_description()
    env_desc = get_environment_descriptions()
    feedback_context = _build_feedback_context()

    system = SYSTEM_PROMPT.format(
        schema=schema_desc,
        environments=env_desc,
        current_env=env["label"],
        env_gravity=env["gravity"],
        physics_rules=PHYSICS_RULES,
        feedback_context=feedback_context,
    )

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        system=system,
        tools=[TOOL_SCHEMA],
        tool_choice={"type": "tool", "name": "configure_simulation"},
        messages=[{"role": "user", "content": user_prompt}],
    )

    for block in response.content:
        if block.type == "tool_use":
            result = block.input
            # Inject environment gravity into any variation that doesn't explicitly set it
            for variation in result.get("variations", []):
                params = variation.get("params", {})
                if "gravity" not in params:
                    params["gravity"] = env["gravity"]
                if "damping" not in params and "damping" in params:
                    params["damping"] = env["damping"]
            return result

    raise RuntimeError("Claude did not return a tool use response")


def parse_prompt_with_base(
    user_prompt: str,
    base_template: str,
    base_params: dict,
    base_label: str,
    environment: str = "earth",
) -> dict:
    """
    Generate 4 variations around a base simulation the user liked.

    This is the "iterate on a winner" flow — the user picked one result
    and wants to explore nearby parameter space.
    """
    env = get_environment(environment)
    schema_desc = get_schema_description()
    feedback_context = _build_feedback_context()

    system = f"""You are a creative simulation director helping a filmmaker iterate on a scene they liked.

The creator picked a simulation they want to refine. Generate 4 new variations that are
CLOSE to the base but each explore a different creative direction. Think of it like a
director saying "I like this take, now give me one that's slightly more dramatic,
one that's subtler, one that's faster, one that pushes further."

## Available templates
{schema_desc}

## Current environment: {env['label']} (gravity={env['gravity']} m/s²)

## The simulation they liked
- Template: {base_template}
- Label: "{base_label}"
- Parameters: {json.dumps(base_params)}

## Rules
- Use the SAME template: {base_template}
- Keep parameters CLOSE to the base — vary by 10-40%, not 500%
- Each variation should have a clear creative direction
- Labels should describe the creative intent ("More Dramatic", "Subtle Grace", "Raw Power")
- If the user added instructions, incorporate them while staying close to the base
{feedback_context}"""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        system=system,
        tools=[TOOL_SCHEMA],
        tool_choice={"type": "tool", "name": "configure_simulation"},
        messages=[{"role": "user", "content": user_prompt or "Give me 4 refined variations of this scene"}],
    )

    for block in response.content:
        if block.type == "tool_use":
            result = block.input
            result["template"] = base_template  # Force same template
            for variation in result.get("variations", []):
                params = variation.get("params", {})
                if "gravity" not in params:
                    params["gravity"] = env["gravity"]
            return result

    raise RuntimeError("Claude did not return a tool use response")
