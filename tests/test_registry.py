# test_registry.py
import logging
import os
import ast
import fetchez.modules
import fetchez.hooks
from fetchez.registry import ModuleRegistry, HookRegistry
from fetchez.hooks import FetchHook

logger = logging.getLogger(__name__)


def test_registry_integrity():
    """Ensure all core modules in the registry can be imported."""

    ModuleRegistry.load_all()
    modules = ModuleRegistry.get_registry()

    assert len(modules) > 0

    # Ensure we only test primary classes, not aliases
    primary_keys = [k for k, v in modules.items() if v.get("cls").lower() == k.lower()]

    for name in primary_keys:
        cls = ModuleRegistry.get_class(name)
        assert cls is not None, f"Failed to load class for {name}"
        assert hasattr(cls, "run"), f"Module {name} missing 'run' method"


def test_module_metadata_complete():
    """Ensure all core modules have the required metadata attributes defined."""

    ModuleRegistry.load_all()
    modules = ModuleRegistry.get_registry()

    # In the new registry, `meta_` is stripped from the keys in the dictionary!
    required_keys = [
        "category",
        "desc",
        "agency",
        "tags",
        "resolution",
        "license",
        "urls",
    ]

    for name, meta in modules.items():
        if name in meta.get("aliases", []):
            continue  # Skip aliases

        missing = [attr for attr in required_keys if attr not in meta]
        assert not missing, f"Module '{name}' is missing metadata: {missing}"


def test_alias_resolution():
    ModuleRegistry.load_all()

    primary_cls = ModuleRegistry.get_class("lidarbc")
    alias_cls = ModuleRegistry.get_class("geobc")

    assert primary_cls is not None
    assert primary_cls is alias_cls


# Hooks
def test_hook_registry_integrity():
    """Ensure all core hooks can be loaded and have required metadata."""

    HookRegistry.load_all()

    hooks = HookRegistry.get_registry()
    assert len(hooks) > 0

    # The standard metadata fields every hook MUST provide
    required_attrs = ["name", "meta_stage", "meta_category", "meta_desc"]

    for name, meta in hooks.items():
        # Get the actual class object, not the string name!
        hook_cls = HookRegistry.get_class(name)

        assert hook_cls is not None, (
            f"Failed to retrieve class object for hook '{name}'"
        )
        assert hasattr(hook_cls, "run"), f"Hook '{name}' missing 'run' method"

        for attr in required_attrs:
            assert hasattr(hook_cls, attr), (
                f"Hook '{name}' ({hook_cls.__name__}) is missing required attribute: '{attr}'"
            )


def test_hook_stage_mapping():
    class DummyHook(FetchHook):
        meta_stage = "post"

    # Defaults to the class meta_stage
    hook = DummyHook()
    assert hook.stage == "post"

    # Can be overridden by the user at runtime
    hook_override = DummyHook(stage="pre")
    assert hook_override.stage == "pre"


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

    mod_dir = os.path.dirname(fetchez.modules.__file__)
    hook_dir = os.path.dirname(fetchez.hooks.__file__)

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
