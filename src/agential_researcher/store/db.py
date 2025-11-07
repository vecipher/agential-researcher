import sqlite3
import os
from typing import Dict, Any, List, Optional
import json
import time

from ..config import settings

def init_db():
    """Initialize the SQLite database with schema"""
    conn = sqlite3.connect(settings.sqlite_path)
    cursor = conn.cursor()
    
    # Create items table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS items (
            id TEXT PRIMARY KEY,
            source TEXT NOT NULL,
            title TEXT,
            abstract TEXT,
            content TEXT,
            summary TEXT,
            embedding_id TEXT,
            created_at REAL,
            updated_at REAL,
            metadata_json TEXT  -- JSON metadata field
        )
    ''')
    
    # Create FTS5 index for full-text search
    cursor.execute('''
        CREATE VIRTUAL TABLE IF NOT EXISTS items_idx USING fts5(
            title, abstract, content,
            content='items',
            content_rowid='rowid'
        )
    ''')
    
    # Create edges table for knowledge graph
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS edges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id TEXT NOT NULL,
            target_id TEXT NOT NULL,
            relation_type TEXT NOT NULL,  -- similar, topical, cites, coauthor
            score REAL,
            created_at REAL,
            UNIQUE(source_id, target_id, relation_type)
        )
    ''')
    
    # Create jobs audit trail table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS jobs (
            job_id TEXT PRIMARY KEY,
            job_type TEXT NOT NULL,
            payload_json TEXT,
            priority INTEGER DEFAULT 10,
            status TEXT DEFAULT 'pending',
            progress INTEGER DEFAULT 0,
            result_json TEXT,
            created_at REAL,
            updated_at REAL,
            completed_at REAL
        )
    ''')
    
    # Create index for jobs table
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_jobs_type ON jobs(job_type)')
    
    conn.commit()
    conn.close()

def item_exists(item_id: str) -> bool:
    """Check if an item with the given ID already exists in the database"""
    conn = sqlite3.connect(settings.sqlite_path)
    cursor = conn.cursor()

    cursor.execute('SELECT 1 FROM items WHERE id = ?', (item_id,))
    result = cursor.fetchone()

    conn.close()
    
    return result is not None

def upsert_item(item_data: Dict[str, Any]) -> str:
    """Upsert an item and update FTS5 index"""
    conn = sqlite3.connect(settings.sqlite_path)
    cursor = conn.cursor()
    
    item_id = item_data.get('id')
    if not item_id:
        raise ValueError("Item must have an ID")
    
    current_time = time.time()
    
    # Insert or replace the item
    cursor.execute('''
        INSERT OR REPLACE INTO items 
        (id, source, title, abstract, content, summary, embedding_id, created_at, updated_at, metadata_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        item_id,
        item_data.get('source'),
        item_data.get('title'),
        item_data.get('abstract'),
        item_data.get('content'),
        item_data.get('summary'),
        item_data.get('embedding_id'),
        item_data.get('created_at', current_time),
        current_time,
        json.dumps(item_data.get('metadata', {}))
    ))
    
    # Update the FTS5 index
    cursor.execute('''
        INSERT OR REPLACE INTO items_idx(rowid, title, abstract, content)
        VALUES (?, ?, ?, ?)
    ''', (cursor.lastrowid, item_data.get('title'), item_data.get('abstract'), item_data.get('content')))
    
    conn.commit()
    conn.close()
    
    return item_id

def insert_job(job_data: Dict[str, Any]) -> str:
    """Insert a job into the audit trail"""
    conn = sqlite3.connect(settings.sqlite_path)
    cursor = conn.cursor()
    
    job_id = job_data.get('job_id')
    if not job_id:
        raise ValueError("Job must have an ID")
    
    current_time = time.time()
    
    cursor.execute('''
        INSERT INTO jobs 
        (job_id, job_type, payload_json, priority, status, progress, result_json, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        job_id,
        job_data.get('job_type'),
        json.dumps(job_data.get('payload', {})),
        job_data.get('priority', 10),
        job_data.get('status', 'pending'),
        job_data.get('progress', 0),
        json.dumps(job_data.get('result', {})),
        current_time,
        current_time
    ))
    
    conn.commit()
    conn.close()
    
    return job_id

def update_job_status(job_id: str, status: str, progress: int = None, result: Dict[str, Any] = None) -> bool:
    """Update job status in audit trail"""
    conn = sqlite3.connect(settings.sqlite_path)
    cursor = conn.cursor()
    
    # Build the update query
    if progress is not None and result is not None:
        cursor.execute('''
            UPDATE jobs SET status = ?, progress = ?, result_json = ?, updated_at = ?
            WHERE job_id = ?
        ''', (status, progress, json.dumps(result), time.time(), job_id))
    elif progress is not None:
        cursor.execute('''
            UPDATE jobs SET status = ?, progress = ?, updated_at = ?
            WHERE job_id = ?
        ''', (status, progress, time.time(), job_id))
    else:
        cursor.execute('''
            UPDATE jobs SET status = ?, updated_at = ?
            WHERE job_id = ?
        ''', (status, time.time(), job_id))
    
    rows_affected = cursor.rowcount
    conn.commit()
    conn.close()
    
    return rows_affected > 0

def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve job by ID"""
    conn = sqlite3.connect(settings.sqlite_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT job_id, job_type, payload_json, priority, status, progress, result_json, 
               created_at, updated_at, completed_at
        FROM jobs WHERE job_id = ?
    ''', (job_id,))
    
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            'job_id': row[0],
            'job_type': row[1],
            'payload_json': json.loads(row[2]) if row[2] else {},
            'priority': row[3],
            'status': row[4],
            'progress': row[5],
            'result_json': json.loads(row[6]) if row[6] else {},
            'created_at': row[7],
            'updated_at': row[8],
            'completed_at': row[9]
        }
    return None

def search_items(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Search items using FTS5"""
    conn = sqlite3.connect(settings.sqlite_path)
    cursor = conn.cursor()
    
    # Use FTS5 for full-text search
    cursor.execute('''
        SELECT i.id, i.source, i.title, i.abstract, i.content, i.summary, i.created_at
        FROM items i
        JOIN items_idx ii ON i.rowid = ii.rowid
        WHERE items_idx MATCH ?
        ORDER BY bm25(items_idx)
        LIMIT ?
    ''', (query, limit))
    
    results = []
    for row in cursor.fetchall():
        results.append({
            'id': row[0],
            'source': row[1],
            'title': row[2],
            'abstract': row[3],
            'content': row[4][:200] + "..." if row[4] else "",  # Truncate content
            'summary': row[5],
            'created_at': row[6]
        })
    
    conn.close()
    return results