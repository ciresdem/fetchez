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

from fetchez.utils import FetchezMainGroup
from .readers import readers_group
from .profiles import profiles_group

STREAMS_COMMANDS = ["readers", "profiles"]


@click.group(cls=FetchezMainGroup, name="streams", fetchez_commands=STREAMS_COMMANDS)
def streams_group():
    """Discover, search, and learn about streams.

    \b
    When Fetchez downloads a file (like a GeoTIFF or NetCDF), it can use Streams
    to read the data piece-by-piece in memory. This allows for  control over how
    to process different datasets.

    \b
    This command group lets you explore the internal 'Readers' that parse the
    files, and the 'Profiles' that tell those readers exactly how to behave.
    """

    pass


streams_group.add_command(readers_group, name="readers")
streams_group.add_command(profiles_group, name="profiles")
