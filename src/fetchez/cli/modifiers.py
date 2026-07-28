#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
fetchez.cli.modifiers
~~~~~~~~~~~~~~~~

Discoverability and documentation for processing modifiers.

:copyright: (c) 2010-2026 Regents of the University of Colorado
:license: MIT, see LICENSE for more details.
"""

import sys
import click

from fetchez.registry import ModifierRegistry
from fetchez.utils import get_class_arguments, FetchezMainGroup, FetchezMainCommand


@click.group(cls=FetchezMainGroup, name="modifiers", fetchez_commands=["list", "info"])
def modifiers_group():
    """Discover, search, and learn about recipe modifiers.

    \b
    Modifiers are middle-ware mutators that can be applied to Recipes.
    They can be used to make on-the-fly modifications to recipes before
    they are run.
    """

    pass


@modifiers_group.command("list", cls=FetchezMainCommand)
@click.option("--search", "-s", help="Filter modifiers by name or keyword.")
def modifiers_list(search):
    """List all available processing modifiers grouped by category."""

    ModifierRegistry.load_all()
    registry = ModifierRegistry.get_registry()

    grouped_modifiers = {}
    for name, meta in registry.items():
        if name in meta.get("aliases", []):
            continue

        if (
            search
            and search.lower() not in name.lower()
            and search.lower() not in meta.get("desc", "").lower()
        ):
            continue

        cat = meta.get("category", "uncategorized").title()
        grouped_modifiers.setdefault(cat, []).append((name, meta))

    click.secho("\nAvailable Modifiers by Category:", fg="cyan", bold=True)
    click.echo("=" * 60)

    for cat in sorted(grouped_modifiers.keys()):
        click.secho(f"\n[ {cat} ]", fg="yellow", bold=True)
        for name, meta in sorted(grouped_modifiers[cat], key=lambda x: x[0]):
            desc = meta.get("desc", "No description provided.")

            name_padded = f"{name:<16}"

            click.echo(f"  {click.style(name_padded, bold=True, fg='green')}: {desc}")

    click.echo(
        "\nRun 'fetchez modifiers info <name>' for arguments and recipe examples.\n"
    )


@modifiers_group.command("info", cls=FetchezMainCommand)
@click.argument("name")
def modifiers_info(name):
    """Show arguments and YAML recipe examples for a specific hook."""

    ModifierRegistry.load_all()
    modifier_cls = ModifierRegistry.get_class(name)
    meta = ModifierRegistry.get_info(name)

    if not modifier_cls:
        click.secho(f"Error: Modifier '{name}' not found.", fg="red")
        sys.exit(1)

    click.secho(f"\n🪝 MODIFIER: {name}", fg="cyan", bold=True)
    click.echo("=" * 60)
    click.echo(f"  Description : {meta.get('desc', 'N/A')}")
    click.echo(f"  Category    : {meta.get('category', 'N/A')}\n")

    # print_class_arguments(modifier_cls)
    args_dict = get_class_arguments(modifier_cls)
    if args_dict:
        click.secho("  Arguments:", fg="yellow", bold=True)
        for key, val in args_dict.items():
            click.echo(f"    - {click.style(key, bold=True)} {val['default']}")

    # Generate the YAML Snippet
    click.secho("\n  YAML Recipe Example:", fg="green", bold=True)
    click.echo("-" * 40)

    click.echo(f"modifier: {name}")

    click.echo("-" * 40 + "\n")
