"""
SYS5 Entry Point

Main entry point for SYS5 artifact generation
Supports both module imports and direct execution
"""

import os
import sys

# Setup path resolution
_workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
if _workspace_root not in sys.path:
    sys.path.insert(0, _workspace_root)

try:
    # Relative import works when module is part of package
    from .main import run_workflow  # type: ignore
except ImportError:
    # Absolute import works when script is run directly
    from backend.app.core.artifacts.system.sys5.main import run_workflow


def generate(config: dict) -> str:
    """
    Entry point for SYS5 - Requirements Extraction

    Args:
        config: Configuration dictionary with:
            - project_name: Project name
            - input_folder_path: Path to input files (relative or absolute)
            - output_dir: Output directory (relative or absolute)
            - req_filename: Excel file name
            - req_sheet_name: Sheet name in Excel
            - version: Version number (optional)

    Returns:
        JSON string with workflow results and extracted requirements
    """
    return run_workflow(config)


# Allow direct execution
if __name__ == "__main__":
    config = {
        "project_name": "tmhc_demo",
        "username": "test@tataelxsi.co.in",
        "version": "V1.0",
        "domain": "automotive",
        "artifact": "SYS5",
        "model": "llm-1-gpt-oss-120b",
        "input_folder_path": "files/test@tataelxsi.co.in/swe6_5/V1.0/SWE6/input",
        "output_dir": "files/test@tataelxsi.co.in/swe6_5/V1.0/SWE6/output",
        "req_filename": "reqs_to_use.xlsx",
        "req_sheet_name": "005",
        "system_requirements_file": "files/test@tataelxsi.co.in/swe6_5/V1.0/SWE6/input/System Requirements.xlsx",
        "command_list_file": "files/test@tataelxsi.co.in/swe6_5/V1.0/SWE6/input/Command List.xlsx",
    }
    result = generate(config)
    print("\n" + "="*80)
    print("GENERATION RESULT:")
    print("="*80)
    print(result)
