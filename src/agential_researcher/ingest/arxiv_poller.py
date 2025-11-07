"""
arXiv Poller Module - Provides continuous polling functionality with 3-second cadence
"""
import asyncio
import time
import logging
from typing import List, Dict, Any
import feedparser
import httpx
from datetime import datetime, timedelta

from ..config import settings
from ..queue.celery_app import celery_app
from ..store.db import upsert_item

logger = logging.getLogger(__name__)

async def poll_arxiv():
    """
    arXiv poller with 3-second cadence - this is the main polling loop
    """
    logger.info("Starting arXiv poller with 3-second cadence...")

    last_poll_time = time.time()
    last_entries = {}

    while True:
        try:
            # Respect arXiv 3-second cadence
            time_since_last_poll = time.time() - last_poll_time
            if time_since_last_poll < settings.arxiv_poll_interval:
                await asyncio.sleep(settings.arxiv_poll_interval - time_since_last_poll)

            logger.info("Polling arXiv for new entries...")

            # Query arXiv for recent papers in CS category
            async with httpx.AsyncClient() as client:
                # Example: Get recent papers in computer science
                url = f"http://export.arxiv.org/api/query?search_query=cat:cs.AI&sortBy=lastUpdatedDate&sortOrder=descending&max_results={settings.arxiv_max_results}"
                response = await client.get(url)

                if response.status_code != 200:
                    logger.error(f"arXiv API returned status {response.status_code}")
                    continue

                # Parse the Atom feed
                feed = feedparser.parse(response.text)

                new_entries = 0
                for entry in feed.entries:
                    # Create a unique ID without version
                    arxiv_id = entry.id.split("/")[-1].split("v")[0]  # Remove version suffix
                    entry_key = f"arxiv:{arxiv_id}"

                    # Check if this is a new entry since last poll
                    if entry_key not in last_entries:
                        logger.info(f"Found new arXiv entry: {entry_key}")

                        # Prepare item data
                        item_data = {
                            'id': entry_key,
                            'source': 'arxiv',
                            'title': entry.title,
                            'abstract': entry.summary,
                            'content': entry.summary,  # For now, use abstract as content
                            'created_at': time.time(),
                            'metadata': {
                                'authors': [author.name for author in entry.authors],
                                'published': entry.published,
                                'updated': entry.updated,
                                'arxiv_id': arxiv_id,
                                'categories': [tag.term for tag in entry.tags] if hasattr(entry, 'tags') else []
                            }
                        }

                        # Insert into database
                        try:
                            upsert_item(item_data)
                            logger.info(f"Inserted arXiv entry: {entry_key}")

                            # Queue for further processing (summarization, embedding)
                            # Create a proper job in the database
                            from ..store.db import insert_job

                            # Create summarize job
                            summarize_job_id = f"job_sum_{arxiv_id}_{int(time.time())}"
                            summarize_job_data = {
                                'job_id': summarize_job_id,
                                'job_type': 'summarize_arxiv',
                                'payload': {'arxiv_id': arxiv_id, 'content': entry.summary},
                                'priority': 10,  # Hot queue priority
                                'status': 'pending',
                                'progress': 0,
                                'result': {},
                                'created_at': time.time(),
                            }
                            insert_job(summarize_job_data)

                            # Send to Celery
                            celery_app.send_task(
                                'src.agential_researcher.queue.tasks.summarize_task',
                                args=[entry.summary, summarize_job_id],
                                queue='hot'
                            )

                            # Create embed job
                            embed_job_id = f"job_emb_{arxiv_id}_{int(time.time())}"
                            embed_job_data = {
                                'job_id': embed_job_id,
                                'job_type': 'embed_arxiv',
                                'payload': {'arxiv_id': arxiv_id, 'content': entry.summary},
                                'priority': 10,  # Hot queue priority
                                'status': 'pending',
                                'progress': 0,
                                'result': {},
                                'created_at': time.time(),
                            }
                            insert_job(embed_job_data)

                            # Send to Celery
                            celery_app.send_task(
                                'src.agential_researcher.queue.tasks.embed_task',
                                args=[entry.summary, entry_key, embed_job_id],
                                queue='hot'
                            )

                            new_entries += 1
                        except Exception as e:
                            logger.error(f"Failed to insert arXiv entry {entry_key}: {e}")

                    last_entries[entry_key] = entry.updated

                logger.info(f"Polled arXiv, found {new_entries} new entries")

            last_poll_time = time.time()

        except Exception as e:
            logger.error(f"Error in arXiv poller: {e}")
            await asyncio.sleep(settings.arxiv_poll_interval)  # Wait before retrying


def start_arxiv_poller():
    """Synchronous function to start the arXiv poller"""
    asyncio.run(poll_arxiv())


if __name__ == "__main__":
    start_arxiv_poller()