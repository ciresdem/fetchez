#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
fetchez.modules.local_fs
~~~~~~~~~~~~~~~~~~~~~~~~

Recursively crawl local directories, spatially filter files using .inf sidecars.

:copyright: (c) 2016 - 2026 Regents of the University of Colorado
:license: MIT, see LICENSE for more details.
"""

import os
import json
import glob
import logging

from fetchez.modules import FetchModule
from fetchez.spatial import Region, regions_intersect_p
from fetchez import cli

logger = logging.getLogger(__name__)


@cli.cli_opts(
    help_text="Crawl and spatially filter a local directory of data.",
    path="The root directory to crawl.",
    ext="File extension to match (e.g., '.tif', '.bag', '.xyz').",
    datatype="Data type tag for downstream hooks (default: 'raster').",
)
class LocalFS(FetchModule):
    name = "local_fs"
    meta_desc = "Crawl, spatially filter, and process local directories of data."
    meta_agency = "Fetchez"
    meta_tags = ["local", "datalist", "folder", "directory"]
    meta_category = "Local Data"
    meta_resolution = "Varies"
    meta_license = "N/A"

    """Local data path Datalists."""

    def __init__(self, path=".", ext=".tif", datatype=None, **kwargs):
        super().__init__(name="local_fs", **kwargs)
        self.path = os.path.abspath(path)
        self.ext = ext if ext.startswith(".") else f".{ext}"
        self.datatype = datatype

    def _read_inf(self, inf_path):
        """Attempt to parse an existing .inf file for spatial bounds."""

        try:
            with open(inf_path, "r") as f:
                data = json.load(f)
                if all(k in data for k in ["min_x", "max_x", "min_y", "max_y"]):
                    return Region.from_list(
                        [data["min_x"], data["max_x"], data["min_y"], data["max_y"]]
                    )
        except Exception:
            pass
        return None

    def run(self):
        if not os.path.exists(self.path):
            logger.error(f"LocalFS path does not exist: {self.path}")
            return self

        search_pattern = os.path.join(self.path, f"**/*{self.ext}")
        matched_files = 0

        logger.debug(f"Crawling {self.path} for '{self.ext}' files...")

        for filepath in glob.iglob(search_pattern, recursive=True):
            file_region = None
            inf_path = filepath + ".inf"

            if os.path.exists(inf_path):
                file_region = self._read_inf(inf_path)

            if file_region:
                if regions_intersect_p(self.wgs_region, file_region):
                    self.add_entry_to_results(
                        url=f"file://{filepath}",
                        dst_fn=filepath,
                        data_type=self.datatype,
                        status=0,
                    )
                    matched_files += 1

            else:
                self.add_entry_to_results(
                    url=f"file://{filepath}",
                    dst_fn=filepath,
                    data_type=self.datatype,
                    status=0,
                )
                matched_files += 1

        logger.debug(f"LocalFS matched {matched_files} files in {self.wgs_region}")
        return self
