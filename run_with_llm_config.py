"""
Example script to run SYS5 Nodes 1 & 2 with LLM configuration

Node 1: Extract requirements and generate test patterns using LLM
Node 2: Find signals and commands from communication matrices
"""

import os
import sys
from backend.app.core.artifacts.system.sys5 import generate
from backend.app.core.artifacts.system.sys5.config import LLM_CONFIG

# ============================================================================
# CONFIGURATION - Update these with your actual values
# ============================================================================

# Option 1: Set API key via environment variable
os.environ["OPENAI_API_KEY"] = "your-openai-api-key-here"

# Option 2: Or update the config directly
# LLM_CONFIG["openai_api_key"] = "your-openai-api-key-here"

# Optional: Configure custom API base URL for Azure OpenAI or other providers
# os.environ["OPENAI_API_BASE"] = "https://your-custom-endpoint.openai.azure.com/v1"

# Update LLM model if needed
LLM_CONFIG["model"] = "gpt-4"  # or "gpt-3.5-turbo"
LLM_CONFIG["temperature"] = 0.7
LLM_CONFIG["max_tokens"] = 2000

print("="*80)
print("LLM CONFIGURATION")
print("="*80)
print(f"Model: {LLM_CONFIG['model']}")
print(f"Temperature: {LLM_CONFIG['temperature']}")
print(f"Max Tokens: {LLM_CONFIG['max_tokens']}")
print(f"API Base: {os.getenv('OPENAI_API_BASE', LLM_CONFIG['openai_api_base'])}")
print("="*80)
print()

# ============================================================================
# TEST CONFIGURATION
# ============================================================================

config = {
    "project_name": "sys5_llm_test",
    "username": "test@example.com",
    "version": "V1.0",
    "domain": "automotive",
    "artifact": "SYS5",
    "model": LLM_CONFIG["model"],
    "input_folder_path": "files/test@tataelxsi.co.in/swe6_5/V1.0/SWE6/input",
    "output_dir": "files/test@tataelxsi.co.in/swe6_5/V1.0/SWE6/output",
    "req_filename": "reqs_to_use.xlsx",
    "req_sheet_name": "005",
    "system_requirements_file": "files/test@tataelxsi.co.in/swe6_5/V1.0/SWE6/input/System Requirements.xlsx",
    "command_list_file": "files/test@tataelxsi.co.in/swe6_5/V1.0/SWE6/input/Command List.xlsx",
}

# ============================================================================
# EXECUTION
# ============================================================================

print("\nStarting SYS5 Workflow (Nodes 1 & 2)...\n")

try:
    result = generate(config)
    print("\n" + "="*80)
    print("EXECUTION SUCCESSFUL")
    print("="*80)
    print(result)

except ValueError as e:
    print(f"\n[ERROR] Configuration Error: {str(e)}")
    print("\nTo fix this:")
    print("1. Set OPENAI_API_KEY environment variable")
    print("2. Or update LLM_CONFIG['openai_api_key'] in this script")

except ImportError as e:
    print(f"\n[ERROR] Import Error: {str(e)}")
    print("\nTo fix this:")
    print("1. Install langchain-openai: pip install langchain-openai")

except Exception as e:
    print(f"\n[ERROR] {type(e).__name__}: {str(e)}")
    import traceback
    traceback.print_exc()

print("\n" + "="*80)
