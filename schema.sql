-- Schema for Agential Researcher System

-- Items table - stores all documents (arXiv papers, HF models/datasets, etc.)
CREATE TABLE IF NOT EXISTS items (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,          -- arxiv, hf_model, hf_dataset, gh_repo
    title TEXT,
    abstract TEXT,
    content TEXT,                  -- Full text content
    summary TEXT,                  -- AI-generated summary
    embedding_id TEXT,             -- Reference to LanceDB embedding
    created_at REAL,               -- Unix timestamp
    updated_at REAL,               -- Unix timestamp
    metadata_json TEXT             -- JSON blob for source-specific metadata
);

-- FTS5 virtual table for full-text search
CREATE VIRTUAL TABLE IF NOT EXISTS items_idx USING fts5(
    title, abstract, content,
    content='items',               -- Contentless table, points to 'items'
    content_rowid='rowid'          -- Link to physical table rowid
);

-- Edges table - knowledge graph relationships
CREATE TABLE IF NOT EXISTS edges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    relation_type TEXT NOT NULL,   -- similar, topical, cites, coauthor, etc.
    score REAL,                    -- Relationship strength/weight
    created_at REAL,               -- Unix timestamp
    UNIQUE(source_id, target_id, relation_type)  -- Prevent duplicate edges
);

-- Jobs audit trail - track all processing jobs
CREATE TABLE IF NOT EXISTS jobs (
    job_id TEXT PRIMARY KEY,
    job_type TEXT NOT NULL,        -- ingest_arxiv, summarize, embed, ocr, etc.
    payload_json TEXT,             -- JSON payload for the job
    priority INTEGER DEFAULT 10,   -- Queue priority (hot=10, vlm_ocr=5, backfill=1, maintenance=2)
    status TEXT DEFAULT 'pending', -- pending, in_progress, completed, failed
    progress INTEGER DEFAULT 0,    -- Progress percentage 0-100
    result_json TEXT,              -- JSON result of the job
    created_at REAL,               -- Unix timestamp
    updated_at REAL,               -- Unix timestamp
    completed_at REAL              -- Unix timestamp (when status becomes completed/failed)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_type ON jobs(job_type);
CREATE INDEX IF NOT EXISTS idx_items_source ON items(source);
CREATE INDEX IF NOT EXISTS idx_items_created_at ON items(created_at);

-- Insert example data for testing
-- INSERT OR IGNORE INTO items (id, source, title, abstract, created_at) VALUES
-- ('arxiv:2103.00020', 'arxiv', 'Attention Is All You Need', 'The dominant sequence transduction models...', 1615000000.0);

-- INSERT OR IGNORE INTO jobs (job_id, job_type, status, created_at) VALUES
-- ('job_001', 'ingest_arxiv', 'completed', 1615000000.0);