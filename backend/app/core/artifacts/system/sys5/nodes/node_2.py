"""Node 2: Signal and Command Extraction from Communication Matrices"""

import json
import os
import sys
import re
from typing import Dict, Any, List, Optional
import pandas as pd

_workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../.."))
if _workspace_root not in sys.path:
    sys.path.insert(0, _workspace_root)

try:
    from ..state import SYS5State
    from ..utils import resolve_path, ensure_directory_exists
except ImportError:
    from backend.app.core.artifacts.system.sys5.state import SYS5State
    from backend.app.core.artifacts.system.sys5.utils import resolve_path, ensure_directory_exists


class Node2FindSignalsAndCommands:
    """
    Node 2: Extract signals and commands from communication matrices

    Process:
    1. For each requirement, extract feature number
    2. Look up feature name and group in Index sheet
    3. Find related signals in Master Comm Matrix
    4. Find related commands in Command List
    5. Save feature details and signal mappings to JSON
    """

    @staticmethod
    def execute(state: SYS5State) -> SYS5State:
        """
        Execute Node 2 - Signal and Command Extraction

        Args:
            state: Current workflow state from Node 1

        Returns:
            Updated state with signals, commands, and feature details
        """
        print(f"\n{'='*80}")
        print("NODE 2: SIGNAL AND COMMAND EXTRACTION")
        print(f"{'='*80}\n")

        config = state["config"]
        requirements = state.get("requirements", [])
        errors = state.get("errors", [])
        signals_data = []
        feature_details_map = {}

        input_folder = config.get("input_folder_path")
        output_dir = config.get("output_dir")
        req_filename = config.get("req_filename", "reqs_to_use.xlsx")

        abs_input_folder = resolve_path(input_folder) if input_folder else None
        abs_output_dir = resolve_path(output_dir)

        # System Requirements file is the same req_filename used in Node 1
        abs_sys_req_path = os.path.join(abs_input_folder, req_filename) if abs_input_folder else None

        # Search for Command List file in input directory
        abs_cmd_list_path = None
        if abs_input_folder and os.path.exists(abs_input_folder):
            for filename in os.listdir(abs_input_folder):
                if filename.endswith('.xlsx') and "command" in filename.lower() and "list" in filename.lower():
                    abs_cmd_list_path = os.path.join(abs_input_folder, filename)
                    break

        if not abs_sys_req_path or not os.path.exists(abs_sys_req_path):
            error_msg = f"System Requirements file not found: {abs_sys_req_path}"
            print(f"[ERROR] {error_msg}\n")
            errors.append(error_msg)
            state["errors"] = errors
            return state

        print(f"[LOG] System Requirements file: {abs_sys_req_path}")
        if abs_cmd_list_path:
            print(f"[LOG] Command List file: {abs_cmd_list_path}")
        else:
            print(f"[LOG] Command List file: Not found (will continue without it)")
        print(f"[LOG] Output directory: {abs_output_dir}\n")

        try:
            # Get available sheets for better error messages
            available_sheets = []
            try:
                import openpyxl
                wb = openpyxl.load_workbook(abs_sys_req_path)
                available_sheets = wb.sheetnames
                print(f"[LOG] Available sheets in {abs_sys_req_path}:")
                for sheet in available_sheets:
                    print(f"      - {repr(sheet)}")
                print()
            except Exception as e:
                print(f"[WARNING] Could not read sheet names: {str(e)}\n")

            # Load Index sheet to map feature numbers to names and groups
            print(f"[LOG] Loading Index sheet from System Requirements file...")
            try:
                index_df = pd.read_excel(abs_sys_req_path, sheet_name="Index")
                print(f"[LOG] Index sheet loaded: {len(index_df)} rows\n")
            except Exception as e:
                print(f"[WARNING] Could not load Index sheet: {str(e)}")
                if available_sheets:
                    print(f"[LOG] Available sheets: {available_sheets}")
                print()
                index_df = None

            # Load Master Comm Matrix
            print(f"[LOG] Loading Master Comm Matrix sheet...")
            try:
                comm_matrix_df = pd.read_excel(abs_sys_req_path, sheet_name="Master Comm Matrix (CAN)")
                print(f"[LOG] Master Comm Matrix loaded: {len(comm_matrix_df)} rows, {len(comm_matrix_df.columns)} columns\n")
            except Exception as e:
                print(f"[WARNING] Could not load Master Comm Matrix (CAN): {str(e)}")
                if available_sheets:
                    print(f"[LOG] Available sheets: {available_sheets}")
                print()
                comm_matrix_df = None

            # Load Command List from separate file
            cmd_list_df = None
            if abs_cmd_list_path:
                print(f"[LOG] Loading Command List sheet...")
                try:
                    cmd_list_df = pd.read_excel(abs_cmd_list_path, sheet_name="Command List")
                    print(f"[LOG] Command List loaded: {len(cmd_list_df)} rows\n")
                except Exception as e:
                    print(f"[WARNING] Could not load Command List: {str(e)}")
                    cmd_list_df = None
            else:
                print(f"[LOG] Command List file not found in input directory, skipping command details\n")

            # Process each requirement
            print(f"[LOG] Processing {len(requirements)} requirements for signal matching...\n")

            for req in requirements:
                req_id = req.get("req_id", f"REQ_{req.get('row_index')}")

                # Extract feature number from REQ_ID (e.g., "019" → "019")
                feature_match = re.search(r'(\d{3})', req_id)
                if not feature_match:
                    print(f"[LOG] {req_id}: Could not extract feature number\n")
                    continue

                feature_num = feature_match.group(1)
                print(f"[LOG] Processing {req_id} with feature number {feature_num}...")

                # Look up feature details in Index sheet
                feature_info = Node2FindSignalsAndCommands._lookup_feature_details(
                    feature_num, index_df
                )

                if feature_info:
                    print(f"      → Feature Name: {feature_info.get('feature_name')}")
                    print(f"      → Feature Group: {feature_info.get('feature_group')}\n")
                    feature_details_map[feature_num] = feature_info
                else:
                    print(f"      → Feature details not found in Index sheet\n")

                # Find Signal Name values for valid rows marked under the feature column
                signal_names = Node2FindSignalsAndCommands._find_related_signals(
                    feature_num, comm_matrix_df
                )

                if signal_names:
                    print(f"      → Found {len(signal_names)} valid signal names")

                    for signal_name in signal_names:
                        if not signal_name:
                            continue

                        cmd_details = None
                        if cmd_list_df is not None:
                            cmd_details = Node2FindSignalsAndCommands._find_command_details(
                                signal_name, cmd_list_df
                            )

                        if cmd_details:
                            print(f"         → {signal_name}: Found command details\n")
                        else:
                            print(f"         → {signal_name}: No command details found\n")

                        signals_data.append({
                            "req_id": req_id,
                            "feature_number": feature_num,
                            "signal_name": signal_name,
                            "feature_details": cmd_details
                        })

            # Save signals and feature details to JSON
            ensure_directory_exists(abs_output_dir)
            timestamp = state["timestamp"]

            signals_file = os.path.join(abs_output_dir, f"signals_{timestamp}.json")
            features_file = os.path.join(abs_output_dir, f"feature_details_{timestamp}.json")

            # Save signals data
            signals_output = {
                "metadata": {
                    "total_signals": len(signals_data),
                    "total_features": len(feature_details_map),
                    "timestamp": timestamp
                },
                "signals": signals_data,
                "feature_details": feature_details_map
            }

            with open(signals_file, 'w') as f:
                json.dump(signals_output, f, indent=2)

            print(f"[SUCCESS] Signals saved to: {signals_file}")
            print(f"[LOG] Total signals extracted: {len(signals_data)}")
            print(f"[LOG] Total features mapped: {len(feature_details_map)}\n")

        except Exception as e:
            error_msg = f"Error during signal extraction: {str(e)}"
            print(f"[ERROR] {error_msg}\n")
            errors.append(error_msg)
            import traceback
            traceback.print_exc()

        # Update state
        state["signals"] = signals_data
        state["feature_details"] = feature_details_map
        state["errors"] = errors

        print(f"{'='*80}")
        print(f"NODE 2 COMPLETED")
        print(f"  Status: {'SUCCESS' if not errors else 'FAILED'}")
        print(f"  Signals extracted: {len(signals_data)}")
        print(f"  Features mapped: {len(feature_details_map)}")
        print(f"  Errors: {len(errors)}")
        print(f"{'='*80}\n")

        return state

    @staticmethod
    def _lookup_feature_details(feature_num: str, index_df: Optional[pd.DataFrame]) -> Optional[Dict[str, Any]]:
        """
        Look up feature name and group from Index sheet

        Args:
            feature_num: Feature number (e.g., "019")
            index_df: Index DataFrame

        Returns:
            Dictionary with feature_name and feature_group, or None
        """
        if index_df is None:
            return None

        try:
            # Look for rows where Feature Number column matches
            # Assuming Index sheet has columns like "Feature Number", "Feature Name", "Feature Group"
            matching_rows = index_df[
                (index_df.iloc[:, 0].astype(str) == feature_num) |
                (index_df.iloc[:, 0].astype(str).str.contains(feature_num, na=False))
            ]

            if len(matching_rows) > 0:
                row = matching_rows.iloc[0]
                return {
                    "feature_number": feature_num,
                    "feature_name": str(row.iloc[1]) if len(row) > 1 else "N/A",
                    "feature_group": str(row.iloc[2]) if len(row) > 2 else "N/A"
                }
        except Exception as e:
            pass

        return None

    @staticmethod
    def _find_related_signals(feature_num: str, comm_matrix_df: Optional[pd.DataFrame]) -> List[str]:
        """
        Find Signal Name values in Master Comm Matrix for rows marked valid
        under the feature column (column header == feature number / sheet name)

        A row is valid when the feature column cell contains a marker
        character (e.g. u+2717 ✕, u+2295 ⊕, or plain x/✓)

        Args:
            feature_num: Feature number (e.g., "019"), matches the column header
            comm_matrix_df: Master Comm Matrix DataFrame

        Returns:
            List of Signal Name values from valid rows
        """
        if comm_matrix_df is None:
            print(f"[WARNING] Master Comm Matrix DataFrame is None, cannot find signals")
            return []

        signal_names = []

        try:
            # Look for feature column (header matches the requirement sheet name)
            feature_col = None
            for col in comm_matrix_df.columns:
                if str(col).strip() == feature_num:
                    feature_col = col
                    break

            if feature_col is None:
                print(f"[WARNING] Feature column '{feature_num}' not found. Available columns:")
                for idx, col in enumerate(comm_matrix_df.columns):
                    print(f"        [{idx:2d}] {repr(str(col).strip())}")
                return signal_names

            print(f"[DEBUG] Found feature column: {repr(feature_col)}")

            # Look for "Signal name" column (case-insensitive, exact match preferred)
            signal_name_col = None
            for col in comm_matrix_df.columns:
                if str(col).strip().lower() == "signal name":
                    signal_name_col = col
                    break

            if signal_name_col is None:
                for col in comm_matrix_df.columns:
                    if "signal name" in str(col).strip().lower():
                        signal_name_col = col
                        break

            if signal_name_col is None:
                print(f"[WARNING] Signal Name column not found. Available columns:")
                for idx, col in enumerate(comm_matrix_df.columns):
                    print(f"        [{idx:2d}] {repr(str(col).strip())}")
                return signal_names

            print(f"[DEBUG] Found signal name column: {repr(signal_name_col)}")

            # Find rows marked with a valid marker character in the feature column
            # Valid markers: "x"/"X" and 〇 (IDEOGRAPHIC NUMBER ZERO, "○")
            marked_rows = comm_matrix_df[comm_matrix_df[feature_col].notna()]
            print(f"[DEBUG] Rows with non-null values in feature column: {len(marked_rows)}")

            marked_rows = marked_rows[
                marked_rows[feature_col].astype(str).str.contains(
                    r'[xX〇]', na=False, regex=True
                )
            ]
            print(f"[DEBUG] Rows matching marker pattern [xX〇]: {len(marked_rows)}")

            for idx, row in marked_rows.iterrows():
                signal_name = row.get(signal_name_col)
                if pd.notna(signal_name):
                    signal_names.append(str(signal_name).strip())

        except Exception as e:
            print(f"[ERROR] Exception in _find_related_signals: {str(e)}")
            import traceback
            traceback.print_exc()

        return signal_names

    @staticmethod
    def _find_command_details(signal_name: str, cmd_list_df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """
        Find command details from Command List sheet (columns B to I)

        Args:
            signal_name: Signal name to search for in Command List
            cmd_list_df: Command List DataFrame

        Returns:
            Dictionary with command details from columns B to I, or None
        """
        try:
            # Search for matching signal name in column A
            matching_rows = cmd_list_df[
                cmd_list_df.iloc[:, 0].astype(str).str.contains(re.escape(signal_name), case=False, na=False)
            ]

            if len(matching_rows) > 0:
                row = matching_rows.iloc[0]

                # Extract columns B to I (indices 1 to 8)
                cmd_details = {}
                for idx in range(1, 9):
                    if idx < len(cmd_list_df.columns):
                        col_name = cmd_list_df.columns[idx]
                        value = row.iloc[idx]
                        cmd_details[col_name] = None if pd.isna(value) else value

                return cmd_details

        except Exception:
            pass

        return None
