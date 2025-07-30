"""Default document analysis schema."""

from typing import List, Optional, Type
from pydantic import BaseModel, Field
from .base import BaseDocumentSchema


class DocumentMetadata(BaseModel):
    """Document metadata information."""
    title: str = Field(description="Document title or subject")
    author: Optional[str] = Field(default=None, description="Document author if available")
    document_type: str = Field(description="Type of document (e.g., report, letter, contract)")
    page_count: int = Field(description="Number of pages in the document")
    language: str = Field(description="Primary language of the document")


class DocumentSection(BaseModel):
    """A section within the document."""
    title: str = Field(description="Section title or heading")
    content_summary: str = Field(description="Brief summary of the section content")
    page_range: str = Field(description="Page numbers where this section appears")


class KeyPoint(BaseModel):
    """An important point or finding from the document."""
    point: str = Field(description="The key point or finding")
    context: str = Field(description="Additional context or explanation")
    page_reference: str = Field(description="Page number(s) where this point is found")


class DefaultDocumentAnalysis(BaseModel):
    """Complete document analysis structure."""
    metadata: DocumentMetadata = Field(description="Document metadata")
    executive_summary: str = Field(description="2-3 paragraph executive summary")
    main_topics: List[str] = Field(description="List of main topics covered")
    sections: List[DocumentSection] = Field(description="Document sections and summaries")
    key_points: List[KeyPoint] = Field(description="Important points with context")
    target_audience: str = Field(description="Intended audience for the document")
    actionable_items: List[str] = Field(description="Action items or recommendations")
    overall_assessment: str = Field(description="Overall quality and usefulness assessment")


class DefaultDocumentSchema(BaseDocumentSchema):
    """Default schema for general document analysis."""
    
    @property
    def schema_class(self) -> Type[BaseModel]:
        return DefaultDocumentAnalysis
    
    @property
    def prompt_template(self) -> str:
        return """Analyze the document and extract:
1. Document metadata (title, author, type, language)
2. Executive summary (2-3 paragraphs)
3. Main topics covered
4. Key sections and their summaries
5. Important key points with context
6. Target audience
7. Actionable items or recommendations
8. Overall assessment of quality and usefulness"""
    
    @property
    def json_example(self) -> str:
        return """{
  "metadata": {
    "title": "string",
    "author": "string or null",
    "document_type": "string",
    "page_count": number,
    "language": "string"
  },
  "executive_summary": "string",
  "main_topics": ["string"],
  "sections": [{
    "title": "string",
    "content_summary": "string", 
    "page_range": "string"
  }],
  "key_points": [{
    "point": "string",
    "context": "string",
    "page_reference": "string"
  }],
  "target_audience": "string",
  "actionable_items": ["string"],
  "overall_assessment": "string"
}"""