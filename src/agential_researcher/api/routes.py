from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import Optional, Dict, Any
import uuid
import time

from ..queue.tasks import enqueue_job_task

router = APIRouter()

# Models
class EnqueueRequest(BaseModel):
    type: str
    payload: Dict[str, Any]
    priority: int = 10  # Default to hot queue

class EnqueueResponse(BaseModel):
    job_id: str

class StatusResponse(BaseModel):
    job_id: str
    state: str
    progress: int
    output_ref: Optional[str] = None
    created_at: float
    completed_at: Optional[float] = None

# In-memory job store (will be replaced with DB in real implementation)
jobs: Dict[str, Dict[str, Any]] = {}

@router.post("/enqueue", response_model=EnqueueResponse, tags=["jobs"])
async def enqueue_job(request: EnqueueRequest):
    """Enqueue a new job for processing"""
    job_id = f"job_{uuid.uuid4().hex}"
    
    # Store job info
    jobs[job_id] = {
        "job_id": job_id,
        "type": request.type,
        "payload": request.payload,
        "priority": request.priority,
        "state": "pending",
        "progress": 0,
        "output_ref": None,
        "created_at": time.time(),
        "completed_at": None
    }
    
    # Send to Celery queue
    result = enqueue_job_task.delay(job_id, request.type, request.payload, request.priority)
    
    return EnqueueResponse(job_id=job_id)

@router.get("/status/{job_id}", response_model=StatusResponse, tags=["jobs"])
async def get_job_status(job_id: str):
    """Get the status of a specific job"""
    if job_id not in jobs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    job = jobs[job_id]
    return StatusResponse(**job)

# Keep the original API endpoints as placeholders
@router.post("/ingest/arxiv", tags=["ingest"])
async def ingest_arxiv():
    """Trigger arXiv backfill/poll (admin-gated)"""
    from ...queue.celery_app import celery_app
    from ...queue.tasks import embed_task, summarize_task
    
    job_id = f"job_arxiv_{uuid.uuid4().hex}"
    jobs[job_id] = {
        "job_id": job_id,
        "type": "ingest_arxiv",
        "payload": {},
        "priority": 10,
        "state": "pending",
        "progress": 0,
        "output_ref": None,
        "created_at": time.time(),
        "completed_at": None
    }
    
    # In a real implementation, this would trigger the actual arXiv polling
    # For now, just return the job ID
    # The actual processing would happen in the arXiv poller service
    
    return {"job_id": job_id}

@router.post("/ingest/content", tags=["ingest"])
async def ingest_content(payload: Dict[str, Any]):
    """Ingest specific content with full pipeline: content → summarize → embed"""
    from ...queue.celery_app import celery_app
    from ...queue.tasks import summarize_task, embed_task
    from ...store.db import upsert_item
    import hashlib
    
    # Generate a content hash for deduplication
    content_to_hash = payload.get("content", "") + payload.get("title", "")
    content_hash = hashlib.sha256(content_to_hash.encode()).hexdigest()
    
    # Create a unique ID based on source and content hash
    source = payload.get("source", "unknown")
    item_id = f"{source}:{content_hash[:16]}"
    
    # Check if item already exists in database to prevent duplicates
    from ...store.db import item_exists
    if item_exists(item_id):
        return {
            "item_id": item_id,
            "status": "duplicate",
            "message": "Item already exists in database"
        }
    
    # Create the item record
    item_data = {
        "id": item_id,
        "source": source,
        "title": payload.get("title", ""),
        "abstract": payload.get("abstract", ""),
        "content": payload.get("content", ""),
        "created_at": time.time(),
        "metadata": payload.get("metadata", {})
    }
    
    # Upsert the item to database
    upsert_item(item_data)
    
    # Create a job to run the full pipeline: summarize -> embed
    summarize_job = celery_app.send_task(
        'src.agential_researcher.queue.tasks.summarize_task',
        args=[payload.get("content", ""), f"sum_job_{uuid.uuid4().hex}"],
        queue='hot'
    )
    
    embed_job = celery_app.send_task(
        'src.agential_researcher.queue.tasks.embed_task',
        args=[payload.get("content", ""), item_id, f"embed_job_{uuid.uuid4().hex}"],
        queue='hot'
    )
    
    return {
        "item_id": item_id,
        "summarize_job_id": summarize_job.id,
        "embed_job_id": embed_job.id,
        "status": "processing"
    }

@router.post("/pdf/parse", tags=["pdf"])
async def parse_pdf():
    """Parse and store markdown from a PDF"""
    job_id = f"job_pdf_{uuid.uuid4().hex}"
    jobs[job_id] = {
        "job_id": job_id,
        "type": "pdf_parse",
        "payload": {},
        "priority": 5,
        "state": "pending",
        "progress": 0,
        "output_ref": None,
        "created_at": time.time(),
        "completed_at": None
    }
    
    return {"job_id": job_id}

@router.post("/ocr/run", tags=["ocr"])
async def run_ocr():
    """Run targeted OCR on specific pages/regions"""
    job_id = f"job_ocr_{uuid.uuid4().hex}"
    jobs[job_id] = {
        "job_id": job_id,
        "type": "ocr_run",
        "payload": {},
        "priority": 5,
        "state": "pending",
        "progress": 0,
        "output_ref": None,
        "created_at": time.time(),
        "completed_at": None
    }
    
    return {"job_id": job_id}

@router.post("/graph/link", tags=["graph"])
async def link_graph():
    """Build knowledge graph edges for IDs"""
    job_id = f"job_graph_{uuid.uuid4().hex}"
    jobs[job_id] = {
        "job_id": job_id,
        "type": "graph_link",
        "payload": {},
        "priority": 10,
        "state": "pending",
        "progress": 0,
        "output_ref": None,
        "created_at": time.time(),
        "completed_at": None
    }
    
    return {"job_id": job_id}

@router.post("/focus/run", tags=["focus"])
async def run_focus():
    """Execute a focus YAML specification"""
    job_id = f"job_focus_{uuid.uuid4().hex}"
    jobs[job_id] = {
        "job_id": job_id,
        "type": "focus_run",
        "payload": {},
        "priority": 10,
        "state": "pending",
        "progress": 0,
        "output_ref": None,
        "created_at": time.time(),
        "completed_at": None
    }
    
    return {"job_id": job_id}

@router.get("/search", tags=["search"])
async def search(query: str = "", limit: int = 10, offset: int = 0, min_score: float = 0.0):
    """Perform lexical+vector fusion search"""
    from ...store.db import search_items
    
    if query:
        results = search_items(query, limit=limit)
        return {
            "query": query,
            "results": results,
            "total_hits": len(results),
            "execution_time_ms": 0  # Placeholder - would track real execution time
        }
    else:
        # Return empty results if no query provided
        return {
            "query": query,
            "results": [],
            "total_hits": 0,
            "execution_time_ms": 0
        }

@router.get("/export/csv", tags=["export"])
async def export_csv(
    item_type: str = "items",  # "items", "jobs"
    limit: int = 1000,
    source: str = None,
    status: str = None
):
    """Export data to CSV format"""
    from ...store import export
    
    if item_type == "items":
        filters = {}
        if source:
            filters['source'] = source
        return {"file": export.export_items_to_csv(limit=limit, filters=filters)}
    elif item_type == "jobs":
        return {"file": export.export_jobs_to_csv(limit=limit, status_filter=status)}
    else:
        raise HTTPException(status_code=400, detail="Invalid item_type. Use 'items' or 'jobs'")

@router.get("/export/xlsx", tags=["export"])
async def export_xlsx(
    limit: int = 1000,
    source: str = None
):
    """Export items to Excel format"""
    from ...store import export
    
    filters = {}
    if source:
        filters['source'] = source
    
    return {"file": export.export_items_to_excel(limit=limit, filters=filters)}