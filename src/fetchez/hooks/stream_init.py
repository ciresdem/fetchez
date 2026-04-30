#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
fetchez.hooks.stream_init
~~~~~~~~~~~~~

This turns files into streams.

:copyright: (c) 2010-2026 Regents of the University of Colorado
:license: MIT, see LICENSE for more details.
"""

import logging

from fetchez.spatial import Region
from fetchez.hooks import FetchHook
from fetchez.registry import ReaderRegistry, ProfileRegistry

logger = logging.getLogger(__name__)


class DataStream(FetchHook):
    """Auto-detects file type and attaches a stream.

    Usage:
      --hook stream-init:stream_type=csv
    """

    name = "stream-init"
    meta_stage = "file"
    meta_desc = "Setup a data stream from input data."
    meta_category = "stream"
    meta_requires = "file"
    meta_aliases = ["stream_init"]

    def __init__(self, stream_type=None, **kwargs):
        super().__init__(**kwargs)
        self.stream_type = stream_type  # .lower()
        self.reader_kwargs = kwargs

    def run(self, entries):
        ReaderRegistry.load_all()
        ProfileRegistry.load_all()

        for mod, entry in entries:
            if entry.get("stream"):
                logger.warning(
                    f"Entry {entry} already has an attached {entry.get('stream_type')} stream..."
                )
                continue

            src = entry.get("dst_fn")
            if not src:
                logger.warning(f"There is nothing to stream here, {entry}.")
                continue

            kwargs_copy = self.reader_kwargs.copy()
            kwargs_copy["region"] = getattr(mod, "region", None)

            dtype = entry.get("data_type")
            hook_dtype = kwargs_copy.pop("data_type", None)
            dtype = self.stream_type or hook_dtype or dtype

            # if dtype in ProfileRegistry.get_registry():
            # profile_args = ProfileRegistry.get_yaml(dtype)
            # print(profile_args)
            reader = ReaderRegistry.get_reader(src, dtype, **kwargs_copy)
            # if dtype:
            #    reader = ReaderRegistry.get_reader_for_dtype(dtype)(src, **kwargs_copy)
            # else:
            # reader = ReaderRegistry.get_reader_for_ext(src.split(".")[-1])(
            #     src, **kwargs_copy
            # )

            if not reader:
                logger.warning(f"No reader could be determined for {dtype}: {entry}")
                continue

            raw_stream = reader.yield_chunks()
            mod.region = Region.from_list(mod.region)

            if raw_stream:
                entry["stream"] = raw_stream
                # --- Pass any schemas ---
                # entry["stream"] = ensure_schema(
                #     raw_stream, module_weight=w, module_unc=u
                # )
                # entry["stream_type"] = "xyz_recarray"
                entry["stream_type"] = getattr(reader, "meta_category", "generic-stream")

        return entries
