"""
Test script to verify the first batch processing pipeline works correctly
This script tests: ingest → summarize → embed pipeline
"""
import asyncio
import time
import sys
from pathlib import Path

# Add src to path so we can import the modules
sys.path.insert(0, str(Path(__file__).parent))

from src.agential_researcher.store.db import init_db, upsert_item, get_job
from src.agential_researcher.queue.celery_app import celery_app
from src.agential_researcher.providers.router import llm_router
from src.agential_researcher.config import settings

def test_first_batch_processing():
    """
    Test the complete pipeline: ingest → summarize → embed
    """
    print("Starting Week 1 - First Batch Processing Test...")
    
    # 1. Initialize database
    print("1. Initializing database...")
    init_db()
    print("✓ Database initialized")
    
    # 2. Test provider health
    print("2. Testing LLM provider health...")
    llm_router.startup_probe_sync()
    print(f"✓ Primary provider health: {llm_router.primary_healthy}")
    print(f"✓ Secondary provider health: {llm_router.secondary_healthy}")
    
    # 3. Create test content to process
    print("3. Creating test content...")
    test_content = """
    This is a test research paper abstract for validating the first batch processing pipeline.
    
    Title: Efficient Neural Network Architectures for Large-Scale Machine Learning
    
    Abstract: We present a novel approach to designing neural network architectures that 
    significantly improve computational efficiency while maintaining model performance. 
    Our method combines attention mechanisms with sparse connectivity patterns to reduce 
    computational overhead by up to 40% compared to traditional dense architectures. 
    Experimental results on multiple benchmark datasets demonstrate superior performance 
    across various tasks including image classification, natural language processing, 
    and sequence modeling. The proposed approach shows particular promise for deployment 
    in resource-constrained environments.
    """
    
    # 4. Insert test item into database (this represents the "ingest" step)
    print("4. Ingesting test content...")
    item_id = f"test:item_{int(time.time())}"
    item_data = {
        'id': item_id,
        'source': 'test',
        'title': 'Test Research Paper',
        'abstract': test_content,
        'content': test_content,
        'created_at': time.time(),
        'metadata': {
            'test_batch': True,
            'created_by': 'first_batch_test'
        }
    }
    
    upsert_item(item_data)
    print(f"✓ Test item ingested with ID: {item_id}")
    
    # 5. Queue summarize task (this represents the "summarize" step)
    print("5. Queuing summarize task...")
    summarize_job_id = f"job_sum_test_{int(time.time())}"
    
    # Add to database as pending job
    from src.agential_researcher.store.db import insert_job
    summarize_job_data = {
        'job_id': summarize_job_id,
        'job_type': 'summarize_test',
        'payload': {'content': test_content, 'item_id': item_id},
        'priority': 10,
        'status': 'pending',
        'progress': 0,
        'result': {},
        'created_at': time.time(),
    }
    insert_job(summarize_job_data)
    
    # Send to Celery queue
    summarize_task = celery_app.send_task(
        'src.agential_researcher.queue.tasks.summarize_task',
        args=[test_content, summarize_job_id],
        queue='hot'
    )
    print(f"✓ Summarize task queued: {summarize_job_id}")
    
    # 6. Queue embed task (this represents the "embed" step)
    print("6. Queuing embed task...")
    embed_job_id = f"job_emb_test_{int(time.time())}"
    
    embed_job_data = {
        'job_id': embed_job_id,
        'job_type': 'embed_test',
        'payload': {'content': test_content, 'item_id': item_id},
        'priority': 10,
        'status': 'pending',
        'progress': 0,
        'result': {},
        'created_at': time.time(),
    }
    insert_job(embed_job_data)
    
    embed_task = celery_app.send_task(
        'src.agential_researcher.queue.tasks.embed_task',
        args=[test_content, item_id, embed_job_id],
        queue='hot'
    )
    print(f"✓ Embed task queued: {embed_job_id}")
    
    # 7. Wait for tasks to complete (with timeout)
    print("7. Waiting for tasks to complete...")
    max_wait_time = 60  # 60 seconds max wait
    start_time = time.time()
    
    summarize_completed = False
    embed_completed = False
    
    while (not summarize_completed or not embed_completed) and (time.time() - start_time < max_wait_time):
        if not summarize_completed:
            summarize_job = get_job(summarize_job_id)
            if summarize_job and summarize_job.get('status') in ['completed', 'failed']:
                summarize_completed = True
                print(f"✓ Summarize task completed with status: {summarize_job.get('status')}")
        
        if not embed_completed:
            embed_job = get_job(embed_job_id)
            if embed_job and embed_job.get('status') in ['completed', 'failed']:
                embed_completed = True
                print(f"✓ Embed task completed with status: {embed_job.get('status')}")
        
        if not (summarize_completed and embed_completed):
            time.sleep(2)  # Wait 2 seconds between checks
    
    # 8. Verify results
    print("8. Verifying results...")
    summarize_job = get_job(summarize_job_id)
    embed_job = get_job(embed_job_id)
    
    if summarize_job and embed_job:
        all_passed = (
            summarize_job.get('status') == 'completed' and 
            embed_job.get('status') == 'completed'
        )
        
        if all_passed:
            print("✅ SUCCESS: First batch processing pipeline completed successfully!")
            print(f"   - Item ID: {item_id}")
            print(f"   - Summarize Job: {summarize_job_id} (Status: {summarize_job.get('status')})")
            print(f"   - Embed Job: {embed_job_id} (Status: {embed_job.get('status')})")
            return True
        else:
            print("❌ FAILED: Pipeline did not complete successfully")
            print(f"   - Summarize Job: {summarize_job.get('status')}")
            print(f"   - Embed Job: {embed_job.get('status')}")
            return False
    else:
        print("❌ FAILED: Could not retrieve job status")
        return False

if __name__ == "__main__":
    success = test_first_batch_processing()
    sys.exit(0 if success else 1)