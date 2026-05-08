from __future__ import annotations

import importlib
from types import ModuleType


def load_specialty_module(name: str) -> ModuleType:
    """Load a specialty package and hydrate its standard exports."""
    module_name = f"specialties.{name}"
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(f"Specialty module not found: {module_name}") from exc

    if not hasattr(module, "SITE_CONFIG"):
        try:
            config_module = importlib.import_module(f"{module_name}.config")
            setattr(module, "SITE_CONFIG", getattr(config_module, "SITE_CONFIG"))
        except ModuleNotFoundError:
            setattr(module, "SITE_CONFIG", {})

    if not hasattr(module, "apply_rules"):
        try:
            postprocess_module = importlib.import_module(f"{module_name}.postprocess")
            if hasattr(postprocess_module, "apply_rules"):
                setattr(module, "apply_rules", getattr(postprocess_module, "apply_rules"))
            elif hasattr(postprocess_module, f"apply_{name}_rules"):
                setattr(module, "apply_rules", getattr(postprocess_module, f"apply_{name}_rules"))
        except ModuleNotFoundError:
            pass

    if not hasattr(module, "apply_rules"):
        raise AttributeError(f"{module_name} does not define apply_rules")

    return module
