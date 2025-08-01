from sqlalchemy import Column, String, Text, Integer, Float, Boolean, DateTime, BigInteger, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class LetterOfCredit(Base):
    __tablename__ = "letter_of_credits"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    lc_reference = Column(String(255), unique=True, nullable=False, index=True)
    sequence_of_total = Column(String(50))
    date_of_issue = Column(String(50))
    applicable_rules = Column(String(255))
    applicant = Column(Text)
    applicant_bank = Column(Text)
    beneficiary = Column(Text)
    available_with_bank = Column(Text)
    reimbursing_bank = Column(Text)
    advising_bank = Column(Text)
    instructions_to_bank = Column(Text)
    credit_amount = Column(String(100))
    percent_tolerance = Column(String(50))
    max_credit_amount = Column(String(100))
    additional_amounts = Column(Text)
    form_of_credit = Column(String(100))
    availability = Column(String(100))
    draft_tenor = Column(String(100))
    drawee = Column(Text)
    mixed_payment_details = Column(Text)
    deferred_payment_details = Column(Text)
    confirmation_instructions = Column(String(100))
    expiry_date_and_place = Column(String(255))
    period_for_presentation = Column(String(255))
    partial_shipments = Column(String(50))
    transshipment = Column(String(50))
    latest_shipment_date = Column(String(50))
    shipment_period = Column(String(255))
    dispatch_place = Column(String(255))
    port_of_loading = Column(String(255))
    port_of_discharge = Column(String(255))
    final_destination = Column(String(255))
    goods_description = Column(Text)
    additional_conditions = Column(Text)
    charges = Column(Text)
    incoterm_rule = Column(String(50))
    incoterm_year = Column(String(10))
    incoterm_named_place = Column(String(255))
    rulebook_versions = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    document_requirements = relationship("LCDocumentRequirement", back_populates="letter_of_credit")
    export_documents = relationship("ExportDocument", back_populates="letter_of_credit")

class LCDocumentRequirement(Base):
    __tablename__ = "lc_document_requirements"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    lc_id = Column(Integer, ForeignKey("letter_of_credits.id"), nullable=False)
    document_id = Column(String(50), nullable=False, index=True)  # e.g., "doc_001"
    name = Column(String(500), nullable=False)
    description = Column(Text)
    quantity = Column(Integer, default=1)
    validation_criteria = Column(JSON)  # Array of validation rules
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    letter_of_credit = relationship("LetterOfCredit", back_populates="document_requirements")

class ExportDocument(Base):
    __tablename__ = "export_documents"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    lc_id = Column(Integer, ForeignKey("letter_of_credits.id"), nullable=False)
    lc_requirement_id = Column(Integer, ForeignKey("lc_document_requirements.id"), nullable=True)  # Classification target
    document_id = Column(String(50), unique=True, nullable=False, index=True)  # e.g., "export_doc_001"
    filename = Column(String(500), nullable=False)
    file_path = Column(String(1000))
    file_size_bytes = Column(BigInteger)
    document_name = Column(String(500))  # AI-extracted name
    summary = Column(Text)  # AI-generated summary
    full_description = Column(Text)  # Complete extracted content
    extraction_timestamp = Column(DateTime)
    extraction_metadata = Column(JSON)  # Model used, schema, etc.
    # Classification fields
    confidence_score = Column(Float)  # 0.0 to 1.0
    reasoning = Column(Text)  # AI explanation
    is_matched = Column(Boolean, default=False)  # Whether document matches requirement
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    letter_of_credit = relationship("LetterOfCredit", back_populates="export_documents")
    lc_requirement = relationship("LCDocumentRequirement")

class ClassificationRun(Base):
    __tablename__ = "classification_runs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    lc_id = Column(Integer, ForeignKey("letter_of_credits.id"), nullable=False)
    run_timestamp = Column(DateTime, default=datetime.utcnow)
    total_export_docs = Column(Integer, nullable=False)
    total_lc_requirements = Column(Integer, nullable=False)
    total_matches_found = Column(Integer, default=0)
    model_used = Column(String(100))
    status = Column(String(50), default="pending")  # pending, running, completed, failed
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    letter_of_credit = relationship("LetterOfCredit")
    classifications = relationship("DocumentClassification", back_populates="classification_run")

class DocumentClassification(Base):
    __tablename__ = "document_classifications"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    export_document_id = Column(Integer, ForeignKey("export_documents.id"), nullable=False)
    lc_requirement_id = Column(Integer, ForeignKey("lc_document_requirements.id"), nullable=False)
    classification_run_id = Column(Integer, ForeignKey("classification_runs.id"), nullable=False)
    confidence_score = Column(Float, nullable=False)  # 0.0 to 1.0
    reasoning = Column(Text)  # AI explanation for the classification
    is_matched = Column(Boolean, default=False)
    classification_timestamp = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    export_document = relationship("ExportDocument")
    lc_requirement = relationship("LCDocumentRequirement")
    classification_run = relationship("ClassificationRun", back_populates="classifications")

