import asyncio
import time
import logging
from typing import List, Dict, Any
from huggingface_hub import HfApi
from huggingface_hub.utils import RepositoryNotFoundError

from ..config import settings
from ..queue.celery_app import celery_app
from ..store.db import upsert_item

logger = logging.getLogger(__name__)

class HuggingFaceIngester:
    def __init__(self):
        self.api = HfApi()
        self.last_updated = {}

    async def poll_hf_models(self):
        """Poll Hugging Face for new models"""
        logger.info("Polling Hugging Face for new models...")
        
        try:
            # Get recently created models
            models = list(self.api.list_models(
                limit=settings.arxiv_max_results,
                sort="lastModified",
                direction=-1  # Most recent first
            ))
            
            new_entries = 0
            for model in models:
                model_id = f"hf:model:{model.author}/{model.modelId}" if model.author else f"hf:model:{model.modelId}"
                
                # Check if this is newer than what we last saw
                if model_id not in self.last_updated or model.lastModified > self.last_updated[model_id]:
                    logger.info(f"Found new/updated HF model: {model_id}")
                    
                    # Prepare item data
                    item_data = {
                        'id': model_id,
                        'source': 'hf_model',
                        'title': model.modelId,
                        'abstract': model.description[:500] if model.description else "",  # Limit abstract length
                        'content': model.description or "",
                        'created_at': time.time(),
                        'metadata': {
                            'author': model.author,
                            'last_modified': model.lastModified,
                            'tags': model.tags,
                            'pipeline_tag': model.pipeline_tag,
                            'library_name': getattr(model, 'library_name', None),
                            'likes': model.likes,
                            'downloads': getattr(model, 'downloads', 0)
                        }
                    }
                    
                    # Insert into database
                    try:
                        upsert_item(item_data)
                        logger.info(f"Inserted HF model: {model_id}")
                        
                        # Queue for further processing
                        celery_app.send_task(
                            'src.agential_researcher.queue.tasks.summarize_task',
                            args=[model.description or f"Model: {model.modelId}", f"job_hf_{model.modelId}"],
                            queue='hot'
                        )
                        
                        new_entries += 1
                    except Exception as e:
                        logger.error(f"Failed to insert HF model {model_id}: {e}")
                    
                    self.last_updated[model_id] = model.lastModified
            
            logger.info(f"Polled HF models, found {new_entries} new/updated entries")
            
        except Exception as e:
            logger.error(f"Error polling HF models: {e}")

    async def poll_hf_datasets(self):
        """Poll Hugging Face for new datasets"""
        logger.info("Polling Hugging Face for new datasets...")
        
        try:
            # Get recently created datasets
            datasets = list(self.api.list_datasets(
                limit=settings.arxiv_max_results,
                sort="lastModified",
                direction=-1  # Most recent first
            ))
            
            new_entries = 0
            for dataset in datasets:
                dataset_id = f"hf:dataset:{dataset.author}/{dataset.id}" if dataset.author else f"hf:dataset:{dataset.id}"
                
                # Check if this is newer than what we last saw
                if dataset_id not in self.last_updated or dataset.lastModified > self.last_updated[dataset_id]:
                    logger.info(f"Found new/updated HF dataset: {dataset_id}")
                    
                    # Prepare item data
                    item_data = {
                        'id': dataset_id,
                        'source': 'hf_dataset',
                        'title': dataset.id,
                        'abstract': dataset.description[:500] if dataset.description else "",
                        'content': dataset.description or "",
                        'created_at': time.time(),
                        'metadata': {
                            'author': dataset.author,
                            'last_modified': dataset.lastModified,
                            'tags': getattr(dataset, 'tags', []),
                            'card_data': getattr(dataset, 'cardData', {}),
                            'likes': getattr(dataset, 'likes', 0),
                            'downloads': getattr(dataset, 'downloads', 0)
                        }
                    }
                    
                    # Insert into database
                    try:
                        upsert_item(item_data)
                        logger.info(f"Inserted HF dataset: {dataset_id}")
                        
                        # Queue for further processing
                        celery_app.send_task(
                            'src.agential_researcher.queue.tasks.summarize_task',
                            args=[dataset.description or f"Dataset: {dataset.id}", f"job_hf_dataset_{dataset.id}"],
                            queue='hot'
                        )
                        
                        new_entries += 1
                    except Exception as e:
                        logger.error(f"Failed to insert HF dataset {dataset_id}: {e}")
                    
                    self.last_updated[dataset_id] = dataset.lastModified
            
            logger.info(f"Polled HF datasets, found {new_entries} new/updated entries")
            
        except Exception as e:
            logger.error(f"Error polling HF datasets: {e}")

    async def poll_hf_spaces(self):
        """Poll Hugging Face for new Spaces (demo applications)"""
        logger.info("Polling Hugging Face for new Spaces...")
        
        try:
            # Get recently created Spaces
            spaces = list(self.api.list_spaces(
                limit=settings.arxiv_max_results,
                sort="lastModified",
                direction=-1  # Most recent first
            ))
            
            new_entries = 0
            for space in spaces:
                space_id = f"hf:space:{space.author}/{space.id}" if space.author else f"hf:space:{space.id}"
                
                # Check if this is newer than what we last saw
                if space_id not in self.last_updated or space.lastModified > self.last_updated[space_id]:
                    logger.info(f"Found new/updated HF Space: {space_id}")
                    
                    # Prepare item data
                    item_data = {
                        'id': space_id,
                        'source': 'hf_space',
                        'title': space.id,
                        'abstract': space.description[:500] if space.description else "",
                        'content': space.description or "",
                        'created_at': time.time(),
                        'metadata': {
                            'author': space.author,
                            'last_modified': space.lastModified,
                            'tags': getattr(space, 'tags', []),
                            'sdk': getattr(space, 'sdk', None),
                            'likes': getattr(space, 'likes', 0),
                            'spaces_size': getattr(space, 'spacesSize', None)
                        }
                    }
                    
                    # Insert into database
                    try:
                        upsert_item(item_data)
                        logger.info(f"Inserted HF Space: {space_id}")
                        
                        # Queue for further processing
                        celery_app.send_task(
                            'src.agential_researcher.queue.tasks.summarize_task',
                            args=[space.description or f"Space: {space.id}", f"job_hf_space_{space.id}"],
                            queue='hot'
                        )
                        
                        new_entries += 1
                    except Exception as e:
                        logger.error(f"Failed to insert HF Space {space_id}: {e}")
                    
                    self.last_updated[space_id] = space.lastModified
            
            logger.info(f"Polled HF Spaces, found {new_entries} new/updated entries")
            
        except Exception as e:
            logger.error(f"Error polling HF Spaces: {e}")

    async def poll_all(self):
        """Poll all HF content types"""
        logger.info("Starting Hugging Face polling cycle...")
        
        while True:
            try:
                await self.poll_hf_models()
                await self.poll_hf_datasets()
                await self.poll_hf_spaces()
                
                # Wait before next polling cycle
                await asyncio.sleep(settings.arxiv_poll_interval * 10)  # HF doesn't need to be polled as frequently as arXiv
                
            except Exception as e:
                logger.error(f"Error in HF polling cycle: {e}")
                await asyncio.sleep(settings.arxiv_poll_interval * 10)  # Wait before retrying


def start_hf_poller():
    """Synchronous function to start the HF poller"""
    hf_ingester = HuggingFaceIngester()
    asyncio.run(hf_ingester.poll_all())

if __name__ == "__main__":
    start_hf_poller()