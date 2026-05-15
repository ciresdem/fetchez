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
from fetchez.registry import ProfileRegistry, ReaderRegistry
from fetchez.utils import FetchezMainGroup, FetchezMainCommand
from fetchez.api import search_profiles


@click.group(
    cls=FetchezMainGroup,
    name="profiles",
    fetchez_commands=["copy", "dump", "info", "list"],
)
def profiles_group():
    """Discover, inspect, and copy stream format profiles.

    \b
    Different datasets are formatted differently (e.g., one NetCDF uses 'lon'
    and 'lat', another uses 'x' and 'y'). Profiles are YAML dictionaries that
    tell a Reader exactly how to parse a specific dataset's format.
    """

    pass


def _print_grouped_profiles(grouped_profiles):
    click.secho(
        "\n📜 Available Format Stream Profiles by Category:", fg="cyan", bold=True
    )
    click.echo("=" * 60)

    for cat in sorted(grouped_profiles.keys()):
        click.secho(f"\n[ {cat} ]", fg="yellow", bold=True)
        for name, meta in sorted(grouped_profiles[cat], key=lambda x: x[0]):
            reader = meta.get("reader").get("name", "unknown")
            desc = meta.get("description", "No description provided.")

            name_padded = f"{name:<16}"
            reader_padded = f"[{reader:^6}]"

            click.echo(
                f"  {click.style(name_padded, bold=True, fg='green')} {click.style(reader_padded, fg='blue')} : {desc}"
            )
    click.echo(
        "\nRun 'fetchez streams profiles info <name>' for arguments and recipe examples.\n"
    )


@profiles_group.command("list", cls=FetchezMainCommand)
@click.option("--search", "-s", help="Filter profiles by name or keyword.")
def list_profiles(search):
    """List all available built-in and local profiles."""

    ReaderRegistry.load_all()
    registry = search_profiles(search)
    grouped_profiles = {}
    for name, meta in registry.items():
        if name in meta.get("aliases", []):
            continue

        reader_meta = ReaderRegistry.get_info(meta.get("reader").get("name"))
        cat = reader_meta.get("category", "uncategorized").title()
        grouped_profiles.setdefault(cat, []).append((name, meta))

    _print_grouped_profiles(grouped_profiles)

    # ProfileRegistry.load_all()
    # registry = ProfileRegistry.get_registry()

    # click.secho("\n📜 Available Stream-Reader Profiles:", fg="cyan", bold=True)
    # click.echo("=" * 60)
    # for name, meta in sorted(registry.items()):
    #     # Quick summary for the list view
    #     # project = meta.get("project", {})
    #     desc = (
    #         meta.get("description", "No description provided.").strip().split("\n")[0]
    #     )
    #     reader = meta.get("reader").get("name")

    #     click.secho(f"  {name:<25}", fg="green", bold=True, nl=False)
    #     click.secho(f"[ {reader} ]", fg="yellow", nl=False)
    #     click.echo(f" - {desc}")
    # click.echo("\nRun 'fetchez profiles info <name>' for details.\n")


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
    click.secho(f"\n📜 PROFILE SUMMARY: {name}", fg="cyan", bold=True)
    click.echo("=" * 60)
    click.echo(f"  Description : {meta.get('description', 'N/A').strip()}")

    reader = meta.get("reader").get("name")

    if reader:
        click.secho("\n  Supported Reader:", fg="yellow", bold=True)
        click.echo(f"    - {click.style(reader, fg='green')}")

    # global_hooks = meta.get("global_hooks", [])
    # if global_hooks:
    #     click.echo(f"\n  Global Pipeline Steps ({len(global_hooks)}):")
    #     for hook in global_hooks:
    #         hook_name = hook.get("name") or hook.get("preset") or "Unknown"
    #         click.echo(f"    - {click.style(hook_name, fg='yellow')}")
    click.echo("\n" + "=" * 60 + "\n")
    # click.echo("\n" + "-" * 40 + "\n")


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
    """Copy a reader profile to your local ~/.fetchez/ folder for editing."""

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
