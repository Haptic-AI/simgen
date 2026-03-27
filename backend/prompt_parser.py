"""AI prompt parser — uses Claude API to interpret user prompts into simulation configs."""

import json
import os

import anthropic

from backend.templates import TEMPLATE_SCHEMAS, get_schema_description

client = anthropic.Anthropic()

SYSTEM_PROMPT = """You are a physics simulation configurator. Given a user's natural language description of a physics scenario, you must:

1. Select the best matching simulation template
2. Generate exactly 4 interesting parameter variations

Available templates and their parameters:
{schema}

Rules:
- Pick the single best-matching template
- All parameter values MUST be within the specified min/max ranges
- Make the 4 variations meaningfully different — explore the parameter space
- Give each variation a short descriptive label (2-4 words)
- If the prompt is vague, pick the most visually interesting template and create diverse variations
"""

TOOL_SCHEMA = {
    "name": "configure_simulation",
    "description": "Configure a MuJoCo simulation based on the user's prompt",
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
                "description": "Brief description of what was interpreted from the prompt",
            },
            "variations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "label": {"type": "string", "description": "Short label for this variation"},
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
                "description": "Exactly 4 parameter variations",
            },
        },
        "required": ["template", "description", "variations"],
    },
}


def parse_prompt(user_prompt: str) -> dict:
    """
    Parse a user prompt into a simulation configuration using Claude.

    Returns:
        {
            "template": "pendulum",
            "description": "...",
            "variations": [
                {"label": "Earth gravity", "params": {"length": 1.0, ...}},
                ...
            ]
        }
    """
    schema_desc = get_schema_description()
    system = SYSTEM_PROMPT.format(schema=schema_desc)

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        system=system,
        tools=[TOOL_SCHEMA],
        tool_choice={"type": "tool", "name": "configure_simulation"},
        messages=[{"role": "user", "content": user_prompt}],
    )

    # Extract tool use result
    for block in response.content:
        if block.type == "tool_use":
            return block.input

    raise RuntimeError("Claude did not return a tool use response")
