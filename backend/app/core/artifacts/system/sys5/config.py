"""
Configuration settings for SYS5 workflow

All configurable parameters for requirement extraction and processing
"""

# ============================================================================
# REQUIREMENT KEYWORDS AND MATCHING RULES
# ============================================================================

# Keywords that identify requirement type (exact match, case-insensitive)
# A row is considered a Functional requirement if it contains ANY of these
FUNCTIONAL_REQ_KEYWORDS = [
    "Functional requirement",       # Singular
    "Functional requirements",      # Plural
]

# Keywords to EXCLUDE (case-insensitive)
# A row containing any of these will NOT be considered functional
EXCLUDED_KEYWORDS = [
    "non-functional",
    "non functional",
    "nonfunctional",
    "security requirement",
    "performance requirement",
    "quality requirement",
]

# Matching configuration
KEYWORD_MATCHING_CONFIG = {
    "case_sensitive": False,        # Match keywords case-insensitively
    "exact_match": True,            # Require exact word match (not substring)
    "word_boundaries": True,        # Match only complete words
}

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

LOGGING_CONFIG = {
    "verbose": True,                # Print detailed logs
    "log_matched_rows": True,       # Print details of matched rows
    "log_skipped_rows": False,      # Print details of skipped rows
}

# ============================================================================
# OUTPUT CONFIGURATION
# ============================================================================

OUTPUT_CONFIG = {
    "json_indent": 2,               # JSON indentation level
    "include_metadata": True,       # Include metadata in JSON
    "timestamp_format": "%Y%m%d_%H%M%S",
}

# ============================================================================
# FUNCTION: Check if keyword matches requirement
# ============================================================================

def is_functional_requirement(cell_value: str) -> bool:
    """
    Check if a cell value indicates a functional requirement

    Logic:
    1. Check if cell contains ANY excluded keyword -> return False
    2. Check if cell contains ANY functional requirement keyword -> return True
    3. Otherwise -> return False

    Args:
        cell_value: Cell value to check

    Returns:
        True if functional requirement, False otherwise
    """
    if not cell_value:
        return False

    cell_lower = str(cell_value).lower() if not KEYWORD_MATCHING_CONFIG["case_sensitive"] else str(cell_value)

    # Check excluded keywords first
    for excluded_kw in EXCLUDED_KEYWORDS:
        if KEYWORD_MATCHING_CONFIG["case_sensitive"]:
            excluded_lower = excluded_kw
        else:
            excluded_lower = excluded_kw.lower()

        # Exact match with word boundaries
        if KEYWORD_MATCHING_CONFIG["word_boundaries"]:
            if f" {excluded_lower} " in f" {cell_lower} ":
                return False
            if cell_lower.startswith(excluded_lower + " "):
                return False
            if cell_lower.endswith(" " + excluded_lower):
                return False
            if cell_lower == excluded_lower:
                return False
        else:
            if excluded_lower in cell_lower:
                return False

    # Check functional requirement keywords
    for func_kw in FUNCTIONAL_REQ_KEYWORDS:
        if KEYWORD_MATCHING_CONFIG["case_sensitive"]:
            func_lower = func_kw
        else:
            func_lower = func_kw.lower()

        # Exact match with word boundaries
        if KEYWORD_MATCHING_CONFIG["word_boundaries"]:
            if f" {func_lower} " in f" {cell_lower} ":
                return True
            if cell_lower.startswith(func_lower + " "):
                return True
            if cell_lower.endswith(" " + func_lower):
                return True
            if cell_lower == func_lower:
                return True
        else:
            if func_lower in cell_lower:
                return True

    return False
