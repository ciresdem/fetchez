#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
fetchez.api
~~~~~~~~~~~
High-level Python Interface for Fetchez.

Usage:
    import fetchez

    # Search
    fetchez.search("bathymetry")

    # Get Data (Returns list of local file paths)
    files = fetchez.get("nos_hydro", region=[-120, -118, 33, 34], year=2020)

    # Advanced (With Hooks)
    files = fetchez.get("charts", region=[-120, -118, 33, 34], hooks=['unzip', 'filename_filter:match=.000'])
"""

import os
import logging
from typing import List, Optional, Dict, Any

from .utils import parse_hook_string
from .core import run_fetchez
from .spatial import parse_region
from .registry import ModuleRegistry, HookRegistry

logger = logging.getLogger(__name__)


def search(term: Optional[str] = None) -> Dict[Any, Any]:
    """Search available modules by tag, description, or name."""

    ModuleRegistry.load_all()

    if not term:
        return ModuleRegistry.get_registry()

    results = ModuleRegistry.search_modules(term)
    if not results:
        return {}

    found_results = {}
    for mod_key in results:
        meta = ModuleRegistry.get_info(mod_key)
        found_results.update({mod_key: meta})
    return found_results


def get(
    module: str,
    region: Optional[List[float] | str] = None,
    outdir: Optional[str] = None,
    threads: int = 4,
    hooks: Optional[List[str]] = None,
    **kwargs,
) -> List[str]:
    """Fetch data from a module in one line.

    Args:
        module: Module name (e.g., 'nos_hydro', 'tnm').
        region: [W, E, S, N] or 'loc:Boulder'.
        outdir: Where to save files (default: ./<module>).
        threads: Parallel download threads.
        hooks: List of hook strings (e.g. ['unzip', 'audit']).
        **kwargs: Arguments passed directly to the module (year=..., datatype=...).

    Returns:
        A list of absolute paths to the downloaded files.
    """

    ModuleRegistry.load_all()
    HookRegistry.load_all()

    ModCls = ModuleRegistry.get_class(module)
    if not ModCls:
        raise ValueError(f"Unknown module: {module}")

    src_region = parse_region(region)[0] if region else None

    active_hooks = []
    if hooks:
        for h_str in hooks:
            name, h_kwargs = parse_hook_string(h_str)
            HookCls = HookRegistry.get_class(name)
            if HookCls:
                active_hooks.append(HookCls(**h_kwargs))
            else:
                logger.warning(f"Hook '{name}' not found. Skipping.")

    try:
        mod_instance = ModCls(
            src_region=src_region, hook=active_hooks, outdir=outdir, **kwargs
        )
    except Exception as e:
        logger.error(f"Failed to initialize {module}: {e}")
        return []

    logger.info(f"Querying {module}...")
    try:
        mod_instance.run()
    except Exception as e:
        logger.error(f"Query failed: {e}")
        return []

    if not mod_instance.results:
        logger.warning(f"No results found for {module} with given parameters.")
        return []

    run_fetchez([mod_instance], threads=threads)

    downloaded_files = []
    for entry in mod_instance.results:
        if entry.get("status") == 0:
            fn = entry.get("dst_fn")
            if fn and os.path.exists(fn):
                downloaded_files.append(os.path.abspath(fn))

    return downloaded_files
