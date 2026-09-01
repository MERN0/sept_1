import os
import json
import zipfile
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

# Import the LangGraph agent framework
from .agent_graph import run_sys5_workflow


def extract_functional_requirements(excel_path: str, sheet_name: str) -> List[Dict[str, Any]]:
    """
    Extract valid requirements marked as 'Functional requirements' from Excel file.

    Args:
        excel_path: Path to the Excel file
        sheet_name: Name of the sheet to read

    Returns:
        List of dictionaries containing requirement data
    """
    requirements = []

    try:
        # Read the Excel file
        df = pd.read_excel(excel_path, sheet_name=sheet_name)

        # Iterate through each row
        for idx, row in df.iterrows():
            # Check if "Functional requirements" exists in any cell of this row
            is_functional_req = False

            for cell_value in row.values:
                # Skip NaN values
                if pd.isna(cell_value):
                    continue
                # Check if "functional requirements" is in the cell (case-insensitive)
                if "functional requirements" in str(cell_value).lower():
                    is_functional_req = True
                    break

            if is_functional_req:
                # Convert row to dictionary, replacing NaN with None
                row_dict = row.to_dict()
                row_dict = {k: (None if pd.isna(v) else v) for k, v in row_dict.items()}

                requirement = {
                    "row_index": int(idx),
                    "data": row_dict,
                    "type": "Functional"
                }
                requirements.append(requirement)

        return requirements

    except FileNotFoundError:
        raise FileNotFoundError(f"Excel file not found: {excel_path}")
    except Exception as e:
        raise Exception(f"Error reading Excel file: {str(e)}")


def save_requirements_to_json(requirements: List[Dict[str, Any]], output_path: str) -> str:
    """
    Save extracted requirements to a JSON file.

    Args:
        requirements: List of extracted requirements
        output_path: Path where JSON file will be saved

    Returns:
        Path to the created JSON file
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, 'w') as f:
        json.dump({
            "metadata": {
                "total_requirements": len(requirements),
                "extraction_timestamp": datetime.now().isoformat()
            },
            "requirements": requirements
        }, f, indent=2)

    return output_path


def generate(config: dict) -> str:
    """
    Entry point for SYS5 generation using LangGraph agentic framework

    This function orchestrates the multi-phase SYS5 artifact generation process
    using a LangGraph-based workflow with distinct nodes for each phase.

    Args:
        config: Configuration dictionary containing:
            - project_name: Name of the project
            - output_dir: Output directory for artifacts
            - input_folder_path: Path to input files
            - req_filename: Excel requirements filename
            - req_sheet_name: Sheet name in Excel file
            - And other configuration parameters

    Returns:
        JSON string with workflow results and artifacts
    """

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = config.get("output_dir")

    # Run the LangGraph-based workflow
    result_json = run_sys5_workflow(config)

    # Parse result for packaging
    result = json.loads(result_json)

    # ========================== Do not change ==========================
    # Package all output files into a zip
    zip_path = os.path.join(output_dir, f"SYS5_{config.get('project_name')}_{timestamp}.zip")
    os.makedirs(output_dir, exist_ok=True)

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for filename in os.listdir(output_dir):
            file_path = os.path.join(output_dir, filename)
            if os.path.isfile(file_path) and not filename.endswith(".zip"):
                zf.write(file_path, arcname=filename)

    result["output_zip"] = zip_path

    return json.dumps(result, indent=2)


if __name__ == "__main__":
    # ========================== TEST CONFIGURATION ==========================
    config = {
        "project_name": "tmhc_demo",
        "username": "test@tataelxsi.co.in",
        "version": "V1.0",
        "domain": "automotive",
        "artifact": "SYS5",
        "model": "llm-1-gpt-oss-120b",
        "input_folder_path": "files/test@tataelxsi.co.in/swe6_5/V1.0/SWE6/input",
        "output_folder_path": "files/test@tataelxsi.co.in/swe6_5/V1.0/SWE6/output",
        "output_dir": "files/test@tataelxsi.co.in/swe6_5/V1.0/SWE6/output",
        "uploaded_files": [],
        "agent_chain": [
            {"agent_name": "generation_agent", "agent_version": "V1.0", "prompt_content": ""},
            {"agent_name": "verification_agent", "agent_version": "V1.0", "prompt_content": ""},
            {"agent_name": "qa_agent", "agent_version": "V1.0", "prompt_content": ""},
        ],
        "req_filename": "reqs_to_use.xlsx",
        "req_sheet_name": "005",
    }

    # Run the application
    result = generate(config)
    print("\n" + "="*80)
    print("GENERATION RESULT:")
    print("="*80)
    print(result)
