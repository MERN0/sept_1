"""
Single place for all Generate / Validate / Correct prompts (Nodes 7-9).

The actual prompt text is intentionally left as a placeholder for now - only the
input bundle each stage receives is wired up. Fill in GENERATE_PROMPT_TEMPLATE,
VALIDATE_PROMPT_TEMPLATE, and CORRECT_PROMPT_TEMPLATE (or the build_* functions
below) when ready; nothing else in Nodes 7-9 needs to change.
"""

from typing import Any, Dict, Optional

# TODO: write the actual instruction text for each stage. Left as None so the
# nodes can detect "no prompt configured yet" and skip the LLM call cleanly.
GENERATE_PROMPT_TEMPLATE: Optional[str] = None
VALIDATE_PROMPT_TEMPLATE: Optional[str] = None
CORRECT_PROMPT_TEMPLATE: Optional[str] = None


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
    """Returns None until GENERATE_PROMPT_TEMPLATE is written."""
    if GENERATE_PROMPT_TEMPLATE is None:
        return None
    return GENERATE_PROMPT_TEMPLATE.format(**generate_input)


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
    """Returns None until VALIDATE_PROMPT_TEMPLATE is written."""
    if VALIDATE_PROMPT_TEMPLATE is None:
        return None
    return VALIDATE_PROMPT_TEMPLATE.format(**validate_input)


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
    """Returns None until CORRECT_PROMPT_TEMPLATE is written."""
    if CORRECT_PROMPT_TEMPLATE is None:
        return None
    return CORRECT_PROMPT_TEMPLATE.format(**correct_input)
