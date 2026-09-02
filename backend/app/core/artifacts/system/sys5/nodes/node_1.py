"""Node 1: Requirements Extraction from Excel"""

import json
import os
import sys
from typing import Dict, Any
import pandas as pd

# Setup path for imports
_workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../.."))
if _workspace_root not in sys.path:
    sys.path.insert(0, _workspace_root)

try:
    from ..state import SYS5State  # type: ignore
    from ..utils import (resolve_path, ensure_directory_exists, extract_verification_criteria,  # type: ignore
                         prepare_test_pattern_prompt, parse_test_patterns_json)
    from ..config import is_functional_requirement, KEYWORD_MATCHING_CONFIG, FUNCTIONAL_REQ_KEYWORDS, get_llm  # type: ignore
except ImportError:
    from backend.app.core.artifacts.system.sys5.state import SYS5State
    from backend.app.core.artifacts.system.sys5.utils import (
        resolve_path, ensure_directory_exists, extract_verification_criteria,
        prepare_test_pattern_prompt, parse_test_patterns_json
    )
    from backend.app.core.artifacts.system.sys5.config import (
        is_functional_requirement, KEYWORD_MATCHING_CONFIG, FUNCTIONAL_REQ_KEYWORDS, get_llm
    )


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
        test_patterns_data = {}

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

                    # Get requirement ID from data (look for common ID column names)
                    req_id = None
                    for id_col in ["REQ_ID", "Req_ID", "req_id", "ID", "Requirement ID"]:
                        if id_col in row_dict and row_dict[id_col]:
                            req_id = str(row_dict[id_col])
                            break

                    if not req_id:
                        req_id = f"REQ_{idx}"

                    requirement = {
                        "req_id": req_id,
                        "row_index": int(idx),
                        "data": row_dict,
                        "type": "Functional"
                    }
                    requirements.append(requirement)
                    print(f"      → Extracted: {req_id}\n")

            # Summary
            print(f"\n[SUMMARY] Total functional requirements extracted: {len(requirements)}\n")

            # Extract verification criteria from each requirement
            print(f"\n[LOG] Extracting verification criteria from requirements...\n")
            for req in requirements:
                criteria = extract_verification_criteria(req["data"])
                req["verification_criteria"] = criteria
                if criteria:
                    print(f"[LOG] {req['req_id']}: Found criteria: {criteria[:100]}...\n")

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
                json.dump(output_data, f, indent=2, default=str)

            print(f"[SUCCESS] Requirements saved to: {json_file}")
            print(f"[LOG] File size: {os.path.getsize(json_file)} bytes\n")

            # Generate test patterns for requirements with verification criteria
            print(f"\n[LOG] Generating test patterns using LLM...\n")
            reference_format = """{
  "test_cases": [
    {
      "test_case_no": 1,
      "preconditions": {
        "truck_size": "1t",
        "discharge_capacity": "25%",
        "power_control_mode": "P",
        "direction_switch": "FWD",
        "load_capacity": "NL"
      },
      "actions": {
        "option_set": "Enabled",
        "slope_angle": "0 deg"
      },
      "expected_result": "Description"
    }
  ]
}"""

            for req in requirements:
                if req.get("verification_criteria"):
                    try:
                        req_id = req["req_id"]
                        req_desc = req["data"].get("Description", "")
                        criteria = req["verification_criteria"]

                        print(f"[LOG] Generating test pattern for {req_id}...")

                        # Prepare prompt for LLM
                        prompt = prepare_test_pattern_prompt(req_desc, criteria, reference_format)

                        # Call LLM for test pattern generation using configured model
                        llm = get_llm()
                        print(f"[LOG] Calling LLM: {llm.model_name}...")

                        # Invoke LLM with the prompt
                        response = llm.invoke(prompt)

                        # Parse response - LangChain returns content directly
                        test_pattern_json = response.content
                        test_patterns = parse_test_patterns_json(test_pattern_json)
                        test_patterns_data[req_id] = test_patterns

                        print(f"[LOG] Generated {len(test_patterns.get('test_cases', []))} test cases for {req_id}\n")

                    except Exception as lm_error:
                        print(f"[WARNING] Failed to generate test patterns for {req_id}: {str(lm_error)}\n")

            # Test patterns are written into the "Test Pattern" sheet of the
            # single consolidated output workbook (main.py's
            # write_test_cases_workbook) - no separate test_patterns_*.xlsx
            # file is written here anymore.

        except Exception as e:
            error_msg = f"Error during extraction: {str(e)}"
            print(f"[ERROR] {error_msg}\n")
            errors.append(error_msg)

        # Update state
        state["requirements"] = requirements
        state["test_patterns"] = test_patterns_data
        state["errors"] = errors

        # Print completion status
        print(f"{'='*80}")
        print(f"NODE 1 COMPLETED")
        print(f"  Status: {'SUCCESS' if not errors else 'FAILED'}")
        print(f"  Requirements extracted: {len(requirements)}")
        print(f"  Errors: {len(errors)}")
        print(f"{'='*80}\n")

        return state
