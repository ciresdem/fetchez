#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
fetchez.api
~~~~~~~~~~~
High-level Python Interface for Fetchez.

Usage::

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
from .registry import (
    ModuleRegistry,
    HookRegistry,
    RecipeRegistry,
    SchemaRegistry,
    PresetRegistry,
    ProfileRegistry,
)

logger = logging.getLogger(__name__)


def _search_registry(registry_cls, term: Optional[str] = None) -> Dict[str, Any]:
    """Helper to load and search a specific registry."""

    registry_cls.load_all()
    full_reg = registry_cls.get_registry()

    if not term:
        return full_reg

    found = {}
    term_lower = term.lower()
    for name, meta in full_reg.items():
        desc = meta.get("desc", meta.get("desc", ""))
        tags = [t.lower() for t in meta.get("tags", [])]
        aliases = [a.lower() for a in meta.get("aliases", [])]
        category = meta.get("category", meta.get("category", ""))

        if (
            term_lower in name.lower()
            or term_lower in desc.lower()
            or term_lower in tags
            or term_lower in aliases
            or term_lower in category.lower()
        ):
            found[name] = meta

    return found


def list_modules() -> Dict[str, Any]:
    return _search_registry(ModuleRegistry)


def search_modules(term) -> Dict[str, Any]:
    return _search_registry(ModuleRegistry, term)


def list_hooks() -> Dict[str, Any]:
    return _search_registry(HookRegistry)


def search_hooks(term) -> Dict[str, Any]:
    return _search_registry(HookRegistry, term)


def list_recipes() -> Dict[str, Any]:
    return _search_registry(RecipeRegistry)


def list_schemas() -> Dict[str, Any]:
    return _search_registry(SchemaRegistry)


def list_presets() -> Dict[str, Any]:
    return _search_registry(PresetRegistry)


def list_profiles() -> Dict[str, Any]:
    return _search_registry(ProfileRegistry)


def search_profiles(term) -> Dict[str, Any]:
    return _search_registry(ProfileRegistry, term)


def search(term: str) -> Dict[str, Dict[str, Any]]:
    """Search across ALL Fetchez registries simultaneously."""
    return {
        "modules": _search_registry(ModuleRegistry, term),
        "hooks": _search_registry(HookRegistry, term),
        "recipes": _search_registry(RecipeRegistry, term),
        "schemas": _search_registry(SchemaRegistry, term),
        "presets": _search_registry(PresetRegistry, term),
        "profiles": _search_registry(ProfileRegistry, term),
    }


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
            hook_config = parse_hook_string(h_str)
            HookCls = HookRegistry.get_class(hook_config.get("name"))
            if HookCls:
                active_hooks.append(HookCls(**hook_config.get("args", {})))
            else:
                logger.warning(f"Hook {hook_config.get('name')} not found. Skipping.")

    try:
        mod_instance = ModCls(
            src_region=src_region, hook=active_hooks, outdir=outdir, **kwargs
        )
    except Exception as e:
        logger.error(f"Failed to initialize {module}: {e}")
        return []

    logger.debug(f"Querying {module}...")
    try:
        mod_instance.run()
    except Exception as e:
        logger.error(f"Query failed: {e}")
        return []

    if not mod_instance.results:
        logger.debug(f"No results found for {module} with given parameters.")
        return []

    # Grab the final results from the fetchez pipeline
    final_results = run_fetchez([mod_instance], threads=threads)
    downloaded_files = []
    for mod, entry in final_results:  # mod_instance.results:
        if entry.get("status") == 0:
            fn = entry.get("dst_fn")
            if fn and os.path.exists(fn):
                downloaded_files.append(os.path.abspath(fn))

    return downloaded_files


def run_recipe(target: str, region: Optional[str] = None) -> bool:
    """Execute a YAML recipe.

    'target' can be a local file path or the name of a registered recipe.
    """

    import yaml
    from .recipe import Recipe

    RecipeRegistry.load_all()
    base_config = None

    if os.path.exists(target):
        with open(target, "r", encoding="utf-8") as f:
            base_config = yaml.safe_load(f)
    else:
        recipe_meta = RecipeRegistry.get_recipe(target)
        if recipe_meta:
            base_config = recipe_meta["config"]
            logger.info(f"Loaded registered recipe: {target}")

    if not base_config:
        logger.error(f"Recipe '{target}' not found locally or in the registry.")
        return False

    if region:
        base_config["region"] = region

    try:
        Recipe.from_file(base_config).run()
        return True
    except Exception as e:
        logger.error(f"Failed to run recipe '{target}': {e}")
        return False
