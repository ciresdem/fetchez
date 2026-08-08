#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
fetchez.modules.local_fs
~~~~~~~~~~~~~~~~~~~~~~~~

Unified handler for local files, file lists, and directory crawling with spatial indexing.

:copyright: (c) 2016 - 2026 Regents of the University of Colorado
:license: MIT, see LICENSE for more details.
"""

import json
import glob
import logging
from pathlib import Path
from typing import Optional, Any, Union, List

from fetchez.modules import FetchModule
from fetchez.spatial import Region, regions_intersect_p
from fetchez import cli

logger = logging.getLogger(__name__)


@cli.cli_opts(
    help_text="Process local files or crawl and spatially filter directories.",
    path="Single path or directory to process.",
    paths="List of input file paths.",
    ext="File extension to match when crawling directories (e.g., '.tif', '.h5').",
    data_type="Data type tag for downstream hooks.",
)
class LocalFS(FetchModule):
    name = "local_fs"
    meta_aliases = ["file", "path", "local_dataset"]
    meta_desc = (
        "Process local files, file lists, or crawl directories with spatial filtering."
    )
    meta_agency = "Fetchez"
    meta_tags = ["local", "folder", "directory", "file"]
    meta_category = "Local Data"
    meta_resolution = "Varies"
    meta_license = "N/A"

    def __init__(
        self,
        path: Optional[Union[str, Path]] = None,
        paths: Optional[Union[List[Union[str, Path]], str]] = None,
        ext: str = ".tif",
        datatype: Optional[Any] = None,
        data_type: Optional[Any] = None,
        **kwargs,
    ):
        kwargs["use_cache"] = kwargs.get("use_cache", False)  # No cache for local_fs!
        super().__init__(name="local_fs", **kwargs)

        # Support both spellings of data_type
        self.datatype = datatype or data_type or kwargs.get("data_type")
        self.ext = ext if ext.startswith(".") else f".{ext}"

        # Normalize explicit file/path inputs into a single list
        self.targets: List[Path] = []

        for input_item in [path, paths]:
            if not input_item:
                continue
            if isinstance(input_item, (list, tuple)):
                self.targets.extend([Path(p).resolve() for p in input_item])
            elif isinstance(input_item, (str, Path)):
                # Handle comma-separated strings
                for item in str(input_item).split(","):
                    clean_item = item.strip().replace("file://", "")
                    if clean_item:
                        self.targets.append(Path(clean_item).resolve())

    def _read_inf(self, inf_path: Path) -> Optional[Region]:
        """Attempt to parse an existing .inf sidecar file for spatial bounds."""
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

    def _register_file(self, file_path: Path):
        """Helper to register a valid local file entry."""
        file_region = None
        inf_path = file_path.with_name(f"{file_path.name}.inf")

        if inf_path.exists():
            file_region = self._read_inf(inf_path)

        # Apply spatial filtering if region metadata is available
        if file_region and self.wgs_region:
            if not regions_intersect_p(self.wgs_region, file_region):
                return False

        self.add_entry_to_results(
            url=f"file://{file_path}",
            dst_fn=str(file_path),
            data_type=self.datatype,
            status=0,
        )
        return True

    def run(self):
        if not self.targets:
            # Default to current working directory if no paths were supplied
            self.targets = [Path.cwd()]

        matched_files = 0
        for target in self.targets:
            if not target.exists():
                logger.warning(f"LocalFS target path does not exist: {target}")
                continue

            if target.is_file():
                if self._register_file(target):
                    matched_files += 1

            elif target.is_dir():
                search_pattern = target / f"**/*{self.ext}"
                logger.debug(f"Crawling {target} for '{self.ext}' files...")

                for filepath in glob.iglob(str(search_pattern), recursive=True):
                    f_path = Path(filepath)
                    if f_path.is_file() and self._register_file(f_path):
                        matched_files += 1

        logger.debug(f"LocalFS registered {matched_files} local file entries.")
        return self
