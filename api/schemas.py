from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

# Base schemas
class LCDocumentRequirementBase(BaseModel):
    document_id: str
    name: str
    description: Optional[str] = None
    quantity: int = 1
    validation_criteria: Optional[List[str]] = []

class LCDocumentRequirementCreate(LCDocumentRequirementBase):
    pass

class LCDocumentRequirement(LCDocumentRequirementBase):
    id: int
    lc_id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# Letter of Credit schemas
class LetterOfCreditBase(BaseModel):
    lc_reference: str
    sequence_of_total: Optional[str] = None
    date_of_issue: Optional[str] = None
    applicable_rules: Optional[str] = None
    applicant: Optional[str] = None
    applicant_bank: Optional[str] = None
    beneficiary: Optional[str] = None
    available_with_bank: Optional[str] = None
    reimbursing_bank: Optional[str] = None
    advising_bank: Optional[str] = None
    instructions_to_bank: Optional[str] = None
    credit_amount: Optional[str] = None
    percent_tolerance: Optional[str] = None
    max_credit_amount: Optional[str] = None
    additional_amounts: Optional[str] = None
    form_of_credit: Optional[str] = None
    availability: Optional[str] = None
    draft_tenor: Optional[str] = None
    drawee: Optional[str] = None
    mixed_payment_details: Optional[str] = None
    deferred_payment_details: Optional[str] = None
    confirmation_instructions: Optional[str] = None
    expiry_date_and_place: Optional[str] = None
    period_for_presentation: Optional[str] = None
    partial_shipments: Optional[str] = None
    transshipment: Optional[str] = None
    latest_shipment_date: Optional[str] = None
    shipment_period: Optional[str] = None
    dispatch_place: Optional[str] = None
    port_of_loading: Optional[str] = None
    port_of_discharge: Optional[str] = None
    final_destination: Optional[str] = None
    goods_description: Optional[str] = None
    additional_conditions: Optional[str] = None
    charges: Optional[str] = None
    incoterm_rule: Optional[str] = None
    incoterm_year: Optional[str] = None
    incoterm_named_place: Optional[str] = None
    rulebook_versions: Optional[Dict[str, Any]] = None

class LetterOfCreditCreate(LetterOfCreditBase):
    document_requirements: Optional[List[LCDocumentRequirementCreate]] = []

class LetterOfCredit(LetterOfCreditBase):
    id: int
    created_at: datetime
    updated_at: datetime
    document_requirements: List[LCDocumentRequirement] = []
    
    class Config:
        from_attributes = True

# Export Document schemas
class ExportDocumentBase(BaseModel):
    document_id: str
    filename: str
    file_path: Optional[str] = None
    file_size_bytes: Optional[int] = None
    document_name: Optional[str] = None
    summary: Optional[str] = None
    full_description: Optional[str] = None
    extraction_timestamp: Optional[datetime] = None
    extraction_metadata: Optional[Dict[str, Any]] = None

class ExportDocumentCreate(ExportDocumentBase):
    pass

class ExportDocument(ExportDocumentBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# Classification schemas
class DocumentClassificationBase(BaseModel):
    confidence_score: Optional[float] = None
    reasoning: Optional[str] = None
    is_matched: bool = False

class DocumentClassificationCreate(DocumentClassificationBase):
    export_document_id: int
    lc_requirement_id: int
    classification_run_id: int

class DocumentClassification(DocumentClassificationBase):
    id: int
    export_document_id: int
    lc_requirement_id: int
    classification_run_id: int
    created_at: datetime
    updated_at: datetime
    export_document: Optional[ExportDocument] = None
    lc_requirement: Optional[LCDocumentRequirement] = None
    
    class Config:
        from_attributes = True

# Classification Run schemas
class ClassificationRunBase(BaseModel):
    total_export_docs: int = 0
    total_lc_requirements: int = 0
    total_matches_found: int = 0
    model_used: Optional[str] = None
    status: str = "running"
    run_metadata: Optional[Dict[str, Any]] = None

class ClassificationRunCreate(ClassificationRunBase):
    lc_id: int

class ClassificationRun(ClassificationRunBase):
    id: int
    lc_id: int
    run_timestamp: datetime
    created_at: datetime
    updated_at: datetime
    classifications: List[DocumentClassification] = []
    
    class Config:
        from_attributes = True

# Response schemas
class ClassificationSummary(BaseModel):
    lc_reference: str
    total_requirements: int
    total_export_docs: int
    total_matches: int
    match_percentage: float
    unmatched_requirements: List[str]
    unmatched_export_docs: List[str]

class APIResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Any] = None