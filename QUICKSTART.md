# SYS5 Framework - Quick Start Guide

## Installation

### Prerequisites
- Python 3.11+
- pip

### Setup

```bash
# Clone the repository
git clone https://github.com/MERN0/sept_1.git
cd sept_1

# Install dependencies
pip install pandas openpyxl langgraph langchain

# Verify installation
python -m backend.app.core.artifacts.system.sys5.sys5
```

## Basic Usage

### 1. Simple Example

```python
from backend.app.core.artifacts.system.sys5 import generate

# Define your configuration
config = {
    "project_name": "my_project",
    "username": "user@example.com",
    "version": "V1.0",
    "domain": "automotive",
    "artifact": "SYS5",
    "model": "llm-1-gpt-oss-120b",
    "input_folder_path": "./input_files",
    "output_dir": "./output_files",
    "req_filename": "requirements.xlsx",
    "req_sheet_name": "005",
}

# Execute the workflow
result = generate(config)
print(result)
```

### 2. Prepare Your Input Files

**Excel File Structure (requirements.xlsx):**

```
| REQ_ID | Requirement_Type        | Description                    | Priority | Status |
|--------|-------------------------|--------------------------------|----------|--------|
| REQ001 | Functional requirements | System should authenticate     | High     | Active |
| REQ002 | Non-Functional         | System should load < 2 seconds | Medium   | Active |
| REQ003 | Functional requirements | System should validate email   | High     | Active |
```

**Key Points:**
- Column name doesn't matter - any cell with "Functional requirements" marks the row
- Non-functional requirements will be ignored
- All columns in matching rows will be extracted

### 3. Check Output

The system generates three JSON files:

**requirements_[timestamp].json**
```json
{
  "metadata": {
    "total_requirements": 2,
    "extraction_timestamp": "20260901_123616"
  },
  "requirements": [
    {
      "row_index": 0,
      "data": {
        "REQ_ID": "REQ001",
        "Requirement_Type": "Functional requirements",
        "Description": "System should authenticate",
        "Priority": "High",
        "Status": "Active"
      },
      "type": "Functional"
    }
  ]
}
```

**artifacts_[timestamp].json**
```json
{
  "extracted_requirements": {
    "count": 2,
    "data": [...]
  },
  "validated_requirements": {
    "count": 2,
    "data": [...]
  },
  "generated": {
    "generated_documents": [],
    "summary": "Generated artifacts for 2 requirements"
  }
}
```

**workflow_summary_[timestamp].json**
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

## Configuration Reference

### Required Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `project_name` | string | Project identifier | "tmhc_demo" |
| `output_dir` | string | Output directory path | "./output" |
| `input_folder_path` | string | Input folder path | "./input" |
| `req_filename` | string | Excel filename | "reqs_to_use.xlsx" |
| `req_sheet_name` | string | Sheet name in Excel | "005" |

### Optional Fields

| Field | Type | Description | Default |
|-------|------|-------------|---------|
| `username` | string | User identifier | "" |
| `version` | string | Version number | "V1.0" |
| `domain` | string | Domain/Industry | "" |
| `model` | string | LLM model | "" |
| `uploaded_files` | list | File list | [] |
| `agent_chain` | list | Agent configuration | [] |

## Common Tasks

### Task 1: Extract Requirements from New Excel File

```python
config = {
    "project_name": "new_project",
    "username": "user@example.com",
    "version": "V2.0",
    "domain": "finance",
    "input_folder_path": "./input",
    "output_dir": "./output",
    "req_filename": "finance_reqs.xlsx",
    "req_sheet_name": "Requirements",
}

result = generate(config)
print(f"Extracted {result['total_requirements']} requirements")
```

### Task 2: Batch Process Multiple Projects

```python
projects = [
    {"name": "project_a", "file": "reqs_a.xlsx"},
    {"name": "project_b", "file": "reqs_b.xlsx"},
    {"name": "project_c", "file": "reqs_c.xlsx"},
]

for project in projects:
    config = {
        "project_name": project["name"],
        "username": "batch_user@example.com",
        "input_folder_path": "./input",
        "output_dir": "./output",
        "req_filename": project["file"],
        "req_sheet_name": "005",
    }
    
    result = generate(config)
    print(f"{project['name']}: {result['total_requirements']} requirements")
```

### Task 3: Access Workflow Directly

```python
from backend.app.core.artifacts.system.sys5 import run_sys5_workflow

config = {...}
result_json = run_sys5_workflow(config)

import json
result = json.loads(result_json)
print(f"Status: {result['status']}")
print(f"Total artifacts: {len(result['artifacts'])}")
```

### Task 4: Extract Individual Nodes

```python
from backend.app.core.artifacts.system.sys5 import (
    extract_functional_requirements, 
    save_requirements_to_json
)

# Just extract, no workflow
requirements = extract_functional_requirements(
    "input/requirements.xlsx", 
    "005"
)

# Save to JSON
save_requirements_to_json(
    requirements, 
    "output/my_requirements.json"
)
```

## Workflow Phases Explained

### Phase 1: Requirements Extraction
- ✅ **Status**: Production Ready
- Extracts rows marked as "Functional requirements"
- Preserves all column data
- Handles Excel formatting

### Phase 2: Requirements Validation
- ✅ **Status**: Implemented (Logic to expand)
- Validates requirement structure
- Adds validation metadata
- Collects validation errors

### Phase 3: Artifact Generation
- ✅ **Status**: Implemented (Logic to expand)
- Generates documents from requirements
- Creates reports and summaries
- Produces stakeholder artifacts

### Phase Final: Output Saving
- ✅ **Status**: Production Ready
- Saves all data to JSON files
- Creates workflow summary
- Packages files into ZIP archive

## Troubleshooting

### Issue: "Excel file not found"
```
Solution: Verify path in config matches actual file location
- Check input_folder_path is correct
- Verify req_filename exists in that directory
- Ensure no typos in filenames
```

### Issue: "No requirements extracted"
```
Solution: Check Excel file structure
- Verify at least one row has "Functional requirements"
- Text must be in a cell (not cell name/formula)
- Check for extra spaces: "Functional requirements" ≠ "Functional  requirements"
```

### Issue: "No sheet named '005'"
```
Solution: Verify sheet name in Excel
- Open Excel file
- Check actual sheet name (tab at bottom)
- Update req_sheet_name in config to match exactly
- Sheet names are case-sensitive
```

## Advanced Usage

### Custom Configuration

```python
config = {
    # ... standard fields ...
    
    # Extended config
    "agent_chain": [
        {
            "agent_name": "generation_agent",
            "agent_version": "V1.0",
            "prompt_content": "Custom prompt here"
        }
    ],
    "metadata": {
        "author": "user@example.com",
        "department": "Engineering",
        "compliance": "ISO-27001"
    }
}
```

### Error Handling

```python
import json

result_str = generate(config)
result = json.loads(result_str)

if result["status"] == "completed_with_errors":
    print(f"Errors encountered: {result['errors']}")
    
if result["total_requirements"] == 0:
    print("No requirements found in Excel file")
```

### File Organization

```
project_root/
├── input_files/
│   ├── requirements.xlsx
│   ├── technical_specs.xlsx
│   └── ...
├── output_files/
│   ├── requirements_[timestamp].json
│   ├── artifacts_[timestamp].json
│   ├── workflow_summary_[timestamp].json
│   └── SYS5_[project]_[timestamp].zip
└── config.json
```

## Performance Tips

1. **Large Excel Files**: Split into multiple sheets
2. **Batch Processing**: Process projects sequentially
3. **Output Directory**: Use SSD for faster writes
4. **Memory**: Python handles large requirements lists well

## Next Steps

1. Read [ARCHITECTURE.md](./ARCHITECTURE.md) for system design
2. Check [README.md](./README.md) for detailed documentation
3. Explore node implementations in `agent_graph.py`
4. Extend with custom phases as needed

## Support

For issues or questions:
- Check troubleshooting section above
- Review example code
- Examine actual output files for debugging
