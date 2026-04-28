#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
fetchez.cli.pipeline
~~~~~~~~~~~~~~~~

Genreate and run a fetchez pipeline.

:copyright: (c) 2010-2026 Regents of the University of Colorado
:license: MIT, see LICENSE for more details.
"""

import click
import yaml
import inspect
from fetchez.recipe import Recipe
from fetchez.registry import (
    ModuleRegistry,
    BundleRegistry,
    PresetRegistry,
    HookRegistry,
    SchemaRegistry,
)
from fetchez.spatial import parse_region
from fetchez.utils import (
    parse_hook_string,
    colorize,
    CYAN,
    GREEN,
    BOLD,
    FetchezMainGroup,
    FetchezMainCommand,
)


def _populate_subparser(module_cls):
    """Introspect module __init__ to populate subparser arguments."""

    if not module_cls:
        return []

    sig = inspect.signature(module_cls.__init__)
    arg_help = getattr(module_cls, "_cli_arg_help", {})
    params = []

    for name, param in sig.parameters.items():
        if name in [
            "self",
            "kwargs",
            "src_region",
            "callback",
            "outdir",
            "name",
            "params",
            "hook",
        ]:
            continue

        help_str = arg_help.get(name, f"Set {name} parameter")
        default = (
            param.default if param.default is not inspect.Parameter.empty else None
        )
        params.append([f"--{name}", help_str, default])

    return params


def add_options(options):
    def decorator(f):
        for opt in reversed(options or []):
            f = click.option(opt[0], default=opt[2], help=opt[1])(f)
        return f

    return decorator


# class PipelineExecutor(click.Group):
class PipelineExecutor(FetchezMainGroup):
    def list_commands(self, ctx):
        ModuleRegistry.load_all()
        BundleRegistry.load_all()
        mod_list = list(ModuleRegistry.get_registry().keys())
        mod_list.extend(list(BundleRegistry.get_registry().keys()))
        return sorted(mod_list)

    def get_command(self, ctx, name):
        ModuleRegistry.load_all()
        BundleRegistry.load_all()
        mod_cls = ModuleRegistry.get_class(name)
        bundle_yml = BundleRegistry.get_yaml(name)

        if not mod_cls and not bundle_yml:
            return None

        if mod_cls:
            help_text = getattr(mod_cls, "_cli_help_text", f"Run the {name} module.")
            mod_args = _populate_subparser(mod_cls)

        if bundle_yml:
            help_text = bundle_yml.get("description", "")
            mod_args = []

        @click.command(name=name, help=help_text, hidden=False, cls=FetchezMainCommand)
        @click.option("--weight", type=float, default=1.0)
        @click.option("--hook", multiple=True, help="Attach a processing hook")
        @add_options(mod_args)
        def dynamic_module_cmd(weight, hook, **kwargs):
            parsed_hooks = [parse_hook_string(h) for h in hook]
            module_type = "module" if mod_cls else "bundle"
            return {
                "type": "module",
                module_type: name,
                "args": {"weight": weight, **kwargs},
                "hooks": parsed_hooks,
            }

        return dynamic_module_cmd

    def format_commands(self, ctx, formatter):
        """Override the default Click help to group modules by category."""

        commands = []
        for subcommand in self.list_commands(ctx):
            cmd = self.get_command(ctx, subcommand)
            if cmd is None or cmd.hidden:
                continue
            commands.append((subcommand, cmd))

        if not commands:
            return

        grouped_commands = {}
        for name, cmd in commands:
            mod_meta = ModuleRegistry.get_info(name)

            if mod_meta:
                category = mod_meta.get("category", "Other Modules")
            else:
                # category = "📦 Curated Data Bundles"
                category = f"{colorize(colorize('Curated Data Bundles', GREEN), BOLD)}"

            if category not in grouped_commands:
                grouped_commands[category] = []

            grouped_commands[category].append((name, cmd))

        # Print the Bundles first, then alphabetize the remaining categories
        bundle_key = f"{colorize(colorize('Curated Data Bundles', GREEN), BOLD)}"
        if bundle_key in grouped_commands:
            with formatter.section(bundle_key):
                formatter.write_dl(
                    [
                        (f"{colorize(colorize(name, CYAN), BOLD)}", cmd.get_short_help_str(limit=80))
                        for name, cmd in grouped_commands.pop(bundle_key)
                    ]
                )

        # Print the rest of the categories
        for category, cmds in sorted(grouped_commands.items()):
            formatted_category = (
                f"{colorize(colorize(category, GREEN), BOLD)}"
                if category != "Other Modules"
                else category
            )

            with formatter.section(formatted_category):
                formatter.write_dl(
                    [
                        (
                            f"{colorize(colorize(name, CYAN), BOLD):<26}",
                            cmd.get_short_help_str(limit=80),
                        )
                        for name, cmd in cmds
                    ]
                )


@click.command(
    cls=PipelineExecutor, chain=True, help="Build or run a Fetchez pipeline."
)
@click.option("-R", "--region", help="Bounding box (W/E/S/N)")
@click.option("--global-hook", multiple=True, help="Attach a global processing hook")
@click.option("--schema", help="Apply a validation schema (e.g., 'crm')")
@click.option(
    "--threads", default=1, help="Number of parallel download threads (default: 1)."
)
@click.option(
    "--export", type=click.Path(), help="Export to YAML instead of executing."
)
@click.pass_context
def pipeline_group(ctx, region, export, global_hook, schema, threads):
    """Initializes the context before the chained subcommands run."""

    ctx.ensure_object(dict)
    src_region = parse_region(region) if region else None
    ctx.obj["region"] = src_region
    ctx.obj["export"] = export
    # ctx.obj["global_hook"] = parsed_global_hooks


@pipeline_group.result_callback()
def process_pipeline(commands, region, export, global_hook, schema, threads):
    """Executes after all chained commands have returned their dictionaries."""

    HookRegistry.load_all()
    PresetRegistry.load_all()

    modules = [cmd for cmd in commands if cmd.pop("type", None) == "module"]

    parsed_global_hooks = []
    for h in global_hook:
        parsed_h = parse_hook_string(h)
        if parsed_h.get("name") in PresetRegistry.get_registry().keys():
            parsed_h["preset"] = parsed_h.pop("name")
        elif parsed_h.get("name") not in HookRegistry.get_registry().keys():
            click.secho(
                f"Warning: Hook or Preset '{h}' not found in registry! Skipping.",
                fg="yellow",
            )
            continue
        parsed_global_hooks.append(parsed_h)

    # parsed_global_hooks = [parse_hook_string(h) for h in global_hook]

    # Build the recipe configuration dictionary
    config = {
        "project": {"name": "cli_pipeline"},
        "region": str(region) if region else None,
        "modules": modules,
        "global_hooks": parsed_global_hooks,
    }

    if schema:
        if SchemaRegistry.get_registry().get_class(schema) is not None:
            config["schema"] = schema

    if threads:
        config["execution"] = {"threads": threads}

    if export:
        with open(export, "w", encoding="utf-8") as f:
            yaml.dump(config, f, sort_keys=False)
        click.secho(f"Pipeline recipe exported to {export}", fg="green", bold=True)
    else:
        click.secho("Executing dynamic pipeline...", fg="cyan", bold=True, err=True)
        # Because config perfectly matches the YAML schema, the Recipe engine can just run it!
        Recipe.from_dict(config).run()
