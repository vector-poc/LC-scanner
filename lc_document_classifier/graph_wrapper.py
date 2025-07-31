"""
Graph wrapper for LangGraph Studio compatibility.
This module handles the import issues and creates a Studio-compatible graph.
"""

import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import required modules
from langgraph.graph import StateGraph, START, END
from lc_classifier.state import DocumentClassificationState
from lc_classifier.nodes import (
    initialize_state,
    get_next_requirement,
    classify_documents,
    record_assignment,
    check_completion,
    format_results
)


def create_studio_compatible_graph():
    """Create a LangGraph Studio compatible graph without custom checkpointer."""
    
    # Create the state graph
    workflow = StateGraph(DocumentClassificationState)
    
    # Add nodes
    workflow.add_node("initialize_state", initialize_state)
    workflow.add_node("get_next_requirement", get_next_requirement)
    workflow.add_node("classify_documents", classify_documents)
    workflow.add_node("record_assignment", record_assignment)
    workflow.add_node("format_results", format_results)
    
    # Define the workflow edges
    workflow.add_edge(START, "initialize_state")
    workflow.add_edge("initialize_state", "get_next_requirement")
    workflow.add_edge("get_next_requirement", "classify_documents")
    workflow.add_edge("classify_documents", "record_assignment")
    
    # Add conditional edge for loop control
    workflow.add_conditional_edges(
        "record_assignment",
        check_completion,
        {
            "get_next_requirement": "get_next_requirement",
            "format_results": "format_results"
        }
    )
    
    workflow.add_edge("format_results", END)
    
    # Compile the graph WITHOUT custom checkpointer for Studio compatibility
    # Studio provides its own persistence layer
    graph = workflow.compile()
    
    return graph


# Create the main graph instance for LangGraph Studio
graph = create_studio_compatible_graph()

# Export the graph for LangGraph Studio
__all__ = ['graph']