"""Path resolution utilities for relative and absolute paths"""

import os


def resolve_path(path: str, base_path: str = None) -> str:
    """
    Resolve both relative and absolute paths

    Handles:
    - Absolute paths: Returns as-is after normalization
    - Relative paths: Converts to absolute using base_path or current directory

    Args:
        path: Path to resolve (relative or absolute)
        base_path: Base path for relative paths (defaults to current dir)

    Returns:
        Absolute normalized path
    """
    if os.path.isabs(path):
        return os.path.abspath(path)

    if base_path:
        return os.path.abspath(os.path.join(base_path, path))

    return os.path.abspath(path)


def ensure_directory_exists(path: str) -> str:
    """
    Create directory if it doesn't exist

    Args:
        path: Directory path to create

    Returns:
        Absolute path to directory
    """
    abs_path = os.path.abspath(path)
    os.makedirs(abs_path, exist_ok=True)
    return abs_path
