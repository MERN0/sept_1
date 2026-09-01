"""Utility to strip empty/null/NaN entries out of nested dict/list data"""

import math
from typing import Any


def _is_empty(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    if isinstance(value, str) and value.strip().lower() in ("", "nan", "none", "n/a", "na"):
        return True
    if isinstance(value, (dict, list, tuple, set)) and len(value) == 0:
        return True
    return False


def drop_empty_values(data: Any) -> Any:
    """
    Recursively drop dict keys / list items whose value is None, NaN, an
    empty string ("", "NaN", "N/A", "na"), or an empty container, so the
    generation stage isn't fed a mass of placeholder nulls.
    """
    if isinstance(data, dict):
        cleaned = {}
        for key, value in data.items():
            cleaned_value = drop_empty_values(value)
            if not _is_empty(cleaned_value):
                cleaned[key] = cleaned_value
        return cleaned

    if isinstance(data, list):
        cleaned_list = [drop_empty_values(v) for v in data]
        return [v for v in cleaned_list if not _is_empty(v)]

    return data
