#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
fetchez.cli.hooks
~~~~~~~~~~~~~~~~

Discoverability and documentation for processing hooks.

:copyright: (c) 2010-2026 Regents of the University of Colorado
:license: MIT, see LICENSE for more details.
"""

import sys
import click

# from fetchez.api import list_hooks
from fetchez.registry import HookRegistry
from fetchez.utils import get_class_arguments, FetchezMainGroup, FetchezMainCommand


@click.group(
    cls=FetchezMainGroup,
    name="hooks",
    fetchez_commands=["info", "list"],
)
def hooks_group():
    """Discover, search, and learn about data processors.

    Hooks are modular processing steps (filters, transforms, algorithms)
    that manipulate data streams or files in a pipeline.

    \b
    How to use Hooks:
      1. In YAML Recipes: Defined under `hooks` (per-module) or `global_hooks`.
      2. In CLI Commands: Appended directly to data sources using the --hook switch or globally with --globl-hook.

    \b
    CLI String Syntax (Source + Hooks):
      <source> --arg val --hook <hook_name>:arg=val,arg2=val

    \b
    CLI Examples:
      fetchez pipeline --global-hook audit file --path my_data.laz --hook exec:cmd=laszip
    """

    pass


@hooks_group.command("list", cls=FetchezMainCommand)
@click.option("--search", "-s", help="Filter hooks by name or keyword.")
def hook_list(search):
    """List all available processing hooks grouped by category."""

    HookRegistry.load_builtins()
    registry = HookRegistry.get_registry()

    grouped_hooks = {}
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
        grouped_hooks.setdefault(cat, []).append((name, meta))

    click.secho("\nAvailable Hooks by Category:", fg="cyan", bold=True)
    click.echo("=" * 60)

    for cat in sorted(grouped_hooks.keys()):
        click.secho(f"\n[ {cat} ]", fg="yellow", bold=True)
        for name, meta in sorted(grouped_hooks[cat], key=lambda x: x[0]):
            stage = meta.get("stage", "unknown")
            desc = meta.get("desc", "No description provided.")

            name_padded = f"{name:<16}"
            stage_padded = f"[{stage:^6}]"

            click.echo(
                f"  {click.style(name_padded, bold=True, fg='green')} {click.style(stage_padded, fg='blue')} : {desc}"
            )

    click.echo("\nRun 'fetchez hooks info <name>' for arguments and recipe examples.\n")


@hooks_group.command("info", cls=FetchezMainCommand)
@click.argument("name")
def hook_info(name):
    """Show arguments and YAML recipe examples for a specific hook."""

    HookRegistry.load_all()
    hook_cls = HookRegistry.get_class(name)
    meta = HookRegistry.get_info(name)

    if not hook_cls:
        click.secho(f"Error: Hook '{name}' not found.", fg="red")
        sys.exit(1)

    click.secho(f"\n🪝 HOOK: {name}", fg="cyan", bold=True)
    click.echo("=" * 60)
    click.echo(f"  Description : {meta.get('desc', 'N/A')}")
    click.echo(f"  Stage       : {meta.get('stage', 'N/A')}")
    click.echo(f"  Category    : {meta.get('category', 'N/A')}\n")

    # print_class_arguments(hook_cls)
    args_dict = get_class_arguments(hook_cls)

    click.secho("  Arguments:", fg="yellow", bold=True)
    for key, val in args_dict.items():
        click.echo(f"    - {click.style(key, bold=True)} {val}")

    # Generate the YAML Snippet
    click.secho("\n  YAML Recipe Example:", fg="green", bold=True)
    click.echo("-" * 40)

    if meta.get("stage") in ["pre", "file"]:
        click.echo("  # Attached to a specific module:")
        click.echo("  modules:")
        click.echo("    - module: example_source")
        click.echo("      hooks:")
        click.echo(f"        - name: {name}")
    else:
        click.echo("  # Placed in the global pipeline:")
        click.echo("  global_hooks:")
        click.echo(f"    - name: {name}")

    if args_dict:
        click.echo("      args:")
        for k, v in args_dict.items():
            val_str = f'"{v}"' if isinstance(v, str) and v != "REQUIRED" else v
            click.echo(f"        {k}: {val_str}")

    click.echo("-" * 40 + "\n")
