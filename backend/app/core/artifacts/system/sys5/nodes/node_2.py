"""Node 2: Signal and Command Extraction from Communication Matrices"""

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

IDEOGRAPHIC_ZERO = "〇"  # 〇


class Node2FindSignalsAndCommands:
    """
    Node 2: Find Signal Names from filtered rows in Master Comm Matrix and
    extract Command details from Command List sheet.
    """

    @staticmethod
    def _find_command_list_file(input_folder: str):
        """Auto-discover command list file in input folder"""
        if not os.path.isdir(input_folder):
            return None

        for filename in os.listdir(input_folder):
            if filename.lower().endswith('.xlsx'):
                if 'command' in filename.lower() and 'list' in filename.lower():
                    return os.path.join(input_folder, filename)
        return None

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

        # Find and load Command List file
        command_list_file = Node2FindSignalsAndCommands._find_command_list_file(abs_input_folder)
        if not command_list_file:
            error_msg = f"Command List file not found in: {abs_input_folder}"
            print(f"[ERROR] {error_msg}\n")
            errors.append(error_msg)
            state["errors"] = errors
            return state

        print(f"[LOG] Command List file: {command_list_file}\n")

        # Find the correct sheet name, handling whitespace
        excel_file = pd.ExcelFile(command_list_file)
        command_sheet = None
        for sheet in excel_file.sheet_names:
            if sheet.strip().lower() == "command list":
                command_sheet = sheet
                break

        if not command_sheet:
            error_msg = f"Could not find 'Command List' sheet. Available sheets: {excel_file.sheet_names}"
            print(f"[ERROR] {error_msg}\n")
            errors.append(error_msg)
            state["errors"] = errors
            return state

        try:
            command_list_df = pd.read_excel(command_list_file, sheet_name=command_sheet)
            print(f"[LOG] Command List loaded from sheet '{command_sheet}': {len(command_list_df)} rows\n")
        except Exception as e:
            error_msg = f"Could not load Command List sheet: {str(e)}"
            print(f"[ERROR] {error_msg}\n")
            errors.append(error_msg)
            state["errors"] = errors
            return state

        feature_details = dict(state.get("feature_details") or {})

        # Feature/sheet numbers to look up, derived from requirement IDs
        feature_nums = []
        for req in requirements:
            req_id = req.get("req_id", "")
            match = re.search(r'(\d{3})', req_id)
            if match and match.group(1) not in feature_nums:
                feature_nums.append(match.group(1))

        for feature_num in feature_nums:
            print(f"[LOG] Processing feature '{feature_num}'...")

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

            print(f"[LOG] Rows with ideographic zero (〇): {len(filtered)}\n")

            # Extract Signal Names from filtered rows
            if 'Signal Name' not in filtered.columns:
                print(f"[LOG] 'Signal Name' column not found\n")
                continue

            for idx, row in filtered.iterrows():
                signal_name = str(row['Signal Name']).strip()

                # Search for signal name in Command List
                cmd_match = command_list_df[
                    command_list_df['Signal Name'].astype(str).str.strip() == signal_name
                ]

                if len(cmd_match) == 0:
                    print(f"[LOG] Signal '{signal_name}' not found in Command List")
                    continue

                cmd_row = cmd_match.iloc[0]

                # Extract Command Name and Signal Description
                signal_data = {
                    "req_id": "",
                    "feature_number": feature_num,
                    "signal_name": signal_name,
                    "command_name": str(cmd_row.get('Command Name', '')),
                    "signal_description": str(cmd_row.get('Signal Description', ''))
                }

                # Match signal to requirement
                for req in requirements:
                    req_id = req.get("req_id", "")
                    match = re.search(r'(\d{3})', req_id)
                    if match and match.group(1) == feature_num:
                        signal_data["req_id"] = req_id
                        break

                feature_details[signal_name] = signal_data
                print(f"[LOG] Extracted: {signal_name} -> {signal_data['command_name']}, {signal_data['signal_description']}")

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

        print(f"\n[LOG] Total feature details extracted: {len(feature_details)}\n")
        print(f"{'='*80}")
        print("NODE 2 COMPLETED")
        print(f"{'='*80}\n")

        return state
