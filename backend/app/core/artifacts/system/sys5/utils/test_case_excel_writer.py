"""
Excel writer for the Test Cases output workbook.

Produces two sheets, matching the required template:
- "Item_List": one row per test case (Test Type, Feature Name, Test Case ID,
  Variant, Execution Requirement) - a flat index of everything generated.
- "Test Cases": one block per test case, stacked vertically in the same
  sheet. Each block has a header row (Function ID/Feature/Variant/
  Requirement ID/Priority/Mode of Execution/Automated/Test case Description)
  followed by the step table (Test Phase/Step/Test steps/Parameter
  Settings/Units/Expected Value/Units/Deviation to execute the
  command/Remarks), with the Test Phase column merged across each
  PRECONDITION/ACTION/POSTCONDITION group of steps.

Expected shape of each entry in `test_cases` (a list, one dict per test case):
{
    "test_case_id": str,          # e.g. "TMHC_SQTC_22"
    "feature": str,               # e.g. "Slope Assist"
    "variant": str,               # e.g. "A1"
    "requirement_id": str,        # e.g. "5.2.1"
    "priority": str,              # e.g. "P1"
    "mode_of_execution": str,     # e.g. "Automated"
    "automated": str,             # e.g. "Automated" / "Manual"
    "description": str,
    "test_type": str,             # for Item_List, e.g. "System Qualification"
    "execution_requirement": str, # for Item_List
    "steps": [
        {
            "phase": "PRECONDITION" | "ACTION" | "POSTCONDITION" | "Test start" | "End of test",
            "step": int,
            "test_step": str,
            "parameter_settings": Any,
            "units": Any,
            "expected_value": Any,
            "units_2": Any,
            "deviation": Any,      # "Deviation to execute the command"
            "remarks": Any,
        },
        ...
    ]
}

Missing/empty fields are written as blank cells - the writer never crashes on
incomplete data, since Nodes 7-9 currently produce placeholder test cases
until the Generate/Validate/Correct prompts are written.
"""

from typing import Any, Dict, List, Optional

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

HEADER_FILL = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
HEADER_FONT = Font(bold=True, color="FFFFFF")
LABEL_FILL = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
LABEL_FONT = Font(bold=True)
THIN_BORDER = Border(
    left=Side(style="thin"), right=Side(style="thin"),
    top=Side(style="thin"), bottom=Side(style="thin")
)
WRAP_TOP = Alignment(wrap_text=True, vertical="top")
CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)

# "Test Cases" sheet step-table columns
STEP_TABLE_HEADERS = [
    "Test Phase", "Step", "Test steps", "Parameter Settings", "Units",
    "Expected Value", "Units", "Deviation to execute the command", "Remarks"
]
STEP_FIELD_ORDER = [
    "phase", "step", "test_step", "parameter_settings", "units",
    "expected_value", "units_2", "deviation", "remarks"
]

# Header info block above each test case's step table
INFO_HEADERS = [
    "Function ID", "Feature", "Variant", "Requirement ID",
    "Priority", "Mode of Execution", "Automated", "Test case Description"
]
INFO_FIELD_ORDER = [
    "test_case_id", "feature", "variant", "requirement_id",
    "priority", "mode_of_execution", "automated", "description"
]

ITEM_LIST_HEADERS = [
    "Test Type", "Feature Name", "Test Case ID", "Variant", "Execution Requirement"
]


def _set_header_row(ws, row: int, headers: List[str], start_col: int = 1):
    for i, header in enumerate(headers):
        col = start_col + i
        cell = ws.cell(row=row, column=col, value=header)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = CENTER
        cell.border = THIN_BORDER


def write_item_list_sheet(wb: Workbook, test_cases: List[Dict[str, Any]]) -> None:
    """Write the 'Item_List' sheet - a flat index of every test case"""
    ws = wb.create_sheet("Item_List")
    _set_header_row(ws, 1, ITEM_LIST_HEADERS)

    row = 2
    for tc in test_cases:
        ws.cell(row=row, column=1, value=tc.get("test_type", "")).border = THIN_BORDER
        ws.cell(row=row, column=2, value=tc.get("feature", "")).border = THIN_BORDER
        ws.cell(row=row, column=3, value=tc.get("test_case_id", "")).border = THIN_BORDER
        ws.cell(row=row, column=4, value=tc.get("variant", "")).border = THIN_BORDER
        ws.cell(row=row, column=5, value=tc.get("execution_requirement", "")).border = THIN_BORDER
        row += 1

    for col in range(1, len(ITEM_LIST_HEADERS) + 1):
        ws.column_dimensions[get_column_letter(col)].width = 22


def _write_test_case_block(ws, start_row: int, tc: Dict[str, Any]) -> int:
    """
    Write one test case's info header block + step table starting at
    start_row. Returns the row number to start the next block at.
    """
    num_cols = len(STEP_TABLE_HEADERS)

    # --- Info header block: label row + value row ---
    label_row = start_row
    value_row = start_row + 1

    for i, label in enumerate(INFO_HEADERS[:-1]):
        col = i + 1
        lbl_cell = ws.cell(row=label_row, column=col, value=label)
        lbl_cell.font = LABEL_FONT
        lbl_cell.fill = LABEL_FILL
        lbl_cell.alignment = CENTER
        lbl_cell.border = THIN_BORDER

        val_cell = ws.cell(row=value_row, column=col, value=tc.get(INFO_FIELD_ORDER[i], ""))
        val_cell.alignment = WRAP_TOP
        val_cell.border = THIN_BORDER

    # "Test case Description" label + value span the remaining columns
    desc_col = len(INFO_HEADERS)
    desc_label_cell = ws.cell(row=label_row, column=desc_col, value=INFO_HEADERS[-1])
    desc_label_cell.font = LABEL_FONT
    desc_label_cell.fill = LABEL_FILL
    desc_label_cell.alignment = CENTER
    desc_label_cell.border = THIN_BORDER
    if num_cols > desc_col:
        ws.merge_cells(start_row=label_row, start_column=desc_col, end_row=label_row, end_column=num_cols)

    desc_value_cell = ws.cell(row=value_row, column=desc_col, value=tc.get("description", ""))
    desc_value_cell.alignment = WRAP_TOP
    desc_value_cell.border = THIN_BORDER
    if num_cols > desc_col:
        ws.merge_cells(start_row=value_row, start_column=desc_col, end_row=value_row, end_column=num_cols)
    ws.row_dimensions[value_row].height = 60

    # --- Step table header ---
    table_header_row = value_row + 1
    _set_header_row(ws, table_header_row, STEP_TABLE_HEADERS)

    # --- Step rows, with Test Phase merged per contiguous phase group ---
    steps = tc.get("steps") or []
    first_data_row = table_header_row + 1
    row = first_data_row
    phase_start_row = None
    phase_value = None

    def _close_phase_merge(end_row):
        if phase_start_row is not None and end_row > phase_start_row:
            ws.merge_cells(start_row=phase_start_row, start_column=1, end_row=end_row, end_column=1)

    for step in steps:
        for i, field in enumerate(STEP_FIELD_ORDER):
            col = i + 1
            if field == "phase":
                continue  # written separately below to control merging
            cell = ws.cell(row=row, column=col, value=step.get(field, ""))
            cell.border = THIN_BORDER
            cell.alignment = WRAP_TOP if field in ("test_step", "remarks") else Alignment(vertical="top")

        current_phase = step.get("phase", "")
        if current_phase != phase_value:
            _close_phase_merge(row - 1)
            phase_start_row = row
            phase_value = current_phase
        phase_cell = ws.cell(row=row, column=1, value=phase_value if row == phase_start_row else None)
        phase_cell.alignment = CENTER
        phase_cell.border = THIN_BORDER
        phase_cell.font = LABEL_FONT

        row += 1

    _close_phase_merge(row - 1)

    return row + 1  # one blank row between test case blocks


def write_test_cases_sheet(wb: Workbook, test_cases: List[Dict[str, Any]]) -> None:
    """Write the 'Test Cases' sheet - one block per test case, stacked vertically"""
    ws = wb.create_sheet("Test Cases")

    for col in range(1, len(STEP_TABLE_HEADERS) + 1):
        ws.column_dimensions[get_column_letter(col)].width = 24
    ws.column_dimensions[get_column_letter(3)].width = 45  # Test steps
    ws.column_dimensions[get_column_letter(len(STEP_TABLE_HEADERS))].width = 40  # Remarks

    row = 1
    for tc in test_cases:
        row = _write_test_case_block(ws, row, tc)


def write_test_cases_workbook(
    output_path: str,
    test_cases: List[Dict[str, Any]],
    include_cover: bool = False,
) -> None:
    """
    Build the full workbook (Item_List + Test Cases sheets) and save it to
    output_path. include_cover is a placeholder for a future "Cover" /
    "Test Platform" sheet - not implemented yet.
    """
    wb = Workbook()
    wb.remove(wb.active)  # drop the default blank sheet

    write_item_list_sheet(wb, test_cases)
    write_test_cases_sheet(wb, test_cases)

    wb.save(output_path)
