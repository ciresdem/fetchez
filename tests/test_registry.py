import logging
import os
import ast
import fetchez.modules.builtins
import fetchez.hooks.builtins
from fetchez.hooks.registry import HookRegistry
from fetchez.modules.registry import FetchezRegistry

logger = logging.getLogger(__name__)


def test_registry_integrity():
    """Ensure all core modules in the registry can be imported."""

    FetchezRegistry.load_builtins()
    # It is usually best to exclude user plugins in core unit tests to ensure environment isolation
    # FetchezRegistry.load_user_plugins()

    modules = FetchezRegistry._modules
    assert len(modules) > 0

    for name, meta in modules.items():
        logger.info(f"Testing import of: {name}")

        cls = FetchezRegistry.load_module(name)

        # FIXED: Changed mod_key to name to prevent UnboundLocalError
        assert cls is not None, f"Failed to load class for {name}"
        assert hasattr(cls, "run"), f"Module {name} missing 'run' method"


def test_module_metadata_complete():
    """Ensure all core modules have the required metadata attributes defined."""

    FetchezRegistry.load_builtins()
    modules = FetchezRegistry._modules

    # The standard metadata fields every module MUST provide
    required_attrs = [
        "name",
        "meta_category",
        "meta_desc",
        "meta_agency",
        "meta_tags",
        # "meta_region", # we check region specially (it is allowed to be meta_coverage as well.
        "meta_resolution",
        "meta_license",
        "meta_urls",
    ]

    for name, meta in modules.items():
        cls = FetchezRegistry.load_module(name)

        has_coverage = hasattr(cls, "meta_coverage") or hasattr(cls, "meta_region")
        assert has_coverage, f"Module '{name}' missing 'meta_coverage' attribute."

        for attr in required_attrs:
            assert hasattr(cls, attr), (
                f"Module '{name}' ({cls.__name__}) is missing required attribute: '{attr}'"
            )

            val = getattr(cls, attr)
            if attr == "meta_tags":
                assert isinstance(val, list), (
                    f"Module '{name}' attribute 'tags' must be a list."
                )
            elif attr == "meta_urls":
                assert isinstance(val, dict), (
                    f"Module '{name}' attribute 'urls' must be a dictionary."
                )
            elif attr == "meta_desc":
                assert isinstance(val, str) and len(val) > 0, (
                    f"Module '{name}' must have a non-empty description string."
                )


def test_module_aliases():
    """Ensure aliases correctly map to their parent class."""
    FetchezRegistry.load_builtins()

    # Grab a module we know has an alias, like DAV / digital_coast
    dav_class = FetchezRegistry.load_module("dav")
    alias_class = FetchezRegistry.load_module("digital_coast")

    assert dav_class is not None, "Main module 'dav' failed to load."
    assert alias_class is not None, "Alias 'digital_coast' failed to load."

    # The alias should return the EXACT same class object as the main name
    assert dav_class is alias_class, "Alias did not map to the same class object!"


# Hooks
def test_hook_registry_integrity():
    """Ensure all core hooks can be loaded and have required metadata."""

    HookRegistry.load_builtins()
    # HookRegistry.load_user_plugins()

    hooks = HookRegistry._hooks
    assert len(hooks) > 0

    # The standard metadata fields every hook MUST provide
    required_attrs = ["name", "stage", "category", "desc"]

    for name, hook_cls in hooks.items():
        assert hasattr(hook_cls, "run"), f"Hook {name} missing 'run' method"

        for attr in required_attrs:
            assert hasattr(hook_cls, attr), (
                f"Hook '{name}' ({hook_cls.__name__}) is missing required attribute: '{attr}'"
            )


def test_optional_dependencies_are_protected():
    """Ensure all optional dependencies are imported inside a try/except block."""

    OPTIONAL_IMPORTS = {
        "boto3",
        "shapefile",
        "pyproj",
        "shapely",
        "mercantile",
        "earthaccess",
        "pystac",
        "pystac_client",
    }

    mod_dir = os.path.dirname(fetchez.modules.builtins.__file__)
    hook_dir = os.path.dirname(fetchez.hooks.builtins.__file__)

    unprotected_imports = []

    for directory in [mod_dir, hook_dir]:
        for root, _, files in os.walk(directory):
            for file in files:
                if not file.endswith(".py") or file.startswith("_"):
                    continue

                filepath = os.path.join(root, file)
                with open(filepath, "r", encoding="utf-8") as f:
                    source = f.read()

                try:
                    tree = ast.parse(source, filename=filepath)
                except SyntaxError:
                    continue

                safe_lines = set()
                for node in ast.walk(tree):
                    if isinstance(node, ast.Try):
                        safe_lines.update(range(node.lineno, node.end_lineno + 1))

                for node in ast.walk(tree):
                    imported_module = None

                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            base_mod = alias.name.split(".")[0]
                            if base_mod in OPTIONAL_IMPORTS:
                                imported_module = base_mod
                                break

                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            base_mod = node.module.split(".")[0]
                            if base_mod in OPTIONAL_IMPORTS:
                                imported_module = base_mod

                    if imported_module:
                        if node.lineno not in safe_lines:
                            # We found an unprotected import!
                            rel_path = os.path.relpath(filepath, start=os.getcwd())
                            unprotected_imports.append(
                                f"  - {rel_path}:{node.lineno} (imported '{imported_module}')"
                            )

    error_msg = (
        "\n🚨 Found unprotected optional imports! These must be wrapped in a try/except block "
        "to prevent crashing the CLI for users who haven't installed them:\n"
        + "\n".join(unprotected_imports)
    )
    assert not unprotected_imports, error_msg
