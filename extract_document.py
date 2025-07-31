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
import json
from pathlib import Path
from typing import List
from datetime import datetime

from document_extraction_service import (
    DocumentExtractor,
    DefaultDocumentSchema,
    LetterOfCreditSchema,
    SimpleDocumentSchema,
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
    elif schema_name.lower() in ['simple', 'basic']:
        return SimpleDocumentSchema()
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


def find_pdf_files(directory: Path) -> List[Path]:
    """Find all PDF files in the specified directory."""
    pdf_files = []
    for file_path in directory.glob("*.pdf"):
        if file_path.is_file():
            pdf_files.append(file_path)
    
    # Sort by filename for consistent ordering
    pdf_files.sort(key=lambda x: x.name)
    return pdf_files


def process_batch(directory: Path, args):
    """Process all PDF files in a directory and combine results into single JSON."""
    # Find PDF files
    pdf_files = find_pdf_files(directory)
    if not pdf_files:
        print(f"❌ Error: No PDF files found in directory: {directory}")
        sys.exit(1)
    
    print(f"📁 Found {len(pdf_files)} PDF files in {directory}")
    
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
            schema_suffix = args.schema.lower().replace('_', '').replace('.', '_')
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = f"output/batch_extraction_{schema_suffix}_{timestamp}.json"
        else:
            # Ensure output goes to output directory if not already specified
            output_file = Path(output_path)
            if not output_file.is_absolute() and output_file.parent.name != 'output':
                output_path = f"output/{output_path}"
        
        print(f"📋 Schema: {schema.__class__.__name__}")
        print(f"📄 Output file: {output_path}")
        print(f"⚡ Starting batch processing...")
        
        # Process all files and collect results
        combined_results = {
            "extraction_metadata": {
                "timestamp": datetime.now().isoformat(),
                "schema_used": schema.__class__.__name__,
                "model": args.model,
                "total_documents": len(pdf_files),
                "directory": str(directory.absolute())
            },
            "documents": []
        }
        
        successful_extractions = 0
        failed_extractions = 0
        
        for i, pdf_file in enumerate(pdf_files, 1):
            print(f"\n🔍 Processing {i}/{len(pdf_files)}: {pdf_file.name}")
            
            try:
                # Extract information without saving individual files
                result = extractor.extract(
                    file_path=pdf_file,
                    schema=schema,
                    output_path=None  # Don't save individual files
                )
                
                # Convert result to dict
                if hasattr(result, 'model_dump'):
                    result_data = result.model_dump()
                elif hasattr(result, 'dict'):
                    result_data = result.dict()
                else:
                    result_data = dict(result)
                
                # Add document metadata
                document_entry = {
                    "document_id": f"export_doc_{i:03d}",
                    "file_info": {
                        "filename": pdf_file.name,
                        "file_path": str(pdf_file.relative_to(directory)),
                        "file_size_bytes": pdf_file.stat().st_size,
                        "extraction_timestamp": datetime.now().isoformat()
                    },
                    "extraction_result": result_data
                }
                
                combined_results["documents"].append(document_entry)
                successful_extractions += 1
                print(f"✅ Completed: {pdf_file.name}")
                
            except Exception as e:
                failed_extractions += 1
                error_entry = {
                    "document_id": f"doc_{i:03d}",
                    "file_info": {
                        "filename": pdf_file.name,
                        "file_path": str(pdf_file.relative_to(directory)),
                        "file_size_bytes": pdf_file.stat().st_size if pdf_file.exists() else 0,
                        "extraction_timestamp": datetime.now().isoformat()
                    },
                    "extraction_result": None,
                    "error": str(e)
                }
                
                combined_results["documents"].append(error_entry)
                print(f"❌ Failed: {pdf_file.name} - {str(e)}")
                
                if args.verbose:
                    import traceback
                    traceback.print_exc()
        
        # Update metadata with final counts
        combined_results["extraction_metadata"]["successful_extractions"] = successful_extractions
        combined_results["extraction_metadata"]["failed_extractions"] = failed_extractions
        
        # Save combined results
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(combined_results, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Batch processing complete!")
        print(f"📊 Results: {successful_extractions} successful, {failed_extractions} failed")
        print(f"📄 Combined results saved to: {output_path}")
        
        # Show summary statistics
        if args.verbose and successful_extractions > 0:
            print(f"\n📈 Summary Statistics:")
            print(f"   Total documents processed: {len(pdf_files)}")
            print(f"   Success rate: {(successful_extractions/len(pdf_files)*100):.1f}%")
            
            # Calculate average file size
            total_size = sum(doc["file_info"]["file_size_bytes"] for doc in combined_results["documents"])
            avg_size_mb = (total_size / len(pdf_files)) / (1024 * 1024)
            print(f"   Average file size: {avg_size_mb:.1f}MB")
            
    except Exception as e:
        print(f"❌ Error during batch processing: {str(e)}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


def main():
    """Main entry point for the document extraction service."""
    parser = argparse.ArgumentParser(
        description="Extract structured information from PDF documents using configurable schemas",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Available schemas:
  default, general    - General document analysis (title, summary, sections, etc.)
  lc, letter_of_credit - Letter of Credit specific analysis
  simple, basic       - Simple analysis (name, summary, full description)
  module.ClassName    - Custom schema class import

Examples:
  python extract_document.py contract.pdf --schema default
  python extract_document.py trade_finance.pdf --schema lc --output lc_analysis.json
  python extract_document.py custom_doc.pdf --schema myschemas.InvoiceSchema
  python extract_document.py "documents/Export docs/" --batch --schema lc
  python extract_document.py "documents/Export docs/" --batch --output combined.json
        """
    )
    
    parser.add_argument(
        'pdf_path',
        help='Path to the PDF file or directory to analyze'
    )
    
    parser.add_argument(
        '--batch', '-b',
        action='store_true',
        help='Process all PDF files in a directory and combine results into single JSON'
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
    
    # Validate path exists
    pdf_path = Path(args.pdf_path)
    if not pdf_path.exists():
        print(f"❌ Error: Path not found: {pdf_path}")
        sys.exit(1)
    
    # Handle batch processing
    if args.batch:
        if not pdf_path.is_dir():
            print(f"❌ Error: Batch mode requires a directory path: {pdf_path}")
            sys.exit(1)
        process_batch(pdf_path, args)
        return
    
    # Single file processing - ensure it's a file
    if not pdf_path.is_file():
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
            output_path = f"output/{base_name}_{schema_suffix}_analysis.json"
        else:
            # Ensure output goes to output directory if not already specified
            output_file = Path(output_path)
            if not output_file.is_absolute() and output_file.parent.name != 'output':
                output_path = f"output/{output_path}"
        
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