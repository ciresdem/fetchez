#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
fetchez.cli.bundles
~~~~~~~~~~~~~~~~

Discoverability and documentation for fetching bundles.

:copyright: (c) 2010-2026 Regents of the University of Colorado
:license: MIT, see LICENSE for more details.
"""

import sys
import yaml
import click
from pathlib import Path

from fetchez.registry import BundleRegistry
from fetchez.utils import FetchezMainGroup, FetchezMainCommand


@click.group(
    cls=FetchezMainGroup,
    name="bundles",
    fetchez_commands=["copy", "dump", "info", "list"],
)
def bundles_group():
    """Discover, inspect, and copy module groups.

    \b
    Bundles are pre-configured YAML lists of Modules. Instead of manually
    typing out multiple different data sources and their specific arguments,
    you can call a single Bundle that contains them all.

    \b
    Usage:
      Bundles act exactly like Modules. You can pass them directly to `fetchez run`.
      As such, Bundles can reference other Bundles as well as Modules.
    """

    pass


@bundles_group.command("list", cls=FetchezMainCommand)
def list_bundles():
    """List all available built-in and local bundles."""

    BundleRegistry.load_all()
    registry = BundleRegistry.get_registry()

    click.secho("\n📜 Available Module Bundles:", fg="cyan", bold=True)
    click.echo("=" * 60)
    for name, meta in sorted(registry.items()):
        # Quick summary for the list view
        # project = meta.get("project", {})
        desc = (
            meta.get("description", "No description provided.").strip().split("\n")[0]
        )

        click.secho(f"  {name:<25}", fg="green", bold=True, nl=False)
        click.echo(f" - {desc}")
    click.echo("\nRun 'fetchez bundles info <name>' for details.\n")


@bundles_group.command("info", cls=FetchezMainCommand)
@click.argument("name")
def info_bundles(name):
    """Print a clean, readable summary of a bundle's contents."""

    from fetchez.recipe import Recipe

    BundleRegistry.load_all()
    meta = BundleRegistry.get_yaml(name)

    if not meta:
        click.secho(f"Error: Bundle '{name}' not found.", fg="red")
        sys.exit(1)

    # project = meta.get("project", {})
    click.secho(f"\n📜 BUNDLE SUMMARY: {name}", fg="cyan", bold=True)
    click.echo("=" * 60)
    click.echo(f"  Description : {meta.get('description', 'N/A').strip()}")

    modules = Recipe({})._expand_modules(meta.get("modules", []))
    if modules:
        click.echo(f"\n  Data Sources ({len(modules)}):")
        for mod in modules:
            mod_name = mod.get("module") or mod.get("bundle") or "Unknown"
            click.echo(f"    + {click.style(mod_name, fg='green')}")
            for arg in mod.get("args"):
                click.echo(
                    f"     ⤷ {click.style(arg, fg='cyan')}: {mod.get('args').get(arg)}"
                )

    click.echo("=" * 60 + "\n")


@bundles_group.command("dump", cls=FetchezMainCommand)
@click.argument("name")
def dump_bundle(name):
    """Print the raw YAML definition to the terminal."""

    BundleRegistry.load_all()
    meta = BundleRegistry.get_yaml(name)

    if not meta:
        click.secho(f"Error: Bundle '{name}' not found.", fg="red")
        sys.exit(1)

    # Dump the dictionary back to a formatted YAML string
    yaml_str = yaml.dump(meta, sort_keys=False)

    click.secho(f"--- # {name}.yaml", fg="bright_black")
    click.echo(yaml_str)


@bundles_group.command("copy", cls=FetchezMainCommand)
@click.argument("name")
def copy_bundle(name):
    """Copy a module bundle to your local ~/.fetchez/ folder for editing."""

    BundleRegistry.load_all()
    meta = BundleRegistry.get_yaml(name)

    if not meta:
        click.secho(f"Error: Bundle '{name}' not found.", fg="red")
        sys.exit(1)

    # Use the registry's built-in user folder mapping!
    user_dir = Path(f"~/.fetchez/{BundleRegistry.user_folder}").expanduser()
    user_dir.mkdir(parents=True, exist_ok=True)

    out_path = user_dir / f"{name}.yaml"

    if out_path.exists():
        click.secho(f"⚠️  File already exists: {out_path}", fg="yellow")
        click.confirm("Do you want to overwrite it?", abort=True)

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(yaml.dump(meta, sort_keys=False))

    click.secho(f"\n✅ Copied '{name}' to {out_path}", fg="green", bold=True)
    click.echo("Fetchez will now prioritize this local file over the built-in version!")
    click.echo("You can open it in any text editor to safely customize the pipeline.\n")
