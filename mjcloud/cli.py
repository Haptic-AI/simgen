"""MuJoCo Cloud CLI - One-click MuJoCo GPU simulation environments."""
from __future__ import annotations

import os
import subprocess
import sys
import webbrowser

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

from .config import MjCloudConfig, PRESETS, CONFIG_DIR
from . import gcp

console = Console()


def get_config(project: str | None = None, zone: str | None = None) -> MjCloudConfig:
    """Load config with CLI overrides."""
    config = MjCloudConfig.load()
    if project:
        config.project_id = project
    if zone:
        config.zone = zone

    if not config.project_id:
        console.print(
            "[red]No GCP project configured.[/red]\n"
            "Set it with: [bold]mjcloud config --project YOUR_PROJECT_ID[/bold]\n"
            "Or set GOOGLE_CLOUD_PROJECT or MJCLOUD_PROJECT env var."
        )
        raise SystemExit(1)

    return config


@click.group()
@click.version_option()
def cli():
    """MuJoCo Cloud - One-click GPU simulation environments.

    Spin up an NVIDIA L4 GPU instance with MuJoCo, Jupyter, and examples
    pre-installed. Ready to simulate in minutes.
    """
    pass


@cli.command()
@click.option("--project", help="GCP project ID")
@click.option("--zone", default=None, help="GCP zone (default: us-central1-a)")
@click.option("--name", default=None, help="Instance name (auto-generated if not set)")
@click.option(
    "--preset",
    type=click.Choice(list(PRESETS.keys())),
    default="medium",
    help="Instance size preset",
)
@click.option("--disk-size", type=int, default=None, help="Boot disk size in GB")
@click.option("--dry-run", is_flag=True, help="Show what would be created without doing it")
def deploy(project, zone, name, preset, disk_size, dry_run):
    """Deploy a new MuJoCo simulation environment."""
    config = get_config(project, zone)
    preset_info = PRESETS[preset]

    if dry_run:
        console.print(Panel(
            f"[bold]Instance:[/bold] {name or 'mjcloud-<auto>'}\n"
            f"[bold]Preset:[/bold] {preset} ({preset_info['description']})\n"
            f"[bold]Machine:[/bold] {preset_info['machine_type']}\n"
            f"[bold]GPU:[/bold] {preset_info['gpu_type']}\n"
            f"[bold]Zone:[/bold] {config.zone}\n"
            f"[bold]Disk:[/bold] {disk_size or config.disk_size_gb}GB SSD\n"
            f"[bold]Project:[/bold] {config.project_id}",
            title="[bold green]Dry Run - Would Create",
            box=box.ROUNDED,
        ))
        return

    console.print(f"[bold]Deploying MuJoCo environment[/bold] ({preset}: {preset_info['description']})")

    with console.status("[bold green]Creating instance..."):
        info = gcp.create_instance(
            config,
            name=name,
            preset=preset,
            disk_size_gb=disk_size,
        )

    console.print(f"[green]Instance created:[/green] {info['name']}")

    with console.status("[bold green]Waiting for instance to start..."):
        info = gcp.wait_for_running(config, info["name"])

    ip = info["external_ip"]
    console.print()
    console.print(Panel(
        f"[bold green]Your MuJoCo environment is running![/bold green]\n\n"
        f"[bold]Instance:[/bold]  {info['name']}\n"
        f"[bold]IP:[/bold]        {ip}\n"
        f"[bold]Machine:[/bold]   {info['machine_type']}\n"
        f"[bold]Status:[/bold]    {info['status']}\n\n"
        f"[bold]SSH:[/bold]       [cyan]mjcloud ssh {info['name']}[/cyan]\n"
        f"[bold]Jupyter:[/bold]   [cyan]http://{ip}:8888[/cyan]\n\n"
        f"[dim]Note: MuJoCo setup takes ~5-10 min after boot. "
        f"Check progress with: ssh in and tail -f /var/log/mjcloud-setup.log[/dim]",
        title="[bold]MuJoCo Cloud",
        box=box.DOUBLE,
    ))


@cli.command("list")
@click.option("--project", help="GCP project ID")
@click.option("--zone", default=None, help="GCP zone")
def list_instances(project, zone):
    """List all MuJoCo Cloud instances."""
    config = get_config(project, zone)

    with console.status("[bold green]Fetching instances..."):
        instances = gcp.list_instances(config)

    if not instances:
        console.print("[dim]No MuJoCo Cloud instances found.[/dim]")
        return

    table = Table(title="MuJoCo Cloud Instances", box=box.ROUNDED)
    table.add_column("Name", style="cyan")
    table.add_column("Status")
    table.add_column("IP")
    table.add_column("Machine Type")
    table.add_column("Jupyter")

    for inst in instances:
        status_style = "green" if inst["status"] == "RUNNING" else "yellow"
        ip = inst["external_ip"] or "-"
        jupyter = f"http://{ip}:8888" if inst["external_ip"] else "-"
        table.add_row(
            inst["name"],
            f"[{status_style}]{inst['status']}[/{status_style}]",
            ip,
            inst["machine_type"],
            jupyter if inst["status"] == "RUNNING" else "-",
        )

    console.print(table)


@cli.command()
@click.argument("name")
@click.option("--project", help="GCP project ID")
@click.option("--zone", default=None, help="GCP zone")
def status(name, project, zone):
    """Show details for a specific instance."""
    config = get_config(project, zone)

    try:
        info = gcp.get_instance(config, name)
    except Exception as e:
        console.print(f"[red]Instance not found: {name}[/red]")
        raise SystemExit(1)

    ip = info["external_ip"] or "N/A"
    console.print(Panel(
        f"[bold]Name:[/bold]      {info['name']}\n"
        f"[bold]Status:[/bold]    {info['status']}\n"
        f"[bold]IP:[/bold]        {ip}\n"
        f"[bold]Machine:[/bold]   {info['machine_type']}\n"
        f"[bold]Zone:[/bold]      {info['zone']}\n"
        f"[bold]Created:[/bold]   {info['creation_timestamp']}\n"
        f"[bold]Jupyter:[/bold]   http://{ip}:8888" if info["external_ip"] else "",
        title=f"[bold]{info['name']}",
        box=box.ROUNDED,
    ))


@cli.command()
@click.argument("name")
@click.option("--project", help="GCP project ID")
@click.option("--zone", default=None, help="GCP zone")
def ssh(name, project, zone):
    """SSH into a MuJoCo Cloud instance."""
    config = get_config(project, zone)

    cmd = [
        "gcloud", "compute", "ssh", name,
        "--project", config.project_id,
        "--zone", config.zone,
    ]
    console.print(f"[dim]$ {' '.join(cmd)}[/dim]")
    os.execvp("gcloud", cmd)


@cli.command()
@click.argument("name")
@click.option("--project", help="GCP project ID")
@click.option("--zone", default=None, help="GCP zone")
@click.option("--open", "open_browser", is_flag=True, help="Open in browser")
def jupyter(name, project, zone, open_browser):
    """Get Jupyter URL for a MuJoCo Cloud instance."""
    config = get_config(project, zone)
    info = gcp.get_instance(config, name)

    if not info["external_ip"]:
        console.print("[red]Instance has no external IP.[/red]")
        raise SystemExit(1)

    url = f"http://{info['external_ip']}:8888"
    console.print(f"[bold]Jupyter Lab:[/bold] [cyan]{url}[/cyan]")

    if open_browser:
        webbrowser.open(url)


@cli.command()
@click.argument("name")
@click.option("--project", help="GCP project ID")
@click.option("--zone", default=None, help="GCP zone")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
def destroy(name, project, zone, yes):
    """Destroy a MuJoCo Cloud instance."""
    config = get_config(project, zone)

    if not yes:
        click.confirm(
            f"Destroy instance '{name}'? This cannot be undone.",
            abort=True,
        )

    with console.status(f"[bold red]Destroying {name}..."):
        gcp.delete_instance(config, name)

    console.print(f"[green]Instance '{name}' destroyed.[/green]")


@cli.command()
@click.option("--project", help="Set GCP project ID")
@click.option("--zone", help="Set default zone")
def config(project, zone):
    """Configure MuJoCo Cloud defaults."""
    cfg = MjCloudConfig.load()

    if project:
        cfg.project_id = project
    if zone:
        cfg.zone = zone

    if project or zone:
        cfg.save()
        console.print("[green]Configuration saved.[/green]")

    console.print(f"[bold]Project:[/bold]  {cfg.project_id or '[dim]not set[/dim]'}")
    console.print(f"[bold]Zone:[/bold]     {cfg.zone}")
    console.print(f"[bold]Machine:[/bold]  {cfg.machine_type}")
    console.print(f"[bold]Disk:[/bold]     {cfg.disk_size_gb}GB")
    console.print(f"\n[dim]Config file: {CONFIG_DIR / 'config.yaml'}[/dim]")


@cli.command()
def presets():
    """Show available instance presets."""
    table = Table(title="Instance Presets", box=box.ROUNDED)
    table.add_column("Preset", style="cyan bold")
    table.add_column("Machine Type")
    table.add_column("GPU")
    table.add_column("Description")

    for name, info in PRESETS.items():
        table.add_row(
            name,
            info["machine_type"],
            info["gpu_type"],
            info["description"],
        )

    console.print(table)


if __name__ == "__main__":
    cli()
