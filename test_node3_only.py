#!/usr/bin/env python
"""Test Node 3 only"""

import os
import sys
from datetime import datetime

# Add workspace to path
_workspace_root = os.path.abspath(os.path.dirname(__file__))
if _workspace_root not in sys.path:
    sys.path.insert(0, _workspace_root)

from backend.app.core.artifacts.system.sys5.state import SYS5State
from backend.app.core.artifacts.system.sys5.nodes.node_3 import Node3ExtractLogicalSignals

# Configuration
config = {
    "project_name": "test_project",
    "username": "test@example.com",
    "version": "V1.0",
    "domain": "automotive",
    "artifact": "SYS5",
    "model": "gpt-4",
    "input_folder_path": "files/test@tataelxsi.co.in/swe6_5/V1.0/SWE6/input",
    "output_dir": "files/test@tataelxsi.co.in/swe6_5/V1.0/SWE6/output",
    "req_filename": "reqs_to_use.xlsx",
    "req_sheet_name": "005",
}

# Mock requirements (from Node 1)
mock_requirements = [
    {
        "req_id": "REQ_019_001",
        "row_index": 0,
        "data": {},
        "type": "Functional"
    },
    {
        "req_id": "REQ_019_002",
        "row_index": 1,
        "data": {},
        "type": "Functional"
    },
    {
        "req_id": "REQ_020_001",
        "row_index": 2,
        "data": {},
        "type": "Functional"
    }
]

# Create state
state: SYS5State = {
    "config": config,
    "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
    "requirements": mock_requirements,
    "signals": [],
    "logical_signals": [],
    "feature_details": {},
    "errors": []
}

print("\n" + "="*80)
print("TESTING NODE 3 ONLY")
print("="*80 + "\n")

# Execute Node 3
result = Node3ExtractLogicalSignals.execute(state)

print("\n" + "="*80)
print("NODE 3 TEST RESULT")
print("="*80 + "\n")

print(f"Logical Signals Extracted: {len(result.get('logical_signals', []))}")
print(f"Errors: {result.get('errors', [])}")

if result.get('logical_signals'):
    print("\nLogical Signals:")
    import json
    print(json.dumps(result.get('logical_signals'), indent=2))
