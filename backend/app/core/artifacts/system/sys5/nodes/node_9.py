"""Node 9: Correct test cases that failed validation"""

import os
import sys

_workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../.."))
if _workspace_root not in sys.path:
    sys.path.insert(0, _workspace_root)

try:
    from ..state import SYS5State
    from ..config import get_llm
    from ..prompts import build_correct_input, build_correct_prompt, parse_json_response
except ImportError:
    from backend.app.core.artifacts.system.sys5.state import SYS5State
    from backend.app.core.artifacts.system.sys5.config import get_llm
    from backend.app.core.artifacts.system.sys5.prompts import (
        build_correct_input, build_correct_prompt, parse_json_response
    )


class Node9CorrectTestCases:
    """
    Node 9: Correct test cases whose validation_result came back invalid.

    Config: config["max_corrections"] (default 1) caps how many times a
    single test case can go through the Validate -> Correct loop.
    graph.py routes Node 9 back to Node 8 (Validate) as long as a test case
    is still invalid and hasn't used up its correction budget; otherwise it
    proceeds to END. With max_corrections=1 that means exactly one
    Validate -> Correct pass before moving on; with max_corrections=2, a
    second Validate -> Correct pass is allowed, etc.
    """

    @staticmethod
    def execute(state: SYS5State) -> SYS5State:
        print(f"\n{'='*80}")
        print("NODE 9: CORRECT TEST CASES")
        print(f"{'='*80}\n")

        config = state["config"]
        max_corrections = config.get("max_corrections", 1)
        test_cases = dict(state.get("test_cases") or {})
        errors = state.get("errors", [])

        print(f"[LOG] max_corrections configured: {max_corrections}\n")

        try:
            llm = get_llm()
        except Exception as e:
            error_msg = f"Could not initialize LLM: {str(e)}"
            print(f"[ERROR] {error_msg}\n")
            errors.append(error_msg)
            state["errors"] = errors
            return state

        for req_id, entry in test_cases.items():
            validation_result = entry.get("validation_result") or {}
            if validation_result.get("valid") is not False:
                continue  # nothing to correct - valid, or not yet validated

            if entry.get("correction_count", 0) >= max_corrections:
                print(f"[LOG] {req_id}: correction budget ({max_corrections}) already used, leaving as-is\n")
                continue

            correct_input = build_correct_input(
                entry.get("generate_input", {}), entry.get("generated_output"), validation_result
            )
            prompt = build_correct_prompt(correct_input)

            try:
                response = llm.invoke(prompt)
                corrected_output = parse_json_response(response.content, fallback=None)
                if corrected_output is None:
                    raise ValueError("Correct response did not contain parseable JSON")
                entry["generated_output"] = corrected_output
                entry["status"] = "corrected"
                print(f"[LOG] {req_id}: corrected (attempt {entry.get('correction_count', 0) + 1})\n")
            except Exception as e:
                print(f"[WARNING] Correct failed for {req_id}: {str(e)}\n")
                entry["status"] = "correct_failed"

            entry["correction_count"] = entry.get("correction_count", 0) + 1

        state["test_cases"] = test_cases
        state["errors"] = errors

        print(f"{'='*80}")
        print("NODE 9 COMPLETED")
        print(f"{'='*80}\n")

        return state
