"""Document Extraction Service - Configurable PDF analysis with structured output schemas."""

from .core import DocumentExtractor
from .schemas import BaseDocumentSchema, DefaultDocumentSchema, LetterOfCreditSchema

__version__ = "1.0.0"
__all__ = [
    'DocumentExtractor',
    'BaseDocumentSchema', 
    'DefaultDocumentSchema', 
    'LetterOfCreditSchema'
]