#!/usr/bin/env python3
"""
Document Extraction Service - Main Runner

A configurable PDF extraction service that uses OpenRouter with Gemini to analyze documents
and extract structured information based on customizable schemas.

Usage:
    python extract_document.py <pdf_path> [options]

Examples:
    # Basic extraction with default schema
    python extract_document.py document.pdf
    
    # Extract with Letter of Credit schema
    python extract_document.py letter_of_credit.pdf --schema lc
    
    # Save results to specific file
    python extract_document.py document.pdf --output results.json
    
    # Use custom schema class
    python extract_document.py document.pdf --schema custom.MySchema
"""

import argparse
import sys
from pathlib import Path

from document_extraction_service import (
    DocumentExtractor,
    DefaultDocumentSchema,
    LetterOfCreditSchema,
    BaseDocumentSchema
)


def get_schema_class(schema_name: str) -> BaseDocumentSchema:
    """
    Get schema class instance from name.
    
    Args:
        schema_name: Name of the schema ('default', 'lc', or module.ClassName)
        
    Returns:
        Schema instance
    """
    if schema_name.lower() in ['default', 'general']:
        return DefaultDocumentSchema()
    elif schema_name.lower() in ['lc', 'letter_of_credit', 'lettercredit']:
        return LetterOfCreditSchema()
    else:
        # Try to import custom schema
        try:
            if '.' in schema_name:
                module_name, class_name = schema_name.rsplit('.', 1)
                module = __import__(module_name, fromlist=[class_name])
                schema_class = getattr(module, class_name)
                return schema_class()
            else:
                raise ValueError(f"Invalid schema format: {schema_name}")
        except (ImportError, AttributeError) as e:
            raise ValueError(f"Could not import schema '{schema_name}': {e}")


def main():
    """Main entry point for the document extraction service."""
    parser = argparse.ArgumentParser(
        description="Extract structured information from PDF documents using configurable schemas",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Available schemas:
  default, general    - General document analysis (title, summary, sections, etc.)
  lc, letter_of_credit - Letter of Credit specific analysis
  module.ClassName    - Custom schema class import

Examples:
  python extract_document.py contract.pdf --schema default
  python extract_document.py trade_finance.pdf --schema lc --output lc_analysis.json
  python extract_document.py custom_doc.pdf --schema myschemas.InvoiceSchema
        """
    )
    
    parser.add_argument(
        'pdf_path',
        help='Path to the PDF file to analyze'
    )
    
    parser.add_argument(
        '--schema', '-s',
        default='default',
        help='Schema to use for extraction (default: default)'
    )
    
    parser.add_argument(
        '--output', '-o',
        help='Output file path for results (JSON format)'
    )
    
    parser.add_argument(
        '--model', '-m',
        default='google/gemini-2.0-flash-001',
        help='Model to use for analysis (default: google/gemini-2.0-flash-001)'
    )
    
    parser.add_argument(
        '--api-key',
        help='OpenRouter API key (or set OPENROUTER_API_KEY env var)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    
    args = parser.parse_args()
    
    # Validate PDF file exists
    pdf_path = Path(args.pdf_path)
    if not pdf_path.exists():
        print(f"❌ Error: PDF file not found: {pdf_path}")
        sys.exit(1)
    
    try:
        # Get schema instance
        if args.verbose:
            print(f"🔧 Loading schema: {args.schema}")
        schema = get_schema_class(args.schema)
        
        # Initialize extractor
        if args.verbose:
            print(f"🤖 Initializing extractor with model: {args.model}")
        extractor = DocumentExtractor(api_key=args.api_key, model=args.model)
        
        # Show model info
        if args.verbose:
            model_info = extractor.get_model_info()
            print(f"📡 Provider: {model_info['provider']}")
            print(f"🔗 Model: {model_info['model']}")
        
        # Set output path
        output_path = args.output
        if not output_path:
            # Generate default output filename
            base_name = pdf_path.stem
            schema_suffix = args.schema.lower().replace('_', '').replace('.', '_')
            output_path = f"{base_name}_{schema_suffix}_analysis.json"
        
        print(f"🔍 Analyzing: {pdf_path.name}")
        print(f"📋 Schema: {schema.__class__.__name__}")
        print(f"⚡ Processing...")
        
        # Extract information
        result = extractor.extract(
            file_path=pdf_path,
            schema=schema,
            output_path=output_path
        )
        
        print(f"✅ Analysis complete!")
        print(f"📄 Results saved to: {output_path}")
        
        # Show brief summary if verbose
        if args.verbose and hasattr(result, 'model_dump'):
            data = result.model_dump()
            print(f"\n📊 Brief Summary:")
            if 'metadata' in data:
                meta = data['metadata']
                print(f"   Document: {meta.get('title', 'Unknown')}")
                print(f"   Type: {meta.get('document_type', 'Unknown')}")
                print(f"   Pages: {meta.get('page_count', 'Unknown')}")
            
            # Show main topics if available
            if 'main_topics' in data and data['main_topics']:
                print(f"   Topics: {', '.join(data['main_topics'][:3])}{'...' if len(data['main_topics']) > 3 else ''}")
        
    except KeyboardInterrupt:
        print(f"\n⏹️  Analysis interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()