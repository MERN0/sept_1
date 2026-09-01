"""Node 3: Extract Logical Signal Names from Input/Output Signals sheet"""

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

IDEOGRAPHIC_ZERO = "〇"


class Node3ExtractLogicalSignals:
    """
    Node 3: Extract Logical Signal Names from Input/Output Signals sheet.
    Filter by ideographic zero marker and replace underscores with spaces.
    """

    @staticmethod
    def _find_signals_sheet(excel_file):
        """Auto-discover input/output signals sheet"""
        for sheet in excel_file.sheet_names:
            sheet_lower = sheet.lower()
            if ('input' in sheet_lower or 'output' in sheet_lower) and 'signal' in sheet_lower:
                return sheet
        return None

    @staticmethod
    def execute(state: SYS5State) -> SYS5State:
        print(f"\n{'='*80}")
        print("NODE 3: LOGICAL SIGNAL EXTRACTION")
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
            excel_file = pd.ExcelFile(abs_sys_req_path)
            print(f"[LOG] Available sheets: {excel_file.sheet_names}\n")

            signals_sheet = Node3ExtractLogicalSignals._find_signals_sheet(excel_file)
            if not signals_sheet:
                error_msg = f"Could not find Input/Output Signals sheet. Available: {excel_file.sheet_names}"
                print(f"[ERROR] {error_msg}\n")
                errors.append(error_msg)
                state["errors"] = errors
                return state

            signals_df = pd.read_excel(abs_sys_req_path, sheet_name=signals_sheet)
            print(f"[LOG] Signals sheet loaded: {signals_sheet}, {len(signals_df)} rows\n")

        except Exception as e:
            error_msg = f"Could not load signals sheet: {str(e)}"
            print(f"[ERROR] {error_msg}\n")
            errors.append(error_msg)
            state["errors"] = errors
            return state

        # Extract feature numbers from requirements
        feature_nums = []
        for req in requirements:
            req_id = req.get("req_id", "")
            match = re.search(r'(\d{3})', req_id)
            if match and match.group(1) not in feature_nums:
                feature_nums.append(match.group(1))

        logical_signals = []

        for feature_num in feature_nums:
            print(f"[LOG] Processing feature '{feature_num}'...")

            # Find feature column
            feature_col = None
            for col in signals_df.columns:
                if str(col).strip() == feature_num:
                    feature_col = col
                    break

            if feature_col is None:
                print(f"[LOG] No column found matching '{feature_num}'\n")
                continue

            print(f"[LOG] Found column: {repr(feature_col)}")

            # Filter for ideographic zero marker
            filtered = signals_df[
                signals_df[feature_col].astype(str).str.contains(IDEOGRAPHIC_ZERO, na=False)
            ]

            print(f"[LOG] Valid rows with ideographic zero (〇): {len(filtered)}\n")

            # Extract Logical Signal Name from filtered rows
            if 'Logical Signal Name' not in filtered.columns:
                print(f"[LOG] 'Logical Signal Name' column not found\n")
                continue

            for idx, row in filtered.iterrows():
                logical_name = str(row['Logical Signal Name']).strip()

                # Replace underscores with spaces
                formatted_name = logical_name.replace('_', ' ')

                logical_signals.append({
                    "feature_number": feature_num,
                    "logical_signal_name": logical_name,
                    "formatted_name": formatted_name
                })

                print(f"[LOG] {logical_name} -> {formatted_name}")

        print(f"\n[LOG] Total logical signals extracted: {len(logical_signals)}\n")

        state["logical_signals"] = logical_signals
        state["errors"] = errors

        print(f"{'='*80}")
        print("NODE 3 COMPLETED")
        print(f"{'='*80}\n")

        return state
