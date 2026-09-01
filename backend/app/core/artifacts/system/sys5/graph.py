"""LangGraph workflow definition for SYS5"""

import os
import sys
from langgraph.graph import StateGraph, START, END

# Setup path for imports
_workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
if _workspace_root not in sys.path:
    sys.path.insert(0, _workspace_root)

try:
    from .state import SYS5State  # type: ignore
    from .nodes import Node1ExtractRequirements  # type: ignore
except ImportError:
    from backend.app.core.artifacts.system.sys5.state import SYS5State
    from backend.app.core.artifacts.system.sys5.nodes import Node1ExtractRequirements


def build_workflow():
    """
    Build LangGraph workflow with Node 1

    Graph structure:
        START → Node 1 → END

    Returns:
        Compiled LangGraph workflow
    """
    workflow = StateGraph(SYS5State)

    # Add nodes
    workflow.add_node("node_1", Node1ExtractRequirements.execute)

    # Define edges
    workflow.add_edge(START, "node_1")
    workflow.add_edge("node_1", END)

    # Compile and return
    return workflow.compile()
