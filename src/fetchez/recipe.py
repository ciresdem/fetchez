#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
fetchez.recipe
~~~~~~~~~~~~~~

The Recipe Engine.
Loads a configuration (The Recipe) and executes it against the target region.

:copyright: (c) 2010-2026 Regents of the University of Colorado
:license: MIT, see LICENSE for more details.
"""

import os
import copy
import json
import yaml
import inspect
import logging

from .core import run_fetchez
from .spatial import yield_parsed_regions
from .registry import (
    ModuleRegistry,
    HookRegistry,
    ModifierRegistry,
    SchemaRegistry,
    PresetRegistry,
    BundleRegistry,
    RecipeRegistry,
)
from .utils import TqdmLoggingHandler, colorize, CYAN
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

    def to_json(self, indent=2) -> str:
        """Serialize the recipe configuration to a JSON string."""

        return json.dumps(self.config, indent=indent)

    def to_cli(self, executable="fetchez run") -> str:
        """Translate the recipe configuration into a runnable CLI command string."""

        cmd_parts = [executable]

        # Base Pipeline Arguments
        if "region" in self.config:
            cmd_parts.append(f"-R {self.config['region']}")
        if "region_srs" in self.config:
            cmd_parts.append(f"--region-srs {self.config['region_srs']}")
        if "execution" in self.config and "threads" in self.config["execution"]:
            cmd_parts.append(f"--threads {self.config['execution']['threads']}")

        # Global Hooks
        for hook in self.config.get("global_hooks", []):
            hook_name = hook.get("name") or hook.get("preset")
            args = hook.get("args", {})
            if args:
                arg_str = ",".join(
                    f"{k}={'/'.join(map(str, v)) if isinstance(v, list) else v}"
                    for k, v in args.items()
                )
                cmd_parts.append(f"--global-hook {hook_name}:{arg_str}")
            else:
                cmd_parts.append(f"--global-hook {hook_name}")

        # Modules & Bundles
        for mod in self.config.get("modules", []):
            if isinstance(mod, str):
                cmd_parts.append(mod)
                continue

            mod_name = mod.get("module") or mod.get("bundle") or mod.get("recipe")
            mod_args = mod.get("args", {})

            # Start the module segment
            mod_cmd = [mod_name]

            # Append Module Arguments (e.g., --weight 3.0)
            for k, v in mod_args.items():
                mod_cmd.append(f"--{k.replace('_', '-')} {v}")

            cmd_parts.append(" ".join(mod_cmd))

            # Append specific Module Hooks
            for hook in mod.get("hooks", []):
                hook_name = hook.get("name") or hook.get("preset")
                args = hook.get("args", {})
                if args:
                    arg_str = ",".join(
                        f"{k}={'/'.join(map(str, v)) if isinstance(v, list) else v}"
                        for k, v in args.items()
                    )
                    cmd_parts.append(f"  --hook {hook_name}:{arg_str}")
                else:
                    cmd_parts.append(f"  --hook {hook_name}")

        return " \\\n  ".join(cmd_parts)

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

    def _init_modules(
        self, module_defs, target_region=None, global_region_srs="EPSG:4326"
    ):
        """Takes a flat list of module dictionaries and instantiates the Python classes."""

        modules_to_run = []

        for mod_def in module_defs:
            mod_key = mod_def.get("module")
            mod_args = mod_def.get("args", {})
            mod_region_srs = mod_def.get("region_srs", global_region_srs)
            mod_regions = [target_region] if target_region else [None]

            ModCls = ModuleRegistry.get_class(mod_key)
            if not ModCls:
                logger.error(f"Unknown module: {mod_key}")
                continue

            sig = inspect.signature(ModCls.__init__)
            valid_mod_args = {
                k: v
                for k, v in mod_args.items()
                if k in sig.parameters or "kwargs" in str(sig.parameters)
            }

            # Initialize the hooks attached to this specific module
            mod_hooks = self._init_hooks(mod_def.get("hooks", []))

            for region in mod_regions:
                if region is not None and region.valid_p():
                    region.srs = mod_region_srs

                if "path" in mod_args:
                    mod_args["path"] = self._resolve_path(mod_args["path"])

                try:
                    instance = ModCls(
                        src_region=region, hook=mod_hooks, **valid_mod_args
                    )
                    modules_to_run.append(instance)
                except Exception as e:
                    logger.error(f"Failed to load {mod_key}: {e}")

        return modules_to_run

    def _init_hooks(self, hook_defs, mod=None):
        """Takes a flat list of expanded hook dictionaries and instantiates the Python classes."""

        HookRegistry.load_all()
        active_hooks = []

        for h in hook_defs:
            name = h.get("name")
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

            HookCls = HookRegistry.get_class(name)
            if HookCls:
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

    def _inject_batch_context(self, config_block, batch_name, batch_region):
        """Recursively formats strings in the config to inject the batch name."""

        if not batch_name:
            return config_block

        if isinstance(config_block, dict):
            return {
                k: self._inject_batch_context(v, batch_name, batch_region)
                for k, v in config_block.items()
            }
        elif isinstance(config_block, list):
            return [
                self._inject_batch_context(v, batch_name, batch_region)
                for v in config_block
            ]
        elif isinstance(config_block, str):
            return config_block.replace("{batch_name}", str(batch_name))

        return config_block

    def _get_module_signature(self, mod_dict):
        """Creates a unique signature for a module to handle deduplication.
        Ensures that 'tnm' (dataset 1) does not collide with 'tnm' (dataset 3).
        """

        if isinstance(mod_dict, str):
            return mod_dict

        m_name = mod_dict.get("module")
        if not m_name:
            return str(mod_dict)

        args = mod_dict.get("args", {})

        # Ids that make a dataset truly unique within a module
        ids = []
        for key in [
            "datatype",
            "datasets",
            "formats",
            "layer",
            "product",
            "survey_id",
            "url",
            "path",
        ]:
            if key in args:
                ids.append(f"{key}={args[key]}")

        if ids:
            return f"{m_name}::" + "::".join(sorted(ids))
        return m_name

    def _expand_modules(self, raw_modules, parent_weight=1.0):
        """Recursively flattens bundles and deduplicates/merges modules."""

        RecipeRegistry.load_all()

        expanded_dict = {}
        for mod_dict in raw_modules:
            if isinstance(mod_dict, str):
                expanded_dict[mod_dict] = mod_dict
                continue

            # Check if this item is a bundle or a nested recipe
            target = mod_dict.get("bundle") or mod_dict.get("recipe")
            if target:
                BundleRegistry.load_all()
                RecipeRegistry.load_all()

                user_args = mod_dict.get("args", {})
                user_hooks = mod_dict.get("hooks", [])

                # Stack the weights recursively
                current_weight = float(user_args.get("weight", 1.0)) * parent_weight

                bundle_def = BundleRegistry.get_yaml(target)
                if not bundle_def:
                    recipe_meta = RecipeRegistry.get_yaml(target)
                    if recipe_meta:
                        bundle_def = recipe_meta.get("config", {})

                if not bundle_def:
                    try:
                        bundle_def = self.from_file(self._resolve_path(target)).config
                    except Exception:
                        logger.error(
                            f"Bundle/Recipe '{target}' not found locally or in registry."
                        )
                        continue

                child_modules = bundle_def.get("modules", [])

                # Recursively expand the children first
                child_expanded = self._expand_modules(child_modules, current_weight)

                # Process the returned children and inject them into our current pipeline
                for child_mod in child_expanded:
                    if isinstance(child_mod, dict) and "hooks" in child_mod:
                        child_mod["hooks"] = self._expand_hooks(
                            child_mod.get("hooks", []), user_hooks
                        )

                    sig = self._get_module_signature(child_mod)

                    # If a bundle defines a module, add it or let it override an earlier one
                    expanded_dict[sig] = child_mod

            elif "module" in mod_dict:
                sig = self._get_module_signature(mod_dict)

                # --- DEDUPLICATION & MERGE ---
                if sig in expanded_dict and isinstance(expanded_dict[sig], dict):
                    existing = expanded_dict[sig]

                    # Merge args: The newer declaration (Parent) overwrites the existing (Bundle)
                    merged_args = existing.get("args", {}).copy()
                    merged_args.update(mod_dict.get("args", {}))

                    # Hooks: If the override explicitly defines hooks, replace them.
                    # Otherwise, keep the original hooks from the bundle.
                    merged_hooks = mod_dict.get("hooks", existing.get("hooks", []))

                    expanded_dict[sig] = {
                        "module": mod_dict["module"],
                        "args": merged_args,
                        "hooks": merged_hooks,
                    }
                    logger.debug(f"Merged/Overridden module via deduplication: {sig}")
                else:
                    expanded_dict[sig] = mod_dict
            else:
                logger.error(f"Invalid module definition: {mod_dict}")

        return list(expanded_dict.values())

    def _expand_hooks(self, hook_defs, parent_hooks=None):
        """Recursively expands presets into a flat list of hook definition dictionaries."""

        expanded_list = []
        parent_hooks = parent_hooks or []

        for h in hook_defs:
            name = h.get("name")
            is_preset = h.get("preset")

            hook_map = {}
            if parent_hooks:
                hook_map = {
                    hook.get("name"): hook for hook in parent_hooks if "name" in hook
                }
                if name in hook_map:
                    h_args = h.get("args", {}).copy()
                    h_args.update(hook_map[name].get("args", {}))
                    h["args"] = h_args

            if is_preset:
                user_args = h.get("args")

                PresetRegistry.load_all()
                preset_def = PresetRegistry.get_yaml(is_preset)

                if preset_def:
                    preset_hooks = copy.deepcopy(preset_def.get("hooks", []))

                    if user_args:
                        if parent_hooks:
                            hook_map = {
                                hook.get("name"): hook
                                for hook in user_args
                                if "name" in hook
                            }
                            for parent_hook in parent_hooks:
                                name = parent_hook.get("name")

                                if name in hook_map:
                                    # parent_hook.update(hook_map[name])
                                    merged_args = parent_hook.get("args", {}).copy()
                                    merged_args.update(hook_map[name].get("args", {}))
                                    parent_hook["args"] = merged_args

                        else:
                            # parent_hooks.extend(user_args)
                            parent_hooks = (
                                copy.deepcopy(parent_hooks)
                                if parent_hooks
                                else copy.deepcopy(user_args)
                            )

                    # Recursively expand the child hooks, passing down the merged args
                    expanded_child_hooks = self._expand_hooks(
                        preset_hooks, parent_hooks=parent_hooks
                    )
                    expanded_list.extend(expanded_child_hooks)
                else:
                    logger.error(f"Preset '{is_preset}' not found in registry.")
            else:
                expanded_list.append(h)

        return expanded_list

    def _generate_receipt(self):
        import datetime

        name = self.name
        desc = self.config.get("project", {}).get(
            "description", "No description provided."
        )
        region = self.config.get("region", "Global")
        region_srs = self.config.get("region_srs", "EPSG:4326")

        receipt_filename = f"{name.lower().replace(' ', '_')}_receipt.md"
        receipt_path = os.path.join(self.base_dir, receipt_filename)

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        region_str = (
            f"`{region}` (Native CRS: {region_srs})"
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
            valid_keys = [
                "module",
                "bundle",
                "hooks",
                "args",
                "region",
                "region_srs",
                "description",
                "_comment",
            ]

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

    def run(self, outdir=None, shared_cache=None, overwrite=False):
        """Execute the recipe, supporting vector-based batching, caching, and resumption."""

        ModuleRegistry.load_all()
        BundleRegistry.load_all()
        ModifierRegistry.load_all()
        SchemaRegistry.load_all()

        if not self.config:
            return

        self._check_integrity()
        # Check for 'domain' to see if we have the proper extension to run the recipe.
        # Maybe add something like this to _check_integrity
        # domain = self.config.get("domain")

        # Execution parameters
        run_opts = self.config.get("execution", {})
        threads = run_opts.get("threads", 1)
        raw_region = self.config.get("region")
        global_region_srs = self.config.get("region_srs", "EPSG:4326")
        recipe_name = self.config.get("project", {}).get("name", "Unnamed")

        original_cwd = os.getcwd()
        if outdir is None:
            base_outdir = os.path.abspath(original_cwd)
        else:
            base_outdir = os.path.abspath(outdir)

        # State Tracking
        state_file = os.path.join(original_cwd, ".fetchez_batch_state.json")
        completed_tiles = []
        if os.path.exists(state_file) and not overwrite:
            try:
                with open(state_file, "r") as f:
                    completed_tiles = json.load(f)
            except Exception:
                pass

        # Shared Cache
        abs_cache = None
        if shared_cache:
            abs_cache = os.path.abspath(shared_cache)
            os.makedirs(abs_cache, exist_ok=True)
            logger.info(f"Shared cache enabled: {abs_cache}")

        # Batch Loop
        for i, (target_region, feat_name) in enumerate(
            yield_parsed_regions(raw_region)
        ):
            # Batch Name
            if feat_name:
                batch_name = str(feat_name)
            elif target_region and i > 0:
                batch_name = f"batch_{i:03d}"
            else:
                batch_name = None

            # Check State
            if batch_name and batch_name in completed_tiles and not overwrite:
                logger.info(
                    f"Skipping completed tile: {batch_name} (use --overwrite to force)"
                )
                continue

            iteration_config = copy.deepcopy(self.config)

            # Setup the Sub-Folder
            tile_dir = base_outdir  # original_cwd
            if batch_name:
                logger.info(
                    colorize(f"\n--- Running Batch Iteration: {batch_name} ---", CYAN)
                )
                orig_name = iteration_config.get("project", {}).get("name", "Unnamed")
                iteration_config.setdefault("project", {})["name"] = (
                    f"{orig_name}_{batch_name}"
                )

                tile_dir = os.path.join(tile_dir, batch_name)

            os.makedirs(tile_dir, exist_ok=True)
            os.chdir(tile_dir)

            try:
                # Local Region
                if target_region:
                    iteration_config["region"] = target_region.to_list()

                # Initialize & Run Pipeline
                self.base_dir = tile_dir

                # Expand Hooks and Modules
                iteration_config["global_hooks"] = self._expand_hooks(
                    iteration_config.get("global_hooks", [])
                )
                iteration_config["modules"] = self._expand_modules(
                    iteration_config.get("modules", [])
                )

                for mod in iteration_config["modules"]:
                    mod["hooks"] = self._expand_hooks(mod.get("hooks", []))

                # Inject outdir for shared caching
                if abs_cache:
                    for mod in iteration_config.get("modules", []):
                        if mod.get("module") not in ["file", "local_fs", "stdin"]:
                            mod.setdefault("args", {})["outdir"] = abs_cache

                if batch_name or target_region:
                    # Inject the {batch_name} context into outputs
                    iteration_config = self._inject_batch_context(
                        iteration_config,
                        batch_name or target_region.format("fn"),
                        target_region,
                    )

                # Apply any Modifiers
                iteration_config_modified = ModifierRegistry.apply_modifier(
                    iteration_config.copy()
                )
                iteration_valid, iteration_errors = Recipe(
                    iteration_config_modified
                ).validate()
                if not iteration_valid:
                    logger.warning(
                        f"The recipe that was mutated by the modifier is invalid: {iteration_errors}"
                    )
                else:
                    iteration_config = copy.deepcopy(iteration_config)

                # Validate final recipe with any Schemas
                _iteration_validations = SchemaRegistry.validate(
                    iteration_config.copy()
                )
                # TODO: warn/quite if any schema returns invalid

                # Initialize Hooks and Modules ( to python classes )
                try:
                    global_hooks = self._init_hooks(iteration_config["global_hooks"])
                except Exception as e:
                    logger.error(f"Could not initialize recipe global hooks: {e}")
                    continue

                try:
                    modules_to_run = self._init_modules(
                        iteration_config["modules"],
                        target_region=target_region,
                        global_region_srs=global_region_srs,
                    )
                except Exception as e:
                    logger.error(f"Could not initialize recipe modules: {e}")
                    continue

                if not modules_to_run:
                    continue

                # Dump the localized recipe for debugging and reproducibility
                batch_config_fn = f"{batch_name or recipe_name}_recipe.yaml"
                with open(batch_config_fn, "w") as f:
                    yaml.dump(
                        iteration_config,
                        f,
                        sort_keys=False,
                        default_flow_style=False,
                    )
                logger.debug(f"Saved localized recipe to {batch_config_fn}")

                for mod in modules_to_run:
                    mod.run()

                run_fetchez(modules_to_run, threads=threads, global_hooks=global_hooks)

                # Update State
                if batch_name:
                    completed_tiles.append(batch_name)
                    with open(state_file, "w") as f:
                        json.dump(completed_tiles, f, indent=2)

            except Exception as e:
                logger.error(f"Batch '{batch_name or 'run'}' failed: {e}")
                logger.warning(
                    "Batch processing halted. Re-run command to resume from this tile."
                )
                raise

            finally:
                self.base_dir = original_cwd
                os.chdir(original_cwd)

        logger.debug(f"Batch execution complete for {self.name}")
