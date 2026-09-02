"""Node 9: Correct test cases that failed validation"""

import os
import sys
import traceback

_workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../.."))
if _workspace_root not in sys.path:
    sys.path.insert(0, _workspace_root)

try:
    from ..state import SYS5State
    from ..config import get_llm
    from ..prompts import build_correct_input
    from ..utils.agentchain_prompts import get_prompt_from_agentchain
    from ..schema import parse_and_validate_test_case
    from ..utils import ensure_test_start_end
except ImportError:
    from backend.app.core.artifacts.system.sys5.state import SYS5State
    from backend.app.core.artifacts.system.sys5.config import get_llm
    from backend.app.core.artifacts.system.sys5.prompts import build_correct_input
    from backend.app.core.artifacts.system.sys5.utils.agentchain_prompts import get_prompt_from_agentchain
    from backend.app.core.artifacts.system.sys5.schema import parse_and_validate_test_case
    from backend.app.core.artifacts.system.sys5.utils import ensure_test_start_end


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
        agentchain = state.get("agent_chain", [])

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

            # Get prompt from agentchain (node_9_correct_test_cases), or use fallback
            prompt = get_prompt_from_agentchain(agentchain, "node_9_correct_test_cases")
            if not prompt:
                print(f"[LOG] node_9_correct_test_cases prompt not found in agentchain, using fallback\n")
                from ..prompts import build_correct_prompt as fallback_build_correct_prompt
                prompt = fallback_build_correct_prompt(correct_input)
            else:
                # Format the prompt template with actual data
                import json
                try:
                    # Get the test case JSON schema from agentchain
                    json_schema = get_prompt_from_agentchain(agentchain, "test_case_json_schema", "")
                    if not json_schema:
                        from ..prompts import _TEST_CASE_JSON_SHAPE
                        json_schema = _TEST_CASE_JSON_SHAPE

                    prompt = prompt.format(
                        generated_output=json.dumps(correct_input.get("generated_output", {}), indent=2, default=str),
                        validation_issues=json.dumps(correct_input.get("validation_result", {}).get("issues", []), indent=2, default=str),
                        feature_bundle=json.dumps(correct_input.get("generate_input", {}).get("feature_bundle", {}), indent=2, default=str),
                        test_case_json_shape=json_schema
                    )
                except KeyError as fmt_err:
                    print(f"[WARNING] Failed to format prompt template: {fmt_err}, using fallback\n")
                    from ..prompts import build_correct_prompt as fallback_build_correct_prompt
                    prompt = fallback_build_correct_prompt(correct_input)

            try:
                response = llm.invoke(prompt)
                corrected_output = parse_and_validate_test_case(response.content)
            except Exception as e:
                print(f"[WARNING] Correct failed for {req_id}: {str(e)}\n")
                print(f"[DEBUG] Full traceback:\n{traceback.format_exc()}\n")
                entry["status"] = "correct_failed"
                entry["correction_count"] = entry.get("correction_count", 0) + 1
                continue

            # Correct must never drift the canonical id assigned in Node 7 -
            # it's the single standard the Item List and Test Cases sheets
            # both key off of, so re-assert it regardless of what the LLM
            # put in its corrected JSON.
            canonical_id = entry.get("test_case_id")
            if canonical_id:
                corrected_output["test_case_id"] = canonical_id

            # A failure here must never discard an otherwise-successful
            # correction - this is a best-effort mechanical fix-up, not part
            # of what makes a corrected test case valid, so on any error it
            # just keeps the LLM's own corrected steps as-is.
            try:
                corrected_output["steps"], bookend_fixes = ensure_test_start_end(
                    corrected_output.get("steps", [])
                )
            except Exception as norm_error:
                bookend_fixes = []
                print(f"[WARNING] {req_id}: Test_Start/End_of_test normalization failed "
                      f"({str(norm_error)}) - keeping the corrected steps as-is\n")
                print(f"[DEBUG] Full traceback:\n{traceback.format_exc()}\n")

            entry["generated_output"] = corrected_output
            entry["status"] = "corrected"
            print(f"[LOG] {req_id}: corrected (attempt {entry.get('correction_count', 0) + 1})\n")
            if bookend_fixes:
                print(f"[LOG] {req_id}: {'; '.join(bookend_fixes)}\n")

            entry["correction_count"] = entry.get("correction_count", 0) + 1

        state["test_cases"] = test_cases
        state["errors"] = errors

        print(f"{'='*80}")
        print("NODE 9 COMPLETED")
        print(f"{'='*80}\n")

        return state
