#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
fetchez.modules.registry
~~~~~~~~~~~~~~~~~~~~~~~~

This holds the dynamic module registry for Fetchez.
"""

import os
import pkgutil
import importlib
import importlib.util
import inspect
import logging
from typing import Dict, Any

import fetchez.modules.builtins
from fetchez.core import FetchModule

logger = logging.getLogger(__name__)


class FetchezRegistry:
    """Fetchez Module Registry using dynamic discovery."""

    _modules: Dict[str, Any] = {}

    @classmethod
    def load_builtins(cls):
        """Recursively scan and load all built-in modules using pkgutil."""

        if cls._modules:
            return

        for _, modname, ispkg in pkgutil.walk_packages(
            path=fetchez.modules.builtins.__path__,
            prefix=fetchez.modules.builtins.__name__ + ".",
        ):
            if not ispkg:
                try:
                    mod = importlib.import_module(modname)
                    cls._register_from_module(mod)
                except Exception as e:
                    logger.warning(f"Failed to load built-in module {modname}: {e}")

    @classmethod
    def load_user_plugins(cls):
        """Securely scan local directories for user-provided Python plugins."""

        home = os.path.expanduser("~")

        search_dirs = [
            os.path.join(home, ".fetchez", "plugins"),
            os.path.join(home, ".fetchez", "modules"),
            os.path.join(os.getcwd(), ".fetchez", "plugins"),
            os.path.join(os.getcwd(), ".fetchez", "modules"),
        ]

        for p_dir in search_dirs:
            if not os.path.exists(p_dir):
                continue

            for f in os.listdir(p_dir):
                if f.endswith(".py") and not f.startswith("_"):
                    filepath = os.path.join(p_dir, f)
                    mod_name = f"fetchez_user_plugin_{f[:-3]}"

                    try:
                        spec = importlib.util.spec_from_file_location(
                            mod_name, filepath
                        )
                        if spec and spec.loader:
                            mod = importlib.util.module_from_spec(spec)
                            spec.loader.exec_module(mod)
                            cls._register_from_module(mod)
                    except Exception as e:
                        logger.warning(
                            f"Failed to securely load user plugin {filepath}: {e}"
                        )

    @classmethod
    def load_installed_plugins(cls):
        """Load external pip-installed Fetchez modules (e.g., globato, transformez) via entry_points."""

        from importlib.metadata import entry_points

        eps = entry_points(group="fetchez.modules")
        for ep in eps:
            plugin_module = ep.load()
            for _, modname, ispkg in pkgutil.walk_packages(
                path=plugin_module.__path__,
                prefix=plugin_module.__name__ + ".",
            ):
                if not ispkg:
                    try:
                        mod = importlib.import_module(modname)
                        cls._register_from_module(mod)
                    except Exception as e:
                        logger.warning(f"Failed to load built-in module {modname}: {e}")

    @classmethod
    def load_all_modules(cls):
        """Load all the modules. [ builtins, plugins, extensions ]"""

        cls.load_builtins()
        cls.load_user_plugins()
        cls.load_installed_plugins()

    @classmethod
    def _register_from_module(cls, module):
        """Inspect a Python module for classes inheriting from FetchModule."""

        for name, obj in inspect.getmembers(module, inspect.isclass):
            if issubclass(obj, FetchModule) and obj is not FetchModule:
                mod_key = getattr(obj, "name", name.lower())
                meta = {
                    "mod": module.__name__,
                    "cls": name,
                    "_class_obj": obj,
                    "category": getattr(obj, "meta_category", "Generic"),
                    "desc": getattr(obj, "meta_desc", "No description provided."),
                    "agency": getattr(obj, "meta_agency", "Unknown"),
                    "tags": getattr(obj, "meta_tags", []),
                    "region": getattr(
                        obj, "meta_coverage", getattr(obj, "meta_region", "Unknown")
                    ),
                    "resolution": getattr(obj, "meta_resolution", "Unknown"),
                    "license": getattr(obj, "meta_license", "Unknown"),
                    "urls": getattr(obj, "meta_urls", {}),
                    "aliases": obj.__dict__.get("meta_aliases", []),
                }
                cls._modules[mod_key] = meta
                for alias in meta["aliases"]:
                    cls._modules[alias] = meta

    @classmethod
    def get_info(cls, mod_key: str) -> Dict[str, Any]:
        """Retrieve the metadata dictionary for a specific module."""

        return cls._modules.get(mod_key, {})

    @classmethod
    def load_module(cls, mod_key: str):
        """Retrieve the actual class object for a specific module."""

        meta = cls._modules.get(mod_key)
        if meta:
            return meta.get("_class_obj")
        return None

    @classmethod
    def search_modules(cls, term: str):
        """Search modules by name, description, agency, or tags."""

        term = term.lower()
        results = []

        for key, meta in cls._modules.items():
            if (
                term in key.lower()
                or term in meta.get("desc", "").lower()
                or term in meta.get("agency", "").lower()
                or any(term in tag.lower() for tag in meta.get("tags", []))
            ):
                if key not in results:
                    results.append(key)

        return results
