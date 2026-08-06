#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
fetchez.streams.readers.base
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Base fetchez Reader class to create 'streams'

:copyright: (c) 2016 - 2026 Regents of the University of Colorado
:license: MIT, see LICENSE for more details.
"""

from fetchez.spatial import Region


class BaseReader:
    """The base class for fetchez data Readers"""

    def __init__(self, path, region=None, **kwargs):
        self.path = path
        if region is not None and not isinstance(region, Region):
            try:
                self.region = Region.from_list(region)
            except Exception:
                self.region = region
        else:
            self.region = region
        self.kwargs = kwargs

    def yield_chunks(self):
        """Stream read the source and yield standard output."""

        raise NotImplementedError
