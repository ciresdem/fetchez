#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
fetchez.cli.presets
~~~~~~~~~~~~~~~~

Discoverability and documentation for processing macros (presets).

:copyright: (c) 2010-2026 Regents of the University of Colorado
:license: MIT, see LICENSE for more details.
"""

import os
import sys
import yaml
import click
from fetchez.registry import PresetRegistry
from fetchez.utils import FetchezMainGroup, FetchezMainCommand


@click.group(
    cls=FetchezMainGroup,
    name="presets",
    fetchez_commands=["copy", "dump", "info", "list"],
)
def presets_group():
    """Discover, inspect, and copy processing macros.

    \b
    Presets are YAML macros that chain multiple processing Hooks together
    under a single name. If you frequently run the exact same sequence of
    filters, you can save them as a Preset and call them with one word.

    \b
    Usage:
      Presets act exactly like Hooks. You can pass them to `--hook`, `--global-hook`,
      or list them in your Recipe's hook list.
    """

    pass


@presets_group.command("list", cls=FetchezMainCommand)
def list_presets():
    """List all available built-in and local presets."""

    PresetRegistry.load_all()
    registry = PresetRegistry.get_registry()

    click.secho("\n📜 Available Pipeline Presets:", fg="cyan", bold=True)
    click.echo("=" * 60)
    for name, meta in sorted(registry.items()):
        # Quick summary for the list view
        desc = (
            meta.get("description", "No description provided.").strip().split("\n")[0]
        )

        click.secho(f"  {name:<25}", fg="green", bold=True, nl=False)
        click.echo(f" - {desc}")
    click.echo("\nRun 'fetchez presets info <name>' for details.\n")


@presets_group.command("info", cls=FetchezMainCommand)
@click.argument("name")
def info_preset(name):
    """Print a clean, readable summary of a preset's contents."""

    PresetRegistry.load_all()
    meta = PresetRegistry.get_yaml(name)

    if not meta:
        click.secho(f"Error: Preset '{name}' not found.", fg="red")
        sys.exit(1)

    click.secho(f"\n📜 PRESET SUMMARY: {name}", fg="cyan", bold=True)
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


@presets_group.command("dump", cls=FetchezMainCommand)
@click.argument("name")
def dump_preset(name):
    """Print the raw YAML definition to the terminal."""

    PresetRegistry.load_all()
    meta = PresetRegistry.get_yaml(name)

    if not meta:
        click.secho(f"Error: Preset '{name}' not found.", fg="red")
        sys.exit(1)

    # Dump the dictionary back to a formatted YAML string
    yaml_str = yaml.dump(meta, sort_keys=False)

    click.secho(f"--- # {name}.yaml", fg="bright_black")
    click.echo(yaml_str)


@presets_group.command("copy", cls=FetchezMainCommand)
@click.argument("name")
def copy_preset(name):
    """Copy a preset to your local ~/.fetchez/ folder for editing."""

    PresetRegistry.load_all()
    meta = PresetRegistry.get_yaml(name)

    if not meta:
        click.secho(f"Error: Preset '{name}' not found.", fg="red")
        sys.exit(1)

    # Use the registry's built-in user folder mapping!
    user_dir = os.path.expanduser(f"~/.fetchez/{PresetRegistry.user_folder}")
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
