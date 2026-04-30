#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
fetchez.streams.base
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Base fetchez Reader class to create 'streams'

:copyright: (c) 2016 - 2026 Regents of the University of Colorado
:license: MIT, see LICENSE for more details.
"""


class BaseReader:
    """The base class for fetchez data Readers"""

    def __init__(self, path, **kwargs):
        self.path = path
        self.kwargs = kwargs

    def yield_chunks(self):
        """Stream read the source and yield standard output."""

        raise NotImplementedError
