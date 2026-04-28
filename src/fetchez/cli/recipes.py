#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
fetchez.cli.recipes
~~~~~~~~~~~~~~~~

Discoverability and documentation for fetchez recipes.

:copyright: (c) 2010-2026 Regents of the University of Colorado
:license: MIT, see LICENSE for more details.
"""

import os
import sys
import yaml
import click
from fetchez.registry import RecipeRegistry


@click.group(name="recipes")
def recipes_group():
    """Discover, inspect, and copy complete pipeline workflows."""

    pass


@recipes_group.command("list")
def list_recipes():
    """List all available built-in and local recipes."""

    RecipeRegistry.load_all()
    registry = RecipeRegistry.get_registry()

    click.secho("\n📜 Available Pipeline Recipes:", fg="cyan", bold=True)
    click.echo("=" * 60)
    for name, meta in sorted(registry.items()):
        # Quick summary for the list view
        # project = meta.get("project", {})
        desc = meta.get("desc", "No description provided.").strip().split("\n")[0]

        click.secho(f"  {name:<25}", fg="green", bold=True, nl=False)
        click.echo(f" - {desc}")
    click.echo("\nRun 'fetchez recipes info <name>' for details.\n")


@recipes_group.command("info")
@click.argument("name")
def info_recipe(name):
    """Print a clean, readable summary of a recipe's contents."""

    RecipeRegistry.load_all()
    meta = RecipeRegistry.get_yaml(name)

    if not meta:
        click.secho(f"Error: Recipe '{name}' not found.", fg="red")
        sys.exit(1)

    # project = meta.get("project", {})
    click.secho(f"\n📜 RECIPE SUMMARY: {name}", fg="cyan", bold=True)
    click.echo("=" * 60)
    click.echo(f"  Description : {meta.get('desc', 'N/A').strip()}")

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


@recipes_group.command("dump")
@click.argument("name")
def dump_recipe(name):
    """Print the raw YAML definition to the terminal."""

    RecipeRegistry.load_all()
    meta = RecipeRegistry.get_yaml(name)

    if not meta:
        click.secho(f"Error: Recipe '{name}' not found.", fg="red")
        sys.exit(1)

    # Dump the dictionary back to a formatted YAML string
    yaml_str = yaml.dump(meta, sort_keys=False)

    click.secho(f"--- # {name}.yaml", fg="bright_black")
    click.echo(yaml_str)


@recipes_group.command("copy")
@click.argument("name")
def copy_recipe(name):
    """Copy a recipe to your local ~/.fetchez/ folder for editing."""

    RecipeRegistry.load_all()
    meta = RecipeRegistry.get_yaml(name)

    if not meta:
        click.secho(f"Error: Recipe '{name}' not found.", fg="red")
        sys.exit(1)

    # Use the registry's built-in user folder mapping!
    user_dir = os.path.expanduser(f"~/.fetchez/{RecipeRegistry.user_folder}")
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
