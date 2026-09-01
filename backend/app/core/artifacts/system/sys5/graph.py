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
    from .nodes import (  # type: ignore
        Node1ExtractRequirements, Node2FindSignalsAndCommands,
        Node3ExtractLogicalSignals, Node4ExtractAppParameters
    )
except ImportError:
    from backend.app.core.artifacts.system.sys5.state import SYS5State
    from backend.app.core.artifacts.system.sys5.nodes import (
        Node1ExtractRequirements, Node2FindSignalsAndCommands,
        Node3ExtractLogicalSignals, Node4ExtractAppParameters
    )


def build_workflow():
    """
    Build LangGraph workflow with Nodes 1, 2, 3, and 4

    Graph structure:
        START → Node 1 → Node 2 → Node 3 → Node 4 → END

    Returns:
        Compiled LangGraph workflow
    """
    workflow = StateGraph(SYS5State)

    # Add nodes
    workflow.add_node("node_1", Node1ExtractRequirements.execute)
    workflow.add_node("node_2", Node2FindSignalsAndCommands.execute)
    workflow.add_node("node_3", Node3ExtractLogicalSignals.execute)
    workflow.add_node("node_4", Node4ExtractAppParameters.execute)

    # Define edges
    workflow.add_edge(START, "node_1")
    workflow.add_edge("node_1", "node_2")
    workflow.add_edge("node_2", "node_3")
    workflow.add_edge("node_3", "node_4")
    workflow.add_edge("node_4", END)

    # Compile and return
    return workflow.compile()
