#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
fetchez.hooks.set_srs
~~~~~~~~~~~~~

Change the default 'src_srs' of an entry.

:copyright: (c) 2010-2026 Regents of the University of Colorado
:license: MIT, see LICENSE for more details.
"""

import os
import logging
from fetchez.hooks import FetchHook
from fetchez.utils import parse_arg_to_dict

logger = logging.getLogger(__name__)


class SetSrs(FetchHook):
    """Overrides the src_srs attribute of pipeline entries based on rules.

    Useful for mapping generic files to specific parser profiles.

    Usage:
        # Universal override
        --hook set_srs:srs='EPSG:4326+5703'

        # Rule-based override
        --hook set_srs:rules=nos_hydro=EPSG:3857/lidar=EPSG:26911
    """

    name = "set-srs"
    meta_desc = "Override the src_srs of pipeline entries based on rules."
    meta_stage = "manifest"
    meta_category = "metadata"
    meta_aliases = ["set_srs"]

    def __init__(self, srs=None, default=None, rules=None, match_key=None, **kwargs):
        super().__init__(**kwargs)
        self.default = default if default is not None else srs
        self.match_key = match_key

        self.rules = parse_arg_to_dict(rules, cast_type=str)
        self.rules = {str(k).lower(): str(v) for k, v in self.rules.items()}

    def run(self, entries):
        for mod, entry in entries:
            keys_to_check = []

            if self.match_key:
                val = entry.get(self.match_key)
                if val is not None:
                    keys_to_check.append(str(val).lower())
            else:
                if getattr(mod, "name", None):
                    keys_to_check.append(str(mod.name).lower())
                if entry.get("data_type"):
                    keys_to_check.append(str(entry.get("data_type")).lower())
                dst_fn = entry.get("dst_fn")
                if dst_fn:
                    keys_to_check.append(dst_fn.lower())
                    _, ext = os.path.splitext(dst_fn)
                    if ext:
                        keys_to_check.append(ext.lower().lstrip("."))

            assigned_srs = self.default
            match_found = False

            for key in keys_to_check:
                for rule_key, rule_val in self.rules.items():
                    if rule_key in key:
                        assigned_srs = rule_val
                        match_found = True
                        break
                if match_found:
                    break

            if assigned_srs is not None:
                old_srs = entry.get("src_srs", "unknown")
                if old_srs != assigned_srs:
                    entry["src_srs"] = assigned_srs
                    logger.debug(
                        f"Changed src_srs from '{old_srs}' to '{assigned_srs}' "
                        f"for {os.path.basename(entry.get('dst_fn', ''))}"
                    )

        return entries
