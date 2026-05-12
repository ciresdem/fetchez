#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
fetchez.modules.base
~~~~~~~~~~~~~~~~~~~~~~

This holds the FetchModule super class

:copyright: (c) 2010-2026 Regents of the University of Colorado
:license: MIT, see LICENSE for more details.
"""

import os
import logging
import urllib.parse
import json
import hashlib
from typing import List, Dict, Any

from fetchez import spatial
from fetchez import utils
from fetchez.core import Fetch

logger = logging.getLogger(__name__)


class FetchModule:
    """Base class for all Fetchez data modules."""

    # --- Registry Metadata (Override these in subclasses) ---
    name = "base_module"
    meta_category = "Generic"
    meta_desc = "Base module class."
    meta_agency = "Unknown"
    meta_tags: List[Any] = []
    meta_aliases: List[Any] = []
    meta_urls: Dict[Any, Any] = {}

    def __init__(
        self,
        src_region=None,
        hook=None,
        outdir=None,
        min_year=None,
        max_year=None,
        weight=1.0,
        uncertainty=0.0,
        params=None,
        use_cache=True,
        **kwargs,
    ):
        self.region = src_region
        self.outdir = outdir
        self.params = params or {}
        self.status = 0
        self.results = []
        self.use_cache = use_cache

        # Store the parameters used to invoke this module for hashing
        self._init_kwargs = kwargs.copy()
        self._init_kwargs.update(
            {
                "region": list(src_region) if src_region else None,
                "min_year": min_year,
                "max_year": max_year,
                "params": self.params,
            }
        )

        if self.outdir is None:
            self._outdir = os.path.join(os.getcwd(), self.name)
        else:
            self._outdir = os.path.join(self.outdir, self.name)

        self.min_year = utils.int_or(min_year)
        self.max_year = utils.int_or(max_year)
        self.weight = utils.float_or(weight, 1.0)
        self.uncertainty = utils.float_or(uncertainty, 0.0)

        # Default Headers (Can be overridden in subclass)
        self.headers = {"User-Agent": "fetchez/0.5.0"}

        self.internal_hooks = []
        self.external_hooks = hook if hook else []

        # Default to the whole world if the region is invalid or missing.
        # Note: This will result in massive downloads for global datasets!
        if self.region is None or not spatial.region_valid_p(self.region):
            self.region = (-180, 180, -90, 90)

        self.silent = logger.getEffectiveLevel() > logging.INFO

        self._original_run = self.run
        self.run = self._cached_run

    @property
    def hooks(self):
        """Combine internal and external hooks in the correct execution order."""

        return self.internal_hooks + self.external_hooks

    def add_hook(self, hook_obj):
        """Add a hook instance at runtime."""

        if hasattr(hook_obj, "run"):
            self.external_hooks.append(hook_obj)
        else:
            logger.warning(
                f"Hook {hook_obj} does not appear to be a valid FetchHook class."
            )

    def run(self):
        """Override this method in a subclass to populate `self.results`."""

        raise NotImplementedError("Subclasses must implement the `run` method.")

    def _generate_cache_key(self):
        """Generates a deterministic SHA-256 hash based on module properties."""

        # BLACKLIST
        ignored_keys = {
            "outdir",
            "hooks",
            "results",
            "status",
            "use_cache",
            "weight",
            "uncertainty",
            "name",
        }

        def _sanitize(val):
            """Recursively strip out un-hashable objects."""

            if isinstance(val, (str, int, float, bool, type(None))):
                return val
            if isinstance(val, (list, tuple)):
                cleaned = [_sanitize(v) for v in val]
                return [v for v in cleaned if v is not None]
            if isinstance(val, dict):
                cleaned = {str(k): _sanitize(v) for k, v in val.items()}
                return {k: v for k, v in cleaned.items() if v is not None}

            return None

        cache_dict = {}
        for key, val in self.__dict__.items():
            if key.startswith("_") or key in ignored_keys:
                continue

            # Handle the region tuple safely
            if key == "region" and val is not None:
                cache_dict[key] = list(val)
                continue

            clean_val = _sanitize(val)

            # Only add to the hash state if the value survived sanitization
            if clean_val is not None:
                # Exclude completely empty lists/dicts to keep the hash clean
                if isinstance(clean_val, (list, dict)) and not clean_val:
                    continue
                cache_dict[key] = clean_val

        # logger.debug(f"\n--- {self.name} CACHE STATE ---")
        # import pprint
        # pprint.pprint(cache_dict)

        state_str = json.dumps(cache_dict, sort_keys=True)
        return hashlib.sha256(state_str.encode("utf-8")).hexdigest()

    # def _generate_cache_key(self):
    #     """Generates a SHA-256 hash based on the module's parameters."""
    #
    #     state_str = json.dumps(self._init_kwargs, sort_keys=True, default=str)
    #     return hashlib.sha256(state_str.encode('utf-8')).hexdigest()

    def _cached_run(self):
        """Intercepts run() to check the cache before querying remote APIs."""

        if not self.use_cache:
            return self._original_run()

        cache_dir = os.path.join(self._outdir, ".fetchez_cache")
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)

        cache_key = self._generate_cache_key()
        cache_file = os.path.join(cache_dir, f"{self.name}_{cache_key}.json")

        if os.path.exists(cache_file):
            try:
                with open(cache_file, "r") as f:
                    self.results = json.load(f)
                logger.debug(
                    f"[{self.name}] Loaded {len(self.results)} results from cache."
                )
                return
            except Exception as e:
                logger.warning(f"[{self.name}] Cache corrupted, ignoring: {e}")

        logger.debug(f"[{self.name}] Querying remote API...")
        self._original_run()

        # if self.results:
        def _json_fallback(obj):
            """Safely serialize custom objects like Region."""

            if hasattr(obj, "__iter__") and not isinstance(obj, (str, bytes)):
                return list(obj)

            return str(obj)

        try:
            with open(cache_file, "w") as f:
                json.dump(self.results, f, indent=2, default=_json_fallback)
            logger.debug(f"[{self.name}] Saved API results to cache.")
        except Exception as e:
            logger.warning(f"[{self.name}] Failed to save cache: {e}")
            if os.path.exists(cache_file):
                try:
                    os.remove(cache_file)
                except Exception:
                    pass

    def fetch_entry(self, entry, check_size=True, retries=5, verbose=True):
        """Standardized method for fetching a single result entry."""

        try:
            parsed_url = urllib.parse.urlparse(entry["url"])
            if parsed_url.scheme == "ftp":
                status = Fetch(url=entry["url"], headers=self.headers).fetch_ftp_file(
                    entry["dst_fn"]
                )
            else:
                status = Fetch(
                    url=entry["url"],
                    headers=self.headers,
                ).fetch_file(
                    entry["dst_fn"],
                    check_size=check_size,
                    tries=retries,
                    verbose=verbose,
                )
        except Exception as e:
            logger.debug(f"Fetch failed for {entry['url']}: {e}")
            status = -1

        return status

    def add_entry_to_results(self, url, dst_fn, data_type, **kwargs):
        """Add fetch entries to `results`.

        At minimum, `url`, `dst_fn` and `data_type` are required.
        Any additional keyword arguments will be added to the entry dictionary.
        """

        if utils.str_or(dst_fn) is not None:
            # Only join with outdir if dst_fn isn't already an absolute path
            if not os.path.isabs(dst_fn):
                dst_fn = os.path.join(self._outdir, dst_fn)

        entry = {"url": url, "dst_fn": dst_fn, "data_type": data_type}
        entry.update(kwargs)
        self.results.append(entry)


# =============================================================================
# Core/Test Modules
# =============================================================================
class HttpDataset(FetchModule):
    """Fetch an HTTP/HTTPS file directly from a URL."""

    name = "url_fetcher"
    meta_category = "Generic"
    meta_desc = "Fetch a file directly from a URL."
    meta_resolution = "N/A"
    meta_license = "N/A"

    def __init__(self, url=None, **kwargs):
        super().__init__(**kwargs)
        self.url = url

    def run(self):
        if self.url:
            self.add_entry_to_results(self.url, os.path.basename(self.url), "https")


class Scratch(FetchModule):
    """Scratch module that populates results directly from arguments."""

    name = "scratch"
    meta_category = "Reference"
    meta_desc = "Testing module that injects direct arguments into the pipeline."
    meta_resolution = "N/A"
    meta_license = "N/A"

    def __init__(self, url=None, path=None, datatype=None, **kwargs):
        super().__init__(**kwargs)
        self.url = url
        self.path = path
        self.datatype = datatype

    def run(self):
        if self.url and self.path and self.datatype:
            self.add_entry_to_results(self.url, self.path, self.datatype)
