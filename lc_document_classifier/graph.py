"""
Simple LC Document Classifier - LangGraph Implementation
Classifies export documents into LC required document categories
"""

import json
import os
from pathlib import Path
from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from langfuse import Langfuse
from langfuse.langchain import CallbackHandler

# Load environment variables
load_dotenv()

# Initialize Langfuse
langfuse = Langfuse()
langfuse_handler = CallbackHandler()


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
    """Load LC requirements from LC.json"""
    
    try:
        lc_path = Path("../output/LC.json")
        with open(lc_path, 'r', encoding='utf-8') as f:
            lc_data = json.load(f)
        
        requirements = lc_data.get("DOCUMENTS_REQUIRED", [])
        lc_reference = lc_data.get("LC_REFERENCE", "Unknown")
        
        print(f"✅ Loaded LC: {lc_reference}")
        print(f"✅ Found {len(requirements)} required document types:")
        for req in requirements:
            print(f"   - {req.get('name', 'Unknown')}")
        
        return {
            **state,
            "lc_requirements": requirements,
            "lc_reference": lc_reference,
            "status": "requirements_loaded"
        }
        
    except Exception as e:
        print(f"❌ Error loading LC requirements: {e}")
        return {**state, "error": f"Failed to load LC requirements: {e}"}


def load_export_documents(state: ClassificationState) -> ClassificationState:
    """Load export documents from Export_docs.json"""
    
    try:
        export_path = Path("../output/Export_docs.json")
        with open(export_path, 'r', encoding='utf-8') as f:
            export_data = json.load(f)
        
        documents = export_data.get("documents", [])
        
        print(f"✅ Loaded {len(documents)} export documents:")
        for doc in documents[:3]:  # Show first 3
            doc_name = doc["extraction_result"]["document_name"]
            print(f"   - {doc_name}")
        if len(documents) > 3:
            print(f"   ... and {len(documents) - 3} more")
        
        updated_state = {
            **state,
            "export_documents": documents,
            "current_doc_index": 0,
            "classifications": [],
            "total_documents": len(documents),
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
        
        # Add to classifications list
        classifications.append(classification_record)
        
        print(f"📝 Stored classification record:")
        print(f"   🆔 Export Doc ID: {classification_record['export_document_id']}")
        print(f"   📄 Export Doc Name: {classification_record['export_document_name']}")
        print(f"   🏷️  LC Doc ID: {classification_record['lc_document_id']}")
        print(f"   📋 LC Doc Name: {classification_record['lc_document_name']}")
        print(f"   ✅ Is Classified: {classification_record['is_classified']}")
        
        # Move to next document
        next_index = state["current_doc_index"] + 1
        
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


def format_final_results(state: ClassificationState) -> ClassificationState:
    """Format and display final classification results"""
    
    try:
        lc_reference = state.get("lc_reference", "Unknown")
        requirements = state.get("lc_requirements", [])
        classifications = state.get("classifications", [])
        total_docs = state.get("total_documents", 0)
        
        print("\n" + "="*80)
        print("🎯 DOCUMENT CLASSIFICATION RESULTS")
        print("="*80)
        print(f"LC Reference: {lc_reference}")
        
        # Count successful classifications
        classified_count = sum(1 for c in classifications if c.get("is_classified", False))
        print(f"Documents successfully classified: {classified_count}/{total_docs}")
        
        print("\n📋 EXPORT DOCUMENT CLASSIFICATIONS:")
        print("-" * 80)
        
        # Group by LC requirement for better display
        grouped_by_lc = {}
        unclassified_docs = []
        
        for classification in classifications:
            if classification["is_classified"]:
                lc_req_name = classification["lc_document_name"]
                if lc_req_name not in grouped_by_lc:
                    grouped_by_lc[lc_req_name] = []
                grouped_by_lc[lc_req_name].append(classification)
            else:
                unclassified_docs.append(classification)
        
        # Display classified documents grouped by LC requirement
        for requirement in requirements:
            req_name = requirement["name"]
            matched_docs = grouped_by_lc.get(req_name, [])
            
            print(f"\n📄 {req_name}:")
            if matched_docs:
                for doc in matched_docs:
                    print(f"   ✅ {doc['export_document_name']}")
                    print(f"      📊 Confidence: {doc['confidence']:.1%}")
                    print(f"      💭 Reasoning: {doc['reasoning']}")
            else:
                print("   ❌ No matching export documents found")
        
        # Show unclassified documents
        if unclassified_docs:
            print(f"\n❓ UNCLASSIFIED DOCUMENTS:")
            print("-" * 40)
            for doc in unclassified_docs:
                print(f"   ❌ {doc['export_document_name']}")
                print(f"      📊 Best confidence: {doc['confidence']:.1%}")
                print(f"      💭 Reasoning: {doc['reasoning']}")
        
        # Summary statistics
        print(f"\n📊 SUMMARY:")
        print(f"   Total documents processed: {len(classifications)}")
        print(f"   Successfully classified: {classified_count}")
        print(f"   Unclassified: {len(unclassified_docs)}")
        print(f"   Classification rate: {(classified_count/total_docs*100):.1f}%" if total_docs > 0 else "   Classification rate: 0%")
        
        return {
            **state,
            "final_results": classifications,
            "processing_complete": True,
            "status": "completed"
        }
        
    except Exception as e:
        print(f"❌ Error formatting results: {e}")
        return {**state, "error": f"Result formatting failed: {e}"}


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
            
            # Use trace-scoped callback handler if trace_id is provided
            if trace_id:
                trace = langfuse.get_trace(trace_id)
                trace_handler = trace.get_langchain_handler()
                callbacks = [trace_handler]
            else:
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


# Simple runner function
def run_classification():
    """Run the classification graph"""
    
    print("🚀 Starting LC Document Classification")
    print("="*50)
    
    # Create main trace for the classification process
    trace = langfuse.trace(
        name="LC Document Classification",
        tags=["document-classification", "export-documents", "letter-of-credit"],
        metadata={
            "session": "classification_run",
            "version": "1.0"
        }
    )
    
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
        "trace_id": trace.id
    }
    
    config = {
        "configurable": {"thread_id": "classification_run"},
        "recursion_limit": 100
    }
    
    final_state = graph.invoke(initial_state, config=config)
    
    if final_state.get("processing_complete"):
        print("\n🎉 Classification completed successfully!")
    else:
        print("\n⚠️  Classification completed with issues")
        
    return final_state


if __name__ == "__main__":
    run_classification()