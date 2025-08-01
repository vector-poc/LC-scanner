#!/usr/bin/env python3
"""
Database Clear Script for LC-Scanner
Safely clears all data from all tables while preserving table structure
"""

import os
import sys
from datetime import datetime

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from sqlalchemy import text
from database import SessionLocal, engine
from models import (
    LetterOfCredit as LCModel,
    LCDocumentRequirement as LCRequirementModel,
    ExportDocument as ExportDocModel,
    ClassificationRun as ClassificationRunModel,
    DocumentClassification as ClassificationModel
)

def confirm_clear():
    """Ask user for confirmation before clearing data"""
    print("⚠️  WARNING: This will permanently delete ALL data from the database!")
    print("   This action cannot be undone.")
    print()
    print("📊 Tables that will be cleared:")
    print("   • letter_of_credits")
    print("   • lc_document_requirements") 
    print("   • export_documents")
    print("   • classification_runs")
    print("   • document_classifications")
    print()
    
    response = input("Are you sure you want to proceed? Type 'YES' to confirm: ")
    return response.strip().upper() == 'YES'

def get_table_counts(db: Session):
    """Get current record counts for all tables"""
    counts = {}
    
    try:
        counts['letter_of_credits'] = db.query(LCModel).count()
        counts['lc_document_requirements'] = db.query(LCRequirementModel).count()
        counts['export_documents'] = db.query(ExportDocModel).count()
        counts['classification_runs'] = db.query(ClassificationRunModel).count()
        counts['document_classifications'] = db.query(ClassificationModel).count()
    except Exception as e:
        print(f"⚠️  Warning: Could not get table counts: {e}")
        counts = {}
    
    return counts

def clear_table_data(db: Session):
    """Clear all data from tables in the correct order (respecting foreign keys)"""
    print("\n🗑️  Clearing table data...")
    
    try:
        # Clear in reverse dependency order to avoid foreign key constraints
        print("   Clearing document_classifications...")
        deleted_classifications = db.query(ClassificationModel).delete()
        print(f"   ✅ Deleted {deleted_classifications} classification records")
        
        print("   Clearing classification_runs...")
        deleted_runs = db.query(ClassificationRunModel).delete()
        print(f"   ✅ Deleted {deleted_runs} classification run records")
        
        print("   Clearing export_documents...")
        deleted_exports = db.query(ExportDocModel).delete()
        print(f"   ✅ Deleted {deleted_exports} export document records")
        
        print("   Clearing lc_document_requirements...")
        deleted_requirements = db.query(LCRequirementModel).delete()
        print(f"   ✅ Deleted {deleted_requirements} LC requirement records")
        
        print("   Clearing letter_of_credits...")
        deleted_lcs = db.query(LCModel).delete()
        print(f"   ✅ Deleted {deleted_lcs} LC records")
        
        # Commit all deletions
        db.commit()
        print("\n✅ All table data cleared successfully!")
        
        return {
            'classifications': deleted_classifications,
            'runs': deleted_runs,
            'exports': deleted_exports,
            'requirements': deleted_requirements,
            'lcs': deleted_lcs
        }
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ Error clearing table data: {e}")
        raise

def reset_sequences(db: Session):
    """Reset auto-increment sequences for all tables"""
    print("\n🔄 Resetting auto-increment sequences...")
    
    sequences_to_reset = [
        'letter_of_credits_id_seq',
        'lc_document_requirements_id_seq',
        'export_documents_id_seq',
        'classification_runs_id_seq',
        'document_classifications_id_seq'
    ]
    
    try:
        for sequence in sequences_to_reset:
            try:
                db.execute(text(f"ALTER SEQUENCE {sequence} RESTART WITH 1"))
                print(f"   ✅ Reset {sequence}")
            except Exception as e:
                print(f"   ⚠️  Could not reset {sequence}: {e}")
        
        db.commit()
        print("✅ Sequences reset successfully!")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error resetting sequences: {e}")

def verify_clear(db: Session):
    """Verify that all tables are empty"""
    print("\n🔍 Verifying tables are empty...")
    
    counts = get_table_counts(db)
    all_empty = True
    
    for table, count in counts.items():
        if count == 0:
            print(f"   ✅ {table}: {count} records")
        else:
            print(f"   ❌ {table}: {count} records (should be 0)")
            all_empty = False
    
    if all_empty:
        print("\n🎉 All tables successfully cleared!")
    else:
        print("\n⚠️  Some tables still contain data")
    
    return all_empty

def main():
    """Main function to clear all database data"""
    print("="*60)
    print("🗑️  LC-SCANNER DATABASE CLEAR UTILITY")
    print("="*60)
    print(f"📅 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Create database session
    db = SessionLocal()
    
    try:
        # Show current state
        print("\n📊 Current database state:")
        initial_counts = get_table_counts(db)
        total_records = sum(initial_counts.values())
        
        for table, count in initial_counts.items():
            print(f"   {table}: {count} records")
        
        print(f"\n📈 Total records in database: {total_records}")
        
        if total_records == 0:
            print("\n✅ Database is already empty!")
            return
        
        # Get confirmation
        if not confirm_clear():
            print("\n❌ Operation cancelled by user")
            return
        
        print(f"\n🚀 Starting database clear at {datetime.now().strftime('%H:%M:%S')}")
        
        # Clear all data
        deleted_counts = clear_table_data(db)
        
        # Reset sequences
        reset_sequences(db)
        
        # Verify clearing
        verify_clear(db)
        
        # Summary
        print("\n" + "="*60)
        print("📋 CLEAR OPERATION SUMMARY")
        print("="*60)
        print(f"🕐 Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📊 Total records deleted: {sum(deleted_counts.values())}")
        print("\n📈 Records deleted by table:")
        for table, count in deleted_counts.items():
            print(f"   {table}: {count}")
        
        print("\n✅ Database successfully cleared!")
        print("🎯 Ready for fresh data import")
        
    except KeyboardInterrupt:
        print(f"\n⏹️  Operation interrupted by user")
        db.rollback()
    except Exception as e:
        print(f"\n❌ Error during clear operation: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    main()