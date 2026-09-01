# SYS5 - Requirements Extraction and Signal Mapping System

A LangGraph-based agentic framework for extracting functional requirements from Excel files and mapping them to CAN signals and commands for system qualification test case writing.

## Overview

SYS5 is a two-node workflow system that:
1. **Node 1**: Extracts functional requirements from Excel files and generates test patterns using LLM
2. **Node 2**: Maps requirements to CAN signals and commands from communication matrices

## Architecture

```
backend/app/core/artifacts/system/sys5/
├── config.py                    # Configuration and LLM setup
├── state.py                     # TypedDict state definition
├── graph.py                     # LangGraph workflow builder
├── main.py                      # Workflow orchestrator
├── sys5.py                      # Entry point
├── utils.py                     # Helper utilities
└── nodes/
    ├── node_1.py               # Requirements extraction + test pattern generation
    └── node_2.py               # Signal and command mapping
```

## Workflow

```
START → Node 1: Extract Requirements + Generate Test Patterns
           ↓ (with LLM-generated test cases)
        Node 2: Find Signals and Commands from Communication Matrices
           ↓ (with command details)
        END (output JSON with requirements, signals, features)
```

## Node 1: Requirements Extraction

**Process**:
1. Read Excel file (req_filename) from input_folder_path
2. Scan specified sheet (req_sheet_name) for "Functional requirement" keyword
3. Extract verification criteria from each matching row
4. Call LLM (ChatOpenAI) to generate test patterns based on verification criteria
5. Format and save test patterns to Excel output
6. Save extracted requirements to JSON

**Output Files**:
- `requirements_[timestamp].json` - Extracted requirements with verification criteria
- `test_patterns_[timestamp].xlsx` - LLM-generated test cases with preconditions and expected results

**Key Features**:
- Regex-based word boundary matching for keywords (handles punctuation)
- Whitespace-aware verification criteria extraction
- LLM integration via LangChain ChatOpenAI for test pattern generation
- Excel output with formatted headers

## Node 2: Signal and Command Extraction

**Process**:
1. Read System Requirements file (same as req_filename)
2. Load Index sheet to map feature numbers to names and groups
3. Load Master Comm Matrix (CAN) sheet
4. For each requirement, extract feature number (e.g., "019" from "REQ_019_001")
5. Find feature column in Master Comm Matrix by header name
6. Identify rows marked with x/X/〇 (U+3007 IDEOGRAPHIC NUMBER ZERO) as valid
7. Extract Signal Name from each valid row
8. Search Signal Name in Command List sheet
9. Extract command details (columns B-I)
10. Save results as JSON with feature details

**Output Files**:
- `signals_[timestamp].json` - Mapped signals with command details

**Example Structure**:
```json
{
  "signals": [
    {
      "req_id": "REQ_019_001",
      "feature_number": "019",
      "signal_name": "Drv1_Rx1_CmdSpd",
      "feature_details": {
        "Command Type": "Speed Control",
        "Command Code": "0x0001",
        "Data Length": "2 bytes",
        ...
      }
    }
  ],
  "feature_details": {
    "019": {
      "feature_number": "019",
      "feature_name": "Drive Motor Control",
      "feature_group": "Power Management"
    }
  }
}
```

## Configuration

### Required Config Dictionary

```python
config = {
    "project_name": "project_id",
    "username": "user@example.com",
    "version": "V1.0",
    "domain": "automotive",
    "artifact": "SYS5",
    "model": "gpt-4",                                    # LLM model
    "input_folder_path": "files/path/to/input",        # Contains .xlsx files
    "output_dir": "files/path/to/output",              # Output directory
    "req_filename": "reqs_to_use.xlsx",                # Requirement file name
    "req_sheet_name": "005",                           # Sheet name with requirements
}
```

### Input Files Required

1. **System Requirements File** (`req_filename`)
   - Sheet 1: "Index" - Feature number to name mapping
     - Columns: Feature Number | Feature Name | Feature Group
   - Sheet 2: "Master Comm Matrix (CAN)" - Signal definitions
     - Columns: Message ID, Signal Name, Signal Type, ... [Feature Columns]
     - Feature columns named by feature number (e.g., "019", "020")
     - Valid rows marked with x/X/〇 under feature columns
   - Sheet 3: `req_sheet_name` (e.g., "005") - Requirements data
     - Columns: ID | Description | Verification Criteria | Status | Comments
     - Rows with "Functional requirement" keyword are extracted

2. **Command List File** (auto-discovered in input_folder_path)
   - File name must contain "command" and "list" (case-insensitive)
   - Sheet: "Command List"
   - Columns: Signal Name | Command Type | Command Code | Data Length | Validation Method | Response Expected | Timeout (ms) | Error Handling | Notes

### Environment Variables

```bash
OPENAI_API_KEY="sk-..."                    # OpenAI API key
OPENAI_API_BASE="https://api.openai.com/v1"  # Optional custom endpoint
```

## Usage

### Basic Example

```python
from backend.app.core.artifacts.system.sys5 import generate

config = {
    "project_name": "test_project",
    "username": "test@example.com",
    "version": "V1.0",
    "domain": "automotive",
    "artifact": "SYS5",
    "model": "gpt-4",
    "input_folder_path": "files/input",
    "output_dir": "files/output",
    "req_filename": "reqs_to_use.xlsx",
    "req_sheet_name": "005",
}

result_json = generate(config)
```

### Running from CLI

```bash
python run_with_llm_config.py
```

### LLM Configuration

Edit `backend/app/core/artifacts/system/sys5/config.py`:

```python
LLM_CONFIG = {
    "model": "gpt-4",
    "temperature": 0.7,
    "max_tokens": 2000,
    "openai_api_base": "https://api.openai.com/v1",
}
```

## Key Features

### Requirements Extraction
- **Flexible keyword matching** using regex word boundaries
- **Verification criteria extraction** with whitespace cleanup
- **LLM integration** for automated test case generation
- **Excel formatting** with headers, styles, and auto-width columns

### Signal Mapping
- **Feature number extraction** from requirement IDs
- **Multi-format lookup** handling numeric and padded strings
- **Valid row detection** with Unicode marker support (〇, x, X)
- **Command details extraction** with pandas type conversion
- **JSON serialization** with native Python types

### State Management
- TypedDict-based state with clear field definitions
- Timestamp tracking for audit trail
- Error collection across all phases
- Clear separation of concerns between nodes

### Path Resolution
- Relative and absolute path support
- Workspace-relative path resolution
- Auto-discovery of command list files
- Flexible input directory handling

## Error Handling

The system gracefully handles:
- Missing or malformed Excel sheets
- Missing sheet names with available sheets listing
- File not found errors with helpful messages
- NaN/null values in Excel data
- Incompatible data types (numpy/pandas conversion)
- LLM connection errors (non-blocking, continues extraction)

## Data Types

The system automatically converts pandas/numpy types to JSON-serializable Python types:
- `int64` → `int`
- `float64` → `float`
- `object` → `str` (for non-numeric objects)
- NaN/NaT → `None`

## Testing

Run the complete workflow with test data:

```bash
python run_with_llm_config.py
```

This will:
1. Load requirements from test Excel file
2. Extract functional requirements matching the keyword pattern
3. Query OpenAI (if key is set) for test pattern generation
4. Load Master Comm Matrix and Command List sheets
5. Extract signals and commands for each requirement
6. Save JSON outputs with extracted data

## Performance Notes

- Keyword matching uses regex word boundaries (handles punctuation)
- Excel loading uses pandas for efficiency
- Signal extraction filters by column header and marker characters
- Command lookup uses substring matching on Signal Name column
- JSON output includes metadata and timestamp for tracking

## Future Enhancements

- Additional nodes for impact analysis and traceability
- Support for custom marker characters
- Batch processing for multiple requirements files
- Enhanced error recovery and validation
- Cached LLM responses for repeated patterns

## Dependencies

- **LangGraph**: Workflow orchestration
- **LangChain**: LLM integration (ChatOpenAI)
- **Pandas**: Excel file processing
- **OpenPyXL**: Excel formatting and manipulation
- **Python 3.11+**: Core language

## License

Internal use only.
