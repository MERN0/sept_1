"""Node 5: Extract Model Input Mapping + Tolerances, bundle with Test Patterns"""

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

# Words too short/generic to be useful as keyword-match tokens for Tolerances
STOPWORDS = {"the", "for", "and", "rate", "in", "a", "of", "on", "is"}


class Node5ExtractModelConfig:
    """
    Node 5: Extract Model_Input_Mapping and Tolerances sheets from the
    configuration file. Neither sheet has a feature-number column or an
    ideographic-zero marker (unlike Nodes 2-4), so instead of that filter:

    - Model_Input_Mapping is filtered down to only the signals already known
      from state["feature_details"] (substring match, same idiom as Node 3
      against Command List).
    - Tolerances is filtered down by keyword match between each row's
      Description and the requirement descriptions/verification
      criteria/test pattern content collected so far.

    Both sheets can run 500+ rows, so this filtering keeps the output usable
    for a later step that maps requirement + test pattern to config data.
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
    def _normalize(name: str) -> str:
        return str(name).strip().lower().replace('_', '').replace(' ', '')

    @staticmethod
    def _collect_known_signal_names(feature_details):
        """Pull signal_name / logical_signal_name values out of feature_details entries"""
        known = set()
        for entry in feature_details.values():
            if not isinstance(entry, dict):
                continue
            for key in ("signal_name", "logical_signal_name"):
                if entry.get(key):
                    known.add(str(entry[key]))
        return known

    @staticmethod
    def _build_keyword_corpus(requirements, test_patterns):
        """Concatenate requirement + test pattern text into one lowercase corpus"""
        parts = []
        for req in requirements:
            parts.append(str(req.get("data", {}).get("Description", "")))
            parts.append(str(req.get("verification_criteria") or ""))

            req_id = req.get("req_id", "")
            pattern = test_patterns.get(req_id, {})
            parts.append(str(pattern.get("summary", "")))

            for tc in pattern.get("test_cases", []):
                parts.append(str(tc.get("expected_result", "")))
                for val in tc.get("preconditions", {}).values():
                    parts.append(str(val))
                for val in tc.get("actions", {}).values():
                    parts.append(str(val))

        return " ".join(parts).lower()

    @staticmethod
    def execute(state: SYS5State) -> SYS5State:
        print(f"\n{'='*80}")
        print("NODE 5: MODEL CONFIG EXTRACTION")
        print(f"{'='*80}\n")

        config = state["config"]
        requirements = state.get("requirements", [])
        test_patterns = state.get("test_patterns", {})
        feature_details = state.get("feature_details", {})
        errors = state.get("errors", [])

        input_folder = config.get("input_folder_path")
        abs_input_folder = resolve_path(input_folder) if input_folder else None

        if not abs_input_folder:
            error_msg = "input_folder_path not configured"
            print(f"[ERROR] {error_msg}\n")
            errors.append(error_msg)
            state["errors"] = errors
            return state

        config_file = Node5ExtractModelConfig._find_config_file(abs_input_folder)
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

        mapping_sheet = Node5ExtractModelConfig._find_sheet(excel_file, ["model", "input", "map"])
        tolerances_sheet = Node5ExtractModelConfig._find_sheet(excel_file, ["toleranc"])

        if not mapping_sheet or not tolerances_sheet:
            error_msg = (
                f"Could not find required sheets. Model Input Mapping found: {mapping_sheet}, "
                f"Tolerances found: {tolerances_sheet}. Available: {excel_file.sheet_names}"
            )
            print(f"[ERROR] {error_msg}\n")
            errors.append(error_msg)
            state["errors"] = errors
            return state

        # --- Parse Model_Input_Mapping (by column position) ---
        try:
            mapping_df = pd.read_excel(config_file, sheet_name=mapping_sheet)
            print(f"[LOG] Model Input Mapping loaded: {mapping_sheet}, {len(mapping_df)} rows\n")
        except Exception as e:
            error_msg = f"Could not load Model Input Mapping sheet: {str(e)}"
            print(f"[ERROR] {error_msg}\n")
            errors.append(error_msg)
            state["errors"] = errors
            return state

        cols = mapping_df.columns
        if len(cols) < 7:
            error_msg = f"Model Input Mapping sheet has fewer than 7 columns: {list(cols)}"
            print(f"[ERROR] {error_msg}\n")
            errors.append(error_msg)
            state["errors"] = errors
            return state

        sl_no_col, signal_col, test_input_col, model_input_col, output1_col, output2_col, remark_col = cols[:7]

        # Signal column is merged in the source sheet -> continuation rows read as NaN
        mapping_df[sl_no_col] = mapping_df[sl_no_col].ffill()
        mapping_df[signal_col] = mapping_df[signal_col].ffill()

        all_signal_variants = {}
        for idx, row in mapping_df.iterrows():
            signal_name = str(row[signal_col]).strip()
            if not signal_name or signal_name.lower() == "nan":
                continue

            variant = {
                "test_case_input": None if pd.isna(row[test_input_col]) else row[test_input_col],
                "model_input": None if pd.isna(row[model_input_col]) else row[model_input_col],
                "model_output_to_ecu_1": None if pd.isna(row[output1_col]) else row[output1_col],
                "model_output_to_ecu_2": None if pd.isna(row[output2_col]) else row[output2_col],
                "remark": None if pd.isna(row[remark_col]) else row[remark_col],
            }
            all_signal_variants.setdefault(signal_name, []).append(variant)

        print(f"[LOG] Model Input Mapping: {len(all_signal_variants)} distinct signals before filtering\n")
        print(f"[DEBUG] Sample Model_Input_Mapping signal names: {list(all_signal_variants.keys())[:10]}\n")

        known_signal_names = Node5ExtractModelConfig._collect_known_signal_names(feature_details)
        known_normalized = {Node5ExtractModelConfig._normalize(n) for n in known_signal_names}
        print(f"[DEBUG] Known signal names from feature_details ({len(known_signal_names)}): "
              f"{list(known_signal_names)[:10]}\n")

        model_input_mapping = {}
        for signal_name, variants in all_signal_variants.items():
            normalized_signal = Node5ExtractModelConfig._normalize(signal_name)
            matched = any(
                normalized_signal in known or known in normalized_signal
                for known in known_normalized
            )
            if matched:
                model_input_mapping[signal_name] = variants

        print(f"[LOG] Model Input Mapping: {len(all_signal_variants)} signals -> "
              f"{len(model_input_mapping)} matched against known signals\n")

        # --- Parse Tolerances (by column position) ---
        try:
            tolerances_df = pd.read_excel(config_file, sheet_name=tolerances_sheet)
            print(f"[LOG] Tolerances loaded: {tolerances_sheet}, {len(tolerances_df)} rows\n")
        except Exception as e:
            error_msg = f"Could not load Tolerances sheet: {str(e)}"
            print(f"[ERROR] {error_msg}\n")
            errors.append(error_msg)
            state["errors"] = errors
            return state

        tol_cols = tolerances_df.columns
        if len(tol_cols) < 7:
            error_msg = f"Tolerances sheet has fewer than 7 columns: {list(tol_cols)}"
            print(f"[ERROR] {error_msg}\n")
            errors.append(error_msg)
            state["errors"] = errors
            return state

        sl_col, key_col, desc_col, example_col, unit_col, value_col, tol_unit_col = tol_cols[:7]
        remark_col_tol = tol_cols[7] if len(tol_cols) > 7 else None

        all_tolerances = {}
        for idx, row in tolerances_df.iterrows():
            tol_key = str(row[key_col]).strip()
            if not tol_key or tol_key.lower() == "nan":
                continue

            all_tolerances[tol_key] = {
                "description": None if pd.isna(row[desc_col]) else row[desc_col],
                "example": None if pd.isna(row[example_col]) else row[example_col],
                "unit": None if pd.isna(row[unit_col]) else row[unit_col],
                "value": None if pd.isna(row[value_col]) else row[value_col],
                "tolerance_unit": None if pd.isna(row[tol_unit_col]) else row[tol_unit_col],
                "remark": (None if remark_col_tol is None or pd.isna(row[remark_col_tol])
                           else row[remark_col_tol]),
            }

        print(f"[LOG] Tolerances: {len(all_tolerances)} entries before filtering\n")

        corpus = Node5ExtractModelConfig._build_keyword_corpus(requirements, test_patterns)

        tolerances = {}
        for tol_key, tol_data in all_tolerances.items():
            description = str(tol_data.get("description") or "")
            cleaned = description.lower().replace("tolerance for", "").strip()
            words = [w.strip(".,()") for w in cleaned.split()]
            keywords = [w for w in words if len(w) > 3 and w not in STOPWORDS]

            if any(keyword in corpus for keyword in keywords):
                tolerances[tol_key] = tol_data

        print(f"[LOG] Tolerances: {len(all_tolerances)} entries -> "
              f"{len(tolerances)} matched by keyword\n")

        # --- Bundle filtered config data with test patterns ---
        requirements_with_test_patterns = {}
        for req in requirements:
            req_id = req.get("req_id", "")
            requirements_with_test_patterns[req_id] = {
                "description": req.get("data", {}).get("Description", ""),
                "verification_criteria": req.get("verification_criteria"),
                "test_patterns": test_patterns.get(req_id, {}),
            }

        model_config = {
            "requirements_with_test_patterns": requirements_with_test_patterns,
            "model_input_mapping": model_input_mapping,
            "tolerances": tolerances,
        }

        # --- Persist: JSON file + state ---
        output_dir = config.get("output_dir")
        abs_output_dir = resolve_path(output_dir) if output_dir else None
        if abs_output_dir:
            ensure_directory_exists(abs_output_dir)
            timestamp = state.get("timestamp", "")
            json_file = os.path.join(abs_output_dir, f"model_config_{timestamp}.json")
            with open(json_file, 'w') as f:
                json.dump(model_config, f, indent=2, default=str)
            print(f"[LOG] Model config saved to: {json_file}\n")

        state["model_config"] = model_config
        state["errors"] = errors

        print(f"{'='*80}")
        print("NODE 5 COMPLETED")
        print(f"{'='*80}\n")

        return state
