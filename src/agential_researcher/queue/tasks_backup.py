from .celery_app import celery_app
import time
import logging
from typing import Dict, Any

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@celery_app.task(bind=True, name="src.agential_researcher.queue.tasks.enqueue_job_task")
def enqueue_job_task(self, job_id: str, job_type: str, payload: Dict[str, Any], priority: int):
    """
    Minimal no-op task that logs and returns job_id
    """
    logger.info(f"Processing job {job_id} of type {job_type} with priority {priority}")
    
    # Update task state
    self.update_state(
        state="PROGRESS",
        meta={"status": "Processing", "progress": 50}
    )
    
    # Simulate some work
    time.sleep(1)
    
    logger.info(f"Completed job {job_id}")
    
    return {
        "job_id": job_id,
        "status": "completed",
        "processed_at": time.time()
    }

@celery_app.task(bind=True, name="src.agential_researcher.queue.tasks.summarize_task")
def summarize_task(self, content: str, job_id: str = None):
    """
    Actual LLM summarization task that uses the provider router
    """
    from ..providers.router import llm_router
    from ..utils.metrics import record_task_duration
    
    start_time = time.time()
    logger.info(f"Starting summarization for job {job_id}" if job_id else "Starting summarization")
    
    # Update task state
    self.update_state(
        state="PROGRESS",
        meta={"status": "Initializing", "progress": 0}
    )
    
    try:
        # Prepare the summarization prompt
        prompt = f"""
        Please provide a concise summary of the following research content.
        Focus on the main contributions, methodology, and key findings.
        
        Content:
        {content[:4000]}  # Limit content to avoid token issues
        
        Summary:
        """
        
        # Create the payload for the LLM request
        payload = {
            "model": "llm-model",  # Generic model identifier
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 512,
            "temperature": 0.3,  # Lower temperature for more consistent summaries
            "stream": False
        }
        
        self.update_state(
            state="PROGRESS",
            meta={"status": "Calling LLM provider", "progress": 20}
        )
        
        # Call the LLM provider through the router (sync version for Celery)
        summary_response = llm_router.route_request_sync(payload)
        
        self.update_state(
            state="PROGRESS",
            meta={"status": "Processing response", "progress": 80}
        )
        
        # Extract the summary from the response
        if summary_response and "choices" in summary_response:
            summary = summary_response["choices"][0]["message"]["content"].strip()
        else:
            # Fallback if the response format is unexpected
            summary = f"Summary of content: {content[:100]}..."

        # Log the tokens used
        tokens_used = summary_response.get("usage", {}).get("total_tokens", len(content.split())) if summary_response else len(content.split())
        
        logger.info(f"Completed summarization for job {job_id}" if job_id else "Completed summarization")
        
        result = {
            "summary": summary,
            "tokens_used": tokens_used,
            "completed_at": time.time()
        }
        
        # Record task duration metrics
        duration = time.time() - start_time
        from ..utils.metrics import record_task_duration
        record_task_duration("summarize_task", duration)
        
        # Update the job status in the database if job_id is provided
        if job_id:
            from ..store.db import update_job_status
            update_job_status(job_id, "completed", 100, result)
        
        return result
        
    except Exception as e:
        logger.error(f"Error in summarization task: {str(e)}")
        error_result = {
            "summary": None,
            "error": str(e),
            "completed_at": time.time()
        }
        
        # Record task duration even for failed tasks
        duration = time.time() - start_time
        from ..utils.metrics import record_task_duration
        record_task_duration("summarize_task", duration)
        
        # Update the job status as failed if job_id is provided
        if job_id:
            from ..store.db import update_job_status
            update_job_status(job_id, "failed", 100, error_result)
        
        raise e

@celery_app.task(name="src.agential_researcher.queue.tasks.embed_task")
def embed_task(content: str):
    """
    Task to generate embeddings (placeholder)
    """
    logger.info("Generating embeddings")
    
    # Simulate embedding generation
    time.sleep(1.5)
    
    # In a real implementation, this would generate actual embeddings
    embedding_result = {
        "embedding_id": f"emb_{int(time.time())}",
        "dimensions": 384,  # Placeholder
        "content_length": len(content)
    }
    
    logger.info("Completed embeddings generation")
    
    return embedding_result

@celery_app.task(name="src.agential_researcher.queue.tasks.embed_task")
def embed_task(content: str, source_id: str = None, job_id: str = None):
    """
    Task to generate embeddings and store in LanceDB
    """
    from ..store.embedding import generate_and_store_embedding
    from ..utils.metrics import record_task_duration
    
    start_time = time.time()
    logger.info(f"Starting embedding generation for source {source_id}" if source_id else "Starting embedding generation")
    
    if job_id:
        from ..store.db import update_job_status
        update_job_status(job_id, "in_progress", 50)
    
    try:
        # Generate a unique ID for the embedding
        import uuid
        embedding_id = f"emb_{uuid.uuid4().hex[:8]}_{int(time.time())}"
        
        # Generate and store embedding
        result = generate_and_store_embedding(embedding_id, content, source_id)
        
        logger.info(f"Completed embedding generation for: {source_id or embedding_id}")
        
        # Record task duration metrics
        duration = time.time() - start_time
        from ..utils.metrics import record_task_duration
        record_task_duration("embed_task", duration)
        
        # Update job status if provided
        if job_id:
            from ..store.db import update_job_status
            update_job_status(job_id, "completed", 100, result)
        
        return result
        
    except Exception as e:
        logger.error(f"Error in embedding task: {str(e)}")
        error_result = {
            "error": str(e),
            "completed_at": time.time()
        }
        
        # Record task duration even for failed tasks
        duration = time.time() - start_time
        from ..utils.metrics import record_task_duration
        record_task_duration("embed_task", duration)
        
        # Update job status as failed if job_id is provided
        if job_id:
            from ..store.db import update_job_status
            update_job_status(job_id, "failed", 100, error_result)
        
        raise e

@celery_app.task(name="src.agential_researcher.queue.tasks.ocr_task")
def ocr_task(pdf_path: str, page_range: str = None):
    """
    Task to perform OCR on PDF (placeholder)
    """
    logger.info(f"Performing OCR on {pdf_path}, pages: {page_range}")
    
    # Simulate OCR processing
    time.sleep(3)
    
    ocr_result = {
        "pdf_path": pdf_path,
        "pages_processed": page_range or "all",
        "text_extracted": f"Extracted text from {pdf_path}",
        "processing_time": 3.0
    }
    
    logger.info(f"Completed OCR on {pdf_path}")
    
    return ocr_result

@celery_app.task(name="src.agential_researcher.queue.tasks.vlm_task")
def vlm_task(image_path: str, prompt: str = "Describe this image"):
    """
    Task to run Visual Language Model (placeholder)
    """
    logger.info(f"Running VLM on {image_path} with prompt: {prompt}")
    
    # Simulate VLM processing
    time.sleep(4)
    
    vlm_result = {
        "image_path": image_path,
        "prompt": prompt,
        "description": f"Description of image {image_path}",
        "processing_time": 4.0
    }
    
    logger.info(f"Completed VLM on {image_path}")
    
    return vlm_result

@celery_app.task(name="src.agential_researcher.queue.tasks.backfill_task")
def backfill_task(source: str, query: str = None):
    """
    Task for backfill operations
    """
    logger.info(f"Starting backfill from {source}, query: {query}")
    
    # Simulate backfill processing
    time.sleep(5)
    
    backfill_result = {
        "source": source,
        "query": query,
        "items_processed": 100,  # Placeholder
        "processing_time": 5.0
    }
    
    logger.info(f"Completed backfill from {source}")
    
    return backfill_result

@celery_app.task(name="src.agential_researcher.queue.tasks.maintenance_task")
def maintenance_task(operation: str):
    """
    Task for maintenance operations
    """
    logger.info(f"Running maintenance operation: {operation}")
    
    # Simulate maintenance
    time.sleep(2)
    
    maintenance_result = {
        "operation": operation,
        "status": "completed",
        "processing_time": 2.0
    }
    
    logger.info(f"Completed maintenance operation: {operation}")
    
    return maintenance_result