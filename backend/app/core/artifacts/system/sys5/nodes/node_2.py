"""Node 2: Signal and Command Extraction from Communication Matrices"""

import os
import sys
import re
import pandas as pd

_workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../.."))
if _workspace_root not in sys.path:
    sys.path.insert(0, _workspace_root)

try:
    from ..state import SYS5State
    from ..utils import resolve_path
except ImportError:
    from backend.app.core.artifacts.system.sys5.state import SYS5State
    from backend.app.core.artifacts.system.sys5.utils import resolve_path

IDEOGRAPHIC_ZERO = "〇"  # 〇


class Node2FindSignalsAndCommands:
    """
    Node 2, step 1: In the Master Comm Matrix (CAN) sheet, find the column
    whose header matches the feature/sheet number (e.g. "019"), filter it
    for rows marked with the ideographic zero character, and report the count.
    """

    @staticmethod
    def execute(state: SYS5State) -> SYS5State:
        print(f"\n{'='*80}")
        print("NODE 2: SIGNAL AND COMMAND EXTRACTION")
        print(f"{'='*80}\n")

        config = state["config"]
        requirements = state.get("requirements", [])
        errors = state.get("errors", [])

        input_folder = config.get("input_folder_path")
        req_filename = config.get("req_filename", "reqs_to_use.xlsx")

        abs_input_folder = resolve_path(input_folder) if input_folder else None
        abs_sys_req_path = os.path.join(abs_input_folder, req_filename) if abs_input_folder else None

        if not abs_sys_req_path or not os.path.exists(abs_sys_req_path):
            error_msg = f"System Requirements file not found: {abs_sys_req_path}"
            print(f"[ERROR] {error_msg}\n")
            errors.append(error_msg)
            state["errors"] = errors
            return state

        print(f"[LOG] System Requirements file: {abs_sys_req_path}\n")

        try:
            comm_matrix_df = pd.read_excel(abs_sys_req_path, sheet_name="Master Comm Matrix (CAN)")
            print(f"[LOG] Master Comm Matrix loaded: {len(comm_matrix_df)} rows, {len(comm_matrix_df.columns)} columns\n")
        except Exception as e:
            error_msg = f"Could not load Master Comm Matrix (CAN): {str(e)}"
            print(f"[ERROR] {error_msg}\n")
            errors.append(error_msg)
            state["errors"] = errors
            return state

        # Feature/sheet numbers to look up, derived from requirement IDs
        feature_nums = []
        for req in requirements:
            req_id = req.get("req_id", "")
            match = re.search(r'(\d{3})', req_id)
            if match and match.group(1) not in feature_nums:
                feature_nums.append(match.group(1))

        for feature_num in feature_nums:
            print(f"[LOG] Searching header row for sheet name '{feature_num}'...")

            feature_col = None
            for col in comm_matrix_df.columns:
                if str(col).strip() == feature_num:
                    feature_col = col
                    break

            if feature_col is None:
                print(f"[LOG] No column found matching '{feature_num}'\n")
                continue

            print(f"[LOG] Found column: {repr(feature_col)}")

            # Filter the column for the ideographic zero marker
            filtered = comm_matrix_df[
                comm_matrix_df[feature_col].astype(str).str.contains(IDEOGRAPHIC_ZERO, na=False)
            ]

            print(f"[LOG] Rows with ideographic zero (〇) under column '{feature_num}': {len(filtered)}\n")

        state["signals"] = []
        state["feature_details"] = {}
        state["errors"] = errors

        print(f"{'='*80}")
        print("NODE 2 COMPLETED")
        print(f"{'='*80}\n")

        return state
