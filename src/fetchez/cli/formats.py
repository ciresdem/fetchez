#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
fetchez.cli.formats
~~~~~~~~~~~~~~~~

Discoverability and documentation for processing readers.

:copyright: (c) 2010-2026 Regents of the University of Colorado
:license: MIT, see LICENSE for more details.
"""

import click

# from fetchez.api import list_readers
from fetchez.utils import FetchezMainGroup
from .readers import readers_group
from .profiles import profiles_group

FORMATS_COMMANDS = ["readers", "profiles"]


@click.group(cls=FetchezMainGroup, name="formats", fetchez_commands=FORMATS_COMMANDS)
def formats_group():
    """Discover, search, and learn about formats."""

    pass


formats_group.add_command(readers_group, name="readers")
formats_group.add_command(profiles_group, name="profiles")
