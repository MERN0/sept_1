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

        sys_req_file = config.get("system_requirements_file")
        input_folder = config.get("input_folder_path")
        output_dir = config.get("output_dir")

        if not sys_req_file:
            error_msg = "Missing system_requirements_file in config"
            print(f"[ERROR] {error_msg}\n")
            errors.append(error_msg)
            state["errors"] = errors
            return state

        abs_sys_req_path = resolve_path(sys_req_file)
        abs_input_folder = resolve_path(input_folder) if input_folder else None
        abs_output_dir = resolve_path(output_dir)

        # Search for Command List file in input directory
        abs_cmd_list_path = None
        if abs_input_folder and os.path.exists(abs_input_folder):
            for filename in os.listdir(abs_input_folder):
                if "command" in filename.lower() and "list" in filename.lower() and filename.endswith('.xlsx'):
                    abs_cmd_list_path = os.path.join(abs_input_folder, filename)
                    break

        print(f"[LOG] System Requirements file: {abs_sys_req_path}")
        if abs_cmd_list_path:
            print(f"[LOG] Command List file: {abs_cmd_list_path}")
        else:
            print(f"[LOG] Command List file: Not found (will continue without it)")
        print(f"[LOG] Output directory: {abs_output_dir}\n")

        try:
            # Validate System Requirements file exists
            if not os.path.exists(abs_sys_req_path):
                error_msg = f"System Requirements file not found: {abs_sys_req_path}"
                print(f"[ERROR] {error_msg}\n")
                errors.append(error_msg)
                state["errors"] = errors
                return state

            # Load Index sheet to map feature numbers to names and groups
            print(f"[LOG] Loading Index sheet from System Requirements file...")
            try:
                index_df = pd.read_excel(abs_sys_req_path, sheet_name="Index")
                print(f"[LOG] Index sheet loaded: {len(index_df)} rows\n")
            except Exception as e:
                print(f"[WARNING] Could not load Index sheet: {str(e)}")
                index_df = None

            # Load Master Comm Matrix
            print(f"[LOG] Loading Master Comm Matrix sheet...")
            try:
                comm_matrix_df = pd.read_excel(abs_sys_req_path, sheet_name="Master Comm Matrix (CAN)")
                print(f"[LOG] Master Comm Matrix loaded: {len(comm_matrix_df)} rows, {len(comm_matrix_df.columns)} columns\n")
            except Exception as e:
                print(f"[WARNING] Could not load Master Comm Matrix: {str(e)}")
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

                # Find related signals in Master Comm Matrix
                related_signals = Node2FindSignalsAndCommands._find_related_signals(
                    feature_num, comm_matrix_df
                )

                if related_signals:
                    print(f"      → Found {len(related_signals)} related signals")

                    # For each signal, find related commands
                    for signal in related_signals:
                        message_name = signal.get("Message Name")

                        if message_name and cmd_list_df is not None:
                            # Search for command details
                            cmd_details = Node2FindSignalsAndCommands._find_command_details(
                                message_name, cmd_list_df
                            )

                            if cmd_details:
                                signal["feature_details"] = cmd_details
                                print(f"         → {message_name}: Found command details\n")
                            else:
                                print(f"         → {message_name}: No command details found\n")

                        signals_data.append({
                            "req_id": req_id,
                            "feature_number": feature_num,
                            "signal": signal
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
    def _find_related_signals(feature_num: str, comm_matrix_df: Optional[pd.DataFrame]) -> List[Dict[str, Any]]:
        """
        Find signals in Master Comm Matrix marked with the feature number

        Looks for columns with feature numbers (001-083) and extracts rows
        where the feature column is marked with ✕ or ⊕ or other markers

        Args:
            feature_num: Feature number (e.g., "019")
            comm_matrix_df: Master Comm Matrix DataFrame

        Returns:
            List of signal dictionaries
        """
        if comm_matrix_df is None:
            return []

        signals = []

        try:
            # Look for feature column
            feature_col = None
            for col in comm_matrix_df.columns:
                if str(col).strip() == feature_num:
                    feature_col = col
                    break

            if feature_col is None:
                return signals

            # Find rows marked in this feature column
            marked_rows = comm_matrix_df[comm_matrix_df[feature_col].notna()]
            marked_rows = marked_rows[
                marked_rows[feature_col].astype(str).str.contains(
                    r'[✕⊕x✓]', na=False, regex=True
                )
            ]

            # Extract signal details from marked rows
            for idx, row in marked_rows.iterrows():
                signal_dict = {
                    "Signal ID": row.get("Signal ID") if "Signal ID" in row.index else None,
                    "Message Name": row.get("Message Name") if "Message Name" in row.index else None,
                    "Message IDs": row.get("Message IDs") if "Message IDs" in row.index else None,
                    "Logical Signal Name": row.get("Logical Signal Name") if "Logical Signal Name" in row.index else None,
                    "Signal name": row.get("Signal name") if "Signal name" in row.index else None,
                    "Signal Description": row.get("Signal Description") if "Signal Description" in row.index else None,
                    "Physical Range": row.get("Physical Range") if "Physical Range" in row.index else None,
                    "Unit": row.get("Unit") if "Unit" in row.index else None,
                    "ECU HW (Transmitting)": row.get("ECU HW (Transmitting)") if "ECU HW (Transmitting)" in row.index else None,
                    "ECU HW (Receiving)": row.get("ECU HW (Receiving)") if "ECU HW (Receiving)" in row.index else None
                }
                signals.append(signal_dict)

        except Exception as e:
            pass

        return signals

    @staticmethod
    def _find_command_details(message_name: str, cmd_list_df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """
        Find command details from Command List sheet (columns B to I)

        Args:
            message_name: Message name to search for
            cmd_list_df: Command List DataFrame

        Returns:
            Dictionary with command details from columns B to I, or None
        """
        try:
            # Search for matching message name
            matching_rows = cmd_list_df[
                cmd_list_df.iloc[:, 0].astype(str).str.contains(message_name, case=False, na=False)
            ]

            if len(matching_rows) > 0:
                row = matching_rows.iloc[0]

                # Extract columns B to I (indices 1 to 8)
                cmd_details = {}
                col_names = ["Column B", "Column C", "Column D", "Column E", "Column F", "Column G", "Column H", "Column I"]

                for idx, col_name in enumerate(col_names):
                    if idx + 1 < len(row):
                        actual_col_name = cmd_list_df.columns[idx + 1] if idx + 1 < len(cmd_list_df.columns) else col_name
                        cmd_details[actual_col_name] = row.iloc[idx + 1]

                return cmd_details

        except Exception as e:
            pass

        return None
