"""Main LangGraph definition for LC Document Classification."""

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from .state import DocumentClassificationState
from .nodes import (
    initialize_state,
    get_next_requirement,
    classify_documents,
    record_assignment,
    check_completion,
    format_results
)


def create_document_classification_graph():
    """Create and compile the document classification graph."""
    
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
    
    # Add memory for persistence (useful for Studio debugging)
    memory = MemorySaver()
    
    # Compile the graph
    graph = workflow.compile(checkpointer=memory)
    
    return graph


# Create the main graph instance for LangGraph Studio
graph = create_document_classification_graph()


def run_classification(extracted_lc, input_documents, config=None):
    """
    Convenience function to run document classification.
    
    Args:
        extracted_lc: LC analysis dictionary from existing extraction service
        input_documents: List of documents with name, summary, full_text
        config: Optional configuration for graph execution
        
    Returns:
        Classification results
    """
    if config is None:
        config = {
            "configurable": {"thread_id": "default"},
            "recursion_limit": 50  # Allow more steps for complex LC processing
        }
    
    initial_state = {
        "extracted_lc": extracted_lc,
        "input_documents": input_documents,
        "lc_requirements": [],
        "current_requirement_index": 0,
        "current_requirement": None,
        "classification_results": [],
        "final_assignments": {},
        "processing_complete": False,
        "errors": []
    }
    
    result = graph.invoke(initial_state, config=config)
    
    return {
        "final_assignments": result.get("final_assignments", {}),
        "classification_results": result.get("classification_results", []),
        "processing_complete": result.get("processing_complete", False),
        "total_requirements": len(result.get("lc_requirements", [])),
        "total_documents": len(input_documents),
        "errors": result.get("errors", [])
    }