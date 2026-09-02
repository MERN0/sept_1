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
    from .utils import resolve_path, ensure_directory_exists, write_test_cases_workbook  # type: ignore
except ImportError:
    from backend.app.core.artifacts.system.sys5.state import SYS5State
    from backend.app.core.artifacts.system.sys5.graph import build_workflow
    from backend.app.core.artifacts.system.sys5.utils import (
        resolve_path, ensure_directory_exists, write_test_cases_workbook
    )


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
            - max_corrections: How many Validate -> Correct passes a test
              case may go through before Node 9 stops looping back to
              Node 8 (default 1)

    Returns:
        JSON string with workflow results
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Initialize state
    initial_state: SYS5State = {
        "config": config,
        "requirements": [],
        "test_patterns": {},
        "feature_index": {},
        "feature_details": {},
        "logical_signals": [],
        "model_config": {},
        "test_cases": {},
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
        "total_logical_signals": len(final_state["logical_signals"]),
        "total_features": len(final_state["feature_details"]),
        "requirements": final_state["requirements"],
        "test_patterns": final_state["test_patterns"],
        "feature_index": final_state["feature_index"],
        "logical_signals": final_state["logical_signals"],
        "feature_details": final_state["feature_details"],
        "model_config": final_state["model_config"],
        "test_cases": final_state["test_cases"],
        "errors": final_state["errors"],
        "timestamp": timestamp
    }

    # Write the SYS5 output workbook (Cover Page/Test Pattern/Item List/
    # Configurable Parameters/Test Cases), structure matching work_28's
    # reference xlsx_writer.py
    output_dir = config.get("output_dir")
    abs_output_dir = resolve_path(output_dir) if output_dir else None
    if abs_output_dir:
        ensure_directory_exists(abs_output_dir)
        excel_path = os.path.join(abs_output_dir, f"test_cases_{timestamp}.xlsx")
        write_test_cases_workbook(excel_path, final_state)
        print(f"[LOG] Test Cases workbook saved to: {excel_path}\n")

    # Print workflow summary
    print(f"{'='*80}")
    print("WORKFLOW RESULT")
    print(f"{'='*80}")
    print(f"Status: {result['status'].upper()}")
    print(f"Total Requirements: {result['total_requirements']}")
    print(f"Total Logical Signals: {result['total_logical_signals']}")
    print(f"Total Features: {result['total_features']}")
    print(f"Model Input Mapping (matched): {len(result['model_config'].get('model_input_mapping', {}))}")
    print(f"Tolerances (matched): {len(result['model_config'].get('tolerances', {}))}")
    print(f"Test Cases tracked: {len(result['test_cases'])}")
    if result["errors"]:
        print(f"Errors: {result['errors']}")
    print(f"{'='*80}\n")

    return json.dumps(result, indent=2, default=str)
