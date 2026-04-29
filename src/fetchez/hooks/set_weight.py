#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
fetchez.hooks.set_weight
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Assigns processing weights to data entries based on module name or patterns.

:copyright: (c) 2010-2026 Regents of the University of Colorado
:license: MIT, see LICENSE for more details.
"""

import os
import logging
from fetchez.hooks import FetchHook

logger = logging.getLogger(__name__)


class SetWeight(FetchHook):
    """Assigns weights to entries based on rules.

    Usage:
        # In YAML:
        - name: set-weight
          args:
            default: 1.0
            rules:
              nos_hydro: 10.0      # High trust
              lidar: 5.0           # Medium trust
              csb: 0.5             # Low trust
              gmrt: 0.01           # Background fill

    The 'rules' dictionary keys are matched against:
    - The module name (e.g., 'nos_hydro')
    - The 'datatype' entry field (e.g., 'bag', 'xyz')
    """

    name = "set-weight"
    meta_desc = "Assigns weights to entries"
    meta_stage = "pre"
    meta_category = "metadata"
    meta_aliases = ["set_weight"]

    def __init__(self, default=1.0, rules=None, **kwargs):
        super().__init__(**kwargs)
        self.default = float(default)
        self.rules = rules or {}

        self.rules = {str(k).lower(): float(v) for k, v in self.rules.items()}

    def run(self, entries):
        for mod, entry in entries:
            keys_to_check = []

            if getattr(mod, "name", None):
                keys_to_check.append(str(mod.name).lower())

            if entry.get("datatype"):
                keys_to_check.append(str(entry.get("datatype")).lower())

            dst_fn = entry.get("dst_fn")
            if dst_fn:
                _, ext = os.path.splitext(dst_fn)
                if ext:
                    keys_to_check.append(ext.lower().lstrip("."))

            assigned_weight = self.default
            match_found = False

            for key in keys_to_check:
                if key in self.rules:
                    assigned_weight = self.rules[key]
                    match_found = True
                    break

            entry["weight"] = assigned_weight

            if match_found:
                logger.debug(
                    f"Assigned weight {assigned_weight} to {entry.get('dst_fn')} (Matched rule)"
                )
            else:
                logger.debug(
                    f"Assigned default weight {assigned_weight} to {entry.get('dst_fn')}"
                )

        return entries
