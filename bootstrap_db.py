#!/usr/bin/env python3
"""
Database bootstrap script for Agential Researcher
"""
import sqlite3
import os
import sys
from pathlib import Path

# Add src to path so we can import the module
sys.path.insert(0, str(Path(__file__).parent))

from src.agential_researcher.store.db import init_db
from src.agential_researcher.config import settings

def main():
    print("Bootstrapping Agential Researcher database...")
    
    # Initialize the database
    init_db()
    
    print(f"Database initialized at: {settings.sqlite_path}")
    
    # Verify the tables were created
    conn = sqlite3.connect(settings.sqlite_path)
    cursor = conn.cursor()
    
    # Check tables exist
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]
    
    expected_tables = {'items', 'items_idx', 'edges', 'jobs'}
    created_tables = set(tables)
    
    print(f"Tables created: {', '.join(tables)}")
    
    if expected_tables.issubset(created_tables):
        print("✓ All expected tables created successfully")
    else:
        missing = expected_tables - created_tables
        print(f"✗ Missing tables: {missing}")
        sys.exit(1)
    
    conn.close()
    print("Database bootstrap completed successfully!")

if __name__ == "__main__":
    main()