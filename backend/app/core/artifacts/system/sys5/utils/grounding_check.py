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

# Matches "Set X", "Verify X", "Wait_Until X", "Compound X", or "Lib_Foo(..."
_STEP_PATTERN = re.compile(
    r'^(?P<keyword>Test_Start|End_of_test|Set|Verify|Wait_Until|Wait|Compound|Lib_\w+)'
    r'(?:[\s_]+(?P<target>[^\s(]+))?',
    re.IGNORECASE
)


def _normalize(name: str) -> str:
    return str(name).strip().lower().replace('_', '').replace(' ', '')


def collect_known_names(feature_bundle: Dict[str, Any]) -> Dict[str, str]:
    """
    Build {normalized_name: original_name} from every name-bearing source in
    the feature bundle a Generate/Validate call was given: feature_details
    command names, compound_commands keys, library_list keys, and tolerances
    keys (Config_Tol_* references inside Verify/Set steps).

    Uses command_name, not signal_name/logical_signal_name - Signal Name is
    only the raw CAN/HIL identifier used to look up the row in Command List
    (Node 2/3); command_name is the resolved name that actually belongs in
    a generated Set/Verify step, so grounding must check against that.
    """
    known = {}

    for entry in (feature_bundle.get("feature_details") or {}).values():
        if not isinstance(entry, dict):
            continue
        name = entry.get("command_name")
        if name:
            known[_normalize(name)] = str(name)

    for key in (feature_bundle.get("compound_commands") or {}).keys():
        known[_normalize(key)] = key
    for key in (feature_bundle.get("library_list") or {}).keys():
        known[_normalize(key)] = key
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

        if not target:
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
