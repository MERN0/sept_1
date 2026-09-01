"""LangGraph workflow definition for SYS5"""

from langgraph.graph import StateGraph, START, END

from .state import SYS5State
from .nodes import Node1ExtractRequirements


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
