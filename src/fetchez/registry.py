#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
fetchez.registry
~~~~~~~~~~~~~~~~

A unified, dynamic registry system for discovering and loading
Fetchez Modules, Hooks, Schemas, and other plugins.

:copyright: (c) 2010-2026 Regents of the University of Colorado
:license: MIT, see LICENSE for more details.
"""

import os
import pkgutil
import importlib
import importlib.util
import inspect
import logging
from typing import Dict, Any, Type, Optional

from fetchez.modules import FetchModule
from fetchez.hooks import FetchHook
from fetchez.schema import BaseSchema

logger = logging.getLogger(__name__)


class PluginRegistry:
    """Base class for dynamically discovering and registering plugins."""

    # These must be defined by the subclasses
    base_class: Optional[Type] = None
    builtin_pkg: str = ""
    entry_point_group: str = ""
    user_folder: str = ""

    @classmethod
    def get_registry(cls) -> Dict[str, Any]:
        """Initialization of the class-level registry dictionary."""

        if not hasattr(cls, "_registry"):
            setattr(cls, "_registry", {})

        return getattr(cls, "_registry")

    @classmethod
    def load_builtins(cls):
        """Recursively scan and load all built-in plugins."""

        registry = cls.get_registry()
        if registry:
            return

        try:
            builtin_module = importlib.import_module(cls.builtin_pkg)

            for _, modname, ispkg in pkgutil.walk_packages(
                path=builtin_module.__path__,
                prefix=builtin_module.__name__ + ".",
            ):
                if not ispkg:
                    try:
                        mod = importlib.import_module(modname)
                        cls._register_from_module(mod)
                    except Exception as e:
                        logger.warning(f"Failed to load built-in {modname}: {e}")
        except ImportError:
            logger.warning(f"Built-in package {cls.builtin_pkg} not found.")

    @classmethod
    def load_user_plugins(cls):
        """Securely scan local directories for user-provided plugins."""

        home = os.path.expanduser("~")

        search_dirs = [
            os.path.join(home, ".fetchez", cls.user_folder),
            os.path.join(os.getcwd(), ".fetchez", cls.user_folder),
        ]

        for p_dir in search_dirs:
            if not os.path.exists(p_dir):
                continue

            for f in os.listdir(p_dir):
                if f.endswith(".py") and not f.startswith("_"):
                    filepath = os.path.join(p_dir, f)
                    mod_name = f"fetchez_user_{cls.user_folder}_{f[:-3]}"

                    try:
                        spec = importlib.util.spec_from_file_location(
                            mod_name, filepath
                        )
                        if spec and spec.loader:
                            mod = importlib.util.module_from_spec(spec)
                            spec.loader.exec_module(mod)
                            cls._register_from_module(mod)
                    except Exception as e:
                        logger.warning(f"Failed to load user plugin {filepath}: {e}")

    @classmethod
    def load_installed_plugins(cls):
        """Load external pip-installed extensions via entry_points."""

        from importlib.metadata import entry_points

        try:
            eps = entry_points(group=cls.entry_point_group)
            for ep in eps:
                plugin_module = ep.load()
                # Scan the loaded extension for submodules
                for _, modname, ispkg in pkgutil.walk_packages(
                    path=plugin_module.__path__,
                    prefix=plugin_module.__name__ + ".",
                ):
                    if not ispkg:
                        try:
                            mod = importlib.import_module(modname)
                            cls._register_from_module(mod)
                        except Exception as e:
                            logger.warning(
                                f"Failed to load external plugin {modname}: {e}"
                            )
        except Exception as e:
            logger.error(
                f"Error checking entry points for {cls.entry_point_group}: {e}"
            )

    @classmethod
    def load_all(cls):
        """Load all plugins: builtins, user plugins, and pip extensions."""

        cls.load_builtins()
        cls.load_user_plugins()
        cls.load_installed_plugins()

    @classmethod
    def _register_from_module(cls, module):
        """Inspect a module and dynamically extract its metadata."""

        registry = cls.get_registry()

        for name, obj in inspect.getmembers(module, inspect.isclass):
            if issubclass(obj, cls.base_class) and obj is not cls.base_class:
                mod_key = getattr(obj, "name", name.lower())

                meta = {
                    "mod": module.__name__,
                    "cls": name,
                    "_class_obj": obj,
                    "aliases": obj.__dict__.get("meta_aliases", []),
                }

                # METADATA EXTRACTION
                # Modules must define `meta_` atrributes
                for attr_name in dir(obj):
                    if attr_name.startswith("meta_"):
                        clean_key = attr_name.replace("meta_", "")
                        meta[clean_key] = getattr(obj, attr_name)

                # Fallbacks for the CLI
                meta.setdefault("category", "Generic")
                meta.setdefault("desc", "No description provided.")

                registry[mod_key] = meta
                for alias in meta["aliases"]:
                    registry[alias] = meta

    @classmethod
    def get_info(cls, mod_key: str) -> Dict[str, Any]:
        return cls.get_registry().get(mod_key, {})

    @classmethod
    def get_class(cls, mod_key: str):
        meta = cls.get_registry().get(mod_key)
        return meta.get("_class_obj") if meta else None

    load_module = get_class  # alias for backward compatability

    @classmethod
    def list_all(cls) -> Dict[str, Any]:
        return cls.get_registry()

    @classmethod
    def search_modules(cls, term: str):
        """Search modules by name, description, agency, or tags."""

        term = term.lower()
        results = []

        for key, meta in cls.get_registry().items():
            if (
                term in key.lower()
                or term in meta.get("desc", "").lower()
                or term in meta.get("agency", "").lower()
                or any(term in tag.lower() for tag in meta.get("tags", []))
            ):
                if key not in results:
                    results.append(key)

        return results


# =============================================================================
# The Registries
# =============================================================================
class ModuleRegistry(PluginRegistry):
    base_class = FetchModule
    builtin_pkg = "fetchez.modules"
    entry_point_group = "fetchez.modules"
    user_folder = "modules"


class HookRegistry(PluginRegistry):
    base_class = FetchHook
    builtin_pkg = "fetchez.hooks"
    entry_point_group = "fetchez.hooks"
    user_folder = "hooks"


class SchemaRegistry(PluginRegistry):
    base_class = BaseSchema
    builtin_pkg = "fetchez.schemas"
    entry_point_group = "fetchez.schemas"
    user_folder = "schemas"
