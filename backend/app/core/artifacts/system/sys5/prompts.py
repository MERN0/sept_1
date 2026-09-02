"""
Single place for all Generate / Validate / Correct prompts (Nodes 7-9).

Each build_*_prompt() returns the full prompt text for its stage. Keeping
them here (rather than inline in the nodes) means tuning wording later only
touches this file.
"""

import json
import re
from typing import Any, Dict, Optional

# Output JSON shape every stage produces/consumes for the test case itself -
# must match utils/test_case_excel_writer.py's expected generated_output shape.
_TEST_CASE_JSON_SHAPE = """{
  "test_case_id": "string",
  "feature": "string",
  "variant": "string or null",
  "requirement_ids": ["string"],
  "priority": "string or null",
  "mode_of_execution": "Automated",
  "description": "string",
  "status": "clean",
  "steps": [
    {
      "step_no": 1,
      "phase": "PRECONDITION | ACTION | POSTCONDITION",
      "step_text": "string, e.g. 'Set MDL_SEN_Load' or 'Wait'",
      "parameter_settings": "string or null",
      "units": "string or null",
      "expected_value": "string or null",
      "units2": "string or null",
      "whether_execute": "Yes",
      "remarks": "string or null"
    }
  ]
}"""


def build_generate_input(
    requirement: Dict[str, Any],
    test_pattern: Dict[str, Any],
    feature_bundle: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Assemble the per-test-pattern input bundle for the Generate stage:
    the requirement, its generated test pattern, and the relevant feature
    data (feature_details/model_input_mapping/tolerances/compound_commands/
    library_list) collected in Nodes 2-6.
    """
    return {
        "requirement": requirement,
        "test_pattern": test_pattern,
        "feature_bundle": feature_bundle,
    }


def build_generate_prompt(generate_input: Dict[str, Any]) -> Optional[str]:
    requirement = generate_input.get("requirement", {})
    test_pattern = generate_input.get("test_pattern", {})
    feature_bundle = generate_input.get("feature_bundle", {})

    return f"""You write automotive HIL system qualification test cases.

REQUIREMENT:
{json.dumps(requirement, indent=2, default=str)}

TEST PATTERN (preconditions/actions to cover):
{json.dumps(test_pattern, indent=2, default=str)}

KNOWN SIGNALS, TOLERANCES, COMPOUND COMMANDS AND LIBRARY CALLS
(use ONLY names that appear here - never invent a signal/command/library name):
{json.dumps(feature_bundle, indent=2, default=str)}

Write ONE test case covering this test pattern as PRECONDITION -> ACTION -> POSTCONDITION
steps, using Set/Verify/Wait/Wait_Until/Compound_.../Lib_... step text built only from the
names given above. Output ONLY valid JSON matching this shape, no extra text:
{_TEST_CASE_JSON_SHAPE}"""


def build_validate_input(
    generate_input: Dict[str, Any],
    generated_output: Any,
) -> Dict[str, Any]:
    """Assemble the input bundle for the Validate stage."""
    return {
        "generate_input": generate_input,
        "generated_output": generated_output,
    }


def build_validate_prompt(validate_input: Dict[str, Any]) -> Optional[str]:
    generate_input = validate_input.get("generate_input", {})
    generated_output = validate_input.get("generated_output")

    known_names = generate_input.get("feature_bundle", {})

    return f"""Check this generated test case for correctness.

TEST CASE:
{json.dumps(generated_output, indent=2, default=str)}

REQUIREMENT + TEST PATTERN IT SHOULD COVER:
{json.dumps({"requirement": generate_input.get("requirement"), "test_pattern": generate_input.get("test_pattern")}, indent=2, default=str)}

KNOWN SIGNALS/TOLERANCES/COMMANDS/LIBRARY CALLS (every step must reference only these):
{json.dumps(known_names, indent=2, default=str)}

Check: (1) every signal/command/library name used in a step actually appears in the known
list above, (2) steps are ordered PRECONDITION then ACTION then POSTCONDITION, (3) the test
pattern's preconditions/actions/expected_result are all covered.

Output ONLY valid JSON, no extra text:
{{"valid": true or false, "issues": ["short description of each problem found"]}}"""


def build_correct_input(
    generate_input: Dict[str, Any],
    generated_output: Any,
    validation_result: Dict[str, Any],
) -> Dict[str, Any]:
    """Assemble the input bundle for the Correct stage."""
    return {
        "generate_input": generate_input,
        "generated_output": generated_output,
        "validation_result": validation_result,
    }


def build_correct_prompt(correct_input: Dict[str, Any]) -> Optional[str]:
    generate_input = correct_input.get("generate_input", {})
    generated_output = correct_input.get("generated_output")
    validation_result = correct_input.get("validation_result", {})

    return f"""Fix this test case so it no longer has the issues listed below.

TEST CASE:
{json.dumps(generated_output, indent=2, default=str)}

ISSUES TO FIX:
{json.dumps(validation_result.get("issues", []), indent=2, default=str)}

KNOWN SIGNALS/TOLERANCES/COMMANDS/LIBRARY CALLS (every step must reference only these):
{json.dumps(generate_input.get("feature_bundle", {}), indent=2, default=str)}

Output ONLY the corrected test case as valid JSON, same shape as the input, no extra text:
{_TEST_CASE_JSON_SHAPE}"""


def parse_json_response(response_text: str, fallback: Dict[str, Any]) -> Dict[str, Any]:
    """Extract and parse the first {...} block from an LLM response, matching
    the same tolerant approach used by test_pattern_generator.parse_test_patterns_json."""
    try:
        match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
    except json.JSONDecodeError:
        pass
    return fallback
