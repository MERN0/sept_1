# SYS5 - Agentic Requirements Extraction System

A LangGraph-based agentic framework for multi-phase requirements extraction and artifact generation from Excel files.

## Architecture

This project uses **LangGraph** to implement a multi-node workflow that processes requirements through distinct phases. Each phase is implemented as a state machine node with clear inputs, outputs, and transitions.

## Project Structure

```
backend/
└── app/
    └── core/
        └── artifacts/
            └── system/
                └── sys5/
                    ├── sys5.py              # Main entry point
                    ├── agent_graph.py       # LangGraph workflow definition
                    └── __init__.py
```

## Workflow Architecture

### LangGraph Workflow

The system implements a 4-node linear workflow using LangGraph:

```
START → Node 1 → Node 2 → Node 3 → Node Final → END
```

#### Node 1: Requirements Extraction ✅
- **Input**: Config with file paths and sheet information
- **Process**:
  - Read Excel file from configured path
  - Parse the specified sheet
  - Identify rows marked as "Functional requirements"
  - Extract all requirement data from matching rows
- **Output**: Extracted requirements list with row indices and data
- **Key Method**: `SYS5Agent.node_1_extract_requirements()`

#### Node 2: Requirements Validation ✅
- **Input**: Extracted requirements from Node 1
- **Process**: Validate requirement structure and content
- **Output**: Validated requirements with metadata
- **Key Method**: `SYS5Agent.node_2_validate_requirements()`

#### Node 3: Artifact Generation ✅
- **Input**: Validated requirements
- **Process**: Generate documents and artifacts
- **Output**: Generated artifacts and documents
- **Key Method**: `SYS5Agent.node_3_generate_artifacts()`

#### Node Final: Save Output ✅
- **Input**: All artifacts from previous nodes
- **Process**:
  - Save requirements to JSON
  - Save artifacts metadata
  - Save workflow summary
- **Output**: Files saved to disk
- **Key Method**: `SYS5Agent.node_final_save_output()`

## State Management

The workflow uses `SYS5State` to manage data flow between nodes:

```python
class SYS5State(TypedDict):
    config: Dict[str, Any]              # Workflow configuration
    phase: str                          # Current phase identifier
    requirements: List[Dict[str, Any]]  # Extracted requirements
    artifacts: Dict[str, Any]           # Generated artifacts
    errors: List[str]                   # Workflow errors
    timestamp: str                      # Execution timestamp
```

## Configuration

The `generate()` function accepts a config dictionary:

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
}

result = generate(config)
```

### Direct Workflow Access

```python
from backend.app.core.artifacts.system.sys5 import run_sys5_workflow

config = { ... }
result_json = run_sys5_workflow(config)
```

### Running Tests

```bash
python -m backend.app.core.artifacts.system.sys5.sys5
```

## Output

The application generates multiple files:

1. **requirements_[timestamp].json** - Extracted requirements with metadata
2. **artifacts_[timestamp].json** - Generated artifacts summary
3. **workflow_summary_[timestamp].json** - Workflow execution summary
4. **SYS5_[project_name]_[timestamp].zip** - Packaged output files

### Requirements JSON Format

```json
{
  "metadata": {
    "total_requirements": 3,
    "extraction_timestamp": "20260901_123616",
    "phase": "node_1_completed"
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

### Workflow Summary Format

```json
{
  "workflow_summary": {
    "total_phases": 3,
    "final_phase": "final_completed",
    "timestamp": "20260901_123616",
    "errors": [],
    "artifacts_generated": [
      "extracted_requirements",
      "validated_requirements",
      "generated"
    ]
  }
}
```

## Requirements Extraction Logic

A requirement is classified as "Functional" if:
- Any cell in the row contains "Functional requirements" (case-insensitive)
- Other requirement types (Non-Functional, Security, etc.) are excluded

## Key Features

- **Graph-based Architecture**: Uses LangGraph for clear workflow orchestration
- **State Management**: Tracks data flow and state through the workflow
- **Error Handling**: Collects and reports errors at each phase
- **Extensible Design**: Easy to add new nodes and phases
- **Timestamp Tracking**: All artifacts timestamped for audit trail
- **Graceful Handling**: Properly handles NaN/null values in Excel data

## Technologies

- **LangGraph**: Multi-agent orchestration and workflow management
- **Pandas**: Excel file reading and data processing
- **Python 3.11+**: Core language

## Future Phases

- Node 4: Impact Analysis
- Node 5: Requirement Prioritization
- Node 6: Traceability Matrix Generation
- Node 7: Custom Report Generation
