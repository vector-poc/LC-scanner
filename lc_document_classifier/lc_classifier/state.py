"""State management for LC Document Classification Graph."""

from typing import Dict, List, Optional, Any, Annotated
from typing_extensions import TypedDict
from pydantic import BaseModel
import operator


class InputDocument(BaseModel):
    """Represents an input document to be classified."""
    name: str
    summary: str
    full_text: str


class ClassificationResult(BaseModel):
    """Result of classifying documents against an LC requirement."""
    lc_requirement_name: str
    lc_requirement_description: str
    matched_documents: List[str]  # Document names that match
    confidence_scores: List[float]  # Confidence for each match
    reasoning: str
    status: str  # "matched", "no_match", "partial_match"


class DocumentClassificationState(TypedDict):
    """State for the document classification graph."""
    
    # Input data
    extracted_lc: Dict[str, Any]  # LC analysis from existing extraction service
    input_documents: List[Dict[str, str]]  # List of {name, summary, full_text}
    
    # Processing state
    lc_requirements: List[Dict[str, Any]]  # Extracted from LC.DOCUMENTS_REQUIRED
    current_requirement_index: int
    current_requirement: Optional[Dict[str, Any]]
    
    # Results accumulation - using operator.add for appending
    classification_results: Annotated[List[Dict[str, Any]], operator.add]
    
    # Final output
    final_assignments: Dict[str, List[str]]  # LC requirement name -> matched document names
    processing_complete: bool
    
    # Error handling
    errors: Annotated[List[str], operator.add]


class GraphInput(BaseModel):
    """Input schema for the graph invocation."""
    extracted_lc: Dict[str, Any]
    input_documents: List[Dict[str, str]]


class GraphOutput(BaseModel):
    """Output schema for the graph results."""
    final_assignments: Dict[str, List[str]]
    classification_results: List[ClassificationResult]
    processing_complete: bool
    total_requirements: int
    total_documents: int
    errors: List[str]