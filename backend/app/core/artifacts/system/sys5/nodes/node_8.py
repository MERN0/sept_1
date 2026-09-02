"""Node 8: Validate generated test cases"""

import os
import sys

_workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../.."))
if _workspace_root not in sys.path:
    sys.path.insert(0, _workspace_root)

try:
    from ..state import SYS5State
    from ..config import get_llm
    from ..prompts import build_validate_input, build_validate_prompt, parse_json_response
except ImportError:
    from backend.app.core.artifacts.system.sys5.state import SYS5State
    from backend.app.core.artifacts.system.sys5.config import get_llm
    from backend.app.core.artifacts.system.sys5.prompts import (
        build_validate_input, build_validate_prompt, parse_json_response
    )


class Node8ValidateTestCases:
    """
    Node 8: Validate each generated test case against its requirement/test
    pattern and the known signal/command/library pool, via the Validate
    prompt (prompts.py). Sets validation_result = {"valid": bool, "issues":
    [...]}, which graph.py's routing after this node reads to decide
    whether to loop into Node 9 (Correct).
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
            if entry.get("generated_output") is None:
                print(f"[LOG] {req_id}: nothing generated, skipping validation\n")
                continue

            validate_input = build_validate_input(entry.get("generate_input", {}), entry.get("generated_output"))
            prompt = build_validate_prompt(validate_input)

            try:
                response = llm.invoke(prompt)
                validation_result = parse_json_response(
                    response.content, fallback={"valid": False, "issues": ["Validate response was not parseable JSON"]}
                )
                print(f"[LOG] {req_id}: valid={validation_result.get('valid')}, "
                      f"issues={validation_result.get('issues', [])}\n")
                entry["status"] = "validated"
            except Exception as e:
                print(f"[WARNING] Validate failed for {req_id}: {str(e)}\n")
                validation_result = {"valid": False, "issues": [f"Validate call failed: {str(e)}"]}
                entry["status"] = "validate_failed"

            entry["validation_result"] = validation_result

        state["test_cases"] = test_cases
        state["errors"] = errors

        print(f"{'='*80}")
        print("NODE 8 COMPLETED")
        print(f"{'='*80}\n")

        return state
