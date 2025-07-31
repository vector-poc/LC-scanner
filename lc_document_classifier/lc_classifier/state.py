"""State management for LC Document Classification Graph."""

from typing import Dict, List, Optional, Any, Annotated
from typing_extensions import TypedDict
import operator


class DocumentClassificationState(TypedDict):
    """State for the document classification graph."""
    
    # Input data
    extracted_lc: Dict[str, Any]
    input_documents: List[Dict[str, str]]
    
    # Processing state
    lc_requirements: List[Dict[str, Any]]
    current_requirement_index: int
    current_requirement: Optional[Dict[str, Any]]
    
    # Results accumulation
    classification_results: Annotated[List[Dict[str, Any]], operator.add]
    final_assignments: Dict[str, List[str]]
    processing_complete: bool
    
    # Error handling
    errors: Annotated[List[str], operator.add]