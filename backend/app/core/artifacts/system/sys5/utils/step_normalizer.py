"""
Deterministic normalization for a generated/corrected test case's steps.

Test_Start and End_of_test are purely mechanical bookend steps - unlike a
grounded signal name, an enum value, or a remark, there is no requirement-
specific content to get right, so there's no reason to leave their presence
to chance and only catch a miss after the fact via another LLM Correct
round-trip. The same "don't trust the LLM for something 100% mechanical"
reasoning nodes/node_7.py already applies to test_case_id applies here:
guarantee it in code, right after Generate and after every Correct pass.
"""

from typing import Any, Dict, List, Tuple

_TEST_START_STEP = {
    "phase": "PRECONDITION",
    "step_text": "Test_Start",
    "parameter_settings": None,
    "units": None,
    "expected_value": None,
    "units2": None,
    "whether_execute": "Yes",
    "remarks": "Marks the start of the test case",
}

_END_OF_TEST_STEP = {
    "phase": "POSTCONDITION",
    "step_text": "End_of_test",
    "parameter_settings": None,
    "units": None,
    "expected_value": None,
    "units2": None,
    "whether_execute": "Yes",
    "remarks": "Marks the end of the test case",
}


def _first_keyword(step: Dict[str, Any]) -> str:
    text = str(step.get("step_text", "")).strip()
    return text.split()[0] if text else ""


def ensure_test_start_end(steps: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Guarantee the step list opens with Test_Start and closes with
    End_of_test, inserting either as a new step if missing (an empty step
    list gets both) and renumbering step_no sequentially afterward.

    Returns (steps, fixes) - fixes is a list of human-readable strings
    describing what was inserted, empty if the step list was already
    correct, so callers can log when this actually had to do something.
    """
    steps = list(steps) if steps else []
    fixes = []

    if not steps or _first_keyword(steps[0]) != "Test_Start":
        steps.insert(0, dict(_TEST_START_STEP))
        fixes.append("inserted missing Test_Start step at the start")

    if _first_keyword(steps[-1]) != "End_of_test":
        steps.append(dict(_END_OF_TEST_STEP))
        fixes.append("inserted missing End_of_test step at the end")

    for i, step in enumerate(steps, start=1):
        step["step_no"] = i

    return steps, fixes
