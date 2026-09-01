"""In-memory store for feature details, shared across node executions"""

from typing import Any, Dict

# Persists in memory for the lifetime of the process, in addition to
# whatever gets written to the output JSON file.
FEATURE_DETAILS_MEMORY: Dict[str, Any] = {}


def update_feature_details_memory(entries: Dict[str, Any]) -> None:
    """Merge new entries into the in-memory feature details store"""
    FEATURE_DETAILS_MEMORY.update(entries)


def get_feature_details_memory() -> Dict[str, Any]:
    """Return the current in-memory feature details store"""
    return FEATURE_DETAILS_MEMORY
