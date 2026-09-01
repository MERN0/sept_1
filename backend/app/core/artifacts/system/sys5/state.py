"""State management for SYS5 workflow"""

from typing import Dict, Any, List
from typing_extensions import TypedDict


class SYS5State(TypedDict):
    """
    State object for SYS5 workflow

    Tracks the following information across nodes:
    - config: Input configuration
    - requirements: Extracted requirements data (Node 1)
    - feature_details: Signal/command data keyed by signal name (Node 2 - Signal Name,
      Node 3 - Logical Signal Name with underscore), so entries can be looked up later
    - logical_signals: Logical signal extraction results (Node 3)
    - errors: Any errors encountered during processing
    - timestamp: Execution timestamp for artifacts
    """
    config: Dict[str, Any]
    requirements: List[Dict[str, Any]]
    feature_details: Dict[str, Any]
    logical_signals: List[Dict[str, Any]]
    errors: List[str]
    timestamp: str
