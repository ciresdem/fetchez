#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
fetchez.cli.modules
~~~~~~~~~~~~~~~~

Discoverability and documentation for fetching modules.

:copyright: (c) 2010-2026 Regents of the University of Colorado
:license: MIT, see LICENSE for more details.
"""

import click
import sys
from fetchez.registry import ModuleRegistry
from fetchez.utils import get_class_arguments, FetchezMainGroup, FetchezMainCommand
from .bundles import bundles_group

MODULES_COMMANDS = ["info", "list", "search", "bundles", "update-cache"]


@click.group(
    cls=FetchezMainGroup,
    name="modules",
    fetchez_commands=MODULES_COMMANDS,
)
def modules_group():
    """Discover, search, and learn about data sources."""

    pass


@modules_group.command("search", cls=FetchezMainCommand)
@click.argument("term")
def module_search(term):
    """Search all available modules by keyword."""

    ModuleRegistry.load_all()
    registry = ModuleRegistry.get_registry()

    valid_keys = ModuleRegistry.search_modules(term)

    grouped_modules = {}
    for name in valid_keys:
        meta = registry[name]
        # Skip aliases to keep the list clean
        if name in meta.get("aliases", []):
            continue

        cat = meta.get("category", "Other Modules").title()
        grouped_modules.setdefault(cat, []).append((name, meta))

    if not grouped_modules:
        click.secho(f"No modules found matching '{term}'.", fg="yellow")
        return

    click.secho("\n🌍 Available Data Modules:", fg="yellow", bold=True)
    click.echo("=" * 60)

    for cat in sorted(grouped_modules.keys()):
        click.secho(f"\n[ {cat} ]", fg="green", bold=True)
        for name, meta in sorted(grouped_modules[cat], key=lambda x: x[0]):
            desc = meta.get("desc", "No description provided.")
            name_padded = f"{name:<16}"
            click.echo(f"  {click.style(name_padded, bold=True, fg='cyan')} : {desc}")

    click.echo("\nRun 'fetchez modules info <name>' for detailed metadata.\n")


@modules_group.command("list", cls=FetchezMainCommand)
@click.option("--search", "-s", help="Search by name, description, agency, or tag.")
def module_list(search):
    """List all available modules grouped by category."""

    ModuleRegistry.load_fast()
    registry = ModuleRegistry.get_registry()

    valid_keys = ModuleRegistry.search_modules(search) if search else registry.keys()

    grouped_modules = {}
    for name in valid_keys:
        meta = registry[name]
        # Skip aliases to keep the list clean
        if name in meta.get("aliases", []):
            continue

        cat = meta.get("category", "Other Modules").title()
        grouped_modules.setdefault(cat, []).append((name, meta))

    if not grouped_modules:
        click.secho(f"No modules found matching '{search}'.", fg="yellow")
        return

    click.secho("\n🌍 Available Data Modules:", fg="yellow", bold=True)
    click.echo("=" * 60)

    for cat in sorted(grouped_modules.keys()):
        click.secho(f"\n[ {cat} ]", fg="green", bold=True)
        for name, meta in sorted(grouped_modules[cat], key=lambda x: x[0]):
            desc = meta.get("desc", "No description provided.")
            name_padded = f"{name:<16}"
            click.echo(f"  {click.style(name_padded, bold=True, fg='cyan')} : {desc}")

    click.echo("\nRun 'fetchez modules info <name>' for detailed metadata.\n")


@modules_group.command("info", cls=FetchezMainCommand)
@click.argument("name")
def module_info(name):
    """Get detailed metadata and available CLI arguments for a module."""

    ModuleRegistry.load_all()
    meta = ModuleRegistry.get_info(name)
    mod_cls = ModuleRegistry.get_class(name)

    if not meta or not mod_cls:
        click.secho(f"Error: Module '{name}' not found.", fg="red")
        sys.exit(1)

    click.secho(f"\n📦 MODULE: {name}", fg="cyan", bold=True)
    click.echo("=" * 60)
    click.echo(f"  Description : {meta.get('desc', 'N/A')}")
    click.echo(f"  Category    : {meta.get('category', 'N/A')}")
    click.echo(f"  Agency      : {meta.get('agency', 'N/A')}")
    click.echo(f"  Resolution  : {meta.get('resolution', 'N/A')}")
    click.echo(f"  License     : {meta.get('license', 'N/A')}")

    tags = meta.get("tags", [])
    if tags:
        click.echo(f"  Tags        : {', '.join(tags)}")

    urls = meta.get("urls", {})
    if urls:
        click.echo("\n  Links:")
        for link_name, link_url in urls.items():
            click.echo(f"    - {link_name.title()}: {link_url}")

    # args_dict = get_class_arguments(mod_cls)
    args_dict = get_class_arguments(mod_cls)
    click.secho("\n  Arguments:", fg="yellow", bold=True)
    for key, val in args_dict.items():
        click.echo(
            f"    - {click.style(key, bold=True)} {val['type']}[{val['default']}]{val['inherit']}{val['desc']}"
        )

    # Generate the YAML Snippet
    click.secho("\n  YAML Recipe Example:", fg="green", bold=True)
    click.echo("-" * 40)

    click.echo("  modules:")
    click.echo(f"    - module: {name}")

    if args_dict:
        click.echo("      args:")
        for key, val in args_dict.items():
            val_str = (
                f"{val['default']}"
                if isinstance(val["default"], str) and val["default"] != "REQUIRED"
                else val["default"]
            )
            click.echo(f"        {key}: {val_str}")

        # click.echo("      hooks:")
    click.echo("-" * 40 + "\n")


@modules_group.command("update-cache", cls=FetchezMainCommand)
def update_cache():
    """Forces a clean rescan of all built-in, Globato, and user-defined modules.

    Use this if you recently installed a new extension or added a custom Python
    plugin to your ~/.fetchez/modules/ folder and it isn't showing up.
    """

    from fetchez.registry import ModuleRegistry

    cleared = ModuleRegistry.clear_cache()
    if cleared:
        click.secho("Flushed existing module cache.", fg="yellow")
    else:
        click.echo("No existing cache found. Starting fresh.")

    click.echo("Scanning environment for Fetchez modules...")

    ModuleRegistry.load_all()
    registry = ModuleRegistry.get_registry()
    unique_mods = len(set(meta.get("import_path") for meta in registry.values()))

    click.secho(
        f"✨ Successfully rebuilt cache! Found {unique_mods} active modules.",
        fg="green",
        bold=True,
    )


modules_group.add_command(bundles_group, name="bundles")
