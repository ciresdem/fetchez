#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
fetchez.hooks.base
~~~~~~~~~~~~~~~~~~~~~~

This file holds the FetchHook super class

:copyright: (c) 2010-2026 Regents of the University of Colorado
:license: MIT, see LICENSE for more details.
"""


class FetchHook:
    """Base class for all Fetchez Hooks."""

    name = "base_hook"

    # --- Registry Metadata ---
    meta_desc = "Does something."
    meta_category = "uncategorized"

    # 'manifest':   Runs before downloads, manipulating the URL/metadata list.
    # 'file':       Runs per-file immediately after download/generation.
    # 'collection': Runs once after all per-file operations are finished.
    meta_stage = "file"

    def __init__(self, stage=None, **kwargs):
        self.opts = kwargs

        # Grab the stage from kwargs, or fallback to the class meta_stage
        raw_stage = stage or getattr(self.__class__, "meta_stage", "file")

        # Map legacy names to the new modern names
        stage_aliases = {
            "pre": "manifest",
            "post": "collection"
        }

        # Normalize and apply alias
        mapped_stage = stage_aliases.get(raw_stage.lower(), raw_stage.lower())

        # Validate and Set
        if mapped_stage in ["manifest", "file", "collection"]:
            self.stage = mapped_stage
        else:
            self.stage = "file" # Safe fallback

    def __eq__(self, other):
        """Hooks are 'equal' if they are the same type and have identical dicts."""

        if not isinstance(other, type(self)):
            return False
        return self.__dict__ == other.__dict__

    def teardown(self):
        """Cleanup.

        Called strictly once after all processing is complete.
        Override this to close files, finalize grids, or print summaries.
        """

        pass

    def run(self, entry):
        """Execute the hook.

        Args:
            entry: For 'file' stage: [url, path, type, status]
                   For 'manifest'/'collection': The full list of results (so far) or context.

        Returns:
            Modified entry (for 'file' stage pipeline) or None.
        """

        return entry
