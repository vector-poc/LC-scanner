"""Utility functions for LC Document Classification."""

import os
import json
import re
from typing import Dict, List, Any, Optional
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langfuse.langchain import CallbackHandler


class DocumentClassifierLLM:
    """LLM-powered document classifier for LC requirements."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "google/gemini-2.0-flash-001"):
        """Initialize the classifier with LLM."""
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OpenRouter API key is required. Set OPENROUTER_API_KEY env var.")
        
        self.llm = ChatOpenAI(
            model=model,
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
        
        # Initialize Langfuse callback handler
        self.langfuse_handler = CallbackHandler()
    
    def classify_documents(self, 
                          lc_requirement: Dict[str, Any], 
                          input_documents: List[Dict[str, str]]) -> Dict[str, Any]:
        """Classify input documents against an LC requirement."""
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert in Letter of Credit (LC) document analysis and trade finance compliance.
Classify input documents against specific LC document requirements.

Be strict in your matching - false positives can cause compliance issues.
Return only valid JSON with the exact structure requested."""),
            
            ("user", """LC Document Requirement:
Name: {requirement_name}
Description: {requirement_description}
Validation Criteria: {validation_criteria}

Input Documents:
{documents_text}

Return JSON only:
{{
    "matched_documents": ["doc1.pdf"],
    "confidence_scores": [0.95],
    "reasoning": "Brief explanation",
    "status": "matched"
}}""")
        ])
        
        # Format documents
        documents_text = "\n".join([
            f"Document: {doc['name']}\nSummary: {doc['summary']}\nContent: {doc['full_text'][:800]}...\n---"
            for doc in input_documents
        ])
        
        # Format validation criteria
        validation_criteria = ""
        if isinstance(lc_requirement.get('validation_criteria'), list):
            validation_criteria = "; ".join(lc_requirement['validation_criteria'])
        else:
            validation_criteria = str(lc_requirement.get('validation_criteria', 'No specific criteria'))
        
        try:
            response = self.llm.invoke(
                prompt.format_messages(
                    requirement_name=lc_requirement.get('name', 'Unknown'),
                    requirement_description=lc_requirement.get('description', 'No description'),
                    validation_criteria=validation_criteria,
                    documents_text=documents_text
                ),
                config={
                    "callbacks": [self.langfuse_handler],
                    "metadata": {
                        "requirement_name": lc_requirement.get('name', 'Unknown'),
                        "num_documents": len(input_documents),
                        "operation": "document_classification"
                    }
                }
            )
            
            return self._parse_json_response(response.content)
            
        except Exception as e:
            return {
                "matched_documents": [],
                "confidence_scores": [],
                "reasoning": f"Classification error: {str(e)}",
                "status": "error"
            }
    
    def _parse_json_response(self, content: str) -> Dict[str, Any]:
        """Parse JSON response from LLM with fallback handling."""
        try:
            # Clean up common markdown formatting
            if "```json" in content:
                start = content.find("```json") + 7
                end = content.find("```", start)
                content = content[start:end].strip()
            elif not content.strip().startswith('{'):
                # Find JSON pattern in text
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    content = json_match.group(0)
            
            result = json.loads(content)
            
            # Validate and fix structure
            result.setdefault('matched_documents', [])
            result.setdefault('confidence_scores', [])
            result.setdefault('reasoning', 'No reasoning provided')
            result.setdefault('status', 'no_match' if not result['matched_documents'] else 'matched')
            
            # Ensure confidence scores match matched documents
            if len(result['confidence_scores']) != len(result['matched_documents']):
                result['confidence_scores'] = [0.5] * len(result['matched_documents'])
            
            return result
            
        except (json.JSONDecodeError, AttributeError):
            return {
                "matched_documents": [],
                "confidence_scores": [],
                "reasoning": "Failed to parse LLM response",
                "status": "error"
            }


def extract_lc_requirements(extracted_lc: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract document requirements from LC analysis."""
    documents_required = extracted_lc.get('DOCUMENTS_REQUIRED', [])
    
    requirements = []
    for req in documents_required:
        if isinstance(req, dict):
            requirements.append(req)
        else:
            requirements.append({
                'name': str(req),
                'description': '',
                'quantity': 1,
                'validation_criteria': []
            })
    
    return requirements


def validate_input_documents(input_documents: List[Dict[str, str]]) -> List[str]:
    """Validate input document format and return errors."""
    if not input_documents:
        return ["No input documents provided"]
    
    errors = []
    required_fields = ['name', 'summary', 'full_text']
    
    for i, doc in enumerate(input_documents):
        if not isinstance(doc, dict):
            errors.append(f"Document {i+1} is not a dictionary")
            continue
        
        for field in required_fields:
            if field not in doc or not isinstance(doc[field], str) or not doc[field].strip():
                errors.append(f"Document {i+1} missing or invalid field: {field}")
    
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