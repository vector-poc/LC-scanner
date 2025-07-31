"""Utility functions for LC Document Classification."""

import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

# Try to import document extraction service, fallback if not available
try:
    # Add the parent directory to sys.path to import document_extraction_service
    parent_dir = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(parent_dir))
    from document_extraction_service.schemas.letter_of_credit import DocumentRequirement
except ImportError:
    # Fallback: define minimal DocumentRequirement if import fails
    from pydantic import BaseModel
    from typing import List, Optional
    
    class DocumentRequirement(BaseModel):
        name: str
        description: Optional[str] = None
        quantity: int = 1
        validation_criteria: Optional[List[str]] = None


class DocumentClassifierLLM:
    """LLM-powered document classifier for LC requirements."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "google/gemini-2.0-flash-001"):
        """Initialize the classifier with LLM."""
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OpenRouter API key is required. Set OPENROUTER_API_KEY env var.")
        
        self.model = model
        self.llm = ChatOpenAI(
            model=self.model,
            api_key=self.api_key,
            base_url="https://openrouter.ai/api/v1",
            temperature=0.1,
            max_tokens=2000,
            model_kwargs={
                "extra_headers": {
                    "HTTP-Referer": "https://github.com/lc-document-classifier",
                    "X-Title": "LC Document Classifier"
                }
            }
        )
    
    def classify_documents(self, 
                          lc_requirement: Dict[str, Any], 
                          input_documents: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Classify input documents against an LC requirement.
        
        Args:
            lc_requirement: LC document requirement from DOCUMENTS_REQUIRED
            input_documents: List of documents to classify
            
        Returns:
            Classification result with matches, confidence, and reasoning
        """
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert in Letter of Credit (LC) document analysis and trade finance compliance.
Your task is to classify input documents against specific LC document requirements.

For each classification:
1. Analyze the document content carefully
2. Compare against the LC requirement description and validation criteria
3. Provide confidence scores (0.0 to 1.0) for matches
4. Give clear reasoning for your decisions
5. Only match documents that genuinely satisfy the LC requirement

Be strict in your matching - false positives can cause compliance issues."""),
            
            ("user", """LC Document Requirement:
Name: {requirement_name}
Description: {requirement_description}
Quantity Required: {quantity}
Validation Criteria: {validation_criteria}

Input Documents to Classify:
{documents_text}

Please classify each document and return a JSON response with:
{{
    "matched_documents": ["doc1.pdf", "doc2.pdf"],  // Names of matching documents
    "confidence_scores": [0.95, 0.80],  // Confidence for each match (0.0-1.0)
    "reasoning": "Detailed explanation of why documents match or don't match",
    "status": "matched"  // "matched", "no_match", or "partial_match"
}}

Only include documents in matched_documents if they genuinely satisfy the LC requirement.""")
        ])
        
        # Format documents for analysis
        documents_text = ""
        for i, doc in enumerate(input_documents, 1):
            documents_text += f"""
Document {i}: {doc['name']}
Summary: {doc['summary']}
Content Preview: {doc['full_text'][:1000]}{'...' if len(doc['full_text']) > 1000 else ''}
---
"""
        
        # Format validation criteria
        validation_criteria = ""
        if isinstance(lc_requirement.get('validation_criteria'), list):
            validation_criteria = "\n".join([f"- {criteria}" for criteria in lc_requirement['validation_criteria']])
        else:
            validation_criteria = str(lc_requirement.get('validation_criteria', 'No specific criteria'))
        
        try:
            response = self.llm.invoke(prompt.format_messages(
                requirement_name=lc_requirement.get('name', 'Unknown'),
                requirement_description=lc_requirement.get('description', 'No description'),
                quantity=lc_requirement.get('quantity', 1),
                validation_criteria=validation_criteria,
                documents_text=documents_text
            ))
            
            # Parse JSON response
            import json
            import re
            
            content = response.content
            
            # Extract JSON from response if it's wrapped in markdown
            if "```json" in content:
                start = content.find("```json") + 7
                end = content.find("```", start)
                content = content[start:end].strip()
            elif content.strip().startswith('{'):
                pass  # Already clean JSON
            else:
                # Try to find JSON pattern
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    content = json_match.group(0)
                else:
                    raise ValueError(f"No valid JSON found in response: {content}")
            
            result = json.loads(content)
            
            # Validate response structure
            if not isinstance(result.get('matched_documents'), list):
                result['matched_documents'] = []
            if not isinstance(result.get('confidence_scores'), list):
                result['confidence_scores'] = []
            if not result.get('reasoning'):
                result['reasoning'] = "No reasoning provided"
            if not result.get('status'):
                result['status'] = "no_match" if not result['matched_documents'] else "matched"
            
            # Ensure confidence scores match matched documents
            if len(result['confidence_scores']) != len(result['matched_documents']):
                result['confidence_scores'] = [0.5] * len(result['matched_documents'])
            
            return result
            
        except Exception as e:
            # Return error result
            return {
                "matched_documents": [],
                "confidence_scores": [],
                "reasoning": f"Error during classification: {str(e)}",
                "status": "error"
            }


def extract_lc_requirements(extracted_lc: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract document requirements from LC analysis."""
    documents_required = extracted_lc.get('DOCUMENTS_REQUIRED', [])
    
    if not documents_required:
        return []
    
    # Convert to standard dict format if needed
    requirements = []
    for req in documents_required:
        if isinstance(req, dict):
            requirements.append(req)
        else:
            # Handle other formats if needed
            requirements.append({
                'name': str(req),
                'description': '',
                'quantity': 1,
                'validation_criteria': []
            })
    
    return requirements


def validate_input_documents(input_documents: List[Dict[str, str]]) -> List[str]:
    """Validate input document format and return any errors."""
    errors = []
    
    if not input_documents:
        errors.append("No input documents provided")
        return errors
    
    required_fields = ['name', 'summary', 'full_text']
    
    for i, doc in enumerate(input_documents):
        if not isinstance(doc, dict):
            errors.append(f"Document {i+1} is not a dictionary")
            continue
        
        for field in required_fields:
            if field not in doc:
                errors.append(f"Document {i+1} missing required field: {field}")
            elif not isinstance(doc[field], str):
                errors.append(f"Document {i+1} field '{field}' must be a string")
            elif not doc[field].strip():
                errors.append(f"Document {i+1} field '{field}' cannot be empty")
    
    return errors


def format_final_results(classification_results: List[Dict[str, Any]], 
                        lc_requirements: List[Dict[str, Any]]) -> Dict[str, List[str]]:
    """Format classification results into final assignment mapping."""
    final_assignments = {}
    
    for i, result in enumerate(classification_results):
        if i < len(lc_requirements):
            req_name = lc_requirements[i].get('name', f'Requirement_{i+1}')
            final_assignments[req_name] = result.get('matched_documents', [])
    
    return final_assignments