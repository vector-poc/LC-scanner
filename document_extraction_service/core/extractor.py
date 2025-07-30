"""Configurable document extraction service."""

import os
import base64
import json
import re
from pathlib import Path
from typing import Union, Any
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from ..utils.pdf_extractor import PDFExtractor
from ..schemas.base import BaseDocumentSchema
from ..schemas.default import DefaultDocumentSchema

# Load environment variables
load_dotenv()


class DocumentExtractor:
    """Configurable PDF document extraction service using OpenRouter and Gemini via LangChain."""
    
    def __init__(self, api_key: str = None, model: str = "google/gemini-2.0-flash-001"):
        """
        Initialize the DocumentExtractor.
        
        Args:
            api_key: OpenRouter API key. If not provided, will look for OPENROUTER_API_KEY env var.
            model: Model to use for analysis (default: google/gemini-2.0-flash-001)
        """
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OpenRouter API key is required. Set OPENROUTER_API_KEY env var or pass api_key parameter.")
        
        self.model = model
        
        # Initialize the ChatOpenAI model with OpenRouter base URL for Gemini
        self.llm = ChatOpenAI(
            model=self.model,
            api_key=self.api_key,
            base_url="https://openrouter.ai/api/v1",
            temperature=0,
            max_tokens=4000,
            model_kwargs={
                "extra_headers": {
                    "HTTP-Referer": "https://github.com/document-extraction-service",
                    "X-Title": "Document Extraction Service"
                }
            }
        )
    
    def extract(self, 
                file_path: Union[str, Path], 
                schema: BaseDocumentSchema = None,
                filename: str = None,
                output_path: str = None) -> Any:
        """
        Extract structured information from a PDF document.
        
        Args:
            file_path: Path to the PDF file
            schema: Document schema to use for extraction (defaults to DefaultDocumentSchema)
            filename: Optional custom filename to display in analysis
            output_path: Optional path to save results as JSON
            
        Returns:
            Structured analysis results based on the provided schema
            
        Raises:
            FileNotFoundError: If the PDF file doesn't exist
            Exception: If there's an error during extraction
        """
        if schema is None:
            schema = DefaultDocumentSchema()
            
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"PDF file not found: {file_path}")
        
        # Use provided filename or extract from path
        display_filename = filename or file_path.name
        
        try:
            # First try to extract text from PDF
            document_text = PDFExtractor.extract_text_from_file(file_path)
            
            if not document_text.strip():
                raise Exception("No text content found in the PDF file")
            
            # Get page count
            page_count = PDFExtractor.get_page_count(file_path)
            
            # Use text-based analysis with LangChain structured output
            structured_llm = self.llm.with_structured_output(schema.schema_class)
            
            prompt = ChatPromptTemplate.from_messages([
                ("system", "You are an expert document analyst. Analyze the provided PDF document text and extract comprehensive information according to the specified structure."),
                ("user", """Please analyze this PDF document:

Document Text:
{document_text}

Additional Context:
- File name: {filename}
- Page count: {page_count}

{analysis_instructions}

Provide your analysis in the exact structured format specified.""")
            ])
            
            analysis_chain = prompt | structured_llm
            
            result = analysis_chain.invoke({
                "document_text": document_text,
                "filename": display_filename,
                "page_count": page_count,
                "analysis_instructions": schema.prompt_template
            })
            
        except Exception as e:
            if "No text content found" in str(e):
                # If no text is extractable, try PDF upload with OCR
                print("📄 No extractable text found - trying OCR via file upload...")
                result = self._extract_with_upload(file_path, schema, display_filename)
            else:
                raise Exception(f"Error extracting from PDF: {str(e)}")
        
        # Save results if output path is provided
        if output_path:
            self._save_results(result, output_path)
            
        return result
    
    def extract_bytes(self, 
                     pdf_bytes: bytes, 
                     schema: BaseDocumentSchema = None,
                     filename: str = "document.pdf",
                     output_path: str = None) -> Any:
        """
        Extract structured information from PDF bytes.
        
        Args:
            pdf_bytes: PDF content as bytes
            schema: Document schema to use for extraction (defaults to DefaultDocumentSchema)
            filename: Name to use for the document in analysis
            output_path: Optional path to save results as JSON
            
        Returns:
            Structured analysis results based on the provided schema
            
        Raises:
            Exception: If there's an error during extraction
        """
        if schema is None:
            schema = DefaultDocumentSchema()
            
        try:
            # Extract text from PDF bytes
            document_text = PDFExtractor.extract_text_from_bytes(pdf_bytes)
            
            if not document_text.strip():
                raise Exception("No text content found in the PDF file")
            
            # Estimate page count (approximate)
            page_count = document_text.count("--- Page ")
            
            # Use text-based analysis with LangChain structured output
            structured_llm = self.llm.with_structured_output(schema.schema_class)
            
            prompt = ChatPromptTemplate.from_messages([
                ("system", "You are an expert document analyst. Analyze the provided PDF document text and extract comprehensive information according to the specified structure."),
                ("user", """Please analyze this PDF document:

Document Text:
{document_text}

Additional Context:
- File name: {filename}
- Page count: {page_count}

{analysis_instructions}

Provide your analysis in the exact structured format specified.""")
            ])
            
            analysis_chain = prompt | structured_llm
            
            result = analysis_chain.invoke({
                "document_text": document_text,
                "filename": filename,
                "page_count": page_count,
                "analysis_instructions": schema.prompt_template
            })
            
        except Exception as e:
            if "No text content found" in str(e):
                raise e
            raise Exception(f"Error extracting from PDF bytes: {str(e)}")
        
        # Save results if output path is provided
        if output_path:
            self._save_results(result, output_path)
            
        return result
    
    def _extract_with_upload(self, file_path: Union[str, Path], schema: BaseDocumentSchema, filename: str) -> Any:
        """
        Extract information by uploading PDF directly to Gemini for OCR processing.
        
        Args:
            file_path: Path to the PDF file
            schema: Document schema to use for extraction
            filename: Display filename for analysis
            
        Returns:
            Structured analysis results based on the provided schema
        """
        try:
            # Read and encode PDF file to base64
            with open(file_path, "rb") as pdf_file:
                pdf_bytes = pdf_file.read()
            
            base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
            data_url = f"data:application/pdf;base64,{base64_pdf}"
            
            # Use raw OpenAI client for file uploads
            import openai
            
            client = openai.OpenAI(
                api_key=self.api_key,
                base_url="https://openrouter.ai/api/v1",
                timeout=600.0
            )
            
            # Check file size and inform user
            file_size_mb = len(pdf_bytes) / (1024 * 1024)
            print(f"📤 Uploading entire PDF ({file_size_mb:.1f}MB) for complete OCR analysis...")
            print("⏳ This may take a few minutes for large files...")
            
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": schema.get_analysis_prompt(filename)
                            },
                            {
                                "type": "file",
                                "file": {
                                    "filename": filename,
                                    "file_data": data_url
                                }
                            }
                        ]
                    }
                ],
                extra_headers={
                    "HTTP-Referer": "https://github.com/document-extraction-service",
                    "X-Title": "Document Extraction Service"
                },
                timeout=600.0
            )
            
            # Parse the JSON response
            response_text = response.choices[0].message.content
            print(f"📝 Received response ({len(response_text)} characters)")
            
            # Check for error responses
            if response_text.strip().startswith("<!DOCTYPE html") or "cloudflare" in response_text.lower():
                raise Exception("Service returned an error page instead of analysis. Service may be temporarily unavailable.")
            
            # Extract JSON from response
            cleaned_response = self._extract_json_from_response(response_text)
            
            # Parse JSON and create schema object
            try:
                data = json.loads(cleaned_response)
                result = schema.schema_class(**data)
                return result
            except json.JSONDecodeError as e:
                raise Exception(f"Failed to parse JSON response: {e}")
            except Exception as e:
                raise Exception(f"Failed to create schema object: {e}")
                
        except Exception as e:
            raise Exception(f"Error extracting with upload: {str(e)}")
    
    def _extract_json_from_response(self, response_text: str) -> str:
        """Extract JSON content from LLM response."""
        original_text = response_text
        
        # Handle markdown-wrapped JSON
        if "```json" in response_text:
            start = response_text.find("```json") + 7
            end = response_text.find("```", start)
            response_text = response_text[start:end].strip()
        elif response_text.strip().startswith('{'):
            # Already clean JSON
            pass
        else:
            # Try to find JSON pattern
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                response_text = json_match.group(0)
            else:
                raise Exception(f"No valid JSON found in response. Response: {original_text[:500]}")
        
        return response_text
    
    def _save_results(self, result: Any, output_path: str) -> None:
        """Save extraction results to JSON file."""
        # Convert Pydantic model to dict
        if hasattr(result, 'model_dump'):
            data = result.model_dump()
        elif hasattr(result, 'dict'):
            data = result.dict()
        else:
            data = dict(result)
        
        # Ensure output directory exists
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Save to JSON
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Results saved to: {output_path}")
    
    def get_model_info(self) -> dict:
        """Get information about the configured model."""
        return {
            "model": self.model,
            "provider": "OpenRouter",
            "base_url": "https://openrouter.ai/api/v1",
            "temperature": 0.1,
            "max_tokens": 4000
        }