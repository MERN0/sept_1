"""Node 7: Generate test cases, one test pattern at a time"""

import os
import re
import sys
import traceback

_workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../.."))
if _workspace_root not in sys.path:
    sys.path.insert(0, _workspace_root)

try:
    from ..state import SYS5State
    from ..utils import drop_empty_values, ensure_test_start_end
    from ..utils.agentchain_prompts import get_prompt_from_agentchain
    from ..config import get_llm
    from ..prompts import build_generate_input
    from ..schema import parse_and_validate_test_case
except ImportError:
    from backend.app.core.artifacts.system.sys5.state import SYS5State
    from backend.app.core.artifacts.system.sys5.utils import drop_empty_values, ensure_test_start_end
    from backend.app.core.artifacts.system.sys5.utils.agentchain_prompts import get_prompt_from_agentchain
    from backend.app.core.artifacts.system.sys5.config import get_llm
    from backend.app.core.artifacts.system.sys5.prompts import build_generate_input
    from backend.app.core.artifacts.system.sys5.schema import parse_and_validate_test_case


class Node7GenerateTestCases:
    """
    Node 7: Generate a test case per test pattern entry (one at a time).

    Node 1 generates test_patterns[req_id] = {"test_cases": [...], "factors":
    {...}, "summary": ...} - a LIST of distinct precondition/action
    combinations per requirement, not a single pattern. Each entry in that
    list must produce its own generated test case; only iterating the outer
    per-requirement dict (as this node used to) silently generates just one
    test case per requirement and drops the rest of the list.

    For each individual test pattern entry, bundles together the
    requirement, that one pattern entry, and the relevant feature data
    (feature_details + model_input_mapping/tolerances/compound_commands/
    library_list from model_config) into a single input, sends it to the
    LLM via the Generate prompt (prompts.py), and stores the parsed test
    case JSON under a key unique to that (requirement, pattern) pair.

    Each generated test case is assigned a canonical, globally unique
    "TC_TMHC_<NNN>" id (sequential, zero-padded) in code rather than trusting
    whatever id the LLM happens to put in its JSON - this is the single
    standard both the Item List and Test Cases sheets read, so the two
    sheets can never disagree on a test case's id.
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
        agentchain = state.get("agent_chain", [])

        print(f"[LOG] Agent chain status: {len(agentchain)} agents available\n")
        if agentchain:
            agents = [a.get("agent_name") for a in agentchain if isinstance(a, dict)]
            print(f"[LOG] Available agents: {agents}\n")

        # Drop empty/null/NaN entries before building anything from this data
        feature_details = drop_empty_values(state.get("feature_details", {}))
        model_config = drop_empty_values(state.get("model_config", {}))
        state["feature_details"] = feature_details
        state["model_config"] = model_config

        print(f"[LOG] Cleaned feature_details: {len(feature_details)} entries")
        print(f"[LOG] Cleaned model_config keys: {list(model_config.keys())}\n")

        requirements_by_id = {req.get("req_id"): req for req in requirements}
        test_cases = dict(state.get("test_cases") or {})
        test_case_counter = 0

        try:
            llm = get_llm()
        except Exception as e:
            error_msg = f"Could not initialize LLM: {str(e)}"
            print(f"[ERROR] {error_msg}\n")
            errors.append(error_msg)
            state["errors"] = errors
            return state

        for req_id, test_pattern in test_patterns.items():
            pattern_entries = (test_pattern or {}).get("test_cases") or []
            if not pattern_entries:
                print(f"[LOG] {req_id}: no test pattern entries to generate from, skipping\n")
                continue

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

            print(f"[LOG] Processing {len(pattern_entries)} test pattern entry(ies) for {req_id}...")

            for pattern_entry in pattern_entries:
                pattern_no = pattern_entry.get("test_case_no", test_case_counter + 1)
                entry_key = f"{req_id}_{pattern_no}"
                test_case_counter += 1
                test_case_id = f"TC_TMHC_{test_case_counter:03d}"

                generate_input = build_generate_input(requirement, pattern_entry, feature_bundle)

                # Get prompt from agentchain (node_7_generate_test_cases), or use fallback
                prompt = get_prompt_from_agentchain(agentchain, "node_7_generate_test_cases")
                if not prompt:
                    print(f"[LOG] generation_agent prompt not found in agentchain, using fallback\n")
                    from ..prompts import build_generate_prompt as fallback_build_generate_prompt
                    prompt = fallback_build_generate_prompt(generate_input)
                else:
                    # Format the prompt template with actual data
                    import json
                    try:
                        prompt = prompt.format(
                            requirement=json.dumps(generate_input.get("requirement", {}), indent=2, default=str),
                            test_pattern=json.dumps(generate_input.get("test_pattern", {}), indent=2, default=str),
                            feature_bundle=json.dumps(generate_input.get("feature_bundle", {}), indent=2, default=str),
                            test_case_json_shape=json.dumps(generate_input.get("test_case_json_shape", ""), indent=2)
                        )
                    except KeyError as fmt_err:
                        print(f"[WARNING] Failed to format prompt template: {fmt_err}, using fallback\n")
                        from ..prompts import build_generate_prompt as fallback_build_generate_prompt
                        prompt = fallback_build_generate_prompt(generate_input)

                try:
                    response = llm.invoke(prompt)
                    generated_output = parse_and_validate_test_case(response.content)
                    status = "generated"
                except Exception as e:
                    print(f"[WARNING] Generate failed for {req_id} pattern #{pattern_no}: {str(e)}\n")
                    print(f"[DEBUG] Full traceback:\n{traceback.format_exc()}\n")
                    generated_output = None
                    status = "generate_failed"

                if generated_output is not None:
                    generated_output["test_case_id"] = test_case_id
                    # A failure here must never discard an otherwise-successful
                    # generation - this is a best-effort mechanical fix-up, not
                    # part of what makes a test case valid, so on any error it
                    # just leaves the LLM's own steps as-is rather than losing
                    # the whole test case.
                    try:
                        generated_output["steps"], bookend_fixes = ensure_test_start_end(
                            generated_output.get("steps", [])
                        )
                        if bookend_fixes:
                            print(f"[LOG] {test_case_id}: {'; '.join(bookend_fixes)}\n")
                    except Exception as norm_error:
                        print(f"[WARNING] {test_case_id}: Test_Start/End_of_test normalization failed "
                              f"({str(norm_error)}) - keeping the generated steps as-is\n")
                        print(f"[DEBUG] Full traceback:\n{traceback.format_exc()}\n")

                    print(f"[LOG] Generated test case {test_case_id} for {req_id} (pattern #{pattern_no}) "
                          f"with {len(generated_output.get('steps', []))} steps\n")

                test_cases[entry_key] = {
                    "req_id": req_id,
                    "test_case_id": test_case_id,
                    "generate_input": generate_input,
                    "generated_output": generated_output,
                    "validation_result": None,
                    "correction_count": 0,
                    "status": status,
                }

        state["test_cases"] = test_cases
        state["errors"] = errors

        print(f"\n[LOG] Total test cases tracked: {len(test_cases)}\n")
        print(f"{'='*80}")
        print("NODE 7 COMPLETED")
        print(f"{'='*80}\n")

        return state
