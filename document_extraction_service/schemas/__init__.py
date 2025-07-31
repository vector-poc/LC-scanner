"""Schema definitions for document extraction service."""

from .base import BaseDocumentSchema
from .letter_of_credit import LetterOfCreditSchema
from .default import DefaultDocumentSchema
from .simple import SimpleDocumentSchema

__all__ = ['BaseDocumentSchema', 'LetterOfCreditSchema', 'DefaultDocumentSchema', 'SimpleDocumentSchema']