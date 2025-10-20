"""
Pattern matching utilities for file exclusion
"""
import fnmatch
from pathlib import Path


def should_exclude(file_path, exclude_patterns):
    """
    Check if a file should be excluded based on patterns

    Args:
        file_path: Path to check (can be string or Path object)
        exclude_patterns: List of patterns (glob-style)

    Returns:
        bool: True if file should be excluded
    """
    if isinstance(file_path, Path):
        file_path = str(file_path)

    # Normalize path separators
    file_path = file_path.replace('\\', '/')

    for pattern in exclude_patterns:
        # Normalize pattern
        pattern = pattern.replace('\\', '/')

        # Check if pattern matches
        if fnmatch.fnmatch(file_path, pattern):
            return True

        # Check if pattern matches any part of the path
        if pattern.endswith('/') and f'/{pattern}' in f'/{file_path}/':
            return True

        # Check filename only
        if fnmatch.fnmatch(Path(file_path).name, pattern):
            return True

    return False


def filter_files(files, exclude_patterns):
    """
    Filter a list of files based on exclude patterns

    Args:
        files: List of file paths
        exclude_patterns: List of patterns to exclude

    Returns:
        list: Filtered file list
    """
    return [f for f in files if not should_exclude(f, exclude_patterns)]
