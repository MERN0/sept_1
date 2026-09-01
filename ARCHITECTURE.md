# SYS5 Agentic Framework - Architecture Guide

## Overview

The SYS5 system is a LangGraph-based agentic framework designed to process requirements through multiple phases. Each phase is implemented as a distinct node in a state machine workflow.

## System Components

### 1. Entry Point: `backend/app/core/artifacts/system/sys5/sys5.py`

```python
def generate(config: dict) -> str:
    """Main entry point for API/deployment"""
    # Orchestrates the LangGraph workflow
    # Returns JSON result with artifacts
```

**Responsibilities:**
- Accept configuration from API/deployment layer
- Invoke the LangGraph workflow via `run_sys5_workflow()`
- Package output files into ZIP archive
- Return serialized results

### 2. Agentic Framework: `backend/app/core/artifacts/system/sys5/agent_graph.py`

#### State Definition

```python
class SYS5State(TypedDict):
    config: Dict[str, Any]              # Workflow configuration
    phase: str                          # Current phase identifier
    requirements: List[Dict[str, Any]]  # Extracted requirements
    artifacts: Dict[str, Any]           # Generated artifacts
    errors: List[str]                   # Error tracking
    timestamp: str                      # Execution timestamp
```

#### Agent Nodes

**Node 1: Requirements Extraction**
```
Input:  config with file paths
Output: List[Dict] - extracted requirements
Status: ✅ Fully Implemented
```

Extracts functional requirements from Excel file:
- Reads Excel sheet specified in config
- Scans rows for "Functional requirements" marker
- Builds requirement objects with row indices and data
- Handles NaN values gracefully

**Node 2: Requirements Validation**
```
Input:  requirements from Node 1
Output: List[Dict] - validated requirements
Status: ✅ Implemented (Placeholder Logic)
```

Validates extracted requirements:
- Checks requirement structure
- Adds validation flags and error tracking
- Preserves requirement data

**Node 3: Artifact Generation**
```
Input:  validated requirements from Node 2
Output: Dict - generated artifacts
Status: ✅ Implemented (Placeholder Logic)
```

Generates deliverable artifacts:
- Creates documents from requirements
- Generates reports and summaries
- Structures output for final saving

**Node Final: Save Output**
```
Input:  All artifacts and state
Output: Files saved to disk
Status: ✅ Fully Implemented
```

Persists all workflow outputs:
- Saves requirements to JSON
- Saves artifacts metadata to JSON
- Saves workflow summary with execution details
- Creates ZIP package of all outputs

#### Workflow Graph

```
START
  │
  ├─→ [Node 1: Extract Requirements]
  │     Input:  config
  │     Output: requirements[]
  │
  ├─→ [Node 2: Validate Requirements]
  │     Input:  requirements[]
  │     Output: validated_requirements[]
  │
  ├─→ [Node 3: Generate Artifacts]
  │     Input:  validated_requirements[]
  │     Output: generated_artifacts{}
  │
  ├─→ [Node Final: Save Output]
  │     Input:  All state
  │     Output: Files written
  │
  └─→ END
```

## Data Flow

### Configuration Input

```python
config = {
    # Project metadata
    "project_name": "tmhc_demo",
    "username": "test@tataelxsi.co.in",
    "version": "V1.0",
    "domain": "automotive",
    "artifact": "SYS5",
    "model": "llm-1-gpt-oss-120b",
    
    # File paths
    "input_folder_path": "files/input",
    "output_dir": "files/output",
    
    # Processing parameters
    "req_filename": "reqs_to_use.xlsx",
    "req_sheet_name": "005",
    
    # Optional
    "uploaded_files": [],
    "agent_chain": []
}
```

### State Progression

```
Initial State:
  phase: "initialized"
  requirements: []
  artifacts: {}
  errors: []

After Node 1:
  phase: "node_1_completed"
  requirements: [req1, req2, req3, ...]
  artifacts: { extracted_requirements: {...} }

After Node 2:
  phase: "node_2_completed"
  requirements: [req1, req2, req3, ...]
  artifacts: { 
    extracted_requirements: {...},
    validated_requirements: {...}
  }

After Node 3:
  phase: "node_3_completed"
  artifacts: {
    extracted_requirements: {...},
    validated_requirements: {...},
    generated: {...}
  }

After Node Final:
  phase: "final_completed"
  All files written to disk
```

### Output Files

```
output_dir/
├── requirements_[timestamp].json       # Node 1 output
├── artifacts_[timestamp].json          # Node 2-3 outputs
├── workflow_summary_[timestamp].json   # Node Final summary
└── SYS5_[project]_[timestamp].zip      # Packaged archive
```

## Execution Flow

### 1. API Call
```python
from backend.app.core.artifacts.system.sys5 import generate

result = generate(config)
# Returns: JSON string with workflow results
```

### 2. Internal Workflow
```
generate(config)
  ├→ run_sys5_workflow(config)
  │   ├→ build_sys5_graph()
  │   │   └→ StateGraph + edges
  │   ├→ graph.invoke(initial_state)
  │   └→ Returns: JSON result
  ├→ Package outputs to ZIP
  └→ Return: Final JSON with zip path
```

### 3. Node Execution
Each node:
1. Receives current state
2. Processes its input
3. Updates state with output
4. Returns modified state
5. Next node receives modified state

## Error Handling

Errors are collected at each phase:

```python
state["errors"].append(f"Error message at {phase}")
```

Final status reflects errors:
```python
status = "completed_with_errors" if errors else "completed"
```

## Extension Points

### Adding a New Phase

1. **Create new node method in SYS5Agent:**
```python
@staticmethod
def node_N_new_phase(state: SYS5State) -> SYS5State:
    # Process state
    state["phase"] = "node_N_completed"
    state["artifacts"]["new_artifact"] = {...}
    return state
```

2. **Add to graph:**
```python
workflow.add_node("node_N_new_phase", SYS5Agent.node_N_new_phase)
workflow.add_edge("node_N-1_...", "node_N_new_phase")
workflow.add_edge("node_N_new_phase", "...")
```

## Key Design Decisions

### 1. State Machine Architecture
- **Why**: Clear phase boundaries, easy to debug, natural error handling
- **Benefit**: Each phase is independent but connected via state

### 2. Node-based Design
- **Why**: Separates concerns, enables parallel phase execution (future)
- **Benefit**: Scalable, maintainable, testable

### 3. JSON Serialization
- **Why**: Language-agnostic, easy API integration
- **Benefit**: Works with REST APIs, webhooks, async processing

### 4. Timestamp Tracking
- **Why**: Audit trail, allows multiple runs in same output dir
- **Benefit**: Complete execution history

## Performance Considerations

- **Node 1** (Excel parsing): O(n) where n = rows in spreadsheet
- **Node 2** (Validation): O(m) where m = extracted requirements
- **Node 3** (Generation): O(m) artifact generation
- **Node Final** (I/O): O(k) where k = output files

Overall complexity: O(n + 3m + k) ≈ O(n) for typical use cases

## Security Considerations

- File path validation needed for production
- Excel formula injection protection (pandas handles)
- Output directory permissions verification
- Error messages don't expose system paths (in production)

## Testing

### Unit Test Template

```python
def test_node_1_extraction():
    test_config = {...}
    initial_state = {
        "config": test_config,
        "phase": "initialized",
        "requirements": [],
        "artifacts": {},
        "errors": [],
        "timestamp": "test"
    }
    result_state = SYS5Agent.node_1_extract_requirements(initial_state)
    
    assert result_state["phase"] == "node_1_completed"
    assert len(result_state["requirements"]) > 0
    assert result_state["errors"] == []
```

### Integration Test

```python
def test_full_workflow():
    config = {...}
    result = run_sys5_workflow(config)
    
    assert "status" in result
    assert result["status"] == "completed"
    assert result["total_requirements"] > 0
```

## Future Enhancements

- [ ] Parallel node execution for independent phases
- [ ] Conditional edges based on error states
- [ ] Dynamic phase configuration
- [ ] Logging and monitoring hooks
- [ ] Caching between phases
- [ ] Rollback mechanisms
- [ ] Async/await support
- [ ] Webhook notifications
