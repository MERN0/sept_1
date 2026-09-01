"""
Configuration settings for SYS5 workflow

All configurable parameters for requirement extraction and processing
"""

import os
from typing import Optional

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
# LLM CONFIGURATION
# ============================================================================

LLM_CONFIG = {
    "model": "gpt-4",                           # Model name (e.g., gpt-4, gpt-3.5-turbo)
    "openai_api_key": None,                     # API key (set via environment or override)
    "openai_api_base": "https://api.openai.com/v1",  # API base URL
    "temperature": 0.7,                         # Temperature for generation
    "max_tokens": 2000,                         # Maximum tokens in response
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


# ============================================================================
# LLM INITIALIZATION
# ============================================================================

def get_llm():
    """
    Initialize and return ChatOpenAI LLM instance

    Configuration is read from LLM_CONFIG dict and environment variables:
    - OPENAI_API_KEY: Overrides LLM_CONFIG["openai_api_key"]
    - OPENAI_API_BASE: Overrides LLM_CONFIG["openai_api_base"]

    Returns:
        ChatOpenAI instance configured with settings

    Raises:
        ImportError: If langchain_openai is not installed
        ValueError: If API key is not configured
    """
    try:
        from langchain_openai import ChatOpenAI
    except ImportError:
        raise ImportError(
            "langchain-openai is required. Install with: pip install langchain-openai"
        )

    # Get API key from environment or config
    api_key = os.getenv("OPENAI_API_KEY") or LLM_CONFIG.get("openai_api_key")

    if not api_key:
        raise ValueError(
            "OPENAI_API_KEY not set. Set via environment variable or LLM_CONFIG['openai_api_key']"
        )

    # Get API base URL from environment or config
    api_base = os.getenv("OPENAI_API_BASE") or LLM_CONFIG.get("openai_api_base")

    # Initialize and return ChatOpenAI
    llm = ChatOpenAI(
        model=LLM_CONFIG.get("model", "gpt-4"),
        openai_api_key=api_key,
        openai_api_base=api_base,
        temperature=LLM_CONFIG.get("temperature", 0.7),
        max_tokens=LLM_CONFIG.get("max_tokens", 2000),
    )

    return llm
