"""Node 1: Requirements Extraction from Excel"""

import json
import os
import sys
import pandas as pd
from typing import Dict, Any

# Setup path for imports
_workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../.."))
if _workspace_root not in sys.path:
    sys.path.insert(0, _workspace_root)

try:
    from ..state import SYS5State  # type: ignore
    from ..utils import resolve_path, ensure_directory_exists  # type: ignore
    from ..config import is_functional_requirement, KEYWORD_MATCHING_CONFIG, FUNCTIONAL_REQ_KEYWORDS  # type: ignore
except ImportError:
    from backend.app.core.artifacts.system.sys5.state import SYS5State
    from backend.app.core.artifacts.system.sys5.utils import resolve_path, ensure_directory_exists
    from backend.app.core.artifacts.system.sys5.config import is_functional_requirement, KEYWORD_MATCHING_CONFIG, FUNCTIONAL_REQ_KEYWORDS


class Node1ExtractRequirements:
    """
    Node 1: Extract functional requirements from Excel file

    Process:
    1. Resolve input/output paths (relative or absolute)
    2. Read Excel file
    3. Scan for rows containing "Functional requirements"
    4. Extract matching rows with all data
    5. Save results to JSON file
    """

    @staticmethod
    def execute(state: SYS5State) -> SYS5State:
        """
        Execute Node 1 - Requirements Extraction

        Args:
            state: Current workflow state

        Returns:
            Updated state with extracted requirements
        """
        print(f"\n{'='*80}")
        print("NODE 1: REQUIREMENTS EXTRACTION")
        print(f"{'='*80}\n")

        config = state["config"]
        requirements = []
        errors = []

        # Extract configuration
        input_folder = config.get("input_folder_path")
        output_dir = config.get("output_dir")
        req_filename = config.get("req_filename", "reqs_to_use.xlsx")
        req_sheet_name = config.get("req_sheet_name", "005")

        # Resolve paths
        abs_input_folder = resolve_path(input_folder)
        abs_output_dir = resolve_path(output_dir)
        abs_excel_path = os.path.join(abs_input_folder, req_filename)

        # Log path information
        print(f"[LOG] Input folder (relative): {input_folder}")
        print(f"[LOG] Input folder (absolute): {abs_input_folder}")
        print(f"[LOG] Excel file path: {abs_excel_path}")
        print(f"[LOG] Sheet name: {req_sheet_name}")
        print(f"[LOG] Output dir (absolute): {abs_output_dir}\n")

        try:
            # Validate input file exists
            if not os.path.exists(abs_excel_path):
                error_msg = f"File not found: {abs_excel_path}"
                print(f"[ERROR] {error_msg}\n")
                errors.append(error_msg)
                state["errors"] = errors
                return state

            # Read Excel file
            print(f"[LOG] Reading Excel file...\n")
            df = pd.read_excel(abs_excel_path, sheet_name=req_sheet_name)

            print(f"[LOG] Total rows in sheet: {len(df)}")
            print(f"[LOG] Columns: {list(df.columns)}\n")

            # Extract functional requirements
            print(f"[LOG] Scanning rows using configured keywords...")
            print(f"[LOG] Keywords: {FUNCTIONAL_REQ_KEYWORDS}")
            print(f"[LOG] Matching: case_sensitive={KEYWORD_MATCHING_CONFIG['case_sensitive']}, "
                  f"exact_match={KEYWORD_MATCHING_CONFIG['exact_match']}, "
                  f"word_boundaries={KEYWORD_MATCHING_CONFIG['word_boundaries']}\n")

            for idx, row in df.iterrows():
                is_functional = False
                matched_column = None

                # Check each cell in row
                for col_name, cell_value in row.items():
                    if pd.isna(cell_value):
                        continue

                    # Use config-based matching
                    if is_functional_requirement(str(cell_value)):
                        is_functional = True
                        matched_column = col_name
                        print(f"[LOG] Row {idx}: MATCH in column '{col_name}' = '{cell_value}'")
                        break

                # Extract matching row
                if is_functional:
                    row_dict = row.to_dict()
                    row_dict = {k: (None if pd.isna(v) else v) for k, v in row_dict.items()}

                    requirement = {
                        "row_index": int(idx),
                        "data": row_dict,
                        "type": "Functional"
                    }
                    requirements.append(requirement)
                    print(f"      → Extracted: {row_dict}\n")

            # Summary
            print(f"\n[SUMMARY] Total functional requirements extracted: {len(requirements)}\n")

            # Create output directory
            ensure_directory_exists(abs_output_dir)
            print(f"[LOG] Output directory verified: {abs_output_dir}\n")

            # Save to JSON
            timestamp = state["timestamp"]
            json_file = os.path.join(abs_output_dir, f"requirements_{timestamp}.json")

            output_data = {
                "metadata": {
                    "total_requirements": len(requirements),
                    "timestamp": timestamp,
                    "input_file": abs_excel_path,
                    "sheet_name": req_sheet_name,
                    "output_file": json_file
                },
                "requirements": requirements
            }

            with open(json_file, 'w') as f:
                json.dump(output_data, f, indent=2)

            print(f"[SUCCESS] Requirements saved to: {json_file}")
            print(f"[LOG] File size: {os.path.getsize(json_file)} bytes\n")

        except Exception as e:
            error_msg = f"Error during extraction: {str(e)}"
            print(f"[ERROR] {error_msg}\n")
            errors.append(error_msg)

        # Update state
        state["requirements"] = requirements
        state["errors"] = errors

        # Print completion status
        print(f"{'='*80}")
        print(f"NODE 1 COMPLETED")
        print(f"  Status: {'SUCCESS' if not errors else 'FAILED'}")
        print(f"  Requirements extracted: {len(requirements)}")
        print(f"  Errors: {len(errors)}")
        print(f"{'='*80}\n")

        return state
