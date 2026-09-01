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
        Node3ExtractLogicalSignals, Node4ExtractAppParameters,
        Node5ExtractModelConfig, Node6ExtractCompoundAndLibrary,
        Node7GenerateTestCases, Node8ValidateTestCases, Node9CorrectTestCases
    )
except ImportError:
    from backend.app.core.artifacts.system.sys5.state import SYS5State
    from backend.app.core.artifacts.system.sys5.nodes import (
        Node1ExtractRequirements, Node2FindSignalsAndCommands,
        Node3ExtractLogicalSignals, Node4ExtractAppParameters,
        Node5ExtractModelConfig, Node6ExtractCompoundAndLibrary,
        Node7GenerateTestCases, Node8ValidateTestCases, Node9CorrectTestCases
    )


def _test_case_needs_correction(entry, max_corrections):
    validation_result = entry.get("validation_result") or {}
    if validation_result.get("valid") is not False:
        return False
    return entry.get("correction_count", 0) < max_corrections


def _route_after_validate(state):
    """Validate -> Correct only if something came back invalid, else stop here"""
    max_corrections = state["config"].get("max_corrections", 1)
    test_cases = state.get("test_cases", {})
    if any(_test_case_needs_correction(e, max_corrections) for e in test_cases.values()):
        return "node_9"
    return "done"


def _route_after_correct(state):
    """
    Correct -> Validate again as long as a test case is still invalid and
    hasn't used up its correction budget (config["max_corrections"]);
    otherwise stop. With max_corrections=1 this always stops here after a
    single Correct pass; with max_corrections=2 it goes back to Validate
    once more before stopping.
    """
    max_corrections = state["config"].get("max_corrections", 1)
    test_cases = state.get("test_cases", {})
    if any(_test_case_needs_correction(e, max_corrections) for e in test_cases.values()):
        return "node_8"
    return "done"


def build_workflow():
    """
    Build LangGraph workflow with Nodes 1-9

    Graph structure:
        START → Node 1 → Node 2 → Node 3 → Node 4 → Node 5 → Node 6
               → Node 7 (generate) → Node 8 (validate)
                     ⇄ Node 9 (correct)   [loop bounded by config["max_corrections"]]
               → END

    Returns:
        Compiled LangGraph workflow
    """
    workflow = StateGraph(SYS5State)

    # Add nodes
    workflow.add_node("node_1", Node1ExtractRequirements.execute)
    workflow.add_node("node_2", Node2FindSignalsAndCommands.execute)
    workflow.add_node("node_3", Node3ExtractLogicalSignals.execute)
    workflow.add_node("node_4", Node4ExtractAppParameters.execute)
    workflow.add_node("node_5", Node5ExtractModelConfig.execute)
    workflow.add_node("node_6", Node6ExtractCompoundAndLibrary.execute)
    workflow.add_node("node_7", Node7GenerateTestCases.execute)
    workflow.add_node("node_8", Node8ValidateTestCases.execute)
    workflow.add_node("node_9", Node9CorrectTestCases.execute)

    # Define edges
    workflow.add_edge(START, "node_1")
    workflow.add_edge("node_1", "node_2")
    workflow.add_edge("node_2", "node_3")
    workflow.add_edge("node_3", "node_4")
    workflow.add_edge("node_4", "node_5")
    workflow.add_edge("node_5", "node_6")
    workflow.add_edge("node_6", "node_7")
    workflow.add_edge("node_7", "node_8")

    workflow.add_conditional_edges("node_8", _route_after_validate, {"node_9": "node_9", "done": END})
    workflow.add_conditional_edges("node_9", _route_after_correct, {"node_8": "node_8", "done": END})

    # Compile and return
    return workflow.compile()
