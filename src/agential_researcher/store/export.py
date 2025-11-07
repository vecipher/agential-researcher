import pandas as pd
import sqlite3
import json
from typing import List, Dict, Any
from datetime import datetime
import io

from ..config import settings


def export_items_to_csv(limit: int = None, filters: Dict[str, Any] = None) -> str:
    """
    Export items from the database to a CSV file
    Returns the path to the exported file
    """
    conn = sqlite3.connect(settings.sqlite_path)
    
    # Build query with optional filters and limit
    query = """
        SELECT id, source, title, abstract, content, summary, embedding_id, 
               created_at, updated_at, metadata_json
        FROM items
    """
    
    params = []
    if filters:
        conditions = []
        if filters.get('source'):
            conditions.append("source = ?")
            params.append(filters['source'])
        if filters.get('from_date'):
            conditions.append("created_at >= ?")
            params.append(filters['from_date'])
        if filters.get('to_date'):
            conditions.append("created_at <= ?")
            params.append(filters['to_date'])
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
    
    if limit:
        query += f" LIMIT {limit}"
    
    df = pd.read_sql_query(query, conn, params=params)
    
    # Convert timestamps to readable format
    if 'created_at' in df.columns:
        df['created_at'] = pd.to_datetime(df['created_at'], unit='s')
    if 'updated_at' in df.columns:
        df['updated_at'] = pd.to_datetime(df['updated_at'], unit='s')
    
    # Convert metadata_json to string representation if needed
    if 'metadata_json' in df.columns:
        df['metadata'] = df['metadata_json'].apply(
            lambda x: json.loads(x) if x else {}
        )
    
    # Generate filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"items_export_{timestamp}.csv"
    
    # Save to file
    df.to_csv(filename, index=False)
    
    conn.close()
    
    return filename


def export_items_to_excel(limit: int = None, filters: Dict[str, Any] = None) -> str:
    """
    Export items from the database to an Excel file
    Returns the path to the exported file
    """
    conn = sqlite3.connect(settings.sqlite_path)
    
    # Build query with optional filters and limit
    query = """
        SELECT id, source, title, abstract, content, summary, embedding_id, 
               created_at, updated_at, metadata_json
        FROM items
    """
    
    params = []
    if filters:
        conditions = []
        if filters.get('source'):
            conditions.append("source = ?")
            params.append(filters['source'])
        if filters.get('from_date'):
            conditions.append("created_at >= ?")
            params.append(filters['from_date'])
        if filters.get('to_date'):
            conditions.append("created_at <= ?")
            params.append(filters['to_date'])
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
    
    if limit:
        query += f" LIMIT {limit}"
    
    df = pd.read_sql_query(query, conn, params=params)
    
    # Convert timestamps to readable format
    if 'created_at' in df.columns:
        df['created_at'] = pd.to_datetime(df['created_at'], unit='s')
    if 'updated_at' in df.columns:
        df['updated_at'] = pd.to_datetime(df['updated_at'], unit='s')
    
    # Generate filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"items_export_{timestamp}.xlsx"
    
    # Save to Excel with formatting
    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Items', index=False)
        
        # Get the workbook and worksheet to apply formatting
        workbook = writer.book
        worksheet = writer.sheets['Items']
        
        # Auto-adjust column widths
        for column in worksheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)  # Cap at 50 characters
            worksheet.column_dimensions[column_letter].width = adjusted_width
    
    conn.close()
    
    return filename


def export_search_results_to_csv(query: str, limit: int = 100) -> str:
    """
    Export search results to CSV
    """
    from .db import search_items
    
    results = search_items(query, limit=limit)
    
    # Convert to DataFrame
    df = pd.DataFrame(results)
    
    # Convert timestamp if present
    if 'created_at' in df.columns:
        df['created_at'] = pd.to_datetime(df['created_at'], unit='s')
    
    # Generate filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    clean_query = "".join(c for c in query if c.isalnum() or c in (' ', '-', '_')).rstrip()
    clean_query = clean_query[:30]  # Limit length
    filename = f"search_export_{clean_query}_{timestamp}.csv"
    
    # Save to file
    df.to_csv(filename, index=False)
    
    return filename


def export_jobs_to_csv(limit: int = None, status_filter: str = None) -> str:
    """
    Export jobs audit trail to CSV
    """
    conn = sqlite3.connect(settings.sqlite_path)
    
    query = "SELECT * FROM jobs"
    params = []
    
    if status_filter:
        query += " WHERE status = ?"
        params.append(status_filter)
    
    if limit:
        query += f" LIMIT {limit}"
    
    df = pd.read_sql_query(query, conn, params=params)
    
    # Convert timestamps to readable format
    for col in ['created_at', 'updated_at', 'completed_at']:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], unit='s', errors='coerce')
    
    # Generate filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    status_part = f"_{status_filter}" if status_filter else ""
    filename = f"jobs_export{status_part}_{timestamp}.csv"
    
    # Save to file
    df.to_csv(filename, index=False)
    
    conn.close()
    
    return filename