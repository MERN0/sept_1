"""Node 4: Extract App Parameter details from Requirements sheet"""

import json
import os
import sys
import re
import pandas as pd

_workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../.."))
if _workspace_root not in sys.path:
    sys.path.insert(0, _workspace_root)

try:
    from ..state import SYS5State
    from ..utils import resolve_path, ensure_directory_exists, update_feature_details_memory
except ImportError:
    from backend.app.core.artifacts.system.sys5.state import SYS5State
    from backend.app.core.artifacts.system.sys5.utils import resolve_path, ensure_directory_exists, update_feature_details_memory

IDEOGRAPHIC_ZERO = "〇"


class Node4ExtractAppParameters:
    """
    Node 4: Extract App Parameter details from the App Parameter sheet.
    Filter by ideographic zero marker (same as Node 2/3) and save columns
    B to G under feature_details, keyed by sheet name + header column value.
    """

    @staticmethod
    def _find_app_parameter_sheet(excel_file):
        """Auto-discover App Parameter sheet"""
        for sheet in excel_file.sheet_names:
            sheet_lower = sheet.lower()
            if 'app' in sheet_lower and 'param' in sheet_lower:
                return sheet
        return None

    @staticmethod
    def execute(state: SYS5State) -> SYS5State:
        print(f"\n{'='*80}")
        print("NODE 4: APP PARAMETER EXTRACTION")
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

            app_param_sheet = Node4ExtractAppParameters._find_app_parameter_sheet(excel_file)
            if not app_param_sheet:
                error_msg = f"Could not find App Parameter sheet. Available: {excel_file.sheet_names}"
                print(f"[ERROR] {error_msg}\n")
                errors.append(error_msg)
                state["errors"] = errors
                return state

            app_param_df = pd.read_excel(abs_sys_req_path, sheet_name=app_param_sheet)
            print(f"[LOG] App Parameter sheet loaded: {app_param_sheet}, {len(app_param_df)} rows\n")

        except Exception as e:
            error_msg = f"Could not load App Parameter sheet: {str(e)}"
            print(f"[ERROR] {error_msg}\n")
            errors.append(error_msg)
            state["errors"] = errors
            return state

        # Column A is treated as the header/identifier column for keying entries
        if len(app_param_df.columns) == 0:
            error_msg = "App Parameter sheet has no columns"
            print(f"[ERROR] {error_msg}\n")
            errors.append(error_msg)
            state["errors"] = errors
            return state

        header_col = app_param_df.columns[0]

        # Columns B to G (index 1 to 6) to extract
        data_cols = list(app_param_df.columns[1:7])
        print(f"[LOG] Header column (A): {repr(header_col)}")
        print(f"[LOG] Data columns (B-G): {data_cols}\n")

        # Extract feature numbers from requirements
        feature_nums = []
        for req in requirements:
            req_id = req.get("req_id", "")
            match = re.search(r'(\d{3})', req_id)
            if match and match.group(1) not in feature_nums:
                feature_nums.append(match.group(1))

        feature_details = dict(state.get("feature_details") or {})

        for feature_num in feature_nums:
            print(f"[LOG] Processing feature '{feature_num}'...")

            # Find feature column
            feature_col = None
            for col in app_param_df.columns:
                if str(col).strip() == feature_num:
                    feature_col = col
                    break

            if feature_col is None:
                print(f"[LOG] No column found matching '{feature_num}'\n")
                continue

            print(f"[LOG] Found column: {repr(feature_col)}")

            # Filter for ideographic zero marker
            filtered = app_param_df[
                app_param_df[feature_col].astype(str).str.contains(IDEOGRAPHIC_ZERO, na=False)
            ]

            print(f"[LOG] Valid rows with ideographic zero (〇): {len(filtered)}\n")

            for idx, row in filtered.iterrows():
                header_value = str(row[header_col]).strip()

                # Key = sheet name + header column value
                key = f"{app_param_sheet}_{header_value}"

                # Save columns B to G
                row_data = {}
                for col in data_cols:
                    val = row[col]
                    row_data[str(col)] = None if pd.isna(val) else val

                row_data["feature_number"] = feature_num
                row_data["header_value"] = header_value
                row_data["sheet_name"] = app_param_sheet

                feature_details[key] = row_data
                print(f"[LOG] {key} -> {row_data}")

        # Update in-memory store (persists across process, independent of state)
        update_feature_details_memory(feature_details)

        # Write feature_details to JSON, in addition to the in-memory store
        output_dir = config.get("output_dir")
        abs_output_dir = resolve_path(output_dir) if output_dir else None
        if abs_output_dir:
            ensure_directory_exists(abs_output_dir)
            timestamp = state.get("timestamp", "")
            json_file = os.path.join(abs_output_dir, f"feature_details_{timestamp}.json")
            with open(json_file, 'w') as f:
                json.dump(feature_details, f, indent=2, default=str)
            print(f"[LOG] Feature details saved to: {json_file}\n")

        state["feature_details"] = feature_details
        state["errors"] = errors

        print(f"\n[LOG] Total feature details in store: {len(feature_details)}\n")
        print(f"{'='*80}")
        print("NODE 4 COMPLETED")
        print(f"{'='*80}\n")

        return state
