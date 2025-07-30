import io
from pathlib import Path
from typing import Union
from pypdf import PdfReader


class PDFExtractor:
    """Simple PDF text extraction utility."""
    
    @staticmethod
    def extract_text_from_file(file_path: Union[str, Path]) -> str:
        """
        Extract text from a PDF file.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            Extracted text content as a string
            
        Raises:
            FileNotFoundError: If the PDF file doesn't exist
            Exception: If there's an error reading the PDF
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"PDF file not found: {file_path}")
        
        try:
            reader = PdfReader(str(file_path))
            text_content = []
            
            for page_num, page in enumerate(reader.pages, 1):
                page_text = page.extract_text()
                if page_text.strip():
                    text_content.append(f"--- Page {page_num} ---\n{page_text}\n")
            
            return "\n".join(text_content)
            
        except Exception as e:
            raise Exception(f"Error extracting text from PDF: {str(e)}")
    
    @staticmethod
    def extract_text_from_bytes(pdf_bytes: bytes) -> str:
        """
        Extract text from PDF bytes.
        
        Args:
            pdf_bytes: PDF content as bytes
            
        Returns:
            Extracted text content as a string
            
        Raises:
            Exception: If there's an error reading the PDF
        """
        try:
            reader = PdfReader(io.BytesIO(pdf_bytes))
            text_content = []
            
            for page_num, page in enumerate(reader.pages, 1):
                page_text = page.extract_text()
                if page_text.strip():
                    text_content.append(f"--- Page {page_num} ---\n{page_text}\n")
            
            return "\n".join(text_content)
            
        except Exception as e:
            raise Exception(f"Error extracting text from PDF bytes: {str(e)}")
    
    @staticmethod
    def get_page_count(file_path: Union[str, Path]) -> int:
        """
        Get the number of pages in a PDF file.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            Number of pages in the PDF
        """
        try:
            reader = PdfReader(str(file_path))
            return len(reader.pages)
        except Exception:
            return 0