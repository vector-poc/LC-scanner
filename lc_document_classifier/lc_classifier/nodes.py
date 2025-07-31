"""Graph nodes for LC Document Classification."""

from typing import Dict, Any, List
import os
from .state import DocumentClassificationState
from .utils import DocumentClassifierLLM, extract_lc_requirements, validate_input_documents, format_final_results


def initialize_state(state: DocumentClassificationState) -> DocumentClassificationState:
    """Initialize the classification state and extract LC requirements."""
    print("🚀 Initializing document classification state...")
    
    # Validate inputs
    errors = []
    
    # Validate LC data
    if not state.get('extracted_lc'):
        errors.append("No LC data provided")
    
    # Validate input documents
    input_docs = state.get('input_documents', [])
    doc_errors = validate_input_documents(input_docs)
    errors.extend(doc_errors)
    
    # Extract LC requirements
    lc_requirements = []
    if state.get('extracted_lc'):
        lc_requirements = extract_lc_requirements(state['extracted_lc'])
        if not lc_requirements:
            errors.append("No document requirements found in LC")
    
    print(f"📋 Found {len(lc_requirements)} LC requirements")
    print(f"📄 Processing {len(input_docs)} input documents")
    
    if errors:
        print(f"❌ Validation errors: {errors}")
    
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
        current_req = lc_requirements[current_index]
        req_name = current_req.get('name', f'Requirement_{current_index + 1}')
        print(f"📋 Processing requirement {current_index + 1}/{len(lc_requirements)}: {req_name}")
        
        return {
            "current_requirement": current_req
        }
    else:
        print("✅ All requirements processed")
        return {
            "current_requirement": None,
            "processing_complete": True
        }


def classify_documents(state: DocumentClassificationState) -> DocumentClassificationState:
    """Classify input documents against the current LC requirement."""
    current_req = state.get('current_requirement')
    input_documents = state.get('input_documents', [])
    
    if not current_req:
        print("⚠️  No current requirement to process")
        return {"errors": ["No current requirement to process"]}
    
    if not input_documents:
        print("⚠️  No input documents to classify")
        return {"errors": ["No input documents to classify"]}
    
    req_name = current_req.get('name', 'Unknown Requirement')
    print(f"🔍 Classifying documents for: {req_name}")
    
    try:
        # Initialize LLM classifier
        classifier = DocumentClassifierLLM()
        
        # Perform classification
        classification_result = classifier.classify_documents(current_req, input_documents)
        
        # Add requirement info to result
        classification_result['lc_requirement_name'] = req_name
        classification_result['lc_requirement_description'] = current_req.get('description', '')
        
        matched_count = len(classification_result.get('matched_documents', []))
        print(f"✅ Classification complete: {matched_count} documents matched")
        
        return {
            "classification_results": [classification_result]
        }
        
    except Exception as e:
        error_msg = f"Error classifying documents for {req_name}: {str(e)}"
        print(f"❌ {error_msg}")
        
        # Return error result
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
    
    # Increment the index for next iteration
    new_index = current_index + 1
    
    print(f"📝 Recording assignment for requirement {current_index + 1}")
    
    return {
        "current_requirement_index": new_index,
        "current_requirement": None  # Clear current requirement
    }


def check_completion(state: DocumentClassificationState) -> str:
    """Check if all requirements have been processed and determine next step."""
    current_index = state.get('current_requirement_index', 0)
    lc_requirements = state.get('lc_requirements', [])
    
    if current_index >= len(lc_requirements):
        print("🎉 All requirements processed - moving to final results")
        return "format_results"
    else:
        print(f"⏭️  Processing next requirement ({current_index + 1}/{len(lc_requirements)})")
        return "get_next_requirement"


def format_results(state: DocumentClassificationState) -> DocumentClassificationState:
    """Format the final classification results."""
    print("📊 Formatting final results...")
    
    classification_results = state.get('classification_results', [])
    lc_requirements = state.get('lc_requirements', [])
    
    # Create final assignments mapping
    final_assignments = format_final_results(classification_results, lc_requirements)
    
    # Count statistics
    total_requirements = len(lc_requirements)
    total_documents = len(state.get('input_documents', []))
    total_assignments = sum(len(docs) for docs in final_assignments.values())
    
    print(f"📈 Final Statistics:")
    print(f"   - LC Requirements: {total_requirements}")
    print(f"   - Input Documents: {total_documents}")
    print(f"   - Total Assignments: {total_assignments}")
    
    # Show assignment summary
    for req_name, matched_docs in final_assignments.items():
        if matched_docs:
            print(f"   ✅ {req_name}: {len(matched_docs)} documents")
        else:
            print(f"   ❌ {req_name}: No matches")
    
    return {
        "final_assignments": final_assignments,
        "processing_complete": True
    }