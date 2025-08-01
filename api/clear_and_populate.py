#!/usr/bin/env python3
"""
Script to clear database and repopulate with fresh data
"""

import sys
import os

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import drop_tables, create_tables
from populate_db import main as populate_main

def main():
    """Clear database and repopulate"""
    print("="*50)
    print("CLEARING AND REPOPULATING DATABASE")
    print("="*50)
    
    try:
        print("\n1. Dropping all existing tables...")
        drop_tables()
        print("   ✓ All tables dropped successfully")
        
        print("\n2. Creating fresh table structure...")
        create_tables()
        print("   ✓ Tables created successfully")
        
        print("\n3. Populating database with data...")
        populate_main()
        
        print("\n" + "="*50)
        print("DATABASE CLEAR AND REPOPULATION COMPLETED!")
        print("="*50)
        
    except Exception as e:
        print(f"\n❌ Error during database operations: {e}")
        raise

if __name__ == "__main__":
    main()