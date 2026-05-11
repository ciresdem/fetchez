#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
fetchez.hooks.set_srs
~~~~~~~~~~~~~

Change the default 'src_srs' of an entry.

:copyright: (c) 2010-2026 Regents of the University of Colorado
:license: MIT, see LICENSE for more details.
"""

import logging
from fetchez.hooks import FetchHook

logger = logging.getLogger(__name__)


class SetDataType(FetchHook):
    """Overrides the src_srs attribute of pipeline entries.

    Useful for mapping generic files to specific parser profiles.

    Usage: --hook set_srs:srs='epsg:4326+5703'
    """

    name = "set-srs"
    meta_desc = "Override the src_srs of pipeline entries."
    meta_stage = "file"
    meta_category = "metadata"
    meta_aliases = ["set_srs"]

    def __init__(self, srs="EPSG:4326", **kwargs):
        super().__init__(**kwargs)
        self.srs = srs

    def run(self, entries):
        if not self.srs:
            return entries

        for mod, entry in entries:
            if entry.get("status") == 0:
                old_srs = entry.get("srs", "unknown")
                entry["src_srs"] = self.srs
                logger.debug(
                    f"Changed src_srs from '{old_srs}' to '{self.srs}' for {entry.get('dst_fn')}"
                )

        return entries
