"""
Simple LC Document Classifier - LangGraph Implementation
Classifies export documents into LC required document categories
"""

import json
import os
from pathlib import Path
from typing import Optional
from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from langfuse import Langfuse
from langfuse.langchain import CallbackHandler
from db_service import LCDatabaseService, create_db_service
# Import models for type checking
import sys
sys.path.append(str(Path(__file__).parent.parent / "api"))
from models import LetterOfCredit as LCModel

# Load environment variables
load_dotenv()

# Initialize Langfuse
langfuse = Langfuse()
langfuse_handler = CallbackHandler()

# Shared database service instance
_db_service = None

def get_shared_db_service():
    """Get or create a shared database service instance"""
    global _db_service
    if _db_service is None:
        _db_service = create_db_service()
    return _db_service

def close_shared_db_service():
    """Close the shared database service"""
    global _db_service
    if _db_service is not None:
        _db_service.close()
        _db_service = None


class ClassificationState(TypedDict):
    """State for document classification"""
    lc_requirements: list
    lc_reference: str
    export_documents: list
    current_doc_index: int
    classifications: list
    current_classification: dict
    total_documents: int
    status: str
    error: str
    trace_id: str  # Add trace ID to state
    # Database-related fields
    lc_id: Optional[str]  # LC database ID (used to identify which LC to process)
    classification_run_id: Optional[str]  # Classification run ID


# Pydantic model for structured output
class DocumentClassification(BaseModel):
    """Document classification result"""
    
    selected_lc_document_id: str = Field(description="The ID of the selected LC requirement document or 'OTHER'")
    selected_lc_document_name: str = Field(description="The name of the selected LC requirement document or 'OTHER'")
    confidence: float = Field(description="Confidence score between 0.0 and 1.0", ge=0.0, le=1.0)
    reason: str = Field(description="Brief explanation of why this category was chosen")


def get_langchain_llm():
    """Initialize LangChain LLM with proper configuration"""
    
    try:
        # Try OpenAI API key first
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if openai_api_key:
            return ChatOpenAI(
                model="gpt-4o-mini",
                temperature=0,
                api_key=openai_api_key
            )
        
        # Fallback to OpenRouter
        openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        if openrouter_api_key:
            return ChatOpenAI(
                model="openai/gpt-4o-mini",
                temperature=0,
                api_key=openrouter_api_key,
                base_url="https://openrouter.ai/api/v1"
            )
        
        print("⚠️  No API key found")
        return None
        
    except Exception as e:
        print(f"⚠️  Error initializing LLM: {e}")
        return None


def load_lc_requirements(state: ClassificationState) -> ClassificationState:
    """Load LC requirements from database using lc_id"""
    
    try:
        lc_id = state.get("lc_id")
        
        if not lc_id:
            raise ValueError("LC ID not provided in state. Please provide 'lc_id' to identify which LC to process.")
        
        # Use shared database service
        db_service = get_shared_db_service()
        
        # Try to get LC by ID first, if that fails try by reference
        from models import LetterOfCredit as LCModel
        lc = None
        
        try:
            # Try as integer ID first
            lc = db_service.session.query(LCModel).filter(LCModel.id == int(lc_id)).first()
        except (ValueError, TypeError):
            # If not a valid integer, try as reference string
            lc = db_service.get_lc_by_reference(lc_id)
            if lc:
                lc_id = str(lc.id)
        
        if not lc:
            raise ValueError(f"No LC found with ID or reference: {lc_id}")
        
        # Get LC requirements using the reference
        requirements, lc_ref = db_service.get_lc_requirements_data(lc.lc_reference)
        
        print(f"✅ Loaded LC: {lc_ref} (ID: {lc_id})")
        print(f"✅ Found {len(requirements)} required document types:")
        for req in requirements:
            print(f"   - {req.get('name', 'Unknown')}")
        
        return {
            **state,
            "lc_requirements": requirements,
            "lc_reference": lc_ref,
            "lc_id": lc_id,
            "status": "requirements_loaded"
        }
        
    except Exception as e:
        print(f"❌ Error loading LC requirements: {e}")
        return {**state, "error": f"Failed to load LC requirements: {e}"}


def load_export_documents(state: ClassificationState) -> ClassificationState:
    """Load export documents from database using lc_reference"""
    
    try:
        lc_reference = state.get("lc_reference")
        lc_id = state.get("lc_id")
        
        if not lc_reference:
            raise ValueError("LC reference not available from previous step")
        
        # Use shared database service
        db_service = get_shared_db_service()
        
        # Get export documents from database for this specific LC
        export_data = db_service.get_export_documents_data(lc_reference=lc_reference)
        documents = export_data.get("documents", [])
        
        print(f"✅ Loaded {len(documents)} export documents:")
        for doc in documents[:3]:  # Show first 3
            doc_name = doc["extraction_result"]["document_name"]
            print(f"   - {doc_name}")
        if len(documents) > 3:
            print(f"   ... and {len(documents) - 3} more")
        
        # Create classification run for tracking
        lc_requirements = state.get("lc_requirements", [])
        if lc_id and lc_requirements:
            try:
                run = db_service.create_classification_run(
                    lc_reference=lc_reference,
                    total_export_docs=len(documents),
                    total_lc_requirements=len(lc_requirements),
                    model_used="langchain_gpt-4o-mini"
                )
                classification_run_id = str(run.id)
                print(f"✅ Created classification run: {classification_run_id}")
            except Exception as e:
                print(f"⚠️  Warning: Could not create classification run: {e}")
                classification_run_id = None
        else:
            classification_run_id = None
        
        updated_state = {
            **state,
            "export_documents": documents,
            "current_doc_index": 0,
            "classifications": [],
            "total_documents": len(documents),
            "classification_run_id": classification_run_id,
            "status": "documents_loaded"
        }
        return updated_state
        
    except Exception as e:
        print(f"❌ Error loading export documents: {e}")
        return {**state, "error": f"Failed to load export documents: {e}"}


def classify_current_document(state: ClassificationState) -> ClassificationState:
    """Classify current export document against LC requirements"""
    
    documents = state.get("export_documents", [])
    requirements = state.get("lc_requirements", [])
    current_index = state.get("current_doc_index", 0)
    
    # Check if we've processed all documents
    if current_index >= len(documents):
        print(f"🏁 Reached end of documents (index {current_index} >= {len(documents)})")
        return {**state, "status": "all_classified"}
    
    current_doc = documents[current_index]
    
    # Extract document data - data will follow exact JSON format
    extraction_result = current_doc["extraction_result"]
    doc_name = extraction_result["document_name"]
    doc_summary = extraction_result["summary"]
    
    print(f"\n🔍 Classifying document {current_index + 1}/{len(documents)}: {doc_name}")
    
    # Create prompt with all LC requirements for LLM to choose from
    requirements_text = ""
    for i, requirement in enumerate(requirements, 1):
        req_id = requirement.get("document_id", f"doc_{i:03d}")
        req_name = requirement.get("name", "")
        req_description = requirement.get("description", "") or ""
        desc_preview = req_description[:200] + "..." if len(req_description) > 200 else req_description
        requirements_text += f"{i}. ID: {req_id} | NAME: {req_name}\n   Description: {desc_preview}\n\n"
    
    prompt = f"""You are classifying an export document into one of the LC (Letter of Credit) required document categories.

EXPORT DOCUMENT:
Name: {doc_name}
Summary: {doc_summary}

LC REQUIRED DOCUMENT CATEGORIES:
{requirements_text}

INSTRUCTIONS:
- Analyze the export document name and summary
- Select the MOST APPROPRIATE LC requirement from the list above
- Look at both the ID and NAME to make your selection
- If none of the categories match well, use "OTHER" for both ID and NAME

You must respond with structured output containing:
- selected_lc_document_id: The document ID (e.g., "doc_001") or "OTHER"
- selected_lc_document_name: The document name or "OTHER"  
- confidence: Score between 0.0 and 1.0
- reason: Brief explanation of your choice

Example good matches:
- If document is an invoice → select doc_001 "MANUALLY SIGNED INVOICES"
- If document is inspection certificate → select doc_006 "ORIGINAL LAMINATED PRE SHIPMENT INSPECTION CERTIFICATE"
- If document is registration certificate → select doc_004 "ORIGINAL EXPORT CERTIFICATE/CERTIFICATE OF REGISTRATION" """

    # Call AI classifier with single prompt and trace ID
    trace_id = state.get("trace_id")
    classification_result = call_ai_classifier_with_selection(prompt, trace_id)
    
    # Validate classification result
    if classification_result is None:
        classification_result = {
            "selected_lc_document_id": "OTHER",
            "selected_lc_document_name": "OTHER", 
            "confidence": 0.1,
            "reason": "LLM function returned None"
        }
    elif not isinstance(classification_result, dict):
        classification_result = {
            "selected_lc_document_id": "OTHER",
            "selected_lc_document_name": "OTHER", 
            "confidence": 0.1,
            "reason": f"Invalid return type: {type(classification_result)}"
        }
    else:
        # Ensure all required keys exist
        required_keys = ["selected_lc_document_id", "selected_lc_document_name", "confidence", "reason"]
        for key in required_keys:
            if key not in classification_result:
                classification_result[key] = "OTHER" if "id" in key or "name" in key else (0.0 if key == "confidence" else "Missing data")
    
    print(f"   🤖 LLM Selected ID: {classification_result['selected_lc_document_id']}")
    print(f"   🤖 LLM Selected Name: {classification_result['selected_lc_document_name']}")
    print(f"   📊 Confidence: {classification_result['confidence']:.1%}")
    print(f"   💭 Reason: {classification_result['reason']}")
    
    # Record classification result
    result = {
        "document_id": current_doc["document_id"],
        "document_name": doc_name,
        "best_match_id": classification_result["selected_lc_document_id"],
        "best_match_name": classification_result["selected_lc_document_name"],
        "confidence": classification_result["confidence"],
        "reason": classification_result["reason"],
        "classified": classification_result["selected_lc_document_id"] != "OTHER" and classification_result["confidence"] > 0.5
    }
    
    if result["classified"]:
        print(f"   ✅ CLASSIFIED as: {result['best_match_id']} - {result['best_match_name']} ({result['confidence']:.1%})")
    else:
        print(f"   ❌ NO CLEAR MATCH or classified as OTHER")
    
    return {
        **state,
        "current_classification": result,
        "status": "document_classified"
    }


def record_and_continue(state: ClassificationState) -> ClassificationState:
    """Record the classification result and move to next document"""
    
    try:
        result = state.get("current_classification", {})
        classifications = state.get("classifications", [])
        classification_run_id = state.get("classification_run_id")
        
        # Use the LC document details directly from the LLM response
        if result["classified"]:
            lc_document_id = result["best_match_id"]
            lc_document_name = result["best_match_name"]
        else:
            lc_document_id = ""
            lc_document_name = ""
        
        # Create classification record for this export document
        classification_record = {
            "export_document_id": result["document_id"],
            "export_document_name": result["document_name"],
            "lc_document_id": lc_document_id,
            "lc_document_name": lc_document_name,
            "confidence": result["confidence"],
            "reasoning": result.get("reason", ""),
            "is_classified": result["classified"]
        }
        
        # Save to database if we have the necessary components
        if classification_run_id and result["classified"] and lc_document_id != "OTHER":
            try:
                # Use shared database service for saving
                db_service = get_shared_db_service()
                db_classification, export_doc = db_service.save_classification(
                    classification_run_id=int(classification_run_id),
                    export_document_id=result["document_id"],
                    lc_requirement_id=lc_document_id,
                    confidence=result["confidence"],
                    reasoning=result.get("reason", ""),
                    is_matched=result["classified"]
                )
                print(f"✅ Saved classification to database: {db_classification.id}")
            except Exception as e:
                print(f"⚠️  Warning: Could not save classification to database: {e}")
                # Continue with in-memory classification even if database save fails
        
        # Add to in-memory classifications list for backward compatibility
        classifications.append(classification_record)
        
        print(f"📝 Stored classification record:")
        print(f"   🆔 Export Doc ID: {classification_record['export_document_id']}")
        print(f"   📄 Export Doc Name: {classification_record['export_document_name']}")
        print(f"   🏷️  LC Doc ID: {classification_record['lc_document_id']}")
        print(f"   📋 LC Doc Name: {classification_record['lc_document_name']}")
        print(f"   ✅ Is Classified: {classification_record['is_classified']}")
        
        # Move to next document
        next_index = state["current_doc_index"] + 1
        
        # Check if this was the last document and finalize classification run
        total_docs = state.get("total_documents", 0)
        classification_run_id = state.get("classification_run_id")
        
        if next_index >= total_docs:
            # This was the last document - finalize the classification run
            if classification_run_id:
                try:
                    # Use shared database service for finalizing
                    db_service = get_shared_db_service()
                    classified_count = sum(1 for c in classifications if c.get('is_classified', False))
                    db_service.update_classification_run_status(
                        run_id=int(classification_run_id),
                        status="completed",
                        total_matches_found=classified_count
                    )
                    print(f"✅ Finalized classification run: {classification_run_id}")
                    print(f"✅ Classification completed! Processed {total_docs} documents, found {classified_count} matches")
                except Exception as e:
                    print(f"⚠️  Warning: Could not finalize classification run: {e}")
        
        return {
            **state,
            "classifications": classifications,
            "current_doc_index": next_index,
            "status": "recorded_and_continuing"
        }
        
    except Exception as e:
        print(f"❌ Error recording classification: {e}")
        return {**state, "error": f"Recording failed: {e}"}


def should_continue(state: ClassificationState) -> str:
    """Check if we should continue classifying more documents"""
    
    current_index = state.get("current_doc_index", 0)
    total_docs = state.get("total_documents", 0)
    
    print(f"🔄 SHOULD_CONTINUE: index={current_index}, total={total_docs}")
    
    # Check if we've processed all documents
    if current_index >= total_docs:
        print("✅ All documents processed - ENDING")
        return "end"
    else:
        print(f"➡️  Continue with document {current_index + 1}")
        return "classify_next"



def initialize_graph_with_lc(lc_reference: str, trace_id: str = None) -> ClassificationState:
    """Initialize the graph state with LC reference and database service"""
    
    try:
        # Create database service
        db_service = create_db_service()
        
        # Test database connection
        if not db_service:
            raise ValueError("Could not create database service")
        
        print(f"✅ Database service initialized")
        print(f"🎯 Target LC: {lc_reference}")
        
        # Create initial state with database service and LC reference
        initial_state = {
            "lc_requirements": [],
            "lc_reference": lc_reference,
            "export_documents": [],
            "current_doc_index": 0,
            "classifications": [],
            "current_classification": {},
            "total_documents": 0,
            "status": "initialized",
            "error": "",
            "trace_id": trace_id or "",
            "lc_id": None,
            "classification_run_id": None,
            "db_service": db_service
        }
        
        return initial_state
        
    except Exception as e:
        print(f"❌ Error initializing graph: {e}")
        return {
            "lc_requirements": [],
            "lc_reference": lc_reference,
            "export_documents": [],
            "current_doc_index": 0,
            "classifications": [],
            "current_classification": {},
            "total_documents": 0,
            "status": "initialization_failed",
            "error": f"Initialization failed: {e}",
            "trace_id": trace_id or "",
            "lc_id": None,
            "classification_run_id": None,
            "db_service": None
        }


def call_ai_classifier_with_selection(prompt: str, trace_id: str = None) -> dict:
    """AI classification call using LangChain with structured output"""
    
    # Default fallback response
    fallback_response = {
        "selected_lc_document_id": "OTHER",
        "selected_lc_document_name": "OTHER", 
        "confidence": 0.1,
        "reason": "Classification failed - using fallback"
    }
    
    try:
        llm = get_langchain_llm()
        if not llm:
            print("⚠️  No LLM available, using mock classification")
            fallback_response.update({
                "confidence": 0.6,
                "reason": "Mock classification - no LLM available"
            })
            return fallback_response
        
        # Configure LLM for structured output
        try:
            structured_llm = llm.with_structured_output(DocumentClassification)
        except Exception as e:
            print(f"⚠️  Failed to configure structured output: {e}")
            fallback_response["reason"] = f"Structured output config failed: {str(e)}"
            return fallback_response
        
        # Create message and invoke with Langfuse callback
        try:
            message = HumanMessage(content=prompt)
            
            # Use langfuse callback handler
            callbacks = [langfuse_handler]
            
            result = structured_llm.invoke([message], config={"callbacks": callbacks})
            
            if result is None:
                print("⚠️  LLM returned None result")
                fallback_response["reason"] = "LLM returned None result"
                return fallback_response
                
        except Exception as e:
            print(f"⚠️  LLM invocation failed: {e}")
            fallback_response["reason"] = f"LLM invocation failed: {str(e)}"
            return fallback_response
        
        # Validate and extract result fields
        try:
            response = {
                "selected_lc_document_id": getattr(result, 'selected_lc_document_id', 'OTHER'),
                "selected_lc_document_name": getattr(result, 'selected_lc_document_name', 'OTHER'),
                "confidence": getattr(result, 'confidence', 0.1),
                "reason": getattr(result, 'reason', 'No reason provided')
            }
            
            # Validate response fields
            if not isinstance(response["selected_lc_document_id"], str):
                response["selected_lc_document_id"] = "OTHER"
            if not isinstance(response["selected_lc_document_name"], str):
                response["selected_lc_document_name"] = "OTHER"
            if not isinstance(response["confidence"], (int, float)):
                response["confidence"] = 0.1
            if not isinstance(response["reason"], str):
                response["reason"] = "Invalid reason format"
                
            # Ensure confidence is in valid range
            response["confidence"] = max(0.0, min(1.0, float(response["confidence"])))
            
            return response
            
        except Exception as e:
            print(f"⚠️  Failed to extract result fields: {e}")
            fallback_response["reason"] = f"Result extraction failed: {str(e)}"
            return fallback_response
        
    except Exception as e:
        print(f"⚠️  Unexpected error in LLM call: {e}")
        fallback_response["reason"] = f"Unexpected error: {str(e)}"
        return fallback_response


# Create the LangGraph
def create_graph():
    """Create the document classification graph"""
    
    workflow = StateGraph(ClassificationState)
    
    # Add nodes
    workflow.add_node("load_lc_requirements", load_lc_requirements)
    workflow.add_node("load_export_documents", load_export_documents)
    workflow.add_node("classify_current_document", classify_current_document)
    workflow.add_node("record_and_continue", record_and_continue)
    
    # Add edges
    workflow.add_edge(START, "load_lc_requirements")
    workflow.add_edge("load_lc_requirements", "load_export_documents")
    workflow.add_edge("load_export_documents", "classify_current_document")
    workflow.add_edge("classify_current_document", "record_and_continue")
    
    # Conditional edge for classification loop
    workflow.add_conditional_edges(
        "record_and_continue",
        should_continue,
        {
            "classify_next": "classify_current_document",
            "end": END
        }
    )
    
    return workflow.compile()


# Create the graph instance
graph = create_graph()


# Enhanced runner function with database support
def run_classification(lc_reference: str = None):
    """Run the classification graph with database integration"""
    
    print("🚀 Starting LC Document Classification")
    print("="*50)
    
    # Create main trace for the classification process
    trace_id = langfuse.create_trace_id()
    trace = langfuse.start_span(
        name="LC Document Classification",
        metadata={
            "session": "classification_run",
            "version": "2.0",
            "lc_reference": lc_reference or "unknown"
        }
    )
    
    # Initialize graph state with database service
    if lc_reference:
        print(f"🎯 Using database mode with LC reference: {lc_reference}")
        initial_state = initialize_graph_with_lc(lc_reference, trace_id)
    else:
        print("⚠️  No LC reference provided - using legacy mode")
        # Fallback to old behavior for backward compatibility
        initial_state = {
            "lc_requirements": [],
            "lc_reference": "",
            "export_documents": [],
            "current_doc_index": 0,
            "classifications": [],
            "current_classification": {},
            "total_documents": 0,
            "status": "starting",
            "error": "",
            "trace_id": trace_id,
            "lc_id": None,
            "classification_run_id": None,
            "db_service": None
        }
    
    # Check for initialization errors
    if initial_state.get("status") == "initialization_failed":
        print(f"❌ Graph initialization failed: {initial_state.get('error')}")
        return initial_state
    
    config = {
        "configurable": {"thread_id": "classification_run"},
        "recursion_limit": 100
    }
    
    try:
        final_state = graph.invoke(initial_state, config=config)
        
        # Classification run status is updated in format_final_results
        
        if final_state.get("processing_complete"):
            print("\n🎉 Classification completed successfully!")
        else:
            print("\n⚠️  Classification completed with issues")
            
        return final_state
        
    except Exception as e:
        print(f"❌ Error during classification: {e}")
        
        # Update classification run status to failed if using database
        db_service = initial_state.get("db_service")
        classification_run_id = initial_state.get("classification_run_id")
        
        if db_service and classification_run_id:
            try:
                db_service.update_classification_run_status(
                    run_id=classification_run_id,
                    status="failed"
                )
            except:
                pass  # Don't fail on cleanup errors
        
        return {**initial_state, "error": f"Classification failed: {e}", "status": "failed"}
    
    finally:
        # Clean up database service
        db_service = initial_state.get("db_service")
        if db_service:
            try:
                db_service.close()
                print("✅ Database connection closed")
            except Exception as e:
                print(f"⚠️  Warning: Error closing database connection: {e}")


# Legacy function for backward compatibility
def run_classification_legacy():
    """Run classification using the original JSON file method"""
    return run_classification(lc_reference=None)


if __name__ == "__main__":
    # Try to get LC reference from command line or use a default
    import sys
    
    if len(sys.argv) > 1:
        lc_ref = sys.argv[1]
        print(f"Using LC reference from command line: {lc_ref}")
        run_classification(lc_reference=lc_ref)
    else:
        # Try to find any LC in the database and use the first one
        try:
            with create_db_service() as db_service:
                # Use the first LC found
                first_lc = db_service.session.query(LCModel).first()
                if first_lc:
                    print(f"Using first LC found in database: {first_lc.lc_reference}")
                    run_classification(lc_reference=first_lc.lc_reference)
                else:
                    print("❌ No LCs found in database")
                    print("💡 Run populate_db.py first to load LC data")
        except Exception as e:
            print(f"❌ Could not connect to database: {e}")
            print("📝 Usage: python graph.py [LC_REFERENCE]")
            print("📝 Or ensure database is populated with LC data")