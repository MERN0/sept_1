"""
Deterministic grounding check for generated test steps.

Per the workbook analysis report: the model must never invent a signal,
compound command, or library function name. Rather than trust the LLM's own
Validate answer for this, cross-check every step's referenced name against
the actual names extracted in Nodes 2-6 (feature_details/compound_commands/
library_list) in code - this catches a hallucinated name even if the LLM's
own semantic validation misses it.

Recognizes the report's command grammar:
    Test_Start | End_of_test | Set <name> | Verify <name> | Wait
    | Wait_Until <name> | Compound <name> | Lib_<name>(...)
"""

import re
from typing import Any, Dict, List

_NO_TARGET_KEYWORDS = {"test_start", "end_of_test", "wait"}

# Grammar keywords and generic type/category labels that show up as raw cell
# values in compound_commands/library_list rows (e.g. a "Type" column
# containing "Compound" or "lib") - these are too short/generic to serve as
# a known NAME and would falsely substring-match almost anything (e.g. the
# 3-char value "lib" matching a hallucinated "Lib_TotallyMadeUp" keyword).
_GENERIC_VALUES = {
    "test_start", "end_of_test", "set", "verify", "wait", "wait_until",
    "compound", "lib", "yes", "no", "true", "false", "none", "n/a", "na", "-",
}
_MIN_ROW_VALUE_LEN = 4

# Matches "Set X", "Verify X", "Wait_Until X", "Compound X", or "Lib_Foo(..."
_STEP_PATTERN = re.compile(
    r'^(?P<keyword>Test_Start|End_of_test|Set|Verify|Wait_Until|Wait|Compound|Lib_\w+)'
    r'(?:[\s_]+(?P<target>[^\s(]+))?',
    re.IGNORECASE
)


def _normalize(name: str) -> str:
    return str(name).strip().lower().replace('_', '').replace(' ', '')


def _is_numeric(value: str) -> bool:
    try:
        float(value)
        return True
    except (TypeError, ValueError):
        return False


def _add_row_values(known: Dict[str, str], entries: Dict[str, Any]) -> None:
    """
    Add both the dict key AND every string cell value inside each entry's
    row data. Node 6 keys compound_commands/library_list off the sheet's
    first column (matching Node 4's App Parameter convention), but that
    column is often a serial number in the real sheet (e.g. key
    "compound_commands_36"), not the actual compound/library name - the
    real name text lives inside the row's own values instead. These rows
    are already narrowed down by Node 6's two-stage filter, so treating
    every text value in them as a legitimate known name is safe.
    """
    for key, entry in entries.items():
        known[_normalize(key)] = key
        if not isinstance(entry, dict):
            continue
        for value in entry.values():
            if not isinstance(value, str):
                continue
            cleaned = value.strip()
            normalized = _normalize(cleaned)
            if (
                cleaned
                and not cleaned.isdigit()
                and len(normalized) >= _MIN_ROW_VALUE_LEN
                and normalized not in _GENERIC_VALUES
            ):
                known[normalized] = cleaned


def collect_known_names(feature_bundle: Dict[str, Any]) -> Dict[str, str]:
    """
    Build {normalized_name: original_name} from every name-bearing source in
    the feature bundle a Generate/Validate call was given: feature_details
    command names, model_input_mapping keys (Signal), compound_commands
    keys + row values, library_list keys + row values, and tolerances keys
    (Config_Tol_* references inside Verify/Set steps).

    Uses command_name, not signal_name/logical_signal_name - Signal Name is
    only the raw CAN/HIL identifier used to look up the row in Command List
    (Node 2/3); command_name is the resolved name that actually belongs in
    a generated Set/Verify step, so grounding must check against that.
    model_input_mapping is keyed directly by Signal (Node 5), so those keys
    ARE the real name and are used as-is.
    """
    known = {}

    for entry in (feature_bundle.get("feature_details") or {}).values():
        if not isinstance(entry, dict):
            continue
        name = entry.get("command_name")
        if name:
            known[_normalize(name)] = str(name)

    for key in (feature_bundle.get("model_input_mapping") or {}).keys():
        known[_normalize(key)] = key

    _add_row_values(known, feature_bundle.get("compound_commands") or {})
    _add_row_values(known, feature_bundle.get("library_list") or {})

    for key in (feature_bundle.get("tolerances") or {}).keys():
        known[_normalize(key)] = key

    return known


def check_step_grounding(steps: List[Dict[str, Any]], feature_bundle: Dict[str, Any]) -> List[str]:
    """
    Return a list of human-readable issues for any step whose keyword
    requires a target name that doesn't match (substring, either direction,
    same normalization used throughout this pipeline) anything in the known
    pool. A keyword outside the recognized grammar is also flagged.
    """
    known_names = collect_known_names(feature_bundle)
    issues = []

    for step in steps:
        step_text = str(step.get("step_text", "")).strip()
        if not step_text:
            issues.append(f"Step {step.get('step_no', '?')}: empty step_text")
            continue

        match = _STEP_PATTERN.match(step_text)
        if not match:
            issues.append(f"Step {step.get('step_no', '?')}: '{step_text}' does not match the known command grammar "
                           f"(Test_Start/End_of_test/Set/Verify/Wait/Wait_Until/Compound/Lib_*)")
            continue

        keyword = match.group("keyword")
        target = match.group("target")

        if keyword.lower() in _NO_TARGET_KEYWORDS:
            continue  # Test_Start/End_of_test/Wait need no target name

        # Lib_* : the keyword itself is the library name and must be grounded
        # against library_list - a trailing signal argument (e.g. "Lib_Ramp
        # MDL_SEN_..._Pedal(...)") is optional and checked separately below,
        # a bare call like "Lib_OptionSet" with nothing after it is valid on
        # its own and is NOT a missing-target error.
        if keyword.lower().startswith("lib_"):
            normalized_keyword = _normalize(keyword)
            if not any(normalized_keyword in known or known in normalized_keyword for known in known_names):
                issues.append(
                    f"Step {step.get('step_no', '?')}: library '{keyword}' (from '{step_text}') was not found in "
                    f"the known signals/compounds/library calls/tolerances given to Generate - possible hallucination"
                )
            if not target:
                continue

        elif not target:
            issues.append(f"Step {step.get('step_no', '?')}: '{step_text}' ({keyword}) is missing a target name")
            continue

        normalized_target = _normalize(target)
        matched = any(
            normalized_target in known or known in normalized_target
            for known in known_names
        )
        if not matched:
            issues.append(
                f"Step {step.get('step_no', '?')}: '{target}' (from '{step_text}') was not found in the "
                f"known signals/compounds/library calls/tolerances given to Generate - possible hallucination"
            )

    return issues


def check_enum_parameter_usage(steps: List[Dict[str, Any]], feature_bundle: Dict[str, Any]) -> List[str]:
    """
    For a Set step whose signal is in model_input_mapping, verify
    parameter_settings holds the human-readable test_case_input value
    (e.g. "FWD", "P", "NL", "ON") for that row, not the internal numeric
    model_input code (e.g. 1, 2, 3) - and that the value wasn't misplaced
    into "units" instead of parameter_settings. Same "trust code over
    prompt wording" rationale as check_step_grounding: the Generate/Validate
    prompt states this rule too, but a deterministic check catches it even
    when the LLM doesn't follow it.

    Only applies to genuine enum/state signals - a signal is treated as
    enum-type only if EVERY test_case_input value seen for it is
    non-numeric (e.g. FWD/BWD/NEUTRAL, P/S/E, ON/OFF). A signal whose
    test_case_input values are themselves numeric (e.g. slope angle "0"/
    "3", a speed or load value) is a continuous/analog signal: model_input_
    mapping only lists a couple of *example* rows for it, not an exhaustive
    set of legal values, so any numeric parameter_settings is accepted
    without restriction - rejecting a value just for not literally matching
    one of those examples would wrongly reject legitimate numbers like a
    threshold speed or an arbitrary slope angle.
    """
    model_input_mapping = feature_bundle.get("model_input_mapping") or {}
    normalized_mapping = []
    for signal, variants in model_input_mapping.items():
        if isinstance(variants, list):
            normalized_mapping.append((_normalize(signal), signal, variants))

    issues = []
    for step in steps:
        step_text = str(step.get("step_text", "")).strip()
        match = _STEP_PATTERN.match(step_text)
        if not match or match.group("keyword").lower() != "set":
            continue
        target = match.group("target")
        if not target:
            continue
        normalized_target = _normalize(target)

        variants = None
        matched_signal = None
        for normalized_signal, signal, v in normalized_mapping:
            if normalized_target in normalized_signal or normalized_signal in normalized_target:
                variants, matched_signal = v, signal
                break
        if not variants:
            continue

        test_case_inputs = {
            str(v["test_case_input"]).strip() for v in variants
            if isinstance(v, dict) and v.get("test_case_input") is not None
        }
        model_input_codes = {
            str(v["model_input"]).strip() for v in variants
            if isinstance(v, dict) and v.get("model_input") is not None
        }

        # Continuous/analog signal (slope angle, speed, load, etc.) - the
        # example test_case_input values aren't an exhaustive legal set, so
        # don't restrict parameter_settings to only those examples.
        if test_case_inputs and any(_is_numeric(v) for v in test_case_inputs):
            continue

        param = step.get("parameter_settings")
        units = step.get("units")
        param_str = None if param is None else str(param).strip()
        units_str = None if units is None else str(units).strip()

        if param_str and param_str in model_input_codes and param_str not in test_case_inputs:
            issues.append(
                f"Step {step.get('step_no', '?')}: '{step_text}' has parameter_settings='{param_str}', "
                f"which is the internal model_input code for {matched_signal} - use the human-readable "
                f"test_case_input value instead (one of {sorted(test_case_inputs)})"
            )
        elif not param_str and units_str and units_str in test_case_inputs:
            issues.append(
                f"Step {step.get('step_no', '?')}: '{step_text}' has the enum value '{units_str}' in units "
                f"instead of parameter_settings for {matched_signal}"
            )

    return issues


def check_remarks_present(steps: List[Dict[str, Any]]) -> List[str]:
    """
    Every step must carry a non-empty "remarks" - it is not an optional
    field. schema.py's TestStep keeps remarks Optional so a response missing
    it still parses (a full generate_failed on a single missing remark would
    be too disruptive), and this deterministic check instead flags any step
    without one so the Validate -> Correct loop fills it in, the same
    "trust code over prompt wording" pattern used for grounding and enum
    checks.
    """
    issues = []
    for step in steps:
        remarks = step.get("remarks")
        if remarks is None or not str(remarks).strip():
            issues.append(
                f"Step {step.get('step_no', '?')}: '{step.get('step_text', '')}' is missing remarks - "
                f"every step must include a remark explaining what it does or why"
            )
    return issues
