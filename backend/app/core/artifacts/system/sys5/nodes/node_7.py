"""Node 7: Generate test cases, one test pattern at a time"""

import os
import re
import sys

_workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../.."))
if _workspace_root not in sys.path:
    sys.path.insert(0, _workspace_root)

try:
    from ..state import SYS5State
    from ..utils import drop_empty_values
    from ..prompts import build_generate_input, build_generate_prompt
except ImportError:
    from backend.app.core.artifacts.system.sys5.state import SYS5State
    from backend.app.core.artifacts.system.sys5.utils import drop_empty_values
    from backend.app.core.artifacts.system.sys5.prompts import build_generate_input, build_generate_prompt


class Node7GenerateTestCases:
    """
    Node 7: Generate a test case per test pattern (one at a time).

    For each requirement's test pattern, bundles together the requirement,
    the test pattern, and the relevant feature data (feature_details +
    model_input_mapping/tolerances/compound_commands/library_list from
    model_config) into a single input, then calls the Generate prompt
    (backend/app/core/artifacts/system/sys5/prompts.py). The actual prompt
    text isn't written yet, so until it is, this node stores the assembled
    input for each test pattern with a "pending_prompt" status instead of
    calling an LLM.
    """

    @staticmethod
    def _feature_number(req_id: str):
        match = re.search(r'(\d{3})', req_id or "")
        return match.group(1) if match else None

    @staticmethod
    def _feature_details_for(feature_details, feature_number):
        if not feature_number:
            return {}
        return {
            key: entry for key, entry in feature_details.items()
            if isinstance(entry, dict) and entry.get("feature_number") == feature_number
        }

    @staticmethod
    def execute(state: SYS5State) -> SYS5State:
        print(f"\n{'='*80}")
        print("NODE 7: GENERATE TEST CASES")
        print(f"{'='*80}\n")

        config = state["config"]
        requirements = state.get("requirements", [])
        test_patterns = state.get("test_patterns", {})
        errors = state.get("errors", [])

        # Drop empty/null/NaN entries before building anything from this data
        feature_details = drop_empty_values(state.get("feature_details", {}))
        model_config = drop_empty_values(state.get("model_config", {}))
        state["feature_details"] = feature_details
        state["model_config"] = model_config

        print(f"[LOG] Cleaned feature_details: {len(feature_details)} entries")
        print(f"[LOG] Cleaned model_config keys: {list(model_config.keys())}\n")

        requirements_by_id = {req.get("req_id"): req for req in requirements}
        test_cases = dict(state.get("test_cases") or {})

        for req_id, test_pattern in test_patterns.items():
            print(f"[LOG] Processing test pattern for {req_id} (1 at a time)...")

            requirement = requirements_by_id.get(req_id, {})
            feature_number = Node7GenerateTestCases._feature_number(req_id)

            feature_bundle = {
                "feature_details": Node7GenerateTestCases._feature_details_for(feature_details, feature_number),
                "model_input_mapping": model_config.get("model_input_mapping", {}),
                "tolerances": model_config.get("tolerances", {}),
                "compound_commands": model_config.get("compound_commands", {}),
                "library_list": model_config.get("library_list", {}),
            }
            feature_bundle = drop_empty_values(feature_bundle)

            generate_input = build_generate_input(requirement, test_pattern, feature_bundle)
            prompt = build_generate_prompt(generate_input)

            if prompt is None:
                print(f"[LOG] Generate prompt not yet configured - storing input bundle only for {req_id}\n")
                test_cases[req_id] = {
                    "req_id": req_id,
                    "generate_input": generate_input,
                    "generated_output": None,
                    "validation_result": None,
                    "correction_count": 0,
                    "status": "pending_prompt",
                }
                continue

            # Once GENERATE_PROMPT_TEMPLATE is written, invoke the LLM here
            # and parse its response into generated_output.
            test_cases[req_id] = {
                "req_id": req_id,
                "generate_input": generate_input,
                "generated_output": None,
                "validation_result": None,
                "correction_count": 0,
                "status": "generated",
            }

        state["test_cases"] = test_cases
        state["errors"] = errors

        print(f"\n[LOG] Total test cases tracked: {len(test_cases)}\n")
        print(f"{'='*80}")
        print("NODE 7 COMPLETED")
        print(f"{'='*80}\n")

        return state
