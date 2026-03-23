"""GCP Compute Engine operations for MuJoCo Cloud."""
from __future__ import annotations

import time
import uuid
from pathlib import Path

from google.cloud import compute_v1
from google.api_core.extended_operation import ExtendedOperation

from .config import (
    MjCloudConfig,
    INSTANCE_LABEL,
    DEFAULT_IMAGE_FAMILY,
    DEFAULT_IMAGE_PROJECT,
    PRESETS,
)

STARTUP_SCRIPT_PATH = Path(__file__).parent / "startup_script.sh"
FIREWALL_RULE_NAME = "mjcloud-allow-jupyter"


def _wait_for_operation(
    operation: ExtendedOperation, verbose: bool = False
) -> None:
    """Wait for a GCP extended operation to complete."""
    result = operation.result()
    if operation.error_code:
        raise RuntimeError(
            f"Operation failed: [{operation.error_code}] {operation.error_message}"
        )
    return result


def _generate_instance_name() -> str:
    """Generate a unique instance name."""
    short_id = uuid.uuid4().hex[:8]
    return f"mjcloud-{short_id}"


def get_startup_script() -> str:
    """Read the startup script content."""
    return STARTUP_SCRIPT_PATH.read_text()


def ensure_firewall_rule(project_id: str) -> None:
    """Ensure firewall rule for Jupyter (port 8888) exists."""
    client = compute_v1.FirewallsClient()

    try:
        client.get(project=project_id, firewall=FIREWALL_RULE_NAME)
        return  # Already exists
    except Exception:
        pass

    rule = compute_v1.Firewall(
        name=FIREWALL_RULE_NAME,
        direction="INGRESS",
        allowed=[
            compute_v1.Allowed(
                I_p_protocol="tcp",
                ports=["8888"],
            )
        ],
        source_ranges=["0.0.0.0/0"],
        target_tags=["mjcloud"],
        description="Allow Jupyter access for MuJoCo Cloud instances",
    )

    operation = client.insert(project=project_id, firewall_resource=rule)
    _wait_for_operation(operation)


def create_instance(
    config: MjCloudConfig,
    name: str | None = None,
    preset: str | None = None,
    machine_type: str | None = None,
    disk_size_gb: int | None = None,
) -> dict:
    """Create a new GCE instance with MuJoCo pre-installed.

    Returns dict with instance details (name, zone, external_ip, status).
    """
    instance_name = name or _generate_instance_name()
    mt = machine_type or (PRESETS[preset]["machine_type"] if preset else config.machine_type)
    disk = disk_size_gb or config.disk_size_gb
    gpu_type = PRESETS.get(preset, PRESETS["medium"])["gpu_type"]

    # Ensure firewall rule exists
    ensure_firewall_rule(config.project_id)

    client = compute_v1.InstancesClient()

    # Boot disk
    boot_disk = compute_v1.AttachedDisk(
        auto_delete=True,
        boot=True,
        initialize_params=compute_v1.AttachedDiskInitializeParams(
            disk_size_gb=disk,
            source_image=f"projects/{DEFAULT_IMAGE_PROJECT}/global/images/family/{DEFAULT_IMAGE_FAMILY}",
            disk_type=f"zones/{config.zone}/diskTypes/pd-ssd",
        ),
    )

    # Network interface with external IP
    network_interface = compute_v1.NetworkInterface(
        access_configs=[
            compute_v1.AccessConfig(
                name="External NAT",
                type_="ONE_TO_ONE_NAT",
            )
        ],
    )

    # GPU accelerator
    accelerator = compute_v1.AcceleratorConfig(
        accelerator_count=1,
        accelerator_type=f"zones/{config.zone}/acceleratorTypes/{gpu_type}",
    )

    # Instance resource
    instance = compute_v1.Instance(
        name=instance_name,
        machine_type=f"zones/{config.zone}/machineTypes/{mt}",
        disks=[boot_disk],
        network_interfaces=[network_interface],
        guest_accelerators=[accelerator],
        scheduling=compute_v1.Scheduling(
            on_host_maintenance="TERMINATE",
            automatic_restart=True,
        ),
        metadata=compute_v1.Metadata(
            items=[
                compute_v1.Items(
                    key="startup-script",
                    value=get_startup_script(),
                ),
            ]
        ),
        labels={"mjcloud": "true"},
        tags=compute_v1.Tags(items=["mjcloud"]),
    )

    operation = client.insert(
        project=config.project_id,
        zone=config.zone,
        instance_resource=instance,
    )
    _wait_for_operation(operation)

    return get_instance(config, instance_name)


def get_instance(config: MjCloudConfig, name: str) -> dict:
    """Get instance details."""
    client = compute_v1.InstancesClient()
    instance = client.get(
        project=config.project_id,
        zone=config.zone,
        instance=name,
    )

    external_ip = None
    if instance.network_interfaces:
        for ni in instance.network_interfaces:
            if ni.access_configs:
                for ac in ni.access_configs:
                    if ac.nat_i_p:
                        external_ip = ac.nat_i_p
                        break

    return {
        "name": instance.name,
        "zone": config.zone,
        "status": instance.status,
        "external_ip": external_ip,
        "machine_type": instance.machine_type.split("/")[-1],
        "creation_timestamp": instance.creation_timestamp,
    }


def list_instances(config: MjCloudConfig) -> list[dict]:
    """List all mjcloud instances."""
    client = compute_v1.InstancesClient()

    instances = []
    request = compute_v1.ListInstancesRequest(
        project=config.project_id,
        zone=config.zone,
        filter='labels.mjcloud="true"',
    )

    for instance in client.list(request=request):
        external_ip = None
        if instance.network_interfaces:
            for ni in instance.network_interfaces:
                if ni.access_configs:
                    for ac in ni.access_configs:
                        if ac.nat_i_p:
                            external_ip = ac.nat_i_p
                            break

        instances.append({
            "name": instance.name,
            "zone": config.zone,
            "status": instance.status,
            "external_ip": external_ip,
            "machine_type": instance.machine_type.split("/")[-1],
            "creation_timestamp": instance.creation_timestamp,
        })

    return instances


def delete_instance(config: MjCloudConfig, name: str) -> None:
    """Delete an instance."""
    client = compute_v1.InstancesClient()
    operation = client.delete(
        project=config.project_id,
        zone=config.zone,
        instance=name,
    )
    _wait_for_operation(operation)


def wait_for_running(
    config: MjCloudConfig, name: str, timeout: int = 300, poll_interval: int = 5
) -> dict:
    """Wait for instance to reach RUNNING state."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        info = get_instance(config, name)
        if info["status"] == "RUNNING":
            return info
        time.sleep(poll_interval)
    raise TimeoutError(f"Instance {name} did not reach RUNNING state within {timeout}s")
