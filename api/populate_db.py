#!/usr/bin/env python3
"""
Database population script for LC-Scanner
Migrates existing JSON data from output folder to PostgreSQL database
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from database import SessionLocal, create_tables
from models import (
    LetterOfCredit as LCModel,
    LCDocumentRequirement as LCRequirementModel,
    ExportDocument as ExportDocModel
)

def load_json_file(file_path: str):
    """Load JSON data from file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"File not found: {file_path}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON file {file_path}: {e}")
        return None

def populate_lc_data(db: Session, lc_data: dict):
    """Populate Letter of Credit data"""
    print("Populating Letter of Credit data...")
    
    # Extract document requirements
    documents_required = lc_data.pop("DOCUMENTS_REQUIRED", [])
    
    # Create LC record
    lc_record = LCModel(
        lc_reference=lc_data.get("LC_REFERENCE"),
        sequence_of_total=lc_data.get("SEQUENCE_OF_TOTAL"),
        date_of_issue=lc_data.get("DATE_OF_ISSUE"),
        applicable_rules=lc_data.get("APPLICABLE_RULES"),
        applicant=lc_data.get("APPLICANT"),
        applicant_bank=lc_data.get("APPLICANT_BANK"),
        beneficiary=lc_data.get("BENEFICIARY"),
        available_with_bank=lc_data.get("AVAILABLE_WITH_BANK"),
        reimbursing_bank=lc_data.get("REIMBURSING_BANK"),
        advising_bank=lc_data.get("ADVISING_BANK"),
        instructions_to_bank=lc_data.get("INSTRUCTIONS_TO_BANK"),
        credit_amount=lc_data.get("CREDIT_AMOUNT"),
        percent_tolerance=lc_data.get("PERCENT_TOLERANCE"),
        max_credit_amount=lc_data.get("MAX_CREDIT_AMOUNT"),
        additional_amounts=lc_data.get("ADDITIONAL_AMOUNTS"),
        form_of_credit=lc_data.get("FORM_OF_CREDIT"),
        availability=lc_data.get("AVAILABILITY"),
        draft_tenor=lc_data.get("DRAFT_TENOR"),
        drawee=lc_data.get("DRAWEE"),
        mixed_payment_details=lc_data.get("MIXED_PAYMENT_DETAILS"),
        deferred_payment_details=lc_data.get("DEFERRED_PAYMENT_DETAILS"),
        confirmation_instructions=lc_data.get("CONFIRMATION_INSTRUCTIONS"),
        expiry_date_and_place=lc_data.get("EXPIRY_DATE_AND_PLACE"),
        period_for_presentation=lc_data.get("PERIOD_FOR_PRESENTATION"),
        partial_shipments=lc_data.get("PARTIAL_SHIPMENTS"),
        transshipment=lc_data.get("TRANSSHIPMENT"),
        latest_shipment_date=lc_data.get("LATEST_SHIPMENT_DATE"),
        shipment_period=lc_data.get("SHIPMENT_PERIOD"),
        dispatch_place=lc_data.get("DISPATCH_PLACE"),
        port_of_loading=lc_data.get("PORT_OF_LOADING"),
        port_of_discharge=lc_data.get("PORT_OF_DISCHARGE"),
        final_destination=lc_data.get("FINAL_DESTINATION"),
        goods_description=lc_data.get("GOODS_DESCRIPTION"),
        additional_conditions=lc_data.get("ADDITIONAL_CONDITIONS"),
        charges=lc_data.get("CHARGES"),
        incoterm_rule=lc_data.get("INCOTERM_RULE"),
        incoterm_year=lc_data.get("INCOTERM_YEAR"),
        incoterm_named_place=lc_data.get("INCOTERM_NAMED_PLACE"),
        rulebook_versions=lc_data.get("RULEBOOK_VERSIONS")
    )
    
    # Check if LC already exists
    existing_lc = db.query(LCModel).filter(LCModel.lc_reference == lc_record.lc_reference).first()
    if existing_lc:
        print(f"LC {lc_record.lc_reference} already exists, skipping.")
        return existing_lc
    
    db.add(lc_record)
    db.commit()
    db.refresh(lc_record)
    
    print(f"Created LC: {lc_record.lc_reference}")
    
    # Create document requirements
    for doc_req in documents_required:
        requirement = LCRequirementModel(
            lc_id=lc_record.id,
            document_id=doc_req.get("document_id"),
            name=doc_req.get("name"),
            description=doc_req.get("description"),
            quantity=doc_req.get("quantity", 1),
            validation_criteria=doc_req.get("validation_criteria", [])
        )
        db.add(requirement)
    
    db.commit()
    print(f"Created {len(documents_required)} document requirements for LC {lc_record.lc_reference}")
    
    return lc_record

def populate_export_documents(db: Session, export_data: dict, lc_id):
    """Populate Export Documents data"""
    print("Populating Export Documents data...")
    
    documents = export_data.get("documents", [])
    extraction_metadata = export_data.get("extraction_metadata", {})
    
    created_count = 0
    skipped_count = 0
    
    for doc in documents:
        file_info = doc.get("file_info", {})
        extraction_result = doc.get("extraction_result", {})
        
        # Check if document already exists
        existing_doc = db.query(ExportDocModel).filter(
            ExportDocModel.document_id == doc.get("document_id")
        ).first()
        
        if existing_doc:
            skipped_count += 1
            continue
        
        # Parse extraction timestamp
        extraction_timestamp = None
        if file_info.get("extraction_timestamp"):
            try:
                extraction_timestamp = datetime.fromisoformat(
                    file_info.get("extraction_timestamp").replace("Z", "+00:00")
                )
            except:
                extraction_timestamp = None
        
        export_doc = ExportDocModel(
            lc_id=lc_id,
            document_id=doc.get("document_id"),
            filename=file_info.get("filename"),
            file_path=file_info.get("file_path"),
            file_size_bytes=file_info.get("file_size_bytes"),
            document_name=extraction_result.get("document_name"),
            summary=extraction_result.get("summary"),
            full_description=extraction_result.get("full_description"),
            extraction_timestamp=extraction_timestamp,
            extraction_metadata={
                "original_metadata": extraction_metadata,
                "file_info": file_info
            }
        )
        
        db.add(export_doc)
        created_count += 1
    
    db.commit()
    print(f"Created {created_count} export documents, skipped {skipped_count} existing documents")
    
    return created_count


def main():
    """Main function to populate database"""
    print("Starting database population...")
    
    # Ensure tables exist
    create_tables()
    
    # Create database session
    db = SessionLocal()
    
    try:
        # Define file paths
        base_path = Path(__file__).parent.parent
        lc_file = base_path / "output" / "LC.json"
        export_docs_file = base_path / "output" / "Export_docs.json"
        
        print(f"Looking for files:")
        print(f"  LC file: {lc_file}")
        print(f"  Export docs: {export_docs_file}")
        
        # Load and populate LC data
        lc_data = load_json_file(str(lc_file))
        if lc_data:
            lc_record = populate_lc_data(db, lc_data)
        else:
            print("Could not load LC data, skipping...")
            return
        
        # Load and populate export documents data
        export_data = load_json_file(str(export_docs_file))
        if export_data:
            export_doc_count = populate_export_documents(db, export_data, lc_record.id)
        else:
            print("Could not load export documents data, skipping...")
            return
        
        print("\n" + "="*50)
        print("Database population completed successfully!")
        print("="*50)
        
        # Print summary
        lc_count = db.query(LCModel).count()
        req_count = db.query(LCRequirementModel).count()
        doc_count = db.query(ExportDocModel).count()
        
        print(f"Database Summary:")
        print(f"  Letter of Credits: {lc_count}")
        print(f"  LC Requirements: {req_count}")
        print(f"  Export Documents: {doc_count}")
        
    except Exception as e:
        print(f"Error during population: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    main()