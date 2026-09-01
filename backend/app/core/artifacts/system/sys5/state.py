"""State management for SYS5 workflow"""

from typing import Dict, Any, List
from typing_extensions import TypedDict


class SYS5State(TypedDict):
    """
    State object for SYS5 workflow

    Tracks the following information across nodes:
    - config: Input configuration
    - requirements: Extracted requirements data
    - errors: Any errors encountered during processing
    - timestamp: Execution timestamp for artifacts
    """
    config: Dict[str, Any]
    requirements: List[Dict[str, Any]]
    errors: List[str]
    timestamp: str
