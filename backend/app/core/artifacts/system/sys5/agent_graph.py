"""
LangGraph-based agentic framework for SYS5 artifact generation.
Implements a multi-phase workflow using graph nodes.
"""

import json
import os
from typing import Dict, Any, List
from datetime import datetime
from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict
import pandas as pd


class SYS5State(TypedDict):
    """State management for SYS5 workflow"""
    config: Dict[str, Any]
    phase: str
    requirements: List[Dict[str, Any]]
    artifacts: Dict[str, Any]
    errors: List[str]
    timestamp: str


class SYS5Agent:
    """Agent nodes for SYS5 workflow"""

    @staticmethod
    def node_1_extract_requirements(state: SYS5State) -> SYS5State:
        """
        NODE 1: Extract Functional Requirements from Excel

        Input: Config with file paths and sheet info
        Output: Extracted requirements list
        """
        print(f"\n{'='*80}")
        print("NODE 1: REQUIREMENTS EXTRACTION")
        print(f"{'='*80}")

        config = state["config"]
        requirements = []
        errors = state.get("errors", [])

        try:
            # Get file paths from config
            input_folder = config.get("input_folder_path")
            req_filename = config.get("req_filename", "reqs_to_use.xlsx")
            req_sheet_name = config.get("req_sheet_name", "005")
            excel_file_path = os.path.join(input_folder, req_filename)

            print(f"Reading Excel file: {excel_file_path}")
            print(f"Sheet name: {req_sheet_name}")

            if not os.path.exists(excel_file_path):
                error_msg = f"Excel file not found: {excel_file_path}"
                print(f"ERROR: {error_msg}")
                errors.append(error_msg)
            else:
                # Read Excel file
                df = pd.read_excel(excel_file_path, sheet_name=req_sheet_name)
                print(f"Total rows in Excel: {len(df)}")

                # Extract functional requirements
                for idx, row in df.iterrows():
                    is_functional_req = False

                    for cell_value in row.values:
                        if pd.isna(cell_value):
                            continue
                        if "functional requirements" in str(cell_value).lower():
                            is_functional_req = True
                            break

                    if is_functional_req:
                        row_dict = row.to_dict()
                        row_dict = {k: (None if pd.isna(v) else v) for k, v in row_dict.items()}
                        requirement = {
                            "row_index": int(idx),
                            "data": row_dict,
                            "type": "Functional"
                        }
                        requirements.append(requirement)

                print(f"Extracted {len(requirements)} functional requirements")

        except Exception as e:
            error_msg = f"Error in requirements extraction: {str(e)}"
            print(f"ERROR: {error_msg}")
            errors.append(error_msg)

        # Update state
        state["phase"] = "node_1_completed"
        state["requirements"] = requirements
        state["errors"] = errors
        state["artifacts"]["extracted_requirements"] = {
            "count": len(requirements),
            "data": requirements
        }

        print(f"NODE 1 completed: {len(requirements)} requirements extracted")
        return state

    @staticmethod
    def node_2_validate_requirements(state: SYS5State) -> SYS5State:
        """
        NODE 2: Validate Extracted Requirements (Placeholder for Phase 2)

        Input: Extracted requirements from Node 1
        Output: Validated requirements with metadata
        """
        print(f"\n{'='*80}")
        print("NODE 2: REQUIREMENTS VALIDATION")
        print(f"{'='*80}")

        requirements = state.get("requirements", [])
        errors = state.get("errors", [])

        print(f"Validating {len(requirements)} requirements...")

        # Placeholder validation logic
        validated_reqs = []
        for req in requirements:
            # Basic validation checks
            if "data" in req:
                validated_reqs.append({
                    **req,
                    "validated": True,
                    "validation_errors": []
                })

        print(f"Validated {len(validated_reqs)} requirements")

        state["phase"] = "node_2_completed"
        state["artifacts"]["validated_requirements"] = {
            "count": len(validated_reqs),
            "data": validated_reqs
        }

        return state

    @staticmethod
    def node_3_generate_artifacts(state: SYS5State) -> SYS5State:
        """
        NODE 3: Generate Artifacts (Placeholder for Phase 3)

        Input: Validated requirements
        Output: Generated artifacts and documents
        """
        print(f"\n{'='*80}")
        print("NODE 3: ARTIFACT GENERATION")
        print(f"{'='*80}")

        requirements = state.get("requirements", [])
        print(f"Generating artifacts from {len(requirements)} requirements...")

        # Placeholder artifact generation
        artifacts = {
            "generated_documents": [],
            "summary": f"Generated artifacts for {len(requirements)} requirements"
        }

        state["phase"] = "node_3_completed"
        state["artifacts"]["generated"] = artifacts

        print(f"NODE 3 completed: Artifacts generated")
        return state

    @staticmethod
    def node_final_save_output(state: SYS5State) -> SYS5State:
        """
        NODE FINAL: Save all outputs to disk

        Input: All artifacts from previous nodes
        Output: Saved files and summary
        """
        print(f"\n{'='*80}")
        print("NODE FINAL: SAVE OUTPUT")
        print(f"{'='*80}")

        config = state["config"]
        output_dir = config.get("output_dir")
        timestamp = state["timestamp"]

        os.makedirs(output_dir, exist_ok=True)

        # Save requirements to JSON
        requirements_file = os.path.join(output_dir, f"requirements_{timestamp}.json")
        with open(requirements_file, 'w') as f:
            json.dump({
                "metadata": {
                    "total_requirements": len(state["requirements"]),
                    "extraction_timestamp": timestamp,
                    "phase": state["phase"]
                },
                "requirements": state["requirements"]
            }, f, indent=2)

        print(f"Saved requirements to: {requirements_file}")

        # Save artifacts summary
        artifacts_file = os.path.join(output_dir, f"artifacts_{timestamp}.json")
        with open(artifacts_file, 'w') as f:
            json.dump(state["artifacts"], f, indent=2)

        print(f"Saved artifacts to: {artifacts_file}")

        # Save workflow summary
        summary_file = os.path.join(output_dir, f"workflow_summary_{timestamp}.json")
        with open(summary_file, 'w') as f:
            json.dump({
                "workflow_summary": {
                    "total_phases": len(state["artifacts"]),
                    "final_phase": state["phase"],
                    "timestamp": timestamp,
                    "errors": state.get("errors", []),
                    "artifacts_generated": list(state["artifacts"].keys())
                }
            }, f, indent=2)

        print(f"Saved workflow summary to: {summary_file}")

        state["phase"] = "final_completed"
        return state


def build_sys5_graph() -> StateGraph:
    """
    Build the LangGraph workflow graph for SYS5 artifact generation

    Graph Structure:
        START → Node 1 → Node 2 → Node 3 → Node Final → END

    Returns:
        Compiled StateGraph for SYS5 workflow
    """
    print("Building SYS5 LangGraph workflow...")

    # Create the graph
    workflow = StateGraph(SYS5State)

    # Add nodes
    workflow.add_node("node_1_extract_requirements", SYS5Agent.node_1_extract_requirements)
    workflow.add_node("node_2_validate_requirements", SYS5Agent.node_2_validate_requirements)
    workflow.add_node("node_3_generate_artifacts", SYS5Agent.node_3_generate_artifacts)
    workflow.add_node("node_final_save_output", SYS5Agent.node_final_save_output)

    # Define edges (workflow transitions)
    workflow.add_edge(START, "node_1_extract_requirements")
    workflow.add_edge("node_1_extract_requirements", "node_2_validate_requirements")
    workflow.add_edge("node_2_validate_requirements", "node_3_generate_artifacts")
    workflow.add_edge("node_3_generate_artifacts", "node_final_save_output")
    workflow.add_edge("node_final_save_output", END)

    # Compile the graph
    app = workflow.compile()
    print("SYS5 LangGraph workflow built successfully!")

    return app


def run_sys5_workflow(config: Dict[str, Any]) -> str:
    """
    Execute the SYS5 workflow using LangGraph

    Args:
        config: Configuration dictionary for the workflow

    Returns:
        JSON string with workflow results
    """
    # Initialize state
    initial_state: SYS5State = {
        "config": config,
        "phase": "initialized",
        "requirements": [],
        "artifacts": {},
        "errors": [],
        "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S")
    }

    # Build and run the graph
    graph = build_sys5_graph()

    print(f"\n{'='*80}")
    print("STARTING SYS5 WORKFLOW")
    print(f"{'='*80}")
    print(f"Project: {config.get('project_name')}")
    print(f"Domain: {config.get('domain')}")
    print(f"Version: {config.get('version')}")
    print(f"{'='*80}\n")

    # Execute the workflow
    final_state = graph.invoke(initial_state)

    # Prepare result
    result = {
        "status": "completed" if not final_state["errors"] else "completed_with_errors",
        "phase": final_state["phase"],
        "total_requirements": len(final_state["requirements"]),
        "artifacts": final_state["artifacts"],
        "errors": final_state["errors"],
        "timestamp": final_state["timestamp"]
    }

    print(f"\n{'='*80}")
    print("WORKFLOW COMPLETED")
    print(f"{'='*80}")
    print(f"Status: {result['status']}")
    print(f"Total Requirements: {result['total_requirements']}")
    print(f"Artifacts Generated: {len(result['artifacts'])}")
    print(f"{'='*80}\n")

    return json.dumps(result, indent=2)
