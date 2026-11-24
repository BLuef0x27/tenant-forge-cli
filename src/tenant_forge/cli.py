"""Typer command line interface for TenantForge."""

from __future__ import annotations

import secrets
import subprocess
from pathlib import Path

import typer

from tenant_forge import __version__
from tenant_forge.generator import write_tfvars

app = typer.Typer(
    name="tenant-forge",
    help="Onboard isolated, security-baselined customer tenant environments on AWS.",
    no_args_is_help=True,
)


@app.command()
def onboard(
    tenant: str = typer.Option(
        ...,
        "--tenant",
        "-t",
        help="Tenant identifier; normalized to lowercase letters, digits, and hyphens.",
    ),
    env: str = typer.Option(
        "staging",
        "--env",
        "-e",
        help="Target environment: staging or prod.",
    ),
    cidr: str = typer.Option(
        "10.20.0.0/16",
        "--cidr",
        help="VPC CIDR block; prefix must be between /16 and /24.",
    ),
    dry_run: bool = typer.Option(
        True,
        "--dry-run/--apply",
        help="Run terraform plan (default) or apply -auto-approve.",
    ),
    output_dir: Path = typer.Option(
        Path("tenants"),
        "--output-dir",
        help="Directory that receives the generated .tfvars file.",
    ),
) -> None:
    """Generate tenant variables, preview a bootstrap token, and run Terraform."""
    try:
        tfvars_path = write_tfvars(tenant, env, cidr, output_dir=output_dir)
    except ValueError as exc:
        typer.secho(f"Validation error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2) from exc

    # Preview-only bootstrap token for the tenant handoff checklist. It is
    # generated at run time, never persisted by this tool, and must be
    # rotated by the customer after first use.
    bootstrap_token = "tf_live_" + secrets.token_urlsafe(24)
    typer.secho("Bootstrap API token preview (rotate after customer handoff):", fg=typer.colors.CYAN)
    typer.echo(f"  {bootstrap_token}")
    typer.echo(f"Wrote {tfvars_path}")

    var_file = f"-var-file=../{tfvars_path.as_posix()}"
    if dry_run:
        tf_args = ["plan", var_file]
        action = "plan"
    else:
        tf_args = ["apply", "-auto-approve", var_file]
        action = "apply"

    command_line = ["terraform", "-chdir=terraform", *tf_args]
    typer.echo("Running: " + " ".join(command_line))
    try:
        result = subprocess.run(command_line, check=False)
    except FileNotFoundError:
        typer.secho(
            "terraform binary not found on PATH; install Terraform >= 1.6.0",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(code=2) from None

    if result.returncode != 0:
        typer.secho(
            f"terraform {action} failed with exit code {result.returncode}",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(code=result.returncode)

    typer.secho(f"Tenant '{tenant}' {action} completed successfully.", fg=typer.colors.GREEN)


@app.command()
def version() -> None:
    """Print the TenantForge version."""
    typer.echo(f"tenant-forge {__version__}")


if __name__ == "__main__":
    app()
