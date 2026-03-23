"""MuJoCo Cloud configuration."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml

CONFIG_DIR = Path.home() / ".mjcloud"
CONFIG_FILE = CONFIG_DIR / "config.yaml"

PRESETS = {
    "small": {
        "machine_type": "g2-standard-4",
        "gpu_count": 1,
        "gpu_type": "nvidia-l4",
        "description": "1x L4, 4 vCPU, 16GB RAM (~$0.70/hr)",
    },
    "medium": {
        "machine_type": "g2-standard-8",
        "gpu_count": 1,
        "gpu_type": "nvidia-l4",
        "description": "1x L4, 8 vCPU, 32GB RAM (~$0.98/hr)",
    },
    "large": {
        "machine_type": "g2-standard-16",
        "gpu_count": 1,
        "gpu_type": "nvidia-l4",
        "description": "1x L4, 16 vCPU, 64GB RAM (~$1.53/hr)",
    },
}

DEFAULT_ZONE = "us-central1-a"
DEFAULT_MACHINE_TYPE = "g2-standard-8"
DEFAULT_DISK_SIZE_GB = 100
DEFAULT_IMAGE_FAMILY = "ubuntu-2204-lts"
DEFAULT_IMAGE_PROJECT = "ubuntu-os-cloud"
INSTANCE_LABEL = "mjcloud"


@dataclass
class MjCloudConfig:
    project_id: str = ""
    zone: str = DEFAULT_ZONE
    machine_type: str = DEFAULT_MACHINE_TYPE
    disk_size_gb: int = DEFAULT_DISK_SIZE_GB
    image_family: str = DEFAULT_IMAGE_FAMILY
    image_project: str = DEFAULT_IMAGE_PROJECT

    @classmethod
    def load(cls) -> MjCloudConfig:
        """Load config from ~/.mjcloud/config.yaml, env vars, or defaults."""
        config = cls()

        # Load from file
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE) as f:
                data = yaml.safe_load(f) or {}
            for key, value in data.items():
                if hasattr(config, key):
                    setattr(config, key, value)

        # Env var overrides
        if project := os.environ.get("MJCLOUD_PROJECT"):
            config.project_id = project
        if zone := os.environ.get("MJCLOUD_ZONE"):
            config.zone = zone
        if os.environ.get("GOOGLE_CLOUD_PROJECT"):
            config.project_id = config.project_id or os.environ["GOOGLE_CLOUD_PROJECT"]

        return config

    def save(self) -> None:
        """Save config to ~/.mjcloud/config.yaml."""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        data = {
            "project_id": self.project_id,
            "zone": self.zone,
            "machine_type": self.machine_type,
            "disk_size_gb": self.disk_size_gb,
        }
        with open(CONFIG_FILE, "w") as f:
            yaml.dump(data, f, default_flow_style=False)
