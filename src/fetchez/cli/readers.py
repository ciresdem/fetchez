#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
fetchez.cli.readers
~~~~~~~~~~~~~~~~

Discoverability and documentation for processing readers.

:copyright: (c) 2010-2026 Regents of the University of Colorado
:license: MIT, see LICENSE for more details.
"""

import sys
import click

# from fetchez.api import list_readers
from fetchez.registry import ReaderRegistry
from fetchez.utils import get_class_arguments, FetchezMainGroup, FetchezMainCommand


@click.group(cls=FetchezMainGroup, name="readers", fetchez_commands=["list", "info"])
def readers_group():
    """Discover, search, and learn about recipe readers."""

    pass


@readers_group.command("list", cls=FetchezMainCommand)
@click.option("--search", "-s", help="Filter readers by name or keyword.")
def readers_list(search):
    """List all available processing readers grouped by category."""

    ReaderRegistry.load_all()
    registry = ReaderRegistry.get_registry()

    grouped_readers = {}
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
        grouped_readers.setdefault(cat, []).append((name, meta))

    click.secho("\nAvailable Readers by Category:", fg="cyan", bold=True)
    click.echo("=" * 60)

    for cat in sorted(grouped_readers.keys()):
        click.secho(f"\n[ {cat} ]", fg="yellow", bold=True)
        for name, meta in sorted(grouped_readers[cat], key=lambda x: x[0]):
            desc = meta.get("desc", "No description provided.")

            name_padded = f"{name:<16}"

            click.echo(f"  {click.style(name_padded, bold=True, fg='green')}: {desc}")

    click.echo(
        "\nRun 'fetchez readers info <name>' for arguments and recipe examples.\n"
    )


@readers_group.command("info", cls=FetchezMainCommand)
@click.argument("name")
def readers_info(name):
    """Show arguments and YAML recipe examples for a specific hook."""

    ReaderRegistry.load_all()
    schema_cls = ReaderRegistry.get_class(name)
    meta = ReaderRegistry.get_info(name)

    if not schema_cls:
        click.secho(f"Error: Reader '{name}' not found.", fg="red")
        sys.exit(1)

    click.secho(f"\n🪝 READER: {name}", fg="cyan", bold=True)
    click.echo("=" * 60)
    click.echo(f"  Description : {meta.get('desc', 'N/A')}")
    click.echo(f"  Category    : {meta.get('category', 'N/A')}\n")

    # print_class_arguments(schema_cls)
    args_dict = get_class_arguments(schema_cls)
    if args_dict:
        click.secho("  Arguments:", fg="yellow", bold=True)
        for key, val in args_dict.items():
            click.echo(f"    - {click.style(key, bold=True)} {val['default']}")

    click.echo("\n" + "-" * 40 + "\n")
