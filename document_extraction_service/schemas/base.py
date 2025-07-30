"""Base schema definition for document analysis."""

from abc import ABC, abstractmethod
from typing import Type, Any
from pydantic import BaseModel


class BaseDocumentSchema(ABC):
    """Base class for document analysis schemas."""
    
    @property
    @abstractmethod
    def schema_class(self) -> Type[BaseModel]:
        """Return the Pydantic schema class."""
        pass
    
    @property
    @abstractmethod
    def prompt_template(self) -> str:
        """Return the analysis prompt template."""
        pass
    
    @property
    @abstractmethod
    def json_example(self) -> str:
        """Return example JSON structure for the LLM."""
        pass
    
    def get_analysis_prompt(self, filename: str) -> str:
        """Generate the complete analysis prompt."""
        return f"""Please analyze this PDF document and provide a comprehensive description.

Document file: {filename}

{self.prompt_template}

IMPORTANT: Return ONLY a valid JSON object with no additional text, markdown formatting, or explanations. The JSON structure should be:
{self.json_example}"""