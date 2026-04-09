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
import sys
import pkgutil
import importlib
import importlib.util
import inspect
import logging
from typing import Dict, Any, Type, Optional

from fetchez.modules import FetchModule
from fetchez.hooks import FetchHook
from fetchez.schemas import BaseSchema

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
                            sys.modules[mod_name] = mod
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

    @classmethod
    def apply_schema(cls, config):
        """Looks for a schema in the config and applies its rules."""

        schema_name = config.get("schema")
        if schema_name:
            schema_name = schema_name.lower()
            if schema_name in cls.get_registry():
                logger.info(f"Applying '{schema_name}' schema rules to recipe...")
                SchemaCls = cls.get_class(schema_name)
                return SchemaCls.apply(config)
            else:
                logger.warning(
                    f"Schema '{schema_name}' requested but not registered. Ignoring."
                )

        return config


class RecipeRegistry:
    """A registry for discovering and loading YAML recipes."""

    # _registry = {}
    entry_point_group = "fetchez.recipes"
    user_folder = "recipes"

    @classmethod
    def get_registry(cls) -> Dict[str, Any]:
        """Initialization of the class-level registry dictionary."""

        if not hasattr(cls, "_registry"):
            setattr(cls, "_registry", {})

        return getattr(cls, "_registry")

    # @classmethod
    # def get_registry(cls) -> Dict[str, Any]:
    #     return cls._registry

    @classmethod
    def load_all(cls):

        cls.get_registry()
        # if cls._registry:
        #     return

        import importlib.metadata
        import importlib.resources

        try:
            eps = importlib.metadata.entry_points(group=cls.entry_point_group)
        except TypeError:
            eps = importlib.metadata.entry_points().get(cls.entry_point_group, [])

        for ep in eps:
            pkg_name = ep.value
            try:
                for file_path in importlib.resources.files(pkg_name).iterdir():
                    if file_path.name.endswith((".yaml", ".yml")):
                        cls._register_yaml(
                            file_path.read_text(encoding="utf-8"), str(file_path)
                        )
            except Exception as e:
                logger.warning(f"Failed to load recipes from package {pkg_name}: {e}")

        home_dir = os.path.expanduser(f"~/.fetchez/{cls.user_folder}")
        if os.path.exists(home_dir):
            for fn in os.listdir(home_dir):
                if fn.endswith((".yaml", ".yml")):
                    try:
                        with open(
                            os.path.join(home_dir, fn), "r", encoding="utf-8"
                        ) as f:
                            cls._register_yaml(f.read(), os.path.join(home_dir, fn))
                    except Exception as e:
                        logger.warning(f"Failed to load local recipe {fn}: {e}")

    @classmethod
    def _register_yaml(cls, yaml_content: str, file_path: str):
        import yaml

        registry = cls.get_registry()

        try:
            config = yaml.safe_load(yaml_content)
            if not config or "project" not in config:
                return

            # Use the project name from the YAML, fallback to the filename
            name = config["project"].get(
                "name", os.path.basename(file_path).replace(".yaml", "")
            )
            desc = config["project"].get("description", "No description available.")

            registry[name] = {
                "name": name,
                "desc": desc,
                "config": config,
                "path": file_path,
            }
        except Exception as e:
            logger.debug(f"Failed to parse recipe YAML {file_path}: {e}")

    @classmethod
    def get_recipe(cls, name: str) -> Optional[Dict[str, Any]]:
        registry = cls.get_registry()
        return registry.get(name)
