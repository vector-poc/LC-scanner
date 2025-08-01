#!/usr/bin/env python3
"""
Simple test script for LC-Scanner API
Tests basic functionality of all endpoints
"""

import requests
import json
from datetime import datetime

# API base URL
BASE_URL = "http://localhost:8000"

def test_health():
    """Test health endpoint"""
    print("Testing health endpoint...")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    print("-" * 50)

def test_get_lcs():
    """Test getting all LCs"""
    print("Testing GET /lcs/...")
    response = requests.get(f"{BASE_URL}/lcs/")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        lcs = response.json()
        print(f"Found {len(lcs)} Letter(s) of Credit")
        if lcs:
            print(f"First LC: {lcs[0]['lc_reference']}")
    else:
        print(f"Error: {response.text}")
    print("-" * 50)

def test_get_export_documents():
    """Test getting all export documents"""
    print("Testing GET /export-documents/...")
    response = requests.get(f"{BASE_URL}/export-documents/")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        docs = response.json()
        print(f"Found {len(docs)} export document(s)")
        if docs:
            print(f"First document: {docs[0]['document_name']}")
    else:
        print(f"Error: {response.text}")
    print("-" * 50)

def test_classification_summary():
    """Test classification summary"""
    print("Testing classification summary...")
    
    # First get an LC ID
    response = requests.get(f"{BASE_URL}/lcs/")
    if response.status_code == 200:
        lcs = response.json()
        if lcs:
            lc_id = lcs[0]['id']
            print(f"Testing classification summary for LC: {lcs[0]['lc_reference']}")
            
            # Get classification summary
            summary_response = requests.get(f"{BASE_URL}/classification-summary/{lc_id}")
            print(f"Status: {summary_response.status_code}")
            if summary_response.status_code == 200:
                summary = summary_response.json()
                print(f"Summary: {json.dumps(summary, indent=2)}")
            else:
                print(f"Error: {summary_response.text}")
        else:
            print("No LCs found to test classification summary")
    else:
        print("Could not fetch LCs for classification test")
    print("-" * 50)

def test_run_classification():
    """Test running classification"""
    print("Testing classification run...")
    
    # Get an LC ID
    response = requests.get(f"{BASE_URL}/lcs/")
    if response.status_code == 200:
        lcs = response.json()
        if lcs:
            lc_id = lcs[0]['id']
            print(f"Running classification for LC: {lcs[0]['lc_reference']}")
            
            # Run classification
            classify_response = requests.post(f"{BASE_URL}/classify/{lc_id}")
            print(f"Status: {classify_response.status_code}")
            if classify_response.status_code == 200:
                result = classify_response.json()
                print(f"Classification run completed:")
                print(f"  Total export docs: {result['total_export_docs']}")
                print(f"  Total LC requirements: {result['total_lc_requirements']}")
                print(f"  Total matches found: {result['total_matches_found']}")
                print(f"  Status: {result['status']}")
            else:
                print(f"Error: {classify_response.text}")
        else:
            print("No LCs found to test classification")
    else:
        print("Could not fetch LCs for classification test")
    print("-" * 50)

def test_get_classifications():
    """Test getting classification results"""
    print("Testing GET classifications...")
    
    # Get an LC ID
    response = requests.get(f"{BASE_URL}/lcs/")
    if response.status_code == 200:
        lcs = response.json()
        if lcs:
            lc_id = lcs[0]['id']
            print(f"Getting classifications for LC: {lcs[0]['lc_reference']}")
            
            # Get classifications
            class_response = requests.get(f"{BASE_URL}/classifications/{lc_id}")
            print(f"Status: {class_response.status_code}")
            if class_response.status_code == 200:
                classifications = class_response.json()
                print(f"Found {len(classifications)} classification(s)")
                
                # Show matched classifications
                matched = [c for c in classifications if c['is_matched']]
                print(f"Matched documents: {len(matched)}")
                
                if matched:
                    print("Sample matches:")
                    for match in matched[:3]:  # Show first 3 matches
                        print(f"  Confidence: {match['confidence_score']:.2f}")
                        print(f"  Reasoning: {match['reasoning'][:100]}...")
            else:
                print(f"Error: {class_response.text}")
        else:
            print("No LCs found to test classifications")
    else:
        print("Could not fetch LCs for classification test")
    print("-" * 50)

def main():
    """Run all tests"""
    print("="*60)
    print("LC-Scanner API Test Suite")
    print("="*60)
    
    try:
        # Basic health check
        test_health()
        
        # Test LC endpoints
        test_get_lcs()
        
        # Test export document endpoints
        test_get_export_documents()
        
        # Test classification endpoints
        test_classification_summary()
        test_run_classification()
        test_get_classifications()
        
        print("="*60)
        print("Test suite completed!")
        print("="*60)
        
    except requests.exceptions.ConnectionError:
        print("ERROR: Could not connect to API server.")
        print("Make sure the API is running on http://localhost:8000")
        print("Run: docker-compose up -d")
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    main()