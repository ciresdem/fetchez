import logging
from fetchez.hooks.registry import HookRegistry
from fetchez.registry import FetchezRegistry

logger = logging.getLogger(__name__)


def test_registry_integrity():
    """Ensure all core modules in the registry can be imported."""

    modules = FetchezRegistry._modules.keys()

    for mod_key in modules:
        logger.info(f"Testing import of: {mod_key}")

        cls = FetchezRegistry.load_module(mod_key)

        assert cls is not None, f"Failed to load class for {mod_key}"
        assert hasattr(cls, "run"), f"Module {mod_key} missing 'run' method"


def test_hook_registry_integrity():
    """Ensure all core hooks can be loaded."""

    HookRegistry.load_builtins()
    HookRegistry.load_user_plugins()

    hooks = HookRegistry._hooks
    assert len(hooks) > 0

    for name, hook_cls in hooks.items():
        assert hook_cls.name is not None
