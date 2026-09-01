"""Test Node 1 with different path configurations"""
import os
from backend.app.core.artifacts.system.sys5 import generate

# Test 1: Relative paths (current directory-based)
print("\n" + "="*80)
print("TEST 1: RELATIVE PATHS")
print("="*80)

config_relative = {
    "project_name": "test_relative",
    "version": "V1.0",
    "input_folder_path": "files/test@tataelxsi.co.in/swe6_5/V1.0/SWE6/input",
    "output_dir": "files/test@tataelxsi.co.in/swe6_5/V1.0/SWE6/output",
    "req_filename": "reqs_to_use.xlsx",
    "req_sheet_name": "005",
}

result = generate(config_relative)
print(result)

# Test 2: Absolute paths
print("\n\n" + "="*80)
print("TEST 2: ABSOLUTE PATHS")
print("="*80)

abs_input = os.path.abspath("files/test@tataelxsi.co.in/swe6_5/V1.0/SWE6/input")
abs_output = os.path.abspath("files/test@tataelxsi.co.in/swe6_5/V1.0/SWE6/output")

config_absolute = {
    "project_name": "test_absolute",
    "version": "V1.0",
    "input_folder_path": abs_input,
    "output_dir": abs_output,
    "req_filename": "reqs_to_use.xlsx",
    "req_sheet_name": "005",
}

result = generate(config_absolute)
print(result)

print("\n" + "="*80)
print("ALL TESTS COMPLETED")
print("="*80)
