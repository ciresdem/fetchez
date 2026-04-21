#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
fetchez.hooks.localize_cache
~~~~~~~~~~~~~

Localize fetchez cache into a specific directory.

:copyright: (c) 2010-2026 Regents of the University of Colorado
:license: MIT, see LICENSE for more details.
"""

import os
import shutil
import logging
from fetchez.hooks import FetchHook

logger = logging.getLogger(__name__)


class LocalizeCacheHook(FetchHook):
    """Copies or symlinks fetched pipeline artifacts into a specific local directory."""

    name = "localize_cache"
    meta_stage = "collection"
    meta_domain = "System"
    meta_category = "Utility"

    def __init__(self, target_dir=".", symlink=False, **kwargs):
        super().__init__(**kwargs)
        self.target_dir = os.path.abspath(target_dir)
        self.symlink = str(symlink).lower() in ["true", "1", "t", "yes"]

    def run(self, entries):
        os.makedirs(self.target_dir, exist_ok=True)

        for mod, entry in entries:
            # Get the active file path
            current_path = entry.get("dst_fn") or entry.get("src_fn")

            if not current_path or not os.path.exists(current_path):
                continue

            filename = os.path.basename(current_path)
            local_path = os.path.join(self.target_dir, filename)

            # Skip if the file is already where it needs to be
            if os.path.abspath(current_path) == local_path:
                continue

            try:
                if self.symlink:
                    # Remove existing link to prevent FileExistsError
                    if os.path.lexists(local_path):
                        os.remove(local_path)
                    os.symlink(os.path.abspath(current_path), local_path)
                    logger.info(
                        f"[{self.name}] Symlinked {filename} to {self.target_dir}"
                    )
                else:
                    shutil.copy2(current_path, local_path)
                    logger.info(f"[{self.name}] Copied {filename} to {self.target_dir}")

                # Update the entry.
                entry["dst_fn"] = local_path

            except Exception as e:
                logger.error(f"[{self.name}] Failed to localize {filename}: {e}")

        return entries
