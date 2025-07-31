"""
Graph wrapper for LangGraph Studio compatibility.
Imports the Studio-compatible graph from the main graph module.
"""

from lc_classifier.graph import graph

# Export the graph for LangGraph Studio
__all__ = ['graph']