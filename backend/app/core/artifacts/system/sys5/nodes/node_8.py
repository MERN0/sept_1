"""Node 8: Validate generated test cases"""

import os
import sys

_workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../.."))
if _workspace_root not in sys.path:
    sys.path.insert(0, _workspace_root)

try:
    from ..state import SYS5State
    from ..config import get_llm
    from ..prompts import build_validate_input
    from ..utils.agentchain_prompts import get_prompt_from_agentchain
    from ..schema import parse_and_validate_validation_result
    from ..utils import (
        check_step_grounding, check_enum_parameter_usage, check_remarks_present,
        check_test_start_end_present
    )
except ImportError:
    from backend.app.core.artifacts.system.sys5.state import SYS5State
    from backend.app.core.artifacts.system.sys5.config import get_llm
    from backend.app.core.artifacts.system.sys5.prompts import build_validate_input
    from backend.app.core.artifacts.system.sys5.utils.agentchain_prompts import get_prompt_from_agentchain
    from backend.app.core.artifacts.system.sys5.schema import parse_and_validate_validation_result
    from backend.app.core.artifacts.system.sys5.utils import (
        check_step_grounding, check_enum_parameter_usage, check_remarks_present,
        check_test_start_end_present
    )


class Node8ValidateTestCases:
    """
    Node 8: Validate each generated test case against its requirement/test
    pattern and the known signal/command/library pool.

    Three checks run, not just the LLM's own opinion:
    1. A deterministic grounding check (utils/grounding_check.py) that
       cross-references every step's referenced signal/compound/library name
       against the actual names extracted in Nodes 2-6 - this catches a
       hallucinated name even if the LLM's own semantic validation misses it.
    2. A deterministic enum-parameter check: for a Set step on a
       model_input_mapping signal, parameter_settings must hold the
       human-readable test_case_input value (e.g. "FWD", "ON"), not the
       internal numeric model_input code, and not be misplaced into units.
    3. A deterministic remarks check: every step must carry a non-empty
       remarks value - it is not optional.
    4. A deterministic Test_Start/End_of_test presence check - a backstop:
       Nodes 7/9 already guarantee this in code (utils/step_normalizer.py),
       so this should never actually fire; it exists to surface a bug in
       that normalizer rather than let a missing bookend step slip through
       silently.
    5. The LLM Validate prompt (prompts.py), for everything the deterministic
       checks can't see (phase ordering, coverage of the test pattern, etc).

    Either source failing marks the test case invalid. Sets
    validation_result = {"valid": bool, "issues": [...]}, which graph.py's
    routing after this node reads to decide whether to loop into Node 9
    (Correct).
    """

    @staticmethod
    def execute(state: SYS5State) -> SYS5State:
        print(f"\n{'='*80}")
        print("NODE 8: VALIDATE TEST CASES")
        print(f"{'='*80}\n")

        test_cases = dict(state.get("test_cases") or {})
        errors = state.get("errors", [])
        agentchain = state.get("agent_chain", [])

        try:
            llm = get_llm()
        except Exception as e:
            error_msg = f"Could not initialize LLM: {str(e)}"
            print(f"[ERROR] {error_msg}\n")
            errors.append(error_msg)
            state["errors"] = errors
            return state

        for req_id, entry in test_cases.items():
            generated_output = entry.get("generated_output")
            if generated_output is None:
                print(f"[LOG] {req_id}: nothing generated, skipping validation\n")
                continue

            # 1. Deterministic grounding check against the actual extracted data
            feature_bundle = entry.get("generate_input", {}).get("feature_bundle", {})
            steps = generated_output.get("steps", [])
            grounding_issues = check_step_grounding(steps, feature_bundle)
            if grounding_issues:
                print(f"[LOG] {req_id}: grounding check found {len(grounding_issues)} issue(s): "
                      f"{grounding_issues}\n")

            # 2. Deterministic enum-parameter check (test_case_input vs model_input code)
            enum_issues = check_enum_parameter_usage(steps, feature_bundle)
            if enum_issues:
                print(f"[LOG] {req_id}: enum parameter check found {len(enum_issues)} issue(s): "
                      f"{enum_issues}\n")

            # 3. Deterministic remarks check - every step must have one, not optional
            remarks_issues = check_remarks_present(steps)
            if remarks_issues:
                print(f"[LOG] {req_id}: remarks check found {len(remarks_issues)} issue(s): "
                      f"{remarks_issues}\n")

            # 4. Deterministic Test_Start/End_of_test backstop (Nodes 7/9 already
            # guarantee this in code - this firing means that normalization broke)
            bookend_issues = check_test_start_end_present(steps)
            if bookend_issues:
                print(f"[LOG] {req_id}: Test_Start/End_of_test check found {len(bookend_issues)} issue(s): "
                      f"{bookend_issues}\n")

            deterministic_issues = grounding_issues + enum_issues + remarks_issues + bookend_issues

            # 5. LLM Validate prompt for everything the deterministic checks can't see
            validate_input = build_validate_input(entry.get("generate_input", {}), generated_output)

            # Get prompt from agentchain (verification_agent), or use fallback
            prompt = get_prompt_from_agentchain(agentchain, "verification_agent")
            if not prompt:
                print(f"[LOG] verification_agent prompt not found in agentchain, using fallback\n")
                from ..prompts import build_validate_prompt as fallback_build_validate_prompt
                prompt = fallback_build_validate_prompt(validate_input)
            else:
                # Format the prompt template with actual data
                import json
                try:
                    prompt = prompt.format(
                        generated_output=json.dumps(generated_output, indent=2, default=str),
                        requirement_and_pattern=json.dumps({
                            "requirement": validate_input.get("generate_input", {}).get("requirement", {}),
                            "test_pattern": validate_input.get("generate_input", {}).get("test_pattern", {})
                        }, indent=2, default=str),
                        feature_bundle=json.dumps(validate_input.get("generate_input", {}).get("feature_bundle", {}), indent=2, default=str)
                    )
                except KeyError as fmt_err:
                    print(f"[WARNING] Failed to format prompt template: {fmt_err}, using fallback\n")
                    from ..prompts import build_validate_prompt as fallback_build_validate_prompt
                    prompt = fallback_build_validate_prompt(validate_input)

            try:
                response = llm.invoke(prompt)
                validation_result = parse_and_validate_validation_result(response.content)
                entry["status"] = "validated"
            except Exception as e:
                print(f"[WARNING] Validate failed for {req_id}: {str(e)}\n")
                validation_result = {"valid": False, "issues": [f"Validate call failed: {str(e)}"]}
                entry["status"] = "validate_failed"

            # Merge: either source failing marks the test case invalid
            combined_issues = deterministic_issues + validation_result.get("issues", [])
            validation_result = {
                "valid": validation_result.get("valid", False) and not deterministic_issues,
                "issues": combined_issues,
            }
            print(f"[LOG] {req_id}: valid={validation_result['valid']}, issues={validation_result['issues']}\n")

            entry["validation_result"] = validation_result

        state["test_cases"] = test_cases
        state["errors"] = errors

        print(f"{'='*80}")
        print("NODE 8 COMPLETED")
        print(f"{'='*80}\n")

        return state
