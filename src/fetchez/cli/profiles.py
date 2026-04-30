#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
fetchez.cli.profiles
~~~~~~~~~~~~~~~~

Discoverability and documentation for fetching profiles.

:copyright: (c) 2010-2026 Regents of the University of Colorado
:license: MIT, see LICENSE for more details.
"""

import os
import sys
import yaml
import click
from fetchez.registry import ProfileRegistry
from fetchez.utils import FetchezMainGroup, FetchezMainCommand


@click.group(
    cls=FetchezMainGroup,
    name="profiles",
    fetchez_commands=["copy", "dump", "info", "list"],
)
def profiles_group():
    """Discover, inspect, and copy module groups."""

    pass


@profiles_group.command("list", cls=FetchezMainCommand)
def list_profiles():
    """List all available built-in and local profiles."""

    ProfileRegistry.load_all()
    registry = ProfileRegistry.get_registry()

    click.secho("\n📜 Available Module Profiles:", fg="cyan", bold=True)
    click.echo("=" * 60)
    for name, meta in sorted(registry.items()):
        # Quick summary for the list view
        # project = meta.get("project", {})
        desc = (
            meta.get("description", "No description provided.").strip().split("\n")[0]
        )

        click.secho(f"  {name:<25}", fg="green", bold=True, nl=False)
        click.echo(f" - {desc}")
    click.echo("\nRun 'fetchez profiles info <name>' for details.\n")


@profiles_group.command("info", cls=FetchezMainCommand)
@click.argument("name")
def info_profiles(name):
    """Print a clean, readable summary of a bundle's contents."""

    ProfileRegistry.load_all()
    meta = ProfileRegistry.get_yaml(name)

    if not meta:
        click.secho(f"Error: Profile '{name}' not found.", fg="red")
        sys.exit(1)

    # project = meta.get("project", {})
    click.secho(f"\n📜 BUNDLE SUMMARY: {name}", fg="cyan", bold=True)
    click.echo("=" * 60)
    click.echo(f"  Description : {meta.get('description', 'N/A').strip()}")

    modules = meta.get("modules", [])
    if modules:
        click.echo(f"\n  Data Sources ({len(modules)}):")
        for mod in modules:
            mod_name = mod.get("module") or mod.get("bundle") or "Unknown"
            click.echo(f"    - {click.style(mod_name, fg='green')}")

    global_hooks = meta.get("global_hooks", [])
    if global_hooks:
        click.echo(f"\n  Global Pipeline Steps ({len(global_hooks)}):")
        for hook in global_hooks:
            hook_name = hook.get("name") or hook.get("preset") or "Unknown"
            click.echo(f"    - {click.style(hook_name, fg='yellow')}")
    click.echo("=" * 60 + "\n")


@profiles_group.command("dump", cls=FetchezMainCommand)
@click.argument("name")
def dump_bundle(name):
    """Print the raw YAML definition to the terminal."""

    ProfileRegistry.load_all()
    meta = ProfileRegistry.get_yaml(name)

    if not meta:
        click.secho(f"Error: Profile '{name}' not found.", fg="red")
        sys.exit(1)

    # Dump the dictionary back to a formatted YAML string
    yaml_str = yaml.dump(meta, sort_keys=False)

    click.secho(f"--- # {name}.yaml", fg="bright_black")
    click.echo(yaml_str)


@profiles_group.command("copy", cls=FetchezMainCommand)
@click.argument("name")
def copy_bundle(name):
    """Copy a module bundle to your local ~/.fetchez/ folder for editing."""

    ProfileRegistry.load_all()
    meta = ProfileRegistry.get_yaml(name)

    if not meta:
        click.secho(f"Error: Profile '{name}' not found.", fg="red")
        sys.exit(1)

    # Use the registry's built-in user folder mapping!
    user_dir = os.path.expanduser(f"~/.fetchez/{ProfileRegistry.user_folder}")
    os.makedirs(user_dir, exist_ok=True)

    out_path = os.path.join(user_dir, f"{name}.yaml")

    if os.path.exists(out_path):
        click.secho(f"⚠️  File already exists: {out_path}", fg="yellow")
        click.confirm("Do you want to overwrite it?", abort=True)

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(yaml.dump(meta, sort_keys=False))

    click.secho(f"\n✅ Copied '{name}' to {out_path}", fg="green", bold=True)
    click.echo("Fetchez will now prioritize this local file over the built-in version!")
    click.echo("You can open it in any text editor to safely customize the pipeline.\n")
