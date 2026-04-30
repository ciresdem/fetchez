#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
fetchez.cli.streams
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

STREAMS_COMMANDS = ["readers", "profiles"]


@click.group(cls=FetchezMainGroup, name="streams", fetchez_commands=STREAMS_COMMANDS)
def streams_group():
    """Discover, search, and learn about streams."""

    pass


streams_group.add_command(readers_group, name="readers")
streams_group.add_command(profiles_group, name="profiles")
