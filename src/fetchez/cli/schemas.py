#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
fetchez.cli.schemas
~~~~~~~~~~~~~~~~

Discoverability and documentation for processing schemas.

:copyright: (c) 2010-2026 Regents of the University of Colorado
:license: MIT, see LICENSE for more details.
"""

import sys
import click

# from fetchez.api import list_schemas
from fetchez.registry import SchemaRegistry
from fetchez.utils import get_class_arguments, FetchezMainGroup, FetchezMainCommand


@click.group(
    cls=FetchezMainGroup,
    name="schemas",
    fetchez_commands=["list", "info"]
)
def schemas_group():
    """Discover, search, and learn about recipe schemas."""

    pass


@schemas_group.command("list", cls=FetchezMainCommand)
@click.option("--search", "-s", help="Filter schemas by name or keyword.")
def schemas_list(search):
    """List all available processing schemas grouped by category."""

    SchemaRegistry.load_all()
    registry = SchemaRegistry.get_registry()

    grouped_schemas = {}
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
        grouped_schemas.setdefault(cat, []).append((name, meta))

    click.secho("\nAvailable Schemas by Category:", fg="cyan", bold=True)
    click.echo("=" * 60)

    for cat in sorted(grouped_schemas.keys()):
        click.secho(f"\n[ {cat} ]", fg="yellow", bold=True)
        for name, meta in sorted(grouped_schemas[cat], key=lambda x: x[0]):
            desc = meta.get("desc", "No description provided.")

            name_padded = f"{name:<16}"

            click.echo(f"  {click.style(name_padded, bold=True, fg='green')}: {desc}")

    click.echo(
        "\nRun 'fetchez schemas info <name>' for arguments and recipe examples.\n"
    )


@schemas_group.command("info", cls=FetchezMainCommand)
@click.argument("name")
def schemas_info(name):
    """Show arguments and YAML recipe examples for a specific hook."""

    SchemaRegistry.load_all()
    schema_cls = SchemaRegistry.get_class(name)
    meta = SchemaRegistry.get_info(name)

    if not schema_cls:
        click.secho(f"Error: Schema '{name}' not found.", fg="red")
        sys.exit(1)

    click.secho(f"\n🪝 SCHEMA: {name}", fg="cyan", bold=True)
    click.echo("=" * 60)
    click.echo(f"  Description : {meta.get('desc', 'N/A')}")
    click.echo(f"  Category    : {meta.get('category', 'N/A')}\n")

    # print_class_arguments(schema_cls)
    args_dict = get_class_arguments(schema_cls)

    click.secho("  Arguments:", fg="yellow", bold=True)
    for key, val in args_dict.items():
        click.echo(f"    - {click.style(key, bold=True)} {val}")

    # Generate the YAML Snippet
    click.secho("\n  YAML Recipe Example:", fg="green", bold=True)
    click.echo("-" * 40)

    click.echo(f"schema: {name}")

    click.echo("-" * 40 + "\n")
