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
import json
import pkgutil
import importlib
import importlib.util
import inspect
import logging
from typing import Dict, Any, Type, Optional

from fetchez.modules import FetchModule
from fetchez.hooks import FetchHook
from fetchez.recipes.schemas import BaseSchema
from fetchez.streams import BaseReader

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
        """Scan local directories for user-provided plugins."""

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
    def _get_cache_path(cls):
        """Path to the JSON registry cache."""

        cache_dir = os.path.expanduser("~/.fetchez")
        os.makedirs(cache_dir, exist_ok=True)
        return os.path.join(cache_dir, f"{cls.__name__}_cache.json")

    @classmethod
    def load_fast(cls):
        """Loads from the JSON cache for instant CLI menus.
        If cache is missing, falls back to the slow load_all().
        """

        registry = cls.get_registry()
        if registry:
            return

        cache_path = cls._get_cache_path()
        if os.path.exists(cache_path):
            try:
                with open(cache_path, "r") as f:
                    registry.update(json.load(f))
                return
            except Exception as e:
                logger.debug(f"Cache read failed: {e}")

        cls.load_all()
        cls.save_cache()

    @classmethod
    def save_cache(cls):
        """Dumps the discovered registry to JSON."""

        clean_registry = {}
        for k, meta in cls.get_registry().items():
            clean_meta = {
                key: val
                for key, val in meta.items()
                if isinstance(val, (str, int, float, list, dict))
            }
            clean_registry[k] = clean_meta

        with open(cls._get_cache_path(), "w") as f:
            json.dump(clean_registry, f, indent=2)

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
                meta.setdefault("domain", "Universal (Files)")
                meta.setdefault("requires", "any")

                meta["import_path"] = f"{obj.__module__}.{obj.__name__}"

                registry[mod_key] = meta
                for alias in meta["aliases"]:
                    registry[alias] = meta

    @classmethod
    def get_info(cls, mod_key: str) -> Dict[str, Any]:
        return cls.get_registry().get(mod_key, {})

    @classmethod
    def _get_class(cls, mod_key: str):
        meta = cls.get_registry().get(mod_key)
        return meta.get("_class_obj") if meta else None

    @classmethod
    def get_class(cls, name: str):
        """Returns the class if cached, or lazily imports it on demand."""

        meta = cls.get_registry().get(name)
        if not meta:
            return None

        if "import_path" in meta:
            mod_path, class_name = meta["import_path"].rsplit(".", 1)
            module = importlib.import_module(mod_path)
            actual_cls = getattr(module, class_name)

            return actual_cls

        return None

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
                or any(term in alias.lower() for alias in meta.get("aliases", ""))
            ):
                if key not in results:
                    results.append(key)

        return results


class YamlRegistry:
    """A registry for discovering and loading yaml configuration files (recipes and hook presets)."""

    # These must be defined by the subclasses
    base_class: Optional[Type] = None
    builtin_pkg: str = ""
    entry_point_group: str = ""
    user_folder: str = ""

    @classmethod
    def get_registry(cls) -> Dict[str, Any]:

        if not hasattr(cls, "_registry"):
            setattr(cls, "_registry", {})
        return getattr(cls, "_registry")

    @classmethod
    def load_all(cls):
        cls.get_registry()
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
                logger.warning(f"Failed to load yamls from package {pkg_name}: {e}")

        builtin_module = importlib.import_module(cls.builtin_pkg)
        builtin_path = builtin_module.__path__
        home_dir = os.path.expanduser(f"~/.fetchez/{cls.user_folder}")
        builtin_path.append(home_dir)
        for fdir in builtin_path:
            if os.path.exists(fdir):
                for fn in os.listdir(fdir):
                    if fn.endswith((".yaml", ".yml")):
                        try:
                            with open(
                                os.path.join(fdir, fn), "r", encoding="utf-8"
                            ) as f:
                                cls._register_yaml(f.read(), os.path.join(fdir, fn))
                        except Exception as e:
                            logger.warning(f"Failed to load yaml {fn}: {e}")

    load_fast = load_all

    @classmethod
    def _register_yaml(cls, yaml_content: str, file_path: str):
        import yaml

        registry = cls.get_registry()
        try:
            config = yaml.safe_load(yaml_content)
            if not config:
                return

            if "name" in config:
                registry[config["name"]] = config

        except Exception as e:
            logger.debug(f"Failed to parse YAML {file_path}: {e}")

    @classmethod
    def get_yaml(cls, name: str) -> Optional[Dict[str, Any]]:
        return cls.get_registry().get(name)

    # Temporary for backwards compatibility
    get_preset = get_yaml
    get_recipe = get_yaml


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


# Schemas extend Recipes
class SchemaRegistry(PluginRegistry):
    base_class = BaseSchema
    builtin_pkg = "fetchez.recipes.schemas"
    entry_point_group = "fetchez.recipes.schemas"
    user_folder = "recipes/schemas"

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


class ReaderRegistry(PluginRegistry):
    base_class = BaseReader
    builtin_pkg = "fetchez.streams.readers"
    entry_point_group = "fetchez.streams.readers"
    user_folder = "streams/readers"

    @classmethod
    def get_reader(cls, src, term: str, **kwargs):
        if term:
            profile = ProfileRegistry.get_yaml(term)
            if profile:
                logger.debug(f"Using reader-profile {profile}")
                profile_reader = profile.get("reader", {})
                reader_name = profile_reader.get("name", "")
                reader = cls.get_class(reader_name)
                if reader:
                    profile_args = profile_reader.get("args", {})
                    return reader(src, **profile_args, **kwargs)
            else:
                logger.debug(f"No reader profile found, checking `{term}` data-type")
                reader = cls.get_reader_for_dtype(term)
                if reader:
                    logger.debug(f"Found `{reader.name}` for data-type: `{term}`")
                    return reader(src, **kwargs)

        _ext = src.split(".")[-1]
        logger.debug(f"No reader dtype found, checking `{_ext}` in extensions")
        reader = cls.get_reader_for_ext(_ext)
        if reader:
            return reader(src, **kwargs)

        return None

    @classmethod
    def get_reader_for_ext(cls, ext: str):
        """Iterate through registered readers to find one that supports this extension."""

        for name, meta in cls.get_registry().items():
            if ext.lower() in meta.get("extensions", []):
                return cls.get_class(name)
        return None

    @classmethod
    def get_reader_for_dtype(cls, dtype: str):
        """Iterate through registered readers to find one that supports this dtype."""

        for name, meta in cls.get_registry().items():
            if dtype.lower() in meta.get("dtype", ""):
                return cls.get_class(name)
        return None


class RecipeRegistry(YamlRegistry):
    """A registry for discovering and loading YAML recipes."""

    # _registry = {}
    builtin_pkg = "fetchez.recipes"
    entry_point_group = "fetchez.recipes"
    user_folder = "recipes"

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


# Presets extend Hooks
class PresetRegistry(YamlRegistry):
    builtin_pkg = "fetchez.hooks.presets"
    entry_point_group = "fetchez.hooks.presets"
    user_folder = "hooks/presets"

    @classmethod
    def _register_yaml(cls, yaml_content: str, file_path: str):
        import yaml

        registry = cls.get_registry()

        try:
            config = yaml.safe_load(yaml_content)
            if not config:
                return

            # Legacy ~/.fetchez/presets.py
            if "presets" in config:
                for p_name, p_def in config.get("presets", {}).items():
                    registry[p_name] = p_def
            else:
                if "name" in config and "hooks" in config:
                    registry[config["name"]] = config
        except Exception as e:
            logger.debug(f"Failed to parse preset YAML {file_path}: {e}")

    @classmethod
    def hook_list_from_preset(cls, preset_def):
        """Convert yaml definition to list of Hook Objects."""

        hooks = []
        for h_def in preset_def.get("hooks", []):
            name = h_def.get("name")
            kwargs = h_def.get("args", {})

            hook_cls = HookRegistry.get_class(name)
            if hook_cls:
                try:
                    hooks.append(hook_cls(**kwargs))
                except Exception as exception:
                    logger.error(f"Failed to init preset hook '{name}': {exception}")
            else:
                logger.warning(f"Preset hook '{name}' not found.")

        return hooks


# Bundles extend Modules
class BundleRegistry(YamlRegistry):
    """A registry for discovering and loading Module Bundles (Data Packages)."""

    builtin_pkg = "fetchez.modules.bundles"
    entry_point_group = "fetchez.modules.bundles"
    user_folder = "modules/bundles"

    @classmethod
    def expand_bundle(cls, name):
        bundle_def = cls.get_yaml(name)
        if bundle_def:
            return bundle_def.get("modules")


# Profiles extend Streams
class ProfileRegistry(YamlRegistry):
    """A registry for discovering and loading Format Profilesx."""

    builtin_pkg = "fetchez.streams.profiles"
    entry_point_group = "fetchez.streams.profiles"
    user_folder = "streams/profiles"

    # @classmethod
    # def reader_args_from_profile(cls, profile_def):
    #     """Convert yaml definition to list of Hook Objects."""

    #     readers = {}
    #     profile_id = profile_def.get("profile")
    #     for p_def in profile_def.get("reader", []):
    #         name = p_def.get("name")
    #         kwargs = p_def.get("args", {})
    #         readers[name] = kwargs
    #     return readers


# =============================================================================
# Old YAML Registries (recipe & preset)
# =============================================================================
class _RecipeRegistry:
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


class _PresetRegistry:
    """A registry for discovering and loading hook Presets (Macros)."""

    builtin_pkg = "fetchez.presets"
    entry_point_group = "fetchez.presets"
    user_folder = "presets"

    @classmethod
    def get_registry(cls) -> Dict[str, Any]:

        if not hasattr(cls, "_registry"):
            setattr(cls, "_registry", {})
        return getattr(cls, "_registry")

    @classmethod
    def load_all(cls):
        cls.get_registry()
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
                logger.warning(f"Failed to load presets from package {pkg_name}: {e}")

        builtin_module = importlib.import_module(cls.builtin_pkg)
        builtin_path = builtin_module.__path__
        home_dir = os.path.expanduser(f"~/.fetchez/{cls.user_folder}")
        builtin_path.append(home_dir)
        for fdir in builtin_path:
            if os.path.exists(fdir):
                for fn in os.listdir(fdir):
                    if fn.endswith((".yaml", ".yml")):
                        try:
                            with open(
                                os.path.join(fdir, fn), "r", encoding="utf-8"
                            ) as f:
                                cls._register_yaml(f.read(), os.path.join(fdir, fn))
                        except Exception as e:
                            logger.warning(f"Failed to load preset {fn}: {e}")

        legacy_file = os.path.expanduser("~/.fetchez/presets.yaml")
        if os.path.exists(legacy_file):
            try:
                with open(legacy_file, "r", encoding="utf-8") as f:
                    cls._register_yaml(f.read(), legacy_file, is_legacy=True)
            except Exception:
                pass

    @classmethod
    def _register_yaml(cls, yaml_content: str, file_path: str, is_legacy=False):
        import yaml

        registry = cls.get_registry()

        try:
            config = yaml.safe_load(yaml_content)
            if not config:
                return

            if is_legacy or "presets" in config:
                for p_name, p_def in config.get("presets", {}).items():
                    registry[p_name] = p_def
            else:
                if "name" in config and "hooks" in config:
                    registry[config["name"]] = config
        except Exception as e:
            logger.debug(f"Failed to parse preset YAML {file_path}: {e}")

    @classmethod
    def get_preset(cls, name: str) -> Optional[Dict[str, Any]]:
        return cls.get_registry().get(name)

    @classmethod
    def hook_list_from_preset(cls, preset_def):
        """Convert yaml definition to list of Hook Objects."""

        hooks = []
        for h_def in preset_def.get("hooks", []):
            name = h_def.get("name")
            kwargs = h_def.get("args", {})

            hook_cls = HookRegistry.get_class(name)
            if hook_cls:
                try:
                    hooks.append(hook_cls(**kwargs))
                except Exception as exception:
                    logger.error(f"Failed to init preset hook '{name}': {exception}")
            else:
                logger.warning(f"Preset hook '{name}' not found.")

        return hooks
