"""
SYS5 Entry Point

Main entry point for SYS5 artifact generation
"""

from .main import run_workflow


def generate(config: dict) -> str:
    """
    Entry point for SYS5 - Requirements Extraction

    Args:
        config: Configuration dictionary with:
            - project_name: Project name
            - input_folder_path: Path to input files (relative or absolute)
            - output_dir: Output directory (relative or absolute)
            - req_filename: Excel file name
            - req_sheet_name: Sheet name in Excel
            - version: Version number (optional)

    Returns:
        JSON string with workflow results and extracted requirements
    """
    return run_workflow(config)


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
