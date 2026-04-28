#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
fetchez.cli
~~~~~~~~~~~

The main command-line interface for the Fetchez framework.

:copyright: (c) 2010-2026 Regents of the University of Colorado
:license: MIT, see LICENSE for more details.
"""

import click
import logging
from typing import Optional

from fetchez.utils import TqdmLoggingHandler, FetchezMainGroup, colorize, GREEN, BOLD

from .pipeline import pipeline_group
from .modules import modules_group
from .hooks import hooks_group
from .schemas import schemas_group
from .recipes import recipes_group
from .presets import presets_group
from .bundles import bundles_group


# =============================================================================
# CLI Decorator and Decorations and logging
# =============================================================================
def cli_opts(help_text: Optional[str] = None, **arg_help):
    """Decorator to attach CLI help text to FetchModule classes.

    Args:
        help_text: The description for the module's sub-command.
        **arg_help: Key-value pairs matching __init__ arguments to help strings.
    """

    def decorator(cls):
        cls._cli_help_text = help_text
        cls._cli_arg_help = arg_help
        return cls

    return decorator


def setup_logging(name="fetchez", quiet=False, verbose=False):
    if quiet:
        log_level = logging.WARNING
    elif verbose:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO

    logger = logging.getLogger(name)
    logger.setLevel(log_level)

    logger.propagate = False

    if logger.hasHandlers():
        logger.handlers.clear()

    handler = TqdmLoggingHandler()

    formatter = logging.Formatter("[ %(levelname)s ] %(name)s: %(message)s")
    handler.setFormatter(formatter)

    logger.addHandler(handler)


@click.group(
    cls=FetchezMainGroup,
    # help=f"\b{_cli_logo('fetchez', 'Fetch geospatial data with ease.', __version__)}",
    help="Fetch geospatial data with ease.",
    fetchez_commands={
        "Execution": ["run"],
        "Discovery and Management": [
            "modules",
            "hooks",
            "schemas",
            "recipes",
            "presets",
            "bundles",
        ],
    },
#     epilog=f"""
# \b
# {colorize(colorize('Examples', GREEN), BOLD)}:
#   # Quick fetch for a specific location
#   $ fetchez run -R loc:seattle tides
#   \b
#   # Run multiple modules with weights and specific hooks
#   $ fetchez run -R -120/34/-119/35 coned --weight 2.0 tnm --hook unzip
#   \b
#   # Execute a complete pre-built YAML pipeline recipe
#   $ fetchez run --recipe crm_standard
#   \b
#   # Export a dynamic CLI command into a reusable YAML recipe
#   $ fetchez run -R loc:hawaii --export my_pipeline.yaml bluetopo
#     """
)
@click.version_option(package_name="fetchez")
@click.option("--verbose", is_flag=True, help="Enable verbose debug logging.")
@click.option("--quiet", is_flag=True, help="Suppress non-error output.")
def cli(verbose, quiet):
    """Fetchez CLI."""

    setup_logging(quiet=quiet, verbose=verbose)


cli.add_command(pipeline_group, name="run")
cli.add_command(modules_group, name="modules")
cli.add_command(hooks_group, name="hooks")
cli.add_command(schemas_group, name="schemas")
cli.add_command(recipes_group, name="recipes")
cli.add_command(presets_group, name="presets")
cli.add_command(bundles_group, name="bundles")


if __name__ == "__main__":
    cli()
