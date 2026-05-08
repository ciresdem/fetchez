#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
fetchez.recipe
~~~~~~~~~~~~~~
The Workflow Engine.
Loads a configuration (The Recipe) and executes it against the target region.

:copyright: (c) 2010-2026 Regents of the University of Colorado
:license: MIT, see LICENSE for more details.
"""

import os
import json
import logging

from .core import run_fetchez
from .spatial import parse_region
from .registry import (
    ModuleRegistry,
    HookRegistry,
    SchemaRegistry,
    PresetRegistry,
    BundleRegistry,
)
from .utils import TqdmLoggingHandler
from . import __version__ as fetchez_version

logger = logging.getLogger(__name__)


# This is duplicated in fetchez.cli
# We should move this to utils
def setup_logging(verbose=False):
    log_level = logging.INFO if verbose else logging.WARNING

    logger = logging.getLogger()
    logger.setLevel(log_level)

    if logger.hasHandlers():
        logger.handlers.clear()

    handler = TqdmLoggingHandler()
    formatter = logging.Formatter("[ %(levelname)s ] %(module)s: %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)


def _parse_version(v_str):
    """Dependency-free semantic version parser.
    Converts '2.1.0-beta' into (2, 1, 0).
    """

    parts = []
    for p in v_str.split("."):
        num = "".join(filter(str.isdigit, p))
        parts.append(int(num) if num else 0)
    return tuple(parts)


class Recipe:
    """The Workflow Orchestrator.

    Reads data ingestion and processing recipes from YAML/JSON files
    and executes them.

    Usage:
        # Load the Recipe
        recipe = Recipe.from_file("socal_project.yaml")

        # Run it.
        recipe.run()
    """

    def __init__(self, config, base_dir=None):
        self.config = config
        self.base_dir = base_dir or os.getcwd()
        self.name = self.config.get("project", {}).get("name", "Unnamed_Recipe")
        setup_logging(True)

    @classmethod
    def from_file(cls, config_source):
        """Factory method to load the Recipe.
        Accepts a filename (str) or a dictionary directly.
        """

        if isinstance(config_source, dict):
            return cls(config_source)

        if not os.path.exists(config_source):
            raise FileNotFoundError(f"Recipe not found: {config_source}")

        base_dir = os.path.dirname(os.path.abspath(config_source))
        ext = os.path.splitext(config_source)[1].lower()

        with open(config_source, "r") as f:
            if ext in [".yaml", ".yml"]:
                import yaml

                config = yaml.safe_load(f)
            else:
                config = json.load(f)

        return cls(config, base_dir=base_dir)

    from_dict = from_file

    def _check_integrity(self):
        """Ensures the fetchez version meets the recipe's minimum requirements."""

        conf = self.config.get("config", {})
        min_fz = conf.get("min_fetchez_version")

        if min_fz:
            current = _parse_version(fetchez_version)
            required = _parse_version(min_fz)
            if current < required:
                logger.error(
                    f"Recipe requires fetchez v{min_fz}, but found v{fetchez_version}"
                )
                raise RuntimeError("Fetchez version incompatibility.")

    def _resolve_path(self, path):
        """Resolves output paths relative to the recipe file."""

        if not isinstance(path, str):
            return path
        if path.startswith(("http", "s3://", "gs://", "ftp://")):
            return path
        if os.path.isabs(path):
            return path
        return os.path.abspath(os.path.join(self.base_dir, path))

    def _init_hooks(self, hook_defs, mod=None):
        if not hook_defs:
            return []

        HookRegistry.load_all()
        PresetRegistry.load_all()

        active_hooks = []
        for h in hook_defs:
            name = h.get("name")
            is_preset = h.get("preset")
            raw_kwargs = h.get("args", {})

            kwargs = {}
            for k, v in raw_kwargs.items():
                if k in [
                    "file",
                    "output",
                    "output_grid",
                    "mask_fn",
                    "dem",
                    "barrier",
                    "aux_path",
                    "path",
                ]:
                    kwargs[k] = self._resolve_path(v)
                else:
                    kwargs[k] = v

            # --- PRESET EXPANSION ---
            if is_preset:
                preset_def = PresetRegistry.get_yaml(is_preset)

                if preset_def:
                    import copy

                    preset_hooks = copy.deepcopy(preset_def.get("hooks", []))

                    # --- ARGUMENT INJECTION ---
                    for inner_hook in preset_hooks:
                        h_name = inner_hook.get("name")

                        # If the user passed a dictionary of args specifically for this hook
                        if h_name in kwargs and isinstance(kwargs[h_name], dict):
                            inner_hook.setdefault("args", {}).update(kwargs[h_name])

                    # Recursively parse the expanded hooks
                    expanded_hooks = self._init_hooks(preset_hooks, mod=mod)
                    active_hooks.extend(expanded_hooks)
                else:
                    logger.error(f"Preset '{is_preset}' not found in registry.")

            # --- STANDARD HOOK INITIALIZATION ---
            else:
                HookCls = HookRegistry.get_class(name)
                if HookCls:
                    import inspect

                    sig = inspect.signature(HookCls.__init__)
                    valid_kwargs = {
                        k: v
                        for k, v in kwargs.items()
                        if k in sig.parameters or "kwargs" in str(sig.parameters)
                    }

                    active_hooks.append(HookCls(**valid_kwargs))
                else:
                    logger.warning(f"Hook '{name}' missing.")

        return active_hooks

    def run(self):
        """Execute the recipe!"""

        ModuleRegistry.load_all()
        BundleRegistry.load_all()
        SchemaRegistry.load_all()

        if not self.config:
            return

        self.config = SchemaRegistry.apply_schema(self.config)

        self._check_integrity()
        logger.debug(f"Preparing to execute recipe: {self.name}")

        run_opts = self.config.get("execution", {})
        threads = run_opts.get("threads", 1)

        global_hooks = self._init_hooks(self.config.get("global_hooks", []))
        global_region_def = self.config.get("region")
        global_regions = (
            parse_region(global_region_def) if global_region_def else [None]
        )

        expanded_modules = []

        for mod_dict in self.config.get("modules", []):
            if "bundle" in mod_dict:
                bundle_name = mod_dict["bundle"]
                user_args = mod_dict.get("args", {})
                user_hooks = mod_dict.get("hooks", [])

                # Fetch the curated package from the registry
                bundle_def = BundleRegistry.get_yaml(bundle_name)

                if not bundle_def:
                    logger.error(f"Bundle '{bundle_name}' not found!")
                    continue

                weight_multiplier = float(user_args.get("weight", 1.0))

                # Inject the bundle's modules into the main recipe
                for pkg_mod in bundle_def.get("modules", []):
                    if "weight" in pkg_mod.setdefault("args", {}):
                        original_weight = float(pkg_mod["args"]["weight"])
                        pkg_mod["args"]["weight"] = original_weight * weight_multiplier

                    if user_hooks:
                        pkg_mod.setdefault("hooks", []).extend(user_hooks)

                    expanded_modules.append(pkg_mod)
            else:
                expanded_modules.append(mod_dict)

        self.config["modules"] = expanded_modules

        modules_to_run = []
        for mod_def in self.config.get("modules", []):
            if isinstance(mod_def, str):
                mod_key, mod_args, mod_hooks, mod_region_def = mod_def, {}, [], None
            else:
                mod_key = mod_def.get("module")
                mod_args = mod_def.get("args", {})
                mod_hooks = self._init_hooks(mod_def.get("hooks", []), mod=mod_key)
                mod_region_def = mod_def.get("region")

            mod_regions = (
                parse_region(mod_region_def) if mod_region_def else global_regions
            )

            # Maybe we don't need to enforce this here...
            # if not mod_regions or mod_regions == [None]:
            #     logger.warning(f"Module '{mod_key}' has no target region. Skipping.")
            #     continue

            ModCls = ModuleRegistry.get_class(mod_key)
            if not ModCls:
                logger.error(f"Unknown module: {mod_key}")
                continue

            for region in mod_regions:
                if "path" in mod_args:
                    mod_args["path"] = self._resolve_path(mod_args["path"])

                try:
                    instance = ModCls(src_region=region, hook=mod_hooks, **mod_args)
                    modules_to_run.append(instance)
                except Exception as e:
                    logger.error(f"Failed to load {mod_key}: {e}")

        if not modules_to_run:
            logger.warning("Recipe empty. Nothing to execute.")
            return

        logger.debug(f"Queued {len(modules_to_run)} module queries. Searching...")
        for mod in modules_to_run:
            try:
                mod.run()
            except Exception as e:
                logger.error(
                    f"Module '{mod.name}' failed to generate URLs (Skipping): {e}"
                )

        run_fetchez(modules_to_run, threads=threads, global_hooks=global_hooks)
        logger.debug(f"Recipe complete: {self.name}")

        # self._generate_receipt()

    def _generate_receipt(self):
        import datetime

        name = self.name
        desc = self.config.get("project", {}).get(
            "description", "No description provided."
        )
        region = self.config.get("region", "Global")

        receipt_filename = f"{name.lower().replace(' ', '_')}_receipt.md"
        receipt_path = os.path.join(self.base_dir, receipt_filename)

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Handle the case where region is None (which we just enabled!)
        region_str = (
            f"`{region}`"
            if region and str(region) != "None"
            else "`Global / Not Specified`"
        )

        # Parse Modules for the receipt
        modules_info = []
        mod_counts = {}
        for mod in self.config.get("modules", []):
            m_name = mod.get("module", "Unknown")
            args = mod.get("args", {})
            weight = args.get("weight", 1.0)
            datatype = args.get("datatype", "default")
            modules_info.append(
                f"- **{m_name}** (Weight: {weight}, Datatype: {datatype})"
            )
            mod_counts[m_name] = mod_counts.get(m_name, 0) + 1

        # Parse Global Hooks for the receipt
        hooks_info = []
        expected_outputs = []
        for hook in self.config.get("global_hooks", []):
            h_name = hook.get("name", "Unknown")
            hooks_info.append(f"1. `{h_name}`")

            args = hook.get("args", {})
            for key in args:
                if "output" in key:
                    expected_outputs.append(args[key])

        with open(receipt_path, "w", encoding="utf-8") as f:
            f.write(f"# Pipeline Execution Receipt: {name}\n")
            f.write(f"**Generated by Fetchez v{fetchez_version}**\n")
            f.write(f"*Execution Time: {timestamp}*\n\n")

            f.write("## Project Description\n")
            f.write(f"{desc}\n\n")

            f.write("## Target Region\n")
            f.write(f"{region_str}\n\n")

            f.write("## Data Modules Executed\n")
            if modules_info:
                f.write("\n".join(modules_info) + "\n\n")
            else:
                f.write("*None*\n\n")

            f.write("## Processing Pipeline (Hooks)\n")
            if hooks_info:
                f.write("\n".join(hooks_info) + "\n")
            else:
                f.write("*None*\n")

        # --- Print Terminal Summary ---
        logger.info("=" * 67)
        logger.info(f"✅ PIPELINE COMPLETE: {name}")
        logger.info("=" * 67)

        short_desc = desc[:75] + "..." if len(desc) > 75 else desc
        logger.info(f"Description: {short_desc}")

        if region and str(region) != "None":
            logger.info(f"Region:      {region}")

        sources_str = ", ".join(
            [f"{k} (x{v})" if v > 1 else k for k, v in mod_counts.items()]
        )
        logger.info(f"Sources:     {sources_str}")

        logger.info(f"💾 OUTPUTS SAVED TO: {self.base_dir}")
        for out in expected_outputs:
            logger.info(f"  ➔ {out}")

        logger.info(f"📄 Full processing receipt saved to: {receipt_filename}")
        logger.info("=" * 67)

    def validate(self):
        """Validates the recipe for syntax, missing plugins, dependencies, and logical errors.

        Returns:
          bool: True if valid, False if errors exist.
          list: List of error messages.
        """

        ModuleRegistry.load_all()
        HookRegistry.load_all()

        errors = []
        claimed_outputs = set()

        def check_output_collision(hook_dict, context_name):
            """Helper to check if a hook is clobbering an existing file."""

            out_file = hook_dict.get("args", {}).get("output")
            if out_file:
                if out_file in claimed_outputs:
                    errors.append(
                        f"[{context_name}] Output Collision: Multiple hooks are attempting to write to '{out_file}'."
                    )
                claimed_outputs.add(out_file)

        # Validate Modules
        for mod in self.config.get("modules", []):
            mod_name = mod.get("module")
            mod_keys = mod.keys()
            valid_keys = ["module", "bundle", "hooks", "args", "region", "description", "_comment"]

            for key in mod_keys:
                if key not in valid_keys:
                    errors.append(
                        f"Module `{mod_name}` has unexpected reference to `{key}`"
                    )

            if not ModuleRegistry.get_class(mod_name) and mod_name not in [
                "file",
                "local_fs",
            ]:
                errors.append(f"Missing Module: '{mod_name}'")

            # Check Module-level Hooks
            # mod_hook_counts = {}
            for hook in mod.get("hooks", []):
                h_name = hook.get("name")
                HookCls = HookRegistry.get_class(h_name)

                if not HookCls:
                    errors.append(f"Missing Hook: '{h_name}' (in module {mod_name})")
                    continue

                # Dependency Check
                if hasattr(HookCls, "_validate_deps"):
                    passed, msg = HookCls()._validate_deps()
                    if not passed:
                        errors.append(
                            f"[{mod_name} -> {h_name}] Missing Dependency: {msg}"
                        )

                check_output_collision(hook, f"Module: {mod_name}")

        # Validate Global Hooks
        # global_hook_counts = {}
        for hook in self.config.get("global_hooks", []):
            h_name = hook.get("name")
            HookCls = HookRegistry.get_class(h_name)

            if not HookCls:
                errors.append(f"Missing Global Hook: '{h_name}'")
                continue

            # Dependency Check
            if hasattr(HookCls, "_validate_deps"):
                passed, msg = HookCls()._validate_deps()
                if not passed:
                    errors.append(f"[Global -> {h_name}] Missing Dependency: {msg}")

            check_output_collision(hook, "Global Hooks")

        return len(errors) == 0, errors
