"""
Database service layer for LangGraph classification system
Provides database access functions for LC and export document data
"""

import sys
import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session

# Add the API directory to the Python path
api_dir = Path(__file__).parent.parent / "api"
sys.path.append(str(api_dir))

from database import SessionLocal, engine
from models import (
    LetterOfCredit as LCModel,
    LCDocumentRequirement as LCRequirementModel,
    ExportDocument as ExportDocModel,
    ClassificationRun as ClassificationRunModel,
    DocumentClassification as ClassificationModel
)

class LCDatabaseService:
    """Database service for LC document classification"""
    
    def __init__(self):
        self.session = SessionLocal()
    
    def close(self):
        """Close database session"""
        if self.session:
            self.session.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    def get_lc_by_reference(self, lc_reference: str) -> Optional[LCModel]:
        """Get LC by reference number"""
        return self.session.query(LCModel).filter(LCModel.lc_reference == lc_reference).first()
    
    def get_lc_requirements_data(self, lc_reference: str) -> Tuple[List[Dict], str]:
        """
        Get LC requirements in the format expected by LangGraph
        Returns: (requirements_list, lc_reference)
        """
        lc = self.get_lc_by_reference(lc_reference)
        if not lc:
            raise ValueError(f"LC with reference {lc_reference} not found")
        
        requirements = []
        for req in lc.document_requirements:
            requirements.append({
                "document_id": req.document_id,
                "name": req.name,
                "description": req.description or "",
                "quantity": req.quantity or 1,
                "validation_criteria": req.validation_criteria or []
            })
        
        return requirements, lc.lc_reference
    
    def get_export_documents_data(self, lc_reference: str = None) -> Dict[str, Any]:
        """
        Get export documents in the format expected by LangGraph
        Returns: documents data with metadata
        """
        if lc_reference:
            # Filter export documents by LC reference
            lc = self.get_lc_by_reference(lc_reference)
            if lc:
                export_docs = self.session.query(ExportDocModel).filter(ExportDocModel.lc_id == lc.id).all()
            else:
                export_docs = []
        else:
            # Get all export documents if no LC reference provided
            export_docs = self.session.query(ExportDocModel).all()
        
        documents = []
        for doc in export_docs:
            documents.append({
                "document_id": doc.document_id,
                "file_info": {
                    "filename": doc.filename,
                    "file_path": doc.file_path,
                    "file_size_bytes": doc.file_size_bytes,
                    "extraction_timestamp": doc.extraction_timestamp.isoformat() if doc.extraction_timestamp else None
                },
                "extraction_result": {
                    "document_name": doc.document_name or "",
                    "summary": doc.summary or "",
                    "full_description": doc.full_description or ""
                }
            })
        
        return {
            "documents": documents,
            "extraction_metadata": {
                "total_documents": len(documents),
                "source": "database",
                "successful_extractions": len([d for d in documents if d["extraction_result"]["document_name"]])
            }
        }
    
    def create_classification_run(self, lc_reference: str, total_export_docs: int, 
                                total_lc_requirements: int, model_used: str = "langraph_classification") -> ClassificationRunModel:
        """Create a new classification run record"""
        lc = self.get_lc_by_reference(lc_reference)
        if not lc:
            raise ValueError(f"LC with reference {lc_reference} not found")
        
        run = ClassificationRunModel(
            lc_id=lc.id,
            total_export_docs=total_export_docs,
            total_lc_requirements=total_lc_requirements,
            model_used=model_used,
            status="running"
        )
        
        self.session.add(run)
        self.session.commit()
        self.session.refresh(run)
        return run
    
    def save_classification(self, classification_run_id: int, export_document_id: str, 
                          lc_requirement_id: str, confidence: float, reasoning: str, 
                          is_matched: bool) -> Tuple[ClassificationModel, ExportDocModel]:
        """
        Save a single classification result
        Updates both the DocumentClassification table and ExportDocument table
        """
        
        # Get the actual database records from the string IDs
        export_doc = self.session.query(ExportDocModel).filter(
            ExportDocModel.document_id == export_document_id
        ).first()
        
        if not export_doc:
            raise ValueError(f"Export document with ID {export_document_id} not found")
        
        lc_req = self.session.query(LCRequirementModel).filter(
            LCRequirementModel.document_id == lc_requirement_id
        ).first()
        
        if not lc_req:
            raise ValueError(f"LC requirement with ID {lc_requirement_id} not found")
        
        # Create classification record in the separate classification table
        classification = ClassificationModel(
            export_document_id=export_doc.id,
            lc_requirement_id=lc_req.id,
            classification_run_id=classification_run_id,
            confidence_score=confidence,
            reasoning=reasoning,
            is_matched=is_matched
        )
        
        # Also update the export document with classification results directly
        export_doc.lc_requirement_id = lc_req.id
        export_doc.confidence_score = confidence
        export_doc.reasoning = reasoning
        export_doc.is_matched = is_matched
        
        self.session.add(classification)
        self.session.commit()
        self.session.refresh(classification)
        self.session.refresh(export_doc)
        
        return classification, export_doc
    
    def update_classification_run_status(self, run_id: int, status: str, 
                                       total_matches_found: int = None) -> ClassificationRunModel:
        """Update classification run status and statistics"""
        run = self.session.query(ClassificationRunModel).filter(
            ClassificationRunModel.id == run_id
        ).first()
        
        if not run:
            raise ValueError(f"Classification run with ID {run_id} not found")
        
        run.status = status
        if total_matches_found is not None:
            run.total_matches_found = total_matches_found
        
        self.session.commit()
        self.session.refresh(run)
        return run
    
    def get_classification_results(self, run_id: int) -> List[Dict]:
        """Get classification results for a run in the format expected by LangGraph"""
        classifications = self.session.query(ClassificationModel).filter(
            ClassificationModel.classification_run_id == run_id
        ).all()
        
        results = []
        for classification in classifications:
            results.append({
                "export_document_id": classification.export_document.document_id,
                "export_document_name": classification.export_document.document_name,
                "lc_document_id": classification.lc_requirement.document_id,
                "lc_document_name": classification.lc_requirement.name,
                "confidence": classification.confidence_score,
                "reasoning": classification.reasoning,
                "is_classified": classification.is_matched
            })
        
        return results
    
    def get_latest_classification_run(self, lc_reference: str) -> Optional[ClassificationRunModel]:
        """Get the latest classification run for an LC"""
        lc = self.get_lc_by_reference(lc_reference)
        if not lc:
            return None
        
        return self.session.query(ClassificationRunModel).filter(
            ClassificationRunModel.lc_id == lc.id
        ).order_by(ClassificationRunModel.run_timestamp.desc()).first()


def create_db_service() -> LCDatabaseService:
    """Factory function to create database service"""
    return LCDatabaseService()


def test_db_connection():
    """Test database connection and basic operations"""
    try:
        with create_db_service() as db_service:
            # Test getting LC data
            lcs = db_service.session.query(LCModel).all()
            print(f"✅ Database connection successful! Found {len(lcs)} LC(s)")
            
            if lcs:
                lc_ref = lcs[0].lc_reference
                print(f"✅ Testing LC requirements for {lc_ref}")
                requirements, ref = db_service.get_lc_requirements_data(lc_ref)
                print(f"✅ Found {len(requirements)} requirements")
                
                print("✅ Testing export documents")
                export_data = db_service.get_export_documents_data()
                print(f"✅ Found {len(export_data['documents'])} export documents")
                
            return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False


if __name__ == "__main__":
    test_db_connection()