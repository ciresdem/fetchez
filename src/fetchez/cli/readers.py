#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
fetchez.cli.streams.readers
~~~~~~~~~~~~~~~~

Discoverability and documentation for stream readers.

:copyright: (c) 2010-2026 Regents of the University of Colorado
:license: MIT, see LICENSE for more details.
"""

import os
import sys
import click

# from fetchez.api import list_readers
from fetchez.registry import ReaderRegistry, ProfileRegistry
from fetchez.utils import get_class_arguments, FetchezMainGroup, FetchezMainCommand


@click.group(cls=FetchezMainGroup, name="readers", fetchez_commands=["list", "info"])
def readers_group():
    """Discover, search, and learn about stream format readers."""

    pass


@readers_group.command("list", cls=FetchezMainCommand)
@click.option("--search", "-s", help="Filter readers by name or keyword.")
def readers_list(search):
    """List all available stream readers grouped by category."""

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

    click.secho("\n🌐 Available Readers by Category:", fg="cyan", bold=True)
    click.echo("=" * 60)

    for cat in sorted(grouped_readers.keys()):
        click.secho(f"\n[ {cat} ]", fg="yellow", bold=True)
        for name, meta in sorted(grouped_readers[cat], key=lambda x: x[0]):
            desc = meta.get("desc", "No description provided.")

            name_padded = f"{name:<16}"

            click.echo(f"  {click.style(name_padded, bold=True, fg='green')}: {desc}")

    click.echo(
        f"\nRun '{os.path.basename(sys.argv[0])} readers info <name>' for arguments and examples.\n"
    )


@readers_group.command("info", cls=FetchezMainCommand)
@click.argument("name")
def readers_info(name):
    """Show arguments and YAML recipe examples for a specific reader."""

    ReaderRegistry.load_all()
    schema_cls = ReaderRegistry.get_class(name)
    meta = ReaderRegistry.get_info(name)

    if not schema_cls:
        click.secho(f"Error: Reader '{name}' not found.", fg="red")
        sys.exit(1)

    click.secho(f"\n🌐 READER: {name}", fg="cyan", bold=True)
    click.echo("=" * 60)
    click.echo(f"  Description : {meta.get('desc', 'N/A')}")
    click.echo(f"  Category    : {meta.get('category', 'N/A')}\n")

    # print_class_arguments(schema_cls)
    args_dict = get_class_arguments(schema_cls)
    if args_dict:
        click.secho("  Arguments:", fg="yellow", bold=True)
        for key, val in args_dict.items():
            click.echo(f"    - {click.style(key, bold=True)} {val['default']}")

    ProfileRegistry.load_all()
    profile_registry = ProfileRegistry.get_registry()
    click.secho("\n  Available Profiles:", fg="yellow", bold=True)
    for profile in profile_registry:
        profile_meta = ProfileRegistry.get_yaml(profile)
        profile_reader = profile_meta.get("reader").get("name")
        if profile_reader == name:
            click.echo(f"    - {click.style(profile_meta.get('name'), bold=True)}")

    click.echo("\n" + "-" * 40 + "\n")
