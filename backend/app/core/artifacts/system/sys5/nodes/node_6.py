"""Node 6: Extract Compound Commands and Library List, merge into model_config"""

import json
import os
import sys
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


class Node6ExtractCompoundAndLibrary:
    """
    Node 6: Extract Compound Commands and Library List sheets from the
    configuration file, and merge the results into state["model_config"]
    alongside the model_input_mapping/tolerances data from Node 5.

    Both sheets get a two-stage filter:
    1. Row-wide keyword pre-filter ("compound" / "lib" substring anywhere in
       the row), then exact-duplicate rows are dropped.
    2. From what remains, keep a row if either:
       - any cell contains the first underscore-token of a known signal name
         from state["feature_details"] as a substring (e.g. "Drv1" from
         "Drv1_Rx1_CmdSpd" matches even if only that first part is present), or
       - any cell contains "initial" or "default" as a substring (always
         included regardless of signal match).
    """

    @staticmethod
    def _find_config_file(input_folder: str):
        """Auto-discover configuration file in input folder"""
        if not os.path.isdir(input_folder):
            return None

        for filename in os.listdir(input_folder):
            if filename.lower().endswith('.xlsx') and 'config' in filename.lower():
                return os.path.join(input_folder, filename)
        return None

    @staticmethod
    def _find_sheet(excel_file, required_words):
        """Find a sheet whose normalized name contains all required_words"""
        for sheet in excel_file.sheet_names:
            normalized = sheet.strip().lower().replace('_', ' ')
            if all(word in normalized for word in required_words):
                return sheet
        return None

    @staticmethod
    def _collect_known_first_tokens(feature_details):
        """First underscore-token of each known signal_name/logical_signal_name"""
        tokens = set()
        for entry in feature_details.values():
            if not isinstance(entry, dict):
                continue
            for key in ("signal_name", "logical_signal_name"):
                name = entry.get(key)
                if name:
                    first_token = str(name).split('_')[0].strip().lower()
                    if first_token:
                        tokens.add(first_token)
        return tokens

    @staticmethod
    def _row_text(row):
        return " ".join(str(v).lower() for v in row.values if pd.notna(v))

    @staticmethod
    def _row_contains(row, keyword):
        return keyword.lower() in Node6ExtractCompoundAndLibrary._row_text(row)

    @staticmethod
    def _row_matches_signal_or_keyword(row, first_tokens):
        row_text = Node6ExtractCompoundAndLibrary._row_text(row)
        if any(tok in row_text for tok in first_tokens):
            return True
        return "initial" in row_text or "default" in row_text

    @staticmethod
    def _extract_sheet(df, sheet_name, pre_filter_keyword, first_tokens):
        """Apply the two-stage filter to one sheet and return a keyed dict of rows"""
        # Stage 1: row-wide keyword pre-filter, then drop exact duplicate rows
        pre_filtered = df[df.apply(
            lambda r: Node6ExtractCompoundAndLibrary._row_contains(r, pre_filter_keyword), axis=1
        )]
        pre_filtered = pre_filtered.drop_duplicates().reset_index(drop=True)
        pre_count = len(pre_filtered)

        # Stage 2: keep rows matching a known signal's first token, or initial/default
        selected = pre_filtered[pre_filtered.apply(
            lambda r: Node6ExtractCompoundAndLibrary._row_matches_signal_or_keyword(r, first_tokens), axis=1
        )]

        first_col = df.columns[0]
        result = {}
        for idx, row in selected.iterrows():
            key_value = str(row[first_col]).strip() if pd.notna(row[first_col]) else str(idx)
            key = f"{sheet_name}_{key_value}"
            row_data = {str(col): (None if pd.isna(row[col]) else row[col]) for col in df.columns}
            # Avoid collisions if the first column isn't unique
            suffix = 1
            unique_key = key
            while unique_key in result:
                suffix += 1
                unique_key = f"{key}_{suffix}"
            result[unique_key] = row_data

        return result, pre_count, len(selected)

    @staticmethod
    def execute(state: SYS5State) -> SYS5State:
        print(f"\n{'='*80}")
        print("NODE 6: COMPOUND COMMANDS AND LIBRARY LIST EXTRACTION")
        print(f"{'='*80}\n")

        config = state["config"]
        feature_details = state.get("feature_details", {})
        errors = state.get("errors", [])
        model_config = dict(state.get("model_config") or {})

        input_folder = config.get("input_folder_path")
        abs_input_folder = resolve_path(input_folder) if input_folder else None

        if not abs_input_folder:
            error_msg = "input_folder_path not configured"
            print(f"[ERROR] {error_msg}\n")
            errors.append(error_msg)
            state["errors"] = errors
            return state

        config_file = Node6ExtractCompoundAndLibrary._find_config_file(abs_input_folder)
        if not config_file:
            error_msg = f"Configuration file not found in: {abs_input_folder}"
            print(f"[ERROR] {error_msg}\n")
            errors.append(error_msg)
            state["errors"] = errors
            return state

        print(f"[LOG] Configuration file: {config_file}\n")

        try:
            excel_file = pd.ExcelFile(config_file)
            print(f"[LOG] Available sheets: {excel_file.sheet_names}\n")
        except Exception as e:
            error_msg = f"Could not open configuration file: {str(e)}"
            print(f"[ERROR] {error_msg}\n")
            errors.append(error_msg)
            state["errors"] = errors
            return state

        compound_sheet = Node6ExtractCompoundAndLibrary._find_sheet(excel_file, ["compound"])
        library_sheet = Node6ExtractCompoundAndLibrary._find_sheet(excel_file, ["librar"])

        if not compound_sheet or not library_sheet:
            error_msg = (
                f"Could not find required sheets. Compound Commands found: {compound_sheet}, "
                f"Library List found: {library_sheet}. Available: {excel_file.sheet_names}"
            )
            print(f"[ERROR] {error_msg}\n")
            errors.append(error_msg)
            state["errors"] = errors
            return state

        first_tokens = Node6ExtractCompoundAndLibrary._collect_known_first_tokens(feature_details)
        print(f"[DEBUG] Known signal first-tokens ({len(first_tokens)}): {list(first_tokens)[:10]}\n")

        # --- Compound Commands ---
        try:
            compound_df = pd.read_excel(config_file, sheet_name=compound_sheet)
            print(f"[LOG] Compound Commands loaded: {compound_sheet}, {len(compound_df)} rows\n")
        except Exception as e:
            error_msg = f"Could not load Compound Commands sheet: {str(e)}"
            print(f"[ERROR] {error_msg}\n")
            errors.append(error_msg)
            state["errors"] = errors
            return state

        compound_commands, compound_pre, compound_final = Node6ExtractCompoundAndLibrary._extract_sheet(
            compound_df, compound_sheet, "compound", first_tokens
        )
        print(f"[LOG] Compound Commands: {len(compound_df)} rows -> {compound_pre} contain 'compound' "
              f"(deduped) -> {compound_final} matched signal/initial/default\n")

        # --- Library List ---
        try:
            library_df = pd.read_excel(config_file, sheet_name=library_sheet)
            print(f"[LOG] Library List loaded: {library_sheet}, {len(library_df)} rows\n")
        except Exception as e:
            error_msg = f"Could not load Library List sheet: {str(e)}"
            print(f"[ERROR] {error_msg}\n")
            errors.append(error_msg)
            state["errors"] = errors
            return state

        library_list, library_pre, library_final = Node6ExtractCompoundAndLibrary._extract_sheet(
            library_df, library_sheet, "lib", first_tokens
        )
        print(f"[LOG] Library List: {len(library_df)} rows -> {library_pre} contain 'lib' "
              f"(deduped) -> {library_final} matched signal/initial/default\n")

        model_config["compound_commands"] = compound_commands
        model_config["library_list"] = library_list

        # --- Persist: JSON file + state ---
        output_dir = config.get("output_dir")
        abs_output_dir = resolve_path(output_dir) if output_dir else None
        if abs_output_dir:
            ensure_directory_exists(abs_output_dir)
            timestamp = state.get("timestamp", "")
            json_file = os.path.join(abs_output_dir, f"model_config_{timestamp}.json")
            with open(json_file, 'w') as f:
                json.dump(model_config, f, indent=2, default=str)
            print(f"[LOG] Model config (with compound commands + library list) saved to: {json_file}\n")

        state["model_config"] = model_config
        state["errors"] = errors

        print(f"{'='*80}")
        print("NODE 6 COMPLETED")
        print(f"{'='*80}\n")

        return state
