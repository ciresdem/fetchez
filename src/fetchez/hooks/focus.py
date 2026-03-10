#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
fetchez.hooks.focus
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Pipeline control hooks for artifact focus.

:copyright: (c) 2010-2026 Regents of the University of Colorado
:license: MIT, see LICENSE for more details.
"""

import logging
from fetchez.hooks import FetchHook

logger = logging.getLogger(__name__)


class FocusSink(FetchHook):
    """Shrinks the pipeline entries down to the output of a specific Sink/Hook.
    Subsequent Post-Hooks will only act on these generated artifacts.

    The target hook must adhere to the 'Artifact Protocol' by registering
    its outputs in `entry['artifacts'][hook_name] = output_path`.

    Usage:
      --hook focus_sink:target=blended_checkpoint
    """

    name = "focus_sink"
    meta_desc = "Focus the pipeline to an 'artifact'"
    meta_stage = "post"
    meta_category = "pipeline"

    def __init__(self, target=None, **kwargs):
        super().__init__(**kwargs)
        self.target = target

    def run(self, entries):
        if not self.target:
            logger.warning("No target specified. Ignoring.")
            return entries

        new_entries = []
        seen_paths = set()
        found_target = False

        for mod, entry in entries:
            artifacts = entry.get("artifacts", {})

            if self.target in artifacts:
                found_target = True

                # Artifacts can be a single path or a list of paths
                artifact_paths = artifacts[self.target]
                if isinstance(artifact_paths, str):
                    artifact_paths = [artifact_paths]

                for path in artifact_paths:
                    if path not in seen_paths:
                        seen_paths.add(path)

                        focused_entry = {
                            "url": f"file://{path}",
                            "dst_fn": path,
                            "status": 0,
                            "data_type": f"{self.target}_artifact",
                            "artifacts": artifacts,
                        }
                        new_entries.append((mod, focused_entry))

        if not found_target:
            logger.warning(
                f"Artifact target '{self.target}' was not found in any pipeline entries! "
                f"Ignoring focus request and passing original stream onward."
            )
            return entries

        logger.info(f"Shrunk pipeline to {len(new_entries)} '{self.target}' artifacts.")
        return new_entries
