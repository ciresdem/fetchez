#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
fetchez.hooks.registry
~~~~~~~~~~~~~~~~~~~~~~

This holds the hook registry.

:copyright: (c) 2010-2026 Regents of the University of Colorado
:license: MIT, see LICENSE for more details.
"""

import pkgutil
import importlib
import os
import logging
import fetchez.hooks.builtins
from typing import Dict, Any
from . import FetchHook

logger = logging.getLogger(__name__)


class HookRegistry:
    """Fetchez Hook Registry using dynamic discovery."""

    _hooks: Dict[str, Any] = {}

    @classmethod
    def load_builtins(cls):
        """Recursively scan and load all built-in hooks using pkgutil."""

        for _, modname, ispkg in pkgutil.walk_packages(
            path=fetchez.hooks.builtins.__path__,
            prefix=fetchez.hooks.builtins.__name__ + ".",
        ):
            if not ispkg:
                try:
                    mod = importlib.import_module(modname)
                    cls._register_from_module(mod)
                except Exception as e:
                    logger.warning(f"Failed to load built-in hook {modname}: {e}")

    @classmethod
    def load_user_plugins(cls):
        """Securely scan local directories for user-provided Python hook scripts."""

        import importlib.util

        home = os.path.expanduser("~")

        search_dirs = [
            os.path.join(home, ".fetchez", "plugins"),
            os.path.join(home, ".fetchez", "hooks"),
            os.path.join(os.getcwd(), ".fetchez", "plugins"),
            os.path.join(os.getcwd(), ".fetchez", "hooks"),
        ]

        for p_dir in search_dirs:
            if not os.path.exists(p_dir):
                continue

            for f in os.listdir(p_dir):
                if f.endswith(".py") and not f.startswith("_"):
                    filepath = os.path.join(p_dir, f)
                    mod_name = f"fetchez_user_hook_{f[:-3]}"

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
                            f"Failed to securely load user hook {filepath}: {e}"
                        )

    @classmethod
    def load_installed_plugins(cls):
        """Load external pip-installed Fetchez plugins via entry_points."""

        from importlib.metadata import entry_points

        eps = entry_points(group="fetchez.hooks")
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
                        logger.warning(f"Failed to load built-in hook {modname}: {e}")

    @classmethod
    def load_all_hooks(cls):
        """Load all the hooks. [ builtins, plugins, extensions ]"""

        cls.load_builtins()
        cls.load_user_plugins()
        cls.load_installed_plugins()

    @classmethod
    def register_hook(cls, hook_cls):
        """Register a hook class.

        The hook must have a 'name' attribute (e.g. name='unzip').
        """

        import inspect

        if not hasattr(hook_cls, "name"):
            logger.warning(
                f"Cannot register hook {hook_cls}: Missing 'name' attribute."
            )
            return

        key = hook_cls.name
        if (
            inspect.isclass(hook_cls)
            and issubclass(hook_cls, FetchHook)
            and hook_cls is not FetchHook
        ):
            cls._hooks[key] = hook_cls
            logger.debug(f"Registered external hook: {key}")

    @classmethod
    def _register_from_module(cls, module):
        """Inspect a module for classes inheriting from FetchHook."""

        import inspect

        for name, obj in inspect.getmembers(module):
            if (
                inspect.isclass(obj)
                and issubclass(obj, FetchHook)
                and obj is not FetchHook
            ):
                key = getattr(obj, "name", name.lower())
                cls._hooks[key] = obj
                logger.debug(f"Registered hook from module: {key}")

    @classmethod
    def get_hook(cls, name):
        """Retrieve a hook class by name."""

        return cls._hooks.get(name)

    @classmethod
    def list_hooks(cls):
        """Return a dict of all registered hooks."""

        return cls._hooks
