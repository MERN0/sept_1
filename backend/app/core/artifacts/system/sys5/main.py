"""Main orchestrator for SYS5 workflow execution"""

import json
import os
import sys
from typing import Dict, Any
from datetime import datetime

# Setup path for imports
_workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
if _workspace_root not in sys.path:
    sys.path.insert(0, _workspace_root)

try:
    from .state import SYS5State  # type: ignore
    from .graph import build_workflow  # type: ignore
except ImportError:
    from backend.app.core.artifacts.system.sys5.state import SYS5State
    from backend.app.core.artifacts.system.sys5.graph import build_workflow


def run_workflow(config: Dict[str, Any]) -> str:
    """
    Execute SYS5 workflow (Node 1)

    Args:
        config: Configuration dictionary with:
            - project_name: Project identifier
            - input_folder_path: Path to input files (relative or absolute)
            - output_dir: Output directory (relative or absolute)
            - req_filename: Excel filename
            - req_sheet_name: Sheet name in Excel
            - version: Optional version number

    Returns:
        JSON string with workflow results
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Initialize state
    initial_state: SYS5State = {
        "config": config,
        "requirements": [],
        "signals": [],
        "feature_details": {},
        "errors": [],
        "timestamp": timestamp
    }

    # Print workflow start
    print(f"\n{'='*80}")
    print("STARTING SYS5 NODE 1 WORKFLOW")
    print(f"{'='*80}")
    print(f"Project: {config.get('project_name')}")
    print(f"Version: {config.get('version', 'N/A')}")
    print(f"Timestamp: {timestamp}")
    print(f"{'='*80}\n")

    # Build and execute workflow
    graph = build_workflow()
    final_state = graph.invoke(initial_state)

    # Prepare result
    result = {
        "status": "success" if not final_state["errors"] else "failed",
        "total_requirements": len(final_state["requirements"]),
        "total_signals": len(final_state["signals"]),
        "total_features": len(final_state["feature_details"]),
        "requirements": final_state["requirements"],
        "signals": final_state["signals"],
        "feature_details": final_state["feature_details"],
        "errors": final_state["errors"],
        "timestamp": timestamp
    }

    # Print workflow summary
    print(f"{'='*80}")
    print("WORKFLOW RESULT")
    print(f"{'='*80}")
    print(f"Status: {result['status'].upper()}")
    print(f"Total Requirements: {result['total_requirements']}")
    print(f"Total Signals: {result['total_signals']}")
    print(f"Total Features: {result['total_features']}")
    if result["errors"]:
        print(f"Errors: {result['errors']}")
    print(f"{'='*80}\n")

    return json.dumps(result, indent=2)
