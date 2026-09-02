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
