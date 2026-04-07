"""Visual themes — floor, skybox, and lighting presets for simulations.

Creators pick a visual mood, not RGB values. These themes apply to both
local passive-physics renders (XML templates) and GPU policy renders.
"""

THEMES = {
    "studio": {
        "label": "Studio",
        "description": "Dark film set with dramatic lighting",
        "floor_rgb": [0.15, 0.15, 0.17],
        "sky_rgb1": [0.03, 0.03, 0.05],
        "sky_rgb2": [0.08, 0.08, 0.12],
        "light_diffuse": [0.9, 0.9, 0.95],
        "light_dir": [-1, -1, -1.5],
        "ambient": [0.15, 0.15, 0.18],
    },
    "outdoor": {
        "label": "Outdoor",
        "description": "Open field under blue sky",
        "floor_rgb": [0.35, 0.42, 0.28],
        "sky_rgb1": [0.45, 0.65, 0.85],
        "sky_rgb2": [0.75, 0.85, 0.95],
        "light_diffuse": [1.0, 0.95, 0.85],
        "light_dir": [-0.5, -1, -2],
        "ambient": [0.35, 0.38, 0.45],
    },
    "industrial": {
        "label": "Industrial",
        "description": "Concrete warehouse floor, harsh overhead lights",
        "floor_rgb": [0.3, 0.3, 0.32],
        "sky_rgb1": [0.2, 0.2, 0.22],
        "sky_rgb2": [0.35, 0.35, 0.38],
        "light_diffuse": [1.0, 1.0, 1.0],
        "light_dir": [0, 0, -1],
        "ambient": [0.3, 0.3, 0.3],
    },
    "desert": {
        "label": "Desert",
        "description": "Sandy ground, warm golden hour light",
        "floor_rgb": [0.65, 0.55, 0.38],
        "sky_rgb1": [0.85, 0.6, 0.35],
        "sky_rgb2": [0.95, 0.8, 0.6],
        "light_diffuse": [1.0, 0.85, 0.6],
        "light_dir": [-2, -0.5, -1],
        "ambient": [0.4, 0.32, 0.22],
    },
    "night": {
        "label": "Night",
        "description": "Dark ground, moonlit atmosphere",
        "floor_rgb": [0.1, 0.1, 0.12],
        "sky_rgb1": [0.02, 0.02, 0.06],
        "sky_rgb2": [0.05, 0.05, 0.15],
        "light_diffuse": [0.4, 0.45, 0.6],
        "light_dir": [-1, -1, -2],
        "ambient": [0.06, 0.06, 0.1],
    },
    "snow": {
        "label": "Snow",
        "description": "White ground, overcast cold light",
        "floor_rgb": [0.85, 0.87, 0.9],
        "sky_rgb1": [0.6, 0.65, 0.7],
        "sky_rgb2": [0.8, 0.82, 0.85],
        "light_diffuse": [0.85, 0.88, 0.95],
        "light_dir": [-0.5, -1, -1.5],
        "ambient": [0.45, 0.47, 0.52],
    },
}

DEFAULT_THEME = "studio"


def get_theme(name: str) -> dict:
    return THEMES.get(name.lower(), THEMES[DEFAULT_THEME])
