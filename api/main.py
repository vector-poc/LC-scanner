from fastapi import FastAPI, Depends, HTTPException, status, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional
import uvicorn
import tempfile
import os
from pathlib import Path
from datetime import datetime
import sys

# Add document extraction service to path
sys.path.append(str(Path(__file__).parent.parent))
from document_extraction_service import (
    DocumentExtractor,
    LetterOfCreditSchema,
    SimpleDocumentSchema,
    DefaultDocumentSchema
)

from database import get_db, create_tables
from models import (
    LetterOfCredit as LCModel,
    LCDocumentRequirement as LCRequirementModel,
    ExportDocument as ExportDocModel,
    DocumentClassification as ClassificationModel,
    ClassificationRun as ClassificationRunModel
)
from schemas import (
    LetterOfCredit,
    LetterOfCreditCreate,
    ExportDocument,
    ExportDocumentCreate,
    DocumentClassification,
    DocumentClassificationCreate,
    ClassificationRun,
    ClassificationRunCreate,
    ClassificationSummary,
    APIResponse
)

app = FastAPI(
    title="LC Scanner API",
    description="API for managing Letter of Credit document requirements and export document classifications",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# File handling utilities
async def save_temp_file(upload_file: UploadFile) -> Path:
    """Save uploaded file to temporary location."""
    if not upload_file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    # Create temporary file
    temp_dir = Path(tempfile.gettempdir()) / "lc_scanner_uploads"
    temp_dir.mkdir(exist_ok=True)
    
    temp_file = temp_dir / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{upload_file.filename}"
    
    # Save uploaded content
    content = await upload_file.read()
    with open(temp_file, 'wb') as f:
        f.write(content)
    
    return temp_file

def cleanup_temp_file(file_path: Path):
    """Clean up temporary file."""
    try:
        if file_path.exists():
            file_path.unlink()
    except Exception:
        pass  # Ignore cleanup errors

def detect_document_type(filename: str) -> str:
    """Detect document type from filename."""
    filename_lower = filename.lower()
    
    if any(keyword in filename_lower for keyword in ['invoice', 'commercial', 'proforma']):
        return 'invoice'
    elif any(keyword in filename_lower for keyword in ['certificate', 'inspection', 'registration']):
        return 'certificate'
    elif any(keyword in filename_lower for keyword in ['bill', 'lading', 'b/l', 'shipping']):
        return 'bill_of_lading'
    elif any(keyword in filename_lower for keyword in ['insurance', 'policy', 'marine', 'cargo']):
        return 'insurance'
    else:
        return 'general'

def get_schema_for_document_type(doc_type: str):
    """Get appropriate schema for document type."""
    if doc_type in ['invoice', 'bill_of_lading', 'insurance', 'general']:
        return SimpleDocumentSchema()
    elif doc_type == 'certificate':
        return DefaultDocumentSchema()
    else:
        return SimpleDocumentSchema()  # Default fallback

# Schema mapping functions
def map_lc_extraction_to_models(extraction_data: dict, db: Session):
    """Map LC extraction results to database models."""
    # Extract document requirements
    documents_required = extraction_data.pop("DOCUMENTS_REQUIRED", []) or []
    
    # Create LC record
    lc_record = LCModel(
        lc_reference=extraction_data.get("LC_REFERENCE"),
        sequence_of_total=extraction_data.get("SEQUENCE_OF_TOTAL"),
        date_of_issue=extraction_data.get("DATE_OF_ISSUE"),
        applicable_rules=extraction_data.get("APPLICABLE_RULES"),
        applicant=extraction_data.get("APPLICANT"),
        applicant_bank=extraction_data.get("APPLICANT_BANK"),
        beneficiary=extraction_data.get("BENEFICIARY"),
        available_with_bank=extraction_data.get("AVAILABLE_WITH_BANK"),
        reimbursing_bank=extraction_data.get("REIMBURSING_BANK"),
        advising_bank=extraction_data.get("ADVISING_BANK"),
        instructions_to_bank=extraction_data.get("INSTRUCTIONS_TO_BANK"),
        credit_amount=extraction_data.get("CREDIT_AMOUNT"),
        percent_tolerance=extraction_data.get("PERCENT_TOLERANCE"),
        max_credit_amount=extraction_data.get("MAX_CREDIT_AMOUNT"),
        additional_amounts=extraction_data.get("ADDITIONAL_AMOUNTS"),
        form_of_credit=extraction_data.get("FORM_OF_CREDIT"),
        availability=extraction_data.get("AVAILABILITY"),
        draft_tenor=extraction_data.get("DRAFT_TENOR"),
        drawee=extraction_data.get("DRAWEE"),
        mixed_payment_details=extraction_data.get("MIXED_PAYMENT_DETAILS"),
        deferred_payment_details=extraction_data.get("DEFERRED_PAYMENT_DETAILS"),
        confirmation_instructions=extraction_data.get("CONFIRMATION_INSTRUCTIONS"),
        expiry_date_and_place=extraction_data.get("EXPIRY_DATE_AND_PLACE"),
        period_for_presentation=extraction_data.get("PERIOD_FOR_PRESENTATION"),
        partial_shipments=extraction_data.get("PARTIAL_SHIPMENTS"),
        transshipment=extraction_data.get("TRANSSHIPMENT"),
        latest_shipment_date=extraction_data.get("LATEST_SHIPMENT_DATE"),
        shipment_period=extraction_data.get("SHIPMENT_PERIOD"),
        dispatch_place=extraction_data.get("DISPATCH_PLACE"),
        port_of_loading=extraction_data.get("PORT_OF_LOADING"),
        port_of_discharge=extraction_data.get("PORT_OF_DISCHARGE"),
        final_destination=extraction_data.get("FINAL_DESTINATION"),
        goods_description=extraction_data.get("GOODS_DESCRIPTION"),
        additional_conditions=extraction_data.get("ADDITIONAL_CONDITIONS"),
        charges=extraction_data.get("CHARGES"),
        incoterm_rule=extraction_data.get("INCOTERM_RULE"),
        incoterm_year=extraction_data.get("INCOTERM_YEAR"),
        incoterm_named_place=extraction_data.get("INCOTERM_NAMED_PLACE"),
        rulebook_versions=extraction_data.get("RULEBOOK_VERSIONS")
    )
    
    # Check if LC already exists
    existing_lc = db.query(LCModel).filter(LCModel.lc_reference == lc_record.lc_reference).first()
    if existing_lc:
        raise HTTPException(status_code=400, detail=f"LC with reference {lc_record.lc_reference} already exists")
    
    db.add(lc_record)
    db.commit()
    db.refresh(lc_record)
    
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
    db.refresh(lc_record)
    return lc_record

def map_export_extraction_to_model(extraction_data: dict, lc_id: int, file_info: dict, doc_counter: int):
    """Map export document extraction results to database model."""
    return ExportDocModel(
        lc_id=lc_id,
        document_id=f"export_doc_{doc_counter:03d}",
        filename=file_info["filename"],
        file_path=file_info.get("file_path"),
        file_size_bytes=file_info["file_size_bytes"],
        document_name=extraction_data.get("document_name"),
        summary=extraction_data.get("summary"),
        full_description=extraction_data.get("full_description"),
        extraction_timestamp=datetime.utcnow(),
        extraction_metadata={
            "schema_used": file_info.get("schema_used"),
            "extraction_timestamp": datetime.utcnow().isoformat(),
            "doc_type_detected": file_info.get("doc_type_detected")
        }
    )

# Create tables on startup (only if they don't exist)
@app.on_event("startup")
async def startup_event():
    try:
        create_tables()
        print("✅ Database tables checked/created successfully")
    except Exception as e:
        print(f"⚠️  Database table creation warning: {e}")

# Health check
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "LC Scanner API"}

# Letter of Credit upload endpoint
@app.post("/lcs/upload", response_model=LetterOfCredit)
async def upload_lc_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload and process a Letter of Credit PDF document"""
    temp_file = None
    
    try:
        # Save uploaded file temporarily
        temp_file = await save_temp_file(file)
        
        # Initialize document extractor
        extractor = DocumentExtractor()
        schema = LetterOfCreditSchema()
        
        # Extract LC data
        result = extractor.extract(
            file_path=temp_file,
            schema=schema,
            output_path=None  # Don't save to file
        )
        
        # Convert result to dict
        if hasattr(result, 'model_dump'):
            extraction_data = result.model_dump()
        elif hasattr(result, 'dict'):
            extraction_data = result.dict()
        else:
            extraction_data = dict(result)
        
        # Map extraction data to database models
        lc_record = map_lc_extraction_to_models(extraction_data, db)
        
        return lc_record
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error processing LC document: {str(e)}")
    finally:
        # Clean up temporary file
        if temp_file:
            cleanup_temp_file(temp_file)

# Letter of Credit endpoints
@app.get("/lcs/", response_model=List[LetterOfCredit])
async def get_all_lcs(db: Session = Depends(get_db)):
    """Get all Letter of Credits"""
    lcs = db.query(LCModel).all()
    return lcs

@app.post("/lcs/", response_model=LetterOfCredit)
async def create_lc(lc: LetterOfCreditCreate, db: Session = Depends(get_db)):
    """Create a new Letter of Credit"""
    
    # Check if LC reference already exists
    existing_lc = db.query(LCModel).filter(LCModel.lc_reference == lc.lc_reference).first()
    if existing_lc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"LC with reference {lc.lc_reference} already exists"
        )
    
    # Create LC
    db_lc = LCModel(**lc.model_dump(exclude={"document_requirements"}))
    db.add(db_lc)
    db.commit()
    db.refresh(db_lc)
    
    # Create document requirements
    for req in lc.document_requirements:
        db_req = LCRequirementModel(**req.model_dump(), lc_id=db_lc.id)
        db.add(db_req)
    
    db.commit()
    db.refresh(db_lc)
    return db_lc

@app.get("/lcs/{lc_id}", response_model=LetterOfCredit)
async def get_lc(lc_id: int, db: Session = Depends(get_db)):
    """Get a specific Letter of Credit by ID"""
    lc = db.query(LCModel).filter(LCModel.id == lc_id).first()
    if not lc:
        raise HTTPException(status_code=404, detail="Letter of Credit not found")
    return lc

@app.get("/lcs/reference/{lc_reference}", response_model=LetterOfCredit)
async def get_lc_by_reference(lc_reference: str, db: Session = Depends(get_db)):
    """Get a Letter of Credit by reference number"""
    lc = db.query(LCModel).filter(LCModel.lc_reference == lc_reference).first()
    if not lc:
        raise HTTPException(status_code=404, detail="Letter of Credit not found")
    return lc

@app.put("/lcs/{lc_id}", response_model=LetterOfCredit)
async def update_lc(lc_id: int, lc_update: LetterOfCreditCreate, db: Session = Depends(get_db)):
    """Update a Letter of Credit"""
    db_lc = db.query(LCModel).filter(LCModel.id == lc_id).first()
    if not db_lc:
        raise HTTPException(status_code=404, detail="Letter of Credit not found")
    
    # Update LC fields
    for key, value in lc_update.model_dump(exclude={"document_requirements"}).items():
        if value is not None:
            setattr(db_lc, key, value)
    
    db.commit()
    db.refresh(db_lc)
    return db_lc

@app.delete("/lcs/{lc_id}")
async def delete_lc(lc_id: int, db: Session = Depends(get_db)):
    """Delete a Letter of Credit"""
    db_lc = db.query(LCModel).filter(LCModel.id == lc_id).first()
    if not db_lc:
        raise HTTPException(status_code=404, detail="Letter of Credit not found")
    
    db.delete(db_lc)
    db.commit()
    return {"message": "Letter of Credit deleted successfully"}

# Export Documents upload endpoint
@app.post("/export-documents/upload/{lc_id}", response_model=List[ExportDocument])
async def upload_export_documents(
    lc_id: int,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    """Upload and process multiple export document PDF files for a specific LC"""
    
    # Check if LC exists
    lc = db.query(LCModel).filter(LCModel.id == lc_id).first()
    if not lc:
        raise HTTPException(status_code=404, detail="Letter of Credit not found")
    
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    
    temp_files = []
    created_documents = []
    
    try:
        # Initialize document extractor
        extractor = DocumentExtractor()
        
        # Get current document count for ID generation
        existing_docs = db.query(ExportDocModel).filter(ExportDocModel.lc_id == lc_id).count()
        doc_counter = existing_docs + 1
        
        for file in files:
            temp_file = None
            try:
                # Save uploaded file temporarily
                temp_file = await save_temp_file(file)
                temp_files.append(temp_file)
                
                # Detect document type and get appropriate schema
                doc_type = detect_document_type(file.filename)
                schema = get_schema_for_document_type(doc_type)
                
                # Extract document data
                result = extractor.extract(
                    file_path=temp_file,
                    schema=schema,
                    output_path=None  # Don't save to file
                )
                
                # Convert result to dict
                if hasattr(result, 'model_dump'):
                    extraction_data = result.model_dump()
                elif hasattr(result, 'dict'):
                    extraction_data = result.dict()
                else:
                    extraction_data = dict(result)
                
                # Prepare file info
                file_info = {
                    "filename": file.filename,
                    "file_path": file.filename,  # Store original filename
                    "file_size_bytes": temp_file.stat().st_size,
                    "schema_used": schema.__class__.__name__,
                    "doc_type_detected": doc_type
                }
                
                # Map extraction data to database model
                export_doc = map_export_extraction_to_model(
                    extraction_data, lc_id, file_info, doc_counter
                )
                
                # Check if document already exists
                existing_doc = db.query(ExportDocModel).filter(
                    ExportDocModel.document_id == export_doc.document_id,
                    ExportDocModel.lc_id == lc_id
                ).first()
                
                if existing_doc:
                    # Update document ID to avoid conflicts
                    doc_counter += 1
                    export_doc.document_id = f"export_doc_{doc_counter:03d}"
                
                db.add(export_doc)
                created_documents.append(export_doc)
                doc_counter += 1
                
            except Exception as e:
                # Log individual file error but continue with others
                print(f"Error processing file {file.filename}: {str(e)}")
                # Create error document entry
                error_doc = ExportDocModel(
                    lc_id=lc_id,
                    document_id=f"export_doc_{doc_counter:03d}",
                    filename=file.filename,
                    file_path=file.filename,
                    file_size_bytes=temp_file.stat().st_size if temp_file and temp_file.exists() else 0,
                    document_name=f"Failed: {file.filename}",
                    summary=f"Processing failed: {str(e)}",
                    full_description=f"Error occurred during document extraction: {str(e)}",
                    extraction_timestamp=datetime.utcnow(),
                    extraction_metadata={
                        "error": str(e),
                        "extraction_timestamp": datetime.utcnow().isoformat()
                    }
                )
                db.add(error_doc)
                created_documents.append(error_doc)
                doc_counter += 1
        
        # Commit all documents
        db.commit()
        
        # Refresh all documents to get complete data
        for doc in created_documents:
            db.refresh(doc)
        
        return created_documents
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error processing export documents: {str(e)}")
    finally:
        # Clean up all temporary files
        for temp_file in temp_files:
            cleanup_temp_file(temp_file)

# Export Document endpoints
@app.get("/export-documents/", response_model=List[ExportDocument])
async def get_all_export_documents(db: Session = Depends(get_db)):
    """Get all export documents"""
    docs = db.query(ExportDocModel).all()
    return docs

@app.post("/export-documents/", response_model=ExportDocument)
async def create_export_document(doc: ExportDocumentCreate, db: Session = Depends(get_db)):
    """Create a new export document"""
    
    # Check if document ID already exists
    existing_doc = db.query(ExportDocModel).filter(ExportDocModel.document_id == doc.document_id).first()
    if existing_doc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Export document with ID {doc.document_id} already exists"
        )
    
    db_doc = ExportDocModel(**doc.model_dump())
    db.add(db_doc)
    db.commit()
    db.refresh(db_doc)
    return db_doc

@app.get("/export-documents/{doc_id}", response_model=ExportDocument)
async def get_export_document(doc_id: int, db: Session = Depends(get_db)):
    """Get a specific export document by ID"""
    doc = db.query(ExportDocModel).filter(ExportDocModel.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Export document not found")
    return doc

@app.get("/export-documents/document-id/{document_id}", response_model=ExportDocument)
async def get_export_document_by_document_id(document_id: str, db: Session = Depends(get_db)):
    """Get an export document by document_id"""
    doc = db.query(ExportDocModel).filter(ExportDocModel.document_id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Export document not found")
    return doc

# Classification endpoints
@app.post("/classify/{lc_id}", response_model=ClassificationRun)
async def run_classification(
    lc_id: int, 
    export_doc_ids: Optional[List[int]] = None,
    db: Session = Depends(get_db)
):
    """Run classification for an LC against export documents"""
    
    # Check if LC exists
    lc = db.query(LCModel).filter(LCModel.id == lc_id).first()
    if not lc:
        raise HTTPException(status_code=404, detail="Letter of Credit not found")
    
    # Get export documents (all if not specified)
    if export_doc_ids:
        export_docs = db.query(ExportDocModel).filter(ExportDocModel.id.in_(export_doc_ids)).all()
    else:
        export_docs = db.query(ExportDocModel).all()
    
    # Get LC requirements
    lc_requirements = db.query(LCRequirementModel).filter(LCRequirementModel.lc_id == lc_id).all()
    
    # Create classification run
    run_data = ClassificationRunCreate(
        lc_id=lc_id,
        total_export_docs=len(export_docs),
        total_lc_requirements=len(lc_requirements),
        model_used="manual_api_call",
        status="completed"
    )
    
    db_run = ClassificationRunModel(**run_data.model_dump())
    db.add(db_run)
    db.commit()
    db.refresh(db_run)
    
    # For now, create placeholder classifications
    # In a real implementation, this would call the LangGraph classification system
    matches_found = 0
    for export_doc in export_docs:
        for lc_req in lc_requirements:
            # Placeholder logic - in reality, this would use AI classification
            is_matched = "invoice" in export_doc.document_name.lower() and "invoice" in lc_req.name.lower()
            confidence = 0.8 if is_matched else 0.2
            
            if is_matched:
                matches_found += 1
            
            classification = ClassificationModel(
                export_document_id=export_doc.id,
                lc_requirement_id=lc_req.id,
                classification_run_id=db_run.id,
                confidence_score=confidence,
                reasoning=f"Document type matching based on keywords",
                is_matched=is_matched
            )
            db.add(classification)
    
    # Update run with matches found
    db_run.total_matches_found = matches_found
    db_run.status = "completed"
    
    db.commit()
    db.refresh(db_run)
    return db_run

@app.get("/classifications/{lc_id}", response_model=List[DocumentClassification])
async def get_classifications(lc_id: int, db: Session = Depends(get_db)):
    """Get classification results for an LC"""
    
    # Check if LC exists
    lc = db.query(LCModel).filter(LCModel.id == lc_id).first()
    if not lc:
        raise HTTPException(status_code=404, detail="Letter of Credit not found")
    
    # Get latest classification run
    latest_run = db.query(ClassificationRunModel).filter(
        ClassificationRunModel.lc_id == lc_id
    ).order_by(ClassificationRunModel.run_timestamp.desc()).first()
    
    if not latest_run:
        return []
    
    classifications = db.query(ClassificationModel).filter(
        ClassificationModel.classification_run_id == latest_run.id
    ).all()
    
    return classifications

@app.get("/classification-runs/", response_model=List[ClassificationRun])
async def get_classification_runs(db: Session = Depends(get_db)):
    """Get all classification runs"""
    runs = db.query(ClassificationRunModel).order_by(ClassificationRunModel.run_timestamp.desc()).all()
    return runs

@app.get("/classification-summary/{lc_id}", response_model=ClassificationSummary)
async def get_classification_summary(lc_id: int, db: Session = Depends(get_db)):
    """Get classification summary for an LC"""
    
    # Check if LC exists
    lc = db.query(LCModel).filter(LCModel.id == lc_id).first()
    if not lc:
        raise HTTPException(status_code=404, detail="Letter of Credit not found")
    
    # Get latest classification run
    latest_run = db.query(ClassificationRunModel).filter(
        ClassificationRunModel.lc_id == lc_id
    ).order_by(ClassificationRunModel.run_timestamp.desc()).first()
    
    if not latest_run:
        return ClassificationSummary(
            lc_reference=lc.lc_reference,
            total_requirements=0,
            total_export_docs=0,
            total_matches=0,
            match_percentage=0.0,
            unmatched_requirements=[],
            unmatched_export_docs=[]
        )
    
    # Get classifications
    classifications = db.query(ClassificationModel).filter(
        ClassificationModel.classification_run_id == latest_run.id,
        ClassificationModel.is_matched == True
    ).all()
    
    matched_requirements = set(c.lc_requirement_id for c in classifications)
    matched_export_docs = set(c.export_document_id for c in classifications)
    
    # Get all requirements and export docs for this LC
    all_requirements = db.query(LCRequirementModel).filter(LCRequirementModel.lc_id == lc_id).all()
    all_export_docs = db.query(ExportDocModel).all()  # Assuming all export docs are relevant
    
    unmatched_req_names = [req.name for req in all_requirements if req.id not in matched_requirements]
    unmatched_doc_names = [doc.document_name for doc in all_export_docs if doc.id not in matched_export_docs]
    
    match_percentage = (latest_run.total_matches_found / max(latest_run.total_lc_requirements, 1)) * 100
    
    return ClassificationSummary(
        lc_reference=lc.lc_reference,
        total_requirements=latest_run.total_lc_requirements,
        total_export_docs=latest_run.total_export_docs,
        total_matches=latest_run.total_matches_found,
        match_percentage=match_percentage,
        unmatched_requirements=unmatched_req_names,
        unmatched_export_docs=unmatched_doc_names
    )

# Reset classifications endpoint
@app.delete("/classifications/reset/{lc_id}", response_model=APIResponse)
async def reset_classifications(lc_id: int, db: Session = Depends(get_db)):
    """Reset all classifications for a given LC's export documents"""
    
    # Check if LC exists
    lc = db.query(LCModel).filter(LCModel.id == lc_id).first()
    if not lc:
        raise HTTPException(status_code=404, detail="Letter of Credit not found")
    
    try:
        # Get all classification runs for this LC
        classification_runs = db.query(ClassificationRunModel).filter(
            ClassificationRunModel.lc_id == lc_id
        ).all()
        
        run_ids = [run.id for run in classification_runs]
        
        # Delete all document classifications for these runs
        classifications_deleted = 0
        if run_ids:
            classifications_deleted = db.query(ClassificationModel).filter(
                ClassificationModel.classification_run_id.in_(run_ids)
            ).delete(synchronize_session=False)
        
        # Delete all classification runs for this LC
        runs_deleted = db.query(ClassificationRunModel).filter(
            ClassificationRunModel.lc_id == lc_id
        ).delete(synchronize_session=False)
        
        # Reset classification fields in export documents for this LC
        export_docs_updated = db.query(ExportDocModel).filter(
            ExportDocModel.lc_id == lc_id
        ).update({
            ExportDocModel.lc_requirement_id: None,
            ExportDocModel.confidence_score: None,
            ExportDocModel.reasoning: None,
            ExportDocModel.is_matched: False
        }, synchronize_session=False)
        
        db.commit()
        
        return APIResponse(
            success=True,
            message=f"Successfully reset all classifications for LC {lc.lc_reference}",
            data={
                "lc_id": lc_id,
                "lc_reference": lc.lc_reference,
                "classifications_deleted": classifications_deleted,
                "classification_runs_deleted": runs_deleted,
                "export_documents_reset": export_docs_updated
            }
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error resetting classifications: {str(e)}")

# New endpoint: Get LC requirements with matched documents
@app.get("/lcs/{lc_id}/requirements-with-matches")
async def get_lc_requirements_with_matches(lc_id: int, db: Session = Depends(get_db)):
    """Get all required documents for a given LC and their matched export documents"""
    
    # Check if LC exists
    lc = db.query(LCModel).filter(LCModel.id == lc_id).first()
    if not lc:
        raise HTTPException(status_code=404, detail="Letter of Credit not found")
    
    # Get all requirements for this LC
    requirements = db.query(LCRequirementModel).filter(LCRequirementModel.lc_id == lc_id).all()
    
    # Get latest classification run for this LC
    latest_run = db.query(ClassificationRunModel).filter(
        ClassificationRunModel.lc_id == lc_id
    ).order_by(ClassificationRunModel.run_timestamp.desc()).first()
    
    result = {
        "lc_reference": lc.lc_reference,
        "lc_id": lc_id,
        "total_requirements": len(requirements),
        "classification_run_id": latest_run.id if latest_run else None,
        "classification_timestamp": latest_run.run_timestamp if latest_run else None,
        "requirements": []
    }
    
    for requirement in requirements:
        req_data = {
            "requirement_id": requirement.id,
            "document_id": requirement.document_id,
            "name": requirement.name,
            "description": requirement.description,
            "quantity": requirement.quantity,
            "validation_criteria": requirement.validation_criteria,
            "matched_documents": [],
            "match_count": 0
        }
        
        if latest_run:
            # Get all matched documents for this requirement
            matched_classifications = db.query(ClassificationModel).filter(
                ClassificationModel.lc_requirement_id == requirement.id,
                ClassificationModel.classification_run_id == latest_run.id,
                ClassificationModel.is_matched == True
            ).all()
            
            req_data["match_count"] = len(matched_classifications)
            
            for classification in matched_classifications:
                export_doc = db.query(ExportDocModel).filter(
                    ExportDocModel.id == classification.export_document_id
                ).first()
                
                if export_doc:
                    matched_doc = {
                        "export_document_id": export_doc.id,
                        "document_id": export_doc.document_id,
                        "filename": export_doc.filename,
                        "document_name": export_doc.document_name,
                        "summary": export_doc.summary,
                        "confidence_score": classification.confidence_score,
                        "reasoning": classification.reasoning,
                        "file_size_bytes": export_doc.file_size_bytes,
                        "extraction_timestamp": export_doc.extraction_timestamp
                    }
                    req_data["matched_documents"].append(matched_doc)
        
        result["requirements"].append(req_data)
    
    # Add summary statistics
    total_matches = sum(req["match_count"] for req in result["requirements"])
    result["total_matches"] = total_matches
    result["match_percentage"] = (total_matches / max(len(requirements), 1)) * 100 if requirements else 0
    
    return result

# Bulk operations
@app.post("/bulk/populate-from-files", response_model=APIResponse)
async def populate_from_files(db: Session = Depends(get_db)):
    """Populate database from existing JSON files"""
    try:
        # This endpoint will be implemented by the population script
        return APIResponse(
            success=True,
            message="Database population endpoint ready. Use the populate_db.py script to load data.",
            data={"endpoint": "/bulk/populate-from-files"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)