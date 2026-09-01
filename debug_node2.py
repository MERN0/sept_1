"""Debug script to test Node 2 signal extraction with actual Excel data"""

import pandas as pd
import os

# Test file path - adjust based on your actual file location
input_folder = "files/test@tataelxsi.co.in/swe6_5/V1.0/SWE6/input"
req_filename = "reqs_to_use.xlsx"
abs_path = os.path.abspath(os.path.join(input_folder, req_filename))

if not os.path.exists(abs_path):
    print(f"[ERROR] File not found: {abs_path}")
    print(f"Checking current directory: {os.getcwd()}")
    print(f"Files in input folder:")
    if os.path.exists(input_folder):
        for f in os.listdir(input_folder):
            print(f"  - {f}")
else:
    print(f"[LOG] Loading Master Comm Matrix from: {abs_path}\n")

    try:
        # Load Master Comm Matrix
        comm_matrix_df = pd.read_excel(abs_path, sheet_name="Master Comm Matrix (CAN)")
        print(f"[LOG] Loaded {len(comm_matrix_df)} rows, {len(comm_matrix_df.columns)} columns\n")

        # Print column headers
        print("[LOG] Column Headers:")
        for idx, col in enumerate(comm_matrix_df.columns):
            print(f"  [{idx:2d}] {repr(col)}")

        print("\n[LOG] Looking for feature '019'...")
        feature_num = "019"

        # Find column with header matching feature_num
        feature_col = None
        for col in comm_matrix_df.columns:
            col_str = str(col).strip()
            print(f"  Comparing {repr(col_str)} == {repr(feature_num)}: {col_str == feature_num}")
            if col_str == feature_num:
                feature_col = col
                print(f"  → MATCH: Column {repr(col)}")
                break

        if feature_col is None:
            print(f"  [WARNING] Feature column not found for '{feature_num}'")
            print(f"  Trying partial matching...")
            for col in comm_matrix_df.columns:
                if str(col).strip() == feature_num or feature_num in str(col):
                    print(f"  → Potential match: {repr(col)}")
        else:
            print(f"\n[LOG] Feature column found: {repr(feature_col)}")

            # Look for Signal Name column
            signal_name_col = None
            for col in comm_matrix_df.columns:
                if str(col).strip().lower() == "signal name":
                    signal_name_col = col
                    print(f"[LOG] Signal Name column found (exact): {repr(col)}")
                    break

            if signal_name_col is None:
                for col in comm_matrix_df.columns:
                    if "signal name" in str(col).strip().lower():
                        signal_name_col = col
                        print(f"[LOG] Signal Name column found (partial): {repr(col)}")
                        break

            if signal_name_col:
                print(f"\n[LOG] Showing first 10 rows of {repr(feature_col)} column:")
                for idx, val in enumerate(comm_matrix_df[feature_col].head(10)):
                    print(f"  Row {idx}: {repr(val)}")

                print(f"\n[LOG] Filtering rows with markers (x, X, 〇)...")
                marked_rows = comm_matrix_df[comm_matrix_df[feature_col].notna()]
                marked_rows = marked_rows[
                    marked_rows[feature_col].astype(str).str.contains(
                        r'[xX〇]', na=False, regex=True
                    )
                ]

                print(f"[LOG] Found {len(marked_rows)} marked rows")

                print(f"\n[LOG] Signal Names from marked rows:")
                for idx, row in marked_rows.iterrows():
                    signal_name = row.get(signal_name_col)
                    feature_val = row.get(feature_col)
                    print(f"  Row {idx}: {repr(signal_name)} (marker: {repr(feature_val)})")
            else:
                print("[ERROR] Signal Name column not found")

    except Exception as e:
        print(f"[ERROR] {str(e)}")
        import traceback
        traceback.print_exc()
