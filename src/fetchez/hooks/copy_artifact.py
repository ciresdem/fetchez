#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
fetchez.hooks.copy_artifact
~~~~~~~~~~~~~

Copy a registrered entry artifact to a new location.

:copyright: (c) 2010-2026 Regents of the University of Colorado
:license: MIT, see LICENSE for more details.
"""

import os
import shutil
import logging
from fetchez.hooks import FetchHook

logger = logging.getLogger(__name__)


class CopyArtifactHook(FetchHook):
    """Copies resulting artifacts to a target directory. Useful for batch collating.

    *Does not modify entry*

    Usage:
      --hook copy-artifact:target_dir="../_collate",match="dem.tif/hillshade.tif"
    """

    name = "copy-artifact"
    meta_stage = "collection"
    meta_category = "Pipeline"
    meta_desc = (
        "Copies resulting artifacts to a target directory. Useful for batch collating."
    )
    meta_aliases = ["copy_artifact"]

    def __init__(self, target_dir="../_collate", match=None, **kwargs):
        super().__init__(**kwargs)
        self.target_dir = os.path.abspath(target_dir)

        if isinstance(match, str):
            self.matches = [m.strip() for m in match.split("/")]
        elif isinstance(match, list):
            self.matches = match
        else:
            self.matches = []

    def run(self, entries):
        os.makedirs(self.target_dir, exist_ok=True)

        for _mod, entry in entries:
            artifacts = entry.get("artifacts", {})
            files_to_copy = []

            if self.matches:
                for _key, path in artifacts.items():
                    if any(m in path for m in self.matches) and os.path.exists(path):
                        files_to_copy.append(path)
            else:
                dst_fn = entry.get("dst_fn")
                if dst_fn and os.path.exists(dst_fn):
                    files_to_copy.append(dst_fn)

            files_to_copy = list(set(files_to_copy))
            for fpath in files_to_copy:
                dest_path = os.path.join(self.target_dir, os.path.basename(fpath))
                logger.info(
                    f"[{self.name}] Collating {os.path.basename(fpath)} -> {self.target_dir}"
                )

                try:
                    shutil.copy2(fpath, dest_path)
                except Exception as e:
                    logger.error(f"[{self.name}] Failed to copy {fpath}: {e}")

        return entries
