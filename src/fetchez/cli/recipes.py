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
from fetchez.recipe import Recipe
from fetchez.registry import RecipeRegistry
from fetchez.utils import FetchezMainGroup, FetchezMainCommand
from .schemas import schemas_group

RECIPE_COMMANDS = ["copy", "dump", "info", "list", "validate", "run", "schemas"]


def validate_dependencies(recipe_obj):
    """Interrogates all modules and hooks to ensure heavy dependencies exist."""

    errors = []

    # Check all global hooks
    for hook in getattr(recipe_obj, "global_hooks", []):
        if hasattr(hook, "_validate_deps"):
            passed, msg = hook._validate_deps()
            if not passed:
                errors.append(f"[{hook.name}] {msg}")

    # Check all streaming hooks inside the modules
    for mod in getattr(recipe_obj, "modules", []):
        for hook in getattr(mod, "hooks", []):
            if hasattr(hook, "_validate_deps"):
                passed, msg = hook._validate_deps()
                if not passed:
                    errors.append(f"[{mod.name} -> {hook.name}] {msg}")

    if errors:
        click.secho("\n[ DEPENDENCY VALIDATION CHECK FAILED ]", fg="red", bold=True)
        click.secho(
            "The following dependencies are missing for this recipe:", fg="yellow"
        )
        for error in errors:
            click.echo(f"   {error}")
        click.echo(
            "\nPlease install the required packages or modify the recipe and try again.\n"
        )
        sys.exit(1)


def _load_yaml(target):
    base_config = None
    if os.path.exists(target) and not os.path.isdir(target):
        with open(target, "r", encoding="utf-8") as f:
            base_config = yaml.safe_load(f)
    else:
        RecipeRegistry.load_all()
        recipe_meta = RecipeRegistry.get_yaml(target)
        if recipe_meta:
            base_config = recipe_meta["config"]
            click.secho(f"Loaded curated recipe: {target}", fg="cyan")

    return base_config


@click.group(
    cls=FetchezMainGroup,
    name="recipes",
    fetchez_commands=RECIPE_COMMANDS,
)
def recipes_group():
    """Discover, inspect, and copy complete pipeline workflows."""

    pass


@recipes_group.command("list", cls=FetchezMainCommand)
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


@recipes_group.command("info", cls=FetchezMainCommand)
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


@recipes_group.command("dump", cls=FetchezMainCommand)
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


@recipes_group.command("copy", cls=FetchezMainCommand)
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


@recipes_group.command("validate", cls=FetchezMainCommand)
@click.argument("name")
def recipe_validate(name):
    """Check a recipe for syntax errors and missing modules/hooks."""

    from fetchez.registry import ModuleRegistry, HookRegistry

    ModuleRegistry.load_all()
    HookRegistry.load_all()

    base_config = _load_yaml(name)
    if not base_config:
        click.secho(
            f"Error: Recipe '{name}' not found locally or in the registry.", fg="red"
        )
        sys.exit(1)

    errors = 0
    click.secho(f"Validating {name}...", fg="blue")

    validate_dependencies(base_config)

    for mod in base_config.get("modules", []):
        mod_name = mod.get("module")
        mod_keys = mod.keys()
        valid_keys = ["module", "hooks", "args"]

        for key in mod_keys:
            if key not in valid_keys:
                click.secho(
                    f"Module `{mod_name}` has unexpected reference to `{key}`", fg="red"
                )
                errors += 1

        if not ModuleRegistry.get_class(mod_name) and mod_name not in [
            "file",
            "local_fs",
        ]:
            click.secho(f"  Missing Module: '{mod_name}'", fg="red")
            errors += 1
        else:
            click.secho(f"  Valid Module: '{mod_name}'", fg="green")

        for hook in mod.get("hooks", []):
            if not HookRegistry.get_class(hook.get("name")):
                click.secho(
                    f"  Missing Hook: '{hook.get('name')}' (in module {mod_name})",
                    fg="red",
                )
                errors += 1
            else:
                click.secho(
                    f"  Valid Hook: '{hook.get('name')}' (in module {mod_name})",
                    fg="green",
                )

    for hook in base_config.get("global_hooks", []):
        if not HookRegistry.get_class(hook.get("name")):
            click.secho(f"  Missing Global Hook: '{hook.get('name')}'", fg="red")
            errors += 1
        else:
            click.secho(f"  Valid Hook: '{hook.get('name')}'", fg="green")

    if errors == 0:
        click.secho("Recipe appears valid!", fg="green", bold=True)
    else:
        click.secho(f"Failed validation with {errors} errors.", fg="red", bold=True)
        sys.exit(1)


@recipes_group.command("run", cls=FetchezMainCommand)
@click.argument("name")
def run_recipe(name):
    """Execute a YAML recipe by registry name or file path."""

    RecipeRegistry.load_all()

    click.secho(f"Executing YAML recipe: {name}...", fg="cyan", bold=True)

    if os.path.exists(name):
        Recipe.from_file(name).run()
        return

    meta = RecipeRegistry.get_yaml(name)
    if not meta:
        click.secho(
            f"Error: Recipe '{name}' not found in registry or local path.", fg="red"
        )
        sys.exit(1)

    Recipe.from_dict(meta).run()


recipes_group.add_command(schemas_group, name="schemas")
