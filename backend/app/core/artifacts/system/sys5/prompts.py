"""
Single place for all Generate / Validate / Correct prompts (Nodes 7-9).

The command grammar and mandatory rules below are transcribed from a
workbook analysis report (docx, see conversation) of a real System
Qualification Test Specification sheet - they are the feature-agnostic
authoring rules that report derived as generalizable across requirements,
not the Slope-Assist-specific step sequence or variant lookup table it also
documented (those are DATA - e.g. Model_Input_Mapping/Tolerances rows - and
must come from feature_bundle at runtime, never be hardcoded here).
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
      "step_text": "string, e.g. 'Set MDL_SEN_Load' or 'Wait' or 'Lib_Ramp MDL_SEN_Accelerator_Pedal(Start=0,Stop=30,Step=1,Time=100)'",
      "parameter_settings": "number or enum value being set, or delay duration - never combined with its unit",
      "units": "unit for parameter_settings, or null",
      "expected_value": "assertion value/condition for Verify/Wait_Until, e.g. '1' or '>5' - or null",
      "units2": "unit for expected_value, or null",
      "whether_execute": "Yes",
      "remarks": "string, REQUIRED for every step - never null or empty - a short remark explaining what this step does or why it's needed"
    }
  ]
}"""

# Command grammar + mandatory rules, from the analysis report. Kept as one
# literal block so both Generate and Validate check the exact same rules.
_COMMAND_GRAMMAR_RULES = """COMMAND GRAMMAR (use ONLY these keywords - nothing else):
- Test_Start: marks test case start. No target, no value.
- End_of_test: marks test case end. No target, no value.
- Set <signal>: assign/configure a value. Numeric or enum value goes in parameter_settings,
  its unit (if any) goes in units. Never write "100ms" as one string - keep value and unit separate.
- Verify <signal>: exact-value or threshold assertion. The assertion goes in expected_value
  (a bare value like "1"/"E", or an operator+value like ">5" or "<=0"), its unit in units2.
- Wait: fixed time delay only, no signal target. Duration in parameter_settings, unit in units.
  Use ONLY for a plain time-based delay - never when continuation depends on a signal's state.
- Wait_Until <signal>: block until a signal condition holds (operator+value in expected_value,
  unit in units2). Use when the next step depends on actual system behavior, not a fixed time.
- Compound <compound_name>: invoke a reusable predefined sequence. compound_name MUST be copied
  verbatim from the compound_commands list given below - never invent or paraphrase one.
- Lib_<name>(<args>): call a library function. The function name and its exact argument names/
  order/units MUST come from the matching entry in the library_list given below - read the
  argument contract from that entry's own description, never assume units it doesn't state.

MANDATORY RULES:
1. Use only commands, signals, compounds, and library functions that appear in the data given
   below. Never invent a signal, unit, expected value, map value, tolerance, compound name, or
   library argument - if something needed isn't present in the data, state that in "remarks"
   rather than making it up.
1a. Where to find the correct name for a Set/Verify/Wait_Until target - this differs by which
    part of the data below it comes from, do not apply one rule to all of them:
    - feature_details: each entry carries both "signal_name" (the raw CAN/HIL wiring identifier,
      lookup-only) and "command_name" (the resolved name to actually use). Use command_name, not
      signal_name, ONLY for names sourced from feature_details.
    - model_input_mapping: there is no separate command_name here - the dict KEY itself (e.g.
      "MDL_SWH_DIR_STATE") IS the correct name to use directly. Do not reject or second-guess a
      model_input_mapping key for "not being a command_name" - that requirement is specific to
      feature_details and does not apply here.
    - compound_commands / library_list: the KEY, or the compound/library name found inside that
      entry's own row data, is the correct name.
    - tolerances: the KEY (e.g. "Config_Tol_Spd") is the correct name.
2. Keep numeric values and their units in separate fields, always.
3. Resolve any scenario-parameter-to-signal/model-input dependency (e.g. a size/mode/direction
   factor implying a particular model input, map, or load value) using the model_input_mapping
   data given below - do not infer such a mapping yourself if it isn't explicitly present there.
3a. Each model_input_mapping row has a human-readable "test_case_input" AND a separate internal
    numeric "model_input" code for that same row. This rule only applies to a genuine enum/state
    signal - one whose test_case_input values are all non-numeric labels (e.g. "FWD"/"BWD"/
    "NEUTRAL", "P"/"S"/"E", "NL"/"FL", "ON"/"OFF"): for those, parameter_settings MUST be the
    test_case_input label, never the numeric model_input code, and never placed in "units"
    instead (units is only for a physical unit like ms/kg/deg/km/h - an enum label is never a
    unit). For a continuous/analog signal whose test_case_input values are themselves numeric
    (e.g. a slope angle row showing "0" or "3", a speed or load value) those rows are only
    EXAMPLES, not the full set of legal values - use whatever numeric value the requirement/test
    pattern actually calls for, not restricted to the example numbers shown.
4. Never invent a tolerance or acceptance range. Use only an exact expected value, a comparison
   operator, or a tolerance that appears in the tolerances data given below.
5. Prefer the current requirement/test pattern's own values over any stale remark text if they
   conflict.
6. Steps must be ordered PRECONDITION, then ACTION, then POSTCONDITION. The FIRST step of every
   test case MUST be Test_Start and the LAST step MUST be End_of_test - never omit either one,
   even for a short test case with only one or two other steps.
7. "remarks" is REQUIRED on every single step - never null, never an empty string. State briefly
   what the step does or why it's there (e.g. "sets baseline speed before applying the ramp",
   "confirms motor returns to idle after the test")."""


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

    return f"""You write automotive HIL system qualification test cases in a strict keyword-driven
grammar. A test case establishes a deterministic PRECONDITION state, applies the ACTION under
test, verifies the expected behavior, then returns to a safe POSTCONDITION and ends.

{_COMMAND_GRAMMAR_RULES}

REQUIREMENT:
{json.dumps(requirement, indent=2, default=str)}

TEST PATTERN (preconditions/actions this test case must cover):
{json.dumps(test_pattern, indent=2, default=str)}

KNOWN DATA - signals (feature_details), model_input_mapping, tolerances, compound_commands,
library_list (use ONLY names/values that appear here):
{json.dumps(feature_bundle, indent=2, default=str)}

Write ONE test case covering this test pattern. Output ONLY valid JSON matching this shape,
no extra text:
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
    feature_bundle = generate_input.get("feature_bundle", {})

    return f"""Check this generated test case against the rules it was written under.

{_COMMAND_GRAMMAR_RULES}

TEST CASE:
{json.dumps(generated_output, indent=2, default=str)}

REQUIREMENT + TEST PATTERN IT SHOULD COVER:
{json.dumps({"requirement": generate_input.get("requirement"), "test_pattern": generate_input.get("test_pattern")}, indent=2, default=str)}

KNOWN DATA (every step must reference only names/values that appear here):
{json.dumps(feature_bundle, indent=2, default=str)}

Check specifically: (1) every signal/compound/library name used in a step actually appears in
the known data above - flag anything that looks invented, (2) every step's keyword is one of
Test_Start/End_of_test/Set/Verify/Wait/Wait_Until/Compound/Lib_*, (3) numeric values and units
are in separate fields, never concatenated, (4) no tolerance or expected value was invented
beyond what the known data supports, (5) steps are ordered PRECONDITION then ACTION then
POSTCONDITION, (6) the test pattern's preconditions/actions/expected_result are all covered,
(7) for a Set step whose signal is in model_input_mapping, parameter_settings holds the
human-readable test_case_input value (e.g. "FWD", "P", "NL", "ON") - flag it if the numeric
model_input code was used instead, or if that value was placed in "units" instead of
parameter_settings, (8) every step has a non-empty "remarks" - flag any step where it's missing,
null, or blank.

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
    feature_bundle = generate_input.get("feature_bundle", {})

    return f"""Fix this test case so it no longer has the issues listed below, without breaking
anything that was already correct.

{_COMMAND_GRAMMAR_RULES}

TEST CASE:
{json.dumps(generated_output, indent=2, default=str)}

ISSUES TO FIX:
{json.dumps(validation_result.get("issues", []), indent=2, default=str)}

KNOWN DATA (every step must reference only names/values that appear here):
{json.dumps(feature_bundle, indent=2, default=str)}

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
