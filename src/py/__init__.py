"""Minimal config-json package."""

from .resolve import (
    ResolveConfigTreeResult,
    ResolvedDomain,
    build_wrapped_effective_config,
    resolve_config_tree,
)

__all__ = [
    "__version__",
    "ResolveConfigTreeResult",
    "ResolvedDomain",
    "build_wrapped_effective_config",
    "resolve_config_tree",
]
__version__ = "0.1.0"
