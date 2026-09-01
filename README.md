# SYS5 - Requirements Extraction System

A phased application for extracting and processing requirements from Excel files.

## Project Structure

```
backend/
└── app/
    └── core/
        └── artifacts/
            └── system/
                └── sys5/
                    └── sys5.py          # Main entry point
```

## Phases

### Phase 1: Requirements Extraction ✅ COMPLETED
- **Description**: Extract functional requirements from Excel file
- **Input**: Excel file with requirements data
- **Process**:
  - Read Excel file from configured path
  - Identify rows marked as "Functional requirements"
  - Extract all requirement data from matching rows
- **Output**: JSON file with extracted requirements and metadata
- **Functions**:
  - `extract_functional_requirements()`: Extracts functional requirements from Excel
  - `save_requirements_to_json()`: Saves requirements to JSON format

### Phase 2: (Planned)
Pending implementation

### Phase 3: (Planned)
Pending implementation

## Configuration

The `generate()` function accepts a config dictionary with the following keys:

```python
config = {
    "project_name": str,              # Project name
    "username": str,                  # User email
    "version": str,                   # Version number
    "domain": str,                    # Domain/Industry
    "artifact": str,                  # Artifact type (SYS5)
    "model": str,                     # LLM model to use
    "input_folder_path": str,         # Path to input files
    "output_folder_path": str,        # Path to output
    "output_dir": str,                # Output directory path
    "uploaded_files": list,           # List of uploaded files
    "agent_chain": list,              # Agent chain configuration
    "req_filename": str,              # Requirements Excel filename
    "req_sheet_name": str,            # Excel sheet name
}
```

## Usage

### Entry Point

```python
from backend.app.core.artifacts.system.sys5 import generate

config = {
    "project_name": "tmhc_demo",
    "username": "test@example.com",
    "version": "V1.0",
    "domain": "automotive",
    "artifact": "SYS5",
    "model": "llm-1-gpt-oss-120b",
    "input_folder_path": "files/input",
    "output_dir": "files/output",
    "req_filename": "reqs_to_use.xlsx",
    "req_sheet_name": "005",
    # ... other config
}

result = generate(config)
```

### Running Tests

```bash
# Run with test configuration
python backend/app/core/artifacts/system/sys5/sys5.py
```

## Output

The application generates:
1. **requirements_[timestamp].json** - Extracted functional requirements with metadata
2. **SYS5_[project_name]_[timestamp].zip** - Packaged output files

### JSON Output Format

```json
{
  "metadata": {
    "total_requirements": 3,
    "extraction_timestamp": "2026-09-01T12:34:35.180182"
  },
  "requirements": [
    {
      "row_index": 0,
      "data": {
        "REQ_ID": "REQ001",
        "Requirement_Type": "Functional requirements",
        "Description": "System should authenticate users",
        "Priority": "High",
        "Status": "Active"
      },
      "type": "Functional"
    }
  ]
}
```

## Requirements Extraction Logic

A requirement is considered "Functional" if:
- Any cell in the row contains the text "Functional requirements" (case-insensitive)
- Rows with "Non-Functional", "Security", or other types are excluded

## Notes

- The extraction is case-insensitive
- NaN/null values are handled gracefully
- Requirements are indexed by their row position in the Excel file
- All extracted data is preserved in the JSON output
