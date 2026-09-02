"""Node 8: Validate generated test cases"""

import os
import sys

_workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../.."))
if _workspace_root not in sys.path:
    sys.path.insert(0, _workspace_root)

try:
    from ..state import SYS5State
    from ..config import get_llm
    from ..prompts import build_validate_input, build_validate_prompt
    from ..schema import parse_and_validate_validation_result
    from ..utils import check_step_grounding
except ImportError:
    from backend.app.core.artifacts.system.sys5.state import SYS5State
    from backend.app.core.artifacts.system.sys5.config import get_llm
    from backend.app.core.artifacts.system.sys5.prompts import build_validate_input, build_validate_prompt
    from backend.app.core.artifacts.system.sys5.schema import parse_and_validate_validation_result
    from backend.app.core.artifacts.system.sys5.utils import check_step_grounding


class Node8ValidateTestCases:
    """
    Node 8: Validate each generated test case against its requirement/test
    pattern and the known signal/command/library pool.

    Two checks run, not just the LLM's own opinion:
    1. A deterministic grounding check (utils/grounding_check.py) that
       cross-references every step's referenced signal/compound/library name
       against the actual names extracted in Nodes 2-6 - this catches a
       hallucinated name even if the LLM's own semantic validation misses it.
    2. The LLM Validate prompt (prompts.py), for everything the deterministic
       check can't see (phase ordering, coverage of the test pattern, etc).

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
            grounding_issues = check_step_grounding(generated_output.get("steps", []), feature_bundle)
            if grounding_issues:
                print(f"[LOG] {req_id}: grounding check found {len(grounding_issues)} issue(s): "
                      f"{grounding_issues}\n")

            # 2. LLM Validate prompt for everything the grounding check can't see
            validate_input = build_validate_input(entry.get("generate_input", {}), generated_output)
            prompt = build_validate_prompt(validate_input)

            try:
                response = llm.invoke(prompt)
                validation_result = parse_and_validate_validation_result(response.content)
                entry["status"] = "validated"
            except Exception as e:
                print(f"[WARNING] Validate failed for {req_id}: {str(e)}\n")
                validation_result = {"valid": False, "issues": [f"Validate call failed: {str(e)}"]}
                entry["status"] = "validate_failed"

            # Merge: either source failing marks the test case invalid
            combined_issues = grounding_issues + validation_result.get("issues", [])
            validation_result = {
                "valid": validation_result.get("valid", False) and not grounding_issues,
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
