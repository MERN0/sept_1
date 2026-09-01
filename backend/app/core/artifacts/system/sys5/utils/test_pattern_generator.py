"""
Test Pattern Generator - Creates test cases from requirements and verification criteria

Uses LLM (via LangChain) to generate test patterns based on requirement descriptions
"""

import json
import re
import os
import sys
from typing import Dict, Any, List, Optional

# Setup path for imports
_workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../.."))
if _workspace_root not in sys.path:
    sys.path.insert(0, _workspace_root)

try:
    from ..config import get_llm  # type: ignore
except ImportError:
    from backend.app.core.artifacts.system.sys5.config import get_llm


def extract_verification_criteria(row_data: Dict[str, Any]) -> Optional[str]:
    """
    Extract verification criteria from requirement row

    Searches for verification criteria column (case-insensitive)
    Handles multiple spaces, newlines, and formatting issues

    Args:
        row_data: Row data dictionary from Excel

    Returns:
        Cleaned verification criteria or None
    """
    for key, value in row_data.items():
        # Check if column name contains "verification" or "criteria"
        if any(term in str(key).lower() for term in ["verification", "criteria", "test"]):
            if value is not None:
                # Clean up whitespace and newlines
                criteria = str(value).strip()
                criteria = re.sub(r'\s+', ' ', criteria)  # Multiple spaces to single
                criteria = re.sub(r'\n+', ' ', criteria)  # Newlines to space
                if criteria:
                    return criteria

    return None


def prepare_test_pattern_prompt(
    req_description: str,
    verification_criteria: str,
    reference_format: str
) -> str:
    """
    Prepare prompt for LLM to generate test patterns

    Args:
        req_description: Requirement description
        verification_criteria: Verification criteria from requirement
        reference_format: Reference format/structure for test cases

    Returns:
        Formatted prompt for LLM
    """
    prompt = f"""
Given the following requirement and verification criteria, generate comprehensive test patterns.

REQUIREMENT DESCRIPTION:
{req_description}

VERIFICATION CRITERIA:
{verification_criteria}

REFERENCE TEST CASE FORMAT:
{reference_format}

TASK:
1. Analyze the requirement and verification criteria
2. Identify test factors and their options
3. Generate test case combinations considering:
   - Preconditions (truck size, discharge capacity, power control mode, direction switch, load capacity)
   - Actions (option set, slope angle)
   - Coverage of all meaningful combinations
   - Avoid redundant test cases

OUTPUT FORMAT (JSON):
{{
  "test_cases": [
    {{
      "test_case_no": 1,
      "preconditions": {{
        "truck_size": "1t",
        "discharge_capacity": "25%",
        "power_control_mode": "P",
        "direction_switch": "FWD",
        "load_capacity": "NL"
      }},
      "actions": {{
        "option_set": "Enabled",
        "slope_angle": "0 deg"
      }},
      "expected_result": "Description of expected behavior"
    }}
  ],
  "factors": {{
    "truck_size": ["1t", "3t"],
    "discharge_capacity": ["25%", "50%", "100%"],
    "power_control_mode": ["P", "S", "E"],
    "direction_switch": ["FWD", "BWD"],
    "load_capacity": ["NL", "FL"],
    "slope_angle": ["0 deg", "3 deg"]
  }},
  "summary": "Brief description of test coverage"
}}

Generate only valid JSON, no extra text.
"""
    return prompt


def parse_test_patterns_json(json_response: str) -> Dict[str, Any]:
    """
    Parse test patterns from LLM JSON response

    Args:
        json_response: JSON response from LLM

    Returns:
        Parsed test patterns dictionary
    """
    try:
        # Extract JSON from response (may contain extra text)
        json_match = re.search(r'\{.*\}', json_response, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            return json.loads(json_str)
    except json.JSONDecodeError:
        pass

    # Return empty structure if parsing fails
    return {
        "test_cases": [],
        "factors": {},
        "summary": "Failed to generate test patterns"
    }


def format_test_patterns_for_excel(test_patterns: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Format test patterns for Excel output

    Converts test pattern structure to flat format for Excel rows

    Args:
        test_patterns: Test patterns dictionary from LLM

    Returns:
        List of rows for Excel output
    """
    rows = []

    # Add header
    rows.append({
        "Type": "HEADER",
        "Test Case No": "Test Case No",
        "Preconditions - Truck Size": "Truck Size",
        "Preconditions - Discharge Capacity": "Discharge %",
        "Preconditions - Power Control Mode": "Power Mode",
        "Preconditions - Direction Switch": "Direction",
        "Preconditions - Load Capacity": "Load Cap",
        "Actions - Option Set": "Option Set",
        "Actions - Slope Angle": "Slope Angle",
        "Expected Result": "Expected Result"
    })

    # Add test cases
    if "test_cases" in test_patterns:
        for tc in test_patterns["test_cases"]:
            row = {
                "Type": "TEST_CASE",
                "Test Case No": tc.get("test_case_no", ""),
                "Preconditions - Truck Size": tc.get("preconditions", {}).get("truck_size", ""),
                "Preconditions - Discharge Capacity": tc.get("preconditions", {}).get("discharge_capacity", ""),
                "Preconditions - Power Control Mode": tc.get("preconditions", {}).get("power_control_mode", ""),
                "Preconditions - Direction Switch": tc.get("preconditions", {}).get("direction_switch", ""),
                "Preconditions - Load Capacity": tc.get("preconditions", {}).get("load_capacity", ""),
                "Actions - Option Set": tc.get("actions", {}).get("option_set", ""),
                "Actions - Slope Angle": tc.get("actions", {}).get("slope_angle", ""),
                "Expected Result": tc.get("expected_result", "")
            }
            rows.append(row)

    # Add factors summary
    rows.append({
        "Type": "SEPARATOR",
        "Test Case No": "",
        "Preconditions - Truck Size": "",
        "Preconditions - Discharge Capacity": "",
        "Preconditions - Power Control Mode": "",
        "Preconditions - Direction Switch": "",
        "Preconditions - Load Capacity": "",
        "Actions - Option Set": "",
        "Actions - Slope Angle": "",
        "Expected Result": ""
    })

    rows.append({
        "Type": "FACTORS",
        "Test Case No": "FACTORS",
        "Preconditions - Truck Size": "",
        "Preconditions - Discharge Capacity": "",
        "Preconditions - Power Control Mode": "",
        "Preconditions - Direction Switch": "",
        "Preconditions - Load Capacity": "",
        "Actions - Option Set": "",
        "Actions - Slope Angle": "",
        "Expected Result": ""
    })

    # Add factor details
    if "factors" in test_patterns:
        for factor, options in test_patterns["factors"].items():
            row = {
                "Type": "FACTOR",
                "Test Case No": factor,
                "Preconditions - Truck Size": "",
                "Preconditions - Discharge Capacity": "",
                "Preconditions - Power Control Mode": "",
                "Preconditions - Direction Switch": "",
                "Preconditions - Load Capacity": "",
                "Actions - Option Set": "",
                "Actions - Slope Angle": "",
                "Expected Result": ", ".join(str(opt) for opt in options)
            }
            rows.append(row)

    # Add summary
    rows.append({
        "Type": "SUMMARY",
        "Test Case No": test_patterns.get("summary", ""),
        "Preconditions - Truck Size": "",
        "Preconditions - Discharge Capacity": "",
        "Preconditions - Power Control Mode": "",
        "Preconditions - Direction Switch": "",
        "Preconditions - Load Capacity": "",
        "Actions - Option Set": "",
        "Actions - Slope Angle": "",
        "Expected Result": ""
    })

    return rows
