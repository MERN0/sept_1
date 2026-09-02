"""
Pydantic boundary models for LLM-generated test case output (Nodes 7/9).

Scope is deliberately narrow: only the Generate/Correct output boundary is
modeled here. Everything else in this pipeline (state, feature_details,
model_config, etc.) stays plain dicts - see the conversation for why a
pipeline-wide pydantic rewrite (as in work_28) wasn't adopted. TestCase/
TestStep exist purely to catch a malformed LLM response (wrong type, a
phase/keyword typo) right at the parse boundary instead of letting it
silently corrupt grounding_check.py or the Excel writer; both models are
converted straight back to plain dicts for the rest of the pipeline.

The TestPhase/StepKeyword Literals encode the same command grammar embedded
as prose in prompts.py's _COMMAND_GRAMMAR_RULES - keep the two in sync if
the grammar ever changes.
"""

import os
import sys
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator

_workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../.."))
if _workspace_root not in sys.path:
    sys.path.insert(0, _workspace_root)

try:
    from .prompts import parse_json_response
except ImportError:
    from backend.app.core.artifacts.system.sys5.prompts import parse_json_response

TestPhase = Literal["PRECONDITION", "ACTION", "POSTCONDITION"]

# Lib_* is an open family (Lib_Ramp, Lib_CheckTorqueLimit, whatever a given
# library_list contains) so it isn't a fixed Literal - validated separately
# by grounding_check.py against the actual extracted library_list.
_FIXED_KEYWORDS = {"Test_Start", "End_of_test", "Set", "Verify", "Wait", "Wait_Until", "Compound"}


class TestStep(BaseModel):
    step_no: int
    phase: TestPhase
    step_text: str = Field(min_length=1)
    parameter_settings: Optional[str] = None
    units: Optional[str] = None
    expected_value: Optional[str] = None
    units2: Optional[str] = None
    whether_execute: str = "Yes"
    remarks: Optional[str] = None

    @field_validator("parameter_settings", "units", "expected_value", "units2", "remarks", mode="before")
    @classmethod
    def _stringify(cls, v):
        # The LLM sometimes emits a bare number/bool for these fields; keep
        # them as strings for consistent downstream handling (Excel cells,
        # grounding_check regex matching) rather than rejecting the response.
        return None if v is None else str(v)

    @field_validator("step_text")
    @classmethod
    def _check_keyword(cls, v: str) -> str:
        first_word = v.strip().split()[0] if v.strip() else ""
        if first_word in _FIXED_KEYWORDS or first_word.startswith("Lib_"):
            return v
        raise ValueError(
            f"step_text '{v}' does not start with a recognized keyword "
            f"(Test_Start/End_of_test/Set/Verify/Wait/Wait_Until/Compound/Lib_*)"
        )


class TestCase(BaseModel):
    test_case_id: str = Field(min_length=1)
    feature: str = ""
    variant: Optional[str] = None
    requirement_ids: List[str] = Field(default_factory=list)
    priority: Optional[str] = None
    mode_of_execution: str = "Automated"
    description: str = ""
    status: Literal["clean", "flagged"] = "clean"
    flag_reason: Optional[str] = None
    remarks_summary: Optional[str] = None
    steps: List[TestStep] = Field(default_factory=list)

    @field_validator("steps")
    @classmethod
    def _check_phase_order(cls, steps: List[TestStep]) -> List[TestStep]:
        order = {"PRECONDITION": 0, "ACTION": 1, "POSTCONDITION": 2}
        last = -1
        for step in steps:
            rank = order[step.phase]
            if rank < last:
                raise ValueError(
                    f"step {step.step_no} has phase '{step.phase}' out of order "
                    f"(steps must go PRECONDITION -> ACTION -> POSTCONDITION)"
                )
            last = rank
        return steps


class ValidationResult(BaseModel):
    valid: bool
    issues: List[str] = Field(default_factory=list)


def parse_and_validate_test_case(response_text: str) -> Dict[str, Any]:
    """
    Parse the LLM's JSON response (Generate/Correct) and validate it against
    the TestCase schema. Raises ValueError (no JSON found) or pydantic's
    ValidationError (wrong shape/type, bad phase order, unrecognized
    keyword) on failure - Nodes 7/9's existing try/except around this call
    turns either into a generate_failed/correct_failed status with the
    error's own message logged, so no separate None-check is needed here.
    Returns a plain dict (schema validated, but the rest of the pipeline
    keeps working with dicts) on success.
    """
    raw = parse_json_response(response_text, fallback=None)
    if raw is None:
        raise ValueError("LLM response did not contain parseable JSON")
    return TestCase.model_validate(raw).model_dump()


def parse_and_validate_validation_result(response_text: str) -> Dict[str, Any]:
    """Same idea as parse_and_validate_test_case, for the Validate stage's
    {"valid": bool, "issues": [...]} response."""
    raw = parse_json_response(response_text, fallback=None)
    if raw is None:
        raise ValueError("LLM response did not contain parseable JSON")
    return ValidationResult.model_validate(raw).model_dump()
