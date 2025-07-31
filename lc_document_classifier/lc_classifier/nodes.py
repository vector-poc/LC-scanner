"""Graph nodes for LC Document Classification."""

from .state import DocumentClassificationState
from .utils import DocumentClassifierLLM, extract_lc_requirements, validate_input_documents, format_final_results


def initialize_state(state: DocumentClassificationState) -> DocumentClassificationState:
    """Initialize the classification state and extract LC requirements."""
    errors = []
    
    # Validate inputs
    if not state.get('extracted_lc'):
        errors.append("No LC data provided")
    
    input_docs = state.get('input_documents', [])
    doc_errors = validate_input_documents(input_docs)
    errors.extend(doc_errors)
    
    # Extract LC requirements
    lc_requirements = []
    if state.get('extracted_lc'):
        lc_requirements = extract_lc_requirements(state['extracted_lc'])
        if not lc_requirements:
            errors.append("No document requirements found in LC")
    
    return {
        "lc_requirements": lc_requirements,
        "current_requirement_index": 0,
        "current_requirement": None,
        "classification_results": [],
        "final_assignments": {},
        "processing_complete": False,
        "errors": errors
    }


def get_next_requirement(state: DocumentClassificationState) -> DocumentClassificationState:
    """Get the next LC requirement to process."""
    current_index = state.get('current_requirement_index', 0)
    lc_requirements = state.get('lc_requirements', [])
    
    if current_index < len(lc_requirements):
        return {"current_requirement": lc_requirements[current_index]}
    else:
        return {
            "current_requirement": None,
            "processing_complete": True
        }


def classify_documents(state: DocumentClassificationState) -> DocumentClassificationState:
    """Classify input documents against the current LC requirement."""
    current_req = state.get('current_requirement')
    input_documents = state.get('input_documents', [])
    
    if not current_req or not input_documents:
        error_msg = "Missing requirement or input documents"
        return {"errors": [error_msg]}
    
    req_name = current_req.get('name', 'Unknown Requirement')
    
    try:
        classifier = DocumentClassifierLLM()
        classification_result = classifier.classify_documents(current_req, input_documents)
        
        # Add requirement metadata
        classification_result['lc_requirement_name'] = req_name
        classification_result['lc_requirement_description'] = current_req.get('description', '')
        
        return {"classification_results": [classification_result]}
        
    except Exception as e:
        error_msg = f"Classification error for {req_name}: {str(e)}"
        error_result = {
            "lc_requirement_name": req_name,
            "lc_requirement_description": current_req.get('description', ''),
            "matched_documents": [],
            "confidence_scores": [],
            "reasoning": error_msg,
            "status": "error"
        }
        
        return {
            "classification_results": [error_result],
            "errors": [error_msg]
        }


def record_assignment(state: DocumentClassificationState) -> DocumentClassificationState:
    """Record the classification result and move to next requirement."""
    current_index = state.get('current_requirement_index', 0)
    
    return {
        "current_requirement_index": current_index + 1,
        "current_requirement": None
    }


def check_completion(state: DocumentClassificationState) -> str:
    """Check if all requirements have been processed and determine next step."""
    current_index = state.get('current_requirement_index', 0)
    lc_requirements = state.get('lc_requirements', [])
    
    if current_index >= len(lc_requirements):
        return "format_results"
    else:
        return "get_next_requirement"


def format_results(state: DocumentClassificationState) -> DocumentClassificationState:
    """Format the final classification results."""
    classification_results = state.get('classification_results', [])
    lc_requirements = state.get('lc_requirements', [])
    
    final_assignments = format_final_results(classification_results, lc_requirements)
    
    return {
        "final_assignments": final_assignments,
        "processing_complete": True
    }