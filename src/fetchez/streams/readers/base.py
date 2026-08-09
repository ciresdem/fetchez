#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
fetchez.streams.readers.base
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Base fetchez Reader class to create 'streams'

:copyright: (c) 2016 - 2026 Regents of the University of Colorado
:license: MIT, see LICENSE for more details.
"""

import json
import numpy as np
import logging

from fetchez.spatial import Region

logger = logging.getLogger(__name__)


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

        self.infos = {}
        self.kwargs = kwargs

    def generate_inf(self, out_path=None):
        out_path = out_path or f"{self.path}.inf"

        minmax = [np.inf, -np.inf, np.inf, -np.inf, np.inf, -np.inf]
        total_pts = 0

        # Consume the stream directly (do not yield!)
        for chunk in self.yield_chunks():
            if chunk is None or len(chunk) == 0:
                continue

            try:
                # xmin, xmax, ymin, ymax, zmin, zmax, count = self._extract_bounds(chunk)
                count = len(chunk)
                xmin = min(chunk.x)
                ymin = min(chunk.y)
                zmin = min(chunk.z)
                xmax = max(chunk.x)
                ymax = max(chunk.y)
                zmax = max(chunk.z)

                total_pts += count
                minmax[0] = min(minmax[0], xmin)  # W
                minmax[1] = max(minmax[1], xmax)  # E
                minmax[2] = min(minmax[2], ymin)  # S
                minmax[3] = max(minmax[3], ymax)  # N
                minmax[4] = min(minmax[4], zmin)  # Z-min
                minmax[5] = max(minmax[5], zmax)  # Z-max
            except Exception:
                # raise
                pass  # Silently fail bounds extraction if chunk is weird

        meta = {}

        # Write the .inf file once the stream is completely exhausted
        if total_pts > 0 and minmax[0] != np.inf:
            w, e, s, n = minmax[0], minmax[1], minmax[2], minmax[3]
            wkt = f"POLYGON (({w} {n}, {e} {n}, {e} {s}, {w} {s}, {w} {n}))"

            meta = {
                "numpts": int(total_pts),
                "minmax": [float(x) for x in minmax],
                "wkt": wkt,
            }

            try:
                with open(out_path, "w") as f:
                    json.dump(meta, f, indent=4)
            except Exception:
                logger.debug(f"Could not write inf file {out_path}")

        return meta

    def _read_chunks(self):
        """Subclasses MUST implement this to yield their specific data chunks."""
        raise NotImplementedError

    def _extract_bounds(self, chunk):
        """Subclasses MUST implement this to return (xmin, xmax, ymin, ymax, zmin, zmax, count)
        for a given chunk.
        """
        raise NotImplementedError

    def yield_chunks(self):
        yield from self._read_chunks()
