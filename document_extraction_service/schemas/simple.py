"""Simple document analysis schema for basic extraction."""

from typing import Type
from pydantic import BaseModel, Field
from .base import BaseDocumentSchema


class SimpleDocumentAnalysis(BaseModel):
    """Simple document analysis structure with just name, summary, and full description."""
    document_name: str = Field(description="Short, descriptive name for the document (max 50 characters)")
    summary: str = Field(description="Brief summary of the document (2-3 sentences)")
    full_description: str = Field(description="Comprehensive, detailed description of the entire document including all content, data, figures, tables, and every single detail")


class SimpleDocumentSchema(BaseDocumentSchema):
    """Simple schema for basic document analysis with comprehensive detail extraction."""
    
    @property
    def schema_class(self) -> Type[BaseModel]:
        return SimpleDocumentAnalysis
    
    @property
    def prompt_template(self) -> str:
        return """Analyze the document and extract:
1. A concise document name (max 50 characters) that describes what the document is
2. A brief summary (2-3 sentences) of the document's main purpose
3. A comprehensive, detailed description that includes:
   - Every single piece of information in the document
   - All data, numbers, figures, amounts, dates, names, addresses
   - All tables, charts, diagrams and their contents
   - All terms, conditions, requirements, specifications
   - All procedures, processes, steps described
   - Any forms, fields, or structured data
   - Contact information, references, citations
   - Legal clauses, regulations, compliance requirements
   - Technical specifications or requirements
   - Any other details, no matter how small

IMPORTANT: The full_description must be extremely comprehensive and include every detail from the document. Do not summarize or omit anything."""
    
    @property
    def json_example(self) -> str:
        return """{
  "document_name": "string (max 50 chars)",
  "summary": "string (2-3 sentences)",
  "full_description": "string (extremely detailed and comprehensive)"
}"""