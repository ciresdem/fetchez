#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
fetchez.click
~~~~~~~~~~~

The main command-line interface for the Fetchez framework.

:copyright: (c) 2010-2026 Regents of the University of Colorado
:license: MIT, see LICENSE for more details.
"""

import click
import logging

from fetchez.utils import _cli_logo, TqdmLoggingHandler, colorize, BOLD, YELLOW
from fetchez import __version__

from .pipeline import pipeline_group

from .modules import modules_group
from .hooks import hooks_group
from .schemas import schemas_group
from .recipes import recipes_group
from .presets import presets_group
from .bundles import bundles_group


def setup_logging(quiet=False, verbose=False):
    if quiet:
        log_level = logging.WARNING
    elif verbose:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO

    logger = logging.getLogger("fetchez")
    logger.setLevel(log_level)

    logger.propagate = False

    if logger.hasHandlers():
        logger.handlers.clear()

    handler = TqdmLoggingHandler()

    formatter = logging.Formatter("[ %(levelname)s ] %(name)s: %(message)s")
    handler.setFormatter(formatter)

    logger.addHandler(handler)


class FetchezMainGroup(click.Group):
    """Custom group to categorize the main CLI commands."""

    def format_commands(self, ctx, formatter):
        commands = []
        for subcommand in self.list_commands(ctx):
            cmd = self.get_command(ctx, subcommand)
            if cmd is None or cmd.hidden:
                continue
            commands.append((subcommand, cmd))

        if not commands:
            return

        categories = {
            f"{colorize('Execution', YELLOW)}": ["run"],
            f"{colorize('Discovery & Management', YELLOW)}": [
                "modules",
                "hooks",
                "schemas",
                "recipes",
                "presets",
                "bundles",
            ],
        }

        for cat_name, cmd_names in categories.items():
            with formatter.section(cat_name):
                cat_cmds = [
                    (f"{colorize(name, BOLD):<17}", cmd.get_short_help_str(limit=80))
                    for name, cmd in commands
                    if name in cmd_names
                ]
                formatter.write_dl(cat_cmds)


@click.group(
    cls=FetchezMainGroup,
    help=f"\b{_cli_logo('fetchez', 'Fetch geospatial data with ease.', __version__)}",
    # help=f"\b\n{_cli_logo('fetchez', 'Fetch geospatial data with ease.', __version__)}",
)
@click.version_option(package_name="fetchez")
def cli():
    """Fetchez CLI."""
    setup_logging()


cli.add_command(pipeline_group, name="run")
cli.add_command(modules_group, name="modules")
cli.add_command(hooks_group, name="hooks")
cli.add_command(schemas_group, name="schemas")
cli.add_command(recipes_group, name="recipes")
cli.add_command(presets_group, name="presets")
cli.add_command(bundles_group, name="bundles")

if __name__ == "__main__":
    cli()
# #!/usr/bin/env python
# # -*- coding: utf-8 -*-

# """
# fetchez.click
# ~~~~~~~~~~~
# The main command-line interface for the Fetchez framework.
# """

# import click
# import logging

# from fetchez.utils import _cli_logo, TqdmLoggingHandler
# from fetchez import __version__

# from .run import run_group
# from .pipeline import pipeline_group

# # from .discover import hooks_group, modules_group
# from .modules import modules_group
# from .hooks import hooks_group
# from .schemas import schemas_group

# from .recipes import recipes_group
# from .presets import presets_group
# from .bundles import bundles_group


# @click.group(
#     help=f"\b{_cli_logo('fetchez', 'Fetch geospatial data with ease.', __version__)}",
# )
# @click.version_option(package_name="fetchez")
# def cli():
#     """Fetchez CLI."""

#     setup_logging()


# cli.add_command(run_group, name="run")
# cli.add_command(pipeline_group, name="pipeline")

# cli.add_command(modules_group, name="modules")
# cli.add_command(hooks_group, name="hooks")
# cli.add_command(schemas_group, name="schemas")

# cli.add_command(recipes_group, name="recipes")
# cli.add_command(presets_group, name="presets")
# cli.add_command(bundles_group, name="bundles")


# if __name__ == "__main__":
#     cli()
