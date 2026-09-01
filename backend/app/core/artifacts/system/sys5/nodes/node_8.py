"""Node 8: Validate generated test cases"""

import os
import sys

_workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../.."))
if _workspace_root not in sys.path:
    sys.path.insert(0, _workspace_root)

try:
    from ..state import SYS5State
    from ..prompts import build_validate_input, build_validate_prompt
except ImportError:
    from backend.app.core.artifacts.system.sys5.state import SYS5State
    from backend.app.core.artifacts.system.sys5.prompts import build_validate_input, build_validate_prompt


class Node8ValidateTestCases:
    """
    Node 8: Validate each generated test case.

    Until VALIDATE_PROMPT_TEMPLATE (prompts.py) is written, this stores a
    "pending_prompt" validation_result instead of calling an LLM. Once real
    generated_output exists and the prompt is filled in, this is where the
    validation_result becomes {"valid": True/False, "issues": [...]}, which
    graph.py's routing after this node reads to decide whether to loop into
    Node 9 (Correct).
    """

    @staticmethod
    def execute(state: SYS5State) -> SYS5State:
        print(f"\n{'='*80}")
        print("NODE 8: VALIDATE TEST CASES")
        print(f"{'='*80}\n")

        test_cases = dict(state.get("test_cases") or {})
        errors = state.get("errors", [])

        for req_id, entry in test_cases.items():
            if entry.get("generated_output") is None:
                print(f"[LOG] {req_id}: nothing generated yet, skipping validation\n")
                continue

            validate_input = build_validate_input(entry.get("generate_input", {}), entry.get("generated_output"))
            prompt = build_validate_prompt(validate_input)

            if prompt is None:
                print(f"[LOG] Validate prompt not yet configured - skipping validation for {req_id}\n")
                entry["validation_result"] = {"valid": None, "issues": [], "note": "Validate prompt not yet configured"}
                entry["status"] = "pending_prompt"
                continue

            # Once VALIDATE_PROMPT_TEMPLATE is written, invoke the LLM here
            # and parse its response into validation_result.
            entry["validation_result"] = {"valid": None, "issues": []}
            entry["status"] = "validated"

        state["test_cases"] = test_cases
        state["errors"] = errors

        print(f"{'='*80}")
        print("NODE 8 COMPLETED")
        print(f"{'='*80}\n")

        return state
