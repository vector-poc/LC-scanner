#!/usr/bin/env python3
"""
Test runner for LC Document Classification Graph.

This script demonstrates how to use the document classification graph
with sample data or real LC extraction results.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from lc_classifier import run_classification
from langfuse.langchain import CallbackHandler
from langfuse import Langfuse


def load_sample_lc_data() -> Dict[str, Any]:
    """Load sample LC data from the existing output."""
    lc_file = Path(__file__).parent.parent / "output" / "LC_compressed_lc_analysis.json"
    
    if lc_file.exists():
        with open(lc_file, 'r') as f:
            return json.load(f)
    else:
        # Return minimal sample data if file not found
        return {
            "DOCUMENTS_REQUIRED": [
                {
                    "name": "Commercial Invoice",
                    "description": "Invoice showing goods description and value",
                    "quantity": 1,
                    "validation_criteria": ["Must be signed", "Must show LC number"]
                },
                {
                    "name": "Bill of Lading",
                    "description": "Transport document for goods",
                    "quantity": 1,
                    "validation_criteria": ["Must be clean", "Must be original"]
                }
            ]
        }


def create_sample_documents():
    """Create sample input documents for testing."""
    return [
        {
            "name": "commercial_invoice_001.pdf",
            "summary": "Commercial invoice for Toyota vehicle export from Japan to Sri Lanka",
            "full_text": """
            COMMERCIAL INVOICE
            
            Invoice No: INV-2024-001
            Date: March 28, 2025
            LC No: DB5032LC2503324
            
            From: ACOS CO., LTD
            To: Supreme Terrace, Kurukula, Ragama, Sri Lanka
            
            Description: 01 UNIT OF USED TOYOTA RAIZE G
            Chassis No: A210A-0084873
            Year: 2024/09
            
            FOB Value: $15,000
            Freight: $2,000
            Insurance: $150
            CIF Total: $17,150
            
            This is to certify that the vehicle complies with emission standards
            and safety requirements as specified in the LC.
            
            [Signed by Authorized Representative]
            """
        },
        {
            "name": "bill_of_lading_002.pdf",
            "summary": "Clean on-board bill of lading for vehicle shipment",
            "full_text": """
            BILL OF LADING
            
            B/L No: BL-2024-5678
            Date: April 5, 2025
            Vessel: MV OCEAN STAR
            
            Shipper: ACOS CO., LTD, Japan
            Consignee: Commercial Bank of Ceylon PLC, Imports Dept
            Notify Party: Supreme Terrace, Kurukula, Ragama, Sri Lanka
            
            Port of Loading: NAGOYA, JAPAN
            Port of Discharge: COLOMBO, SRI LANKA
            
            Description: 01 Unit Used Toyota Raize G
            Marks: As per invoice
            
            FREIGHT PREPAID
            CLEAN ON BOARD
            
            Agent in Sri Lanka:
            Name: Ocean Logistics Lanka
            Address: 123 Port City, Colombo 01
            Tel: +94-11-2345678
            """
        },
        {
            "name": "insurance_certificate_003.pdf",
            "summary": "Marine insurance certificate covering CIF value plus 10%",
            "full_text": """
            MARINE INSURANCE CERTIFICATE
            
            Certificate No: INS-2024-9876
            Date: April 1, 2025
            
            Assured: Commercial Bank of Ceylon PLC
            
            Coverage: Marine Institute Cargo Clauses A
            Institute Strike Clauses Cargo
            Institute War Clauses Cargo
            
            Sum Insured: $18,865 (CIF + 10%)
            Voyage: Japan to Sri Lanka
            
            Claims payable in Sri Lanka by:
            Lanka Insurance Company Ltd
            Colombo, Sri Lanka
            
            This certificate covers transhipment risks.
            """
        }
    ]


def main():
    """Main test function."""
    print("Testing LC Document Classification Graph with Langfuse Tracing")
    print("=" * 60)
    
    # Initialize Langfuse client  
    try:
        from langfuse import Langfuse
        langfuse = Langfuse()
        langfuse_handler = CallbackHandler()
        langfuse_enabled = True
        print("✅ Langfuse tracing enabled")
    except Exception as e:
        print(f"⚠️  Langfuse not available: {e}")
        langfuse_enabled = False
    
    # Load test data
    lc_data = load_sample_lc_data()
    input_documents = create_sample_documents()
    
    print(f"Loaded LC with {len(lc_data.get('DOCUMENTS_REQUIRED', []))} requirements")
    print(f"Created {len(input_documents)} sample documents")
    
    # Run classification
    print("\nRunning document classification...")
    try:
        if langfuse_enabled:
            # Create a trace for this test run using the client method
            trace_id = langfuse.create_trace_id()  
            
        results = run_classification(lc_data, input_documents)
        
        print("\nCLASSIFICATION RESULTS")
        print("=" * 30)
        
        print(f"Status: {'Complete' if results['processing_complete'] else 'Incomplete'}")
        print(f"Requirements: {results['total_requirements']}")
        print(f"Documents: {results['total_documents']}")
        
        if results['errors']:
            print(f"\nErrors: {results['errors']}")
        
        print(f"\nDOCUMENT ASSIGNMENTS:")
        for req_name, matched_docs in results['final_assignments'].items():
            if matched_docs:
                print(f"✓ {req_name}: {', '.join(matched_docs)}")
            else:
                print(f"✗ {req_name}: No matches")
        
        print(f"\nDETAILED RESULTS:")
        for i, result in enumerate(results['classification_results'], 1):
            print(f"\n{i}. {result.get('lc_requirement_name', 'Unknown')}")
            print(f"   Status: {result.get('status', 'unknown')}")
            if result.get('matched_documents'):
                for j, doc in enumerate(result['matched_documents']):
                    conf = result.get('confidence_scores', [0])[j] if j < len(result.get('confidence_scores', [])) else 0
                    print(f"   - {doc} (confidence: {conf:.2f})")
            print(f"   Reasoning: {result.get('reasoning', 'No reasoning provided')[:150]}...")
        
        print(f"\nClassification completed successfully!")
        if langfuse_enabled:
            print(f"\n🔍 Check traces in Langfuse dashboard: https://cloud.langfuse.com/project")
        
    except Exception as e:
        print(f"Error during classification: {str(e)}")
        raise


if __name__ == "__main__":
    main()