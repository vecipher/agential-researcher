import asyncio
import time
import logging
from typing import List, Dict, Any
import httpx
import json
from datetime import datetime

from ..config import settings
from ..queue.celery_app import celery_app
from ..store.db import upsert_item

logger = logging.getLogger(__name__)

class GitHubIngester:
    def __init__(self):
        self.last_processed = {}  # Track last processed timestamp per repo
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Agential-Researcher"
        }
        # Add auth header if token is available
        if hasattr(settings, 'github_token') and settings.github_token:
            self.headers["Authorization"] = f"token {settings.github_token}"

    async def poll_github_trending(self):
        """
        Poll GitHub trending repositories
        """
        logger.info("Polling GitHub for trending repositories...")
        
        try:
            async with httpx.AsyncClient() as client:
                # Get trending repositories for today
                url = f"https://api.github.com/search/repositories"
                params = {
                    "q": "created:>2024-01-01",  # Recent repos
                    "sort": "updated",
                    "order": "desc",
                    "per_page": settings.arxiv_max_results
                }
                
                response = await client.get(url, headers=self.headers, params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    new_entries = 0
                    
                    for repo in data.get('items', []):
                        repo_id = f"gh:repo:{repo['owner']['login']}/{repo['name']}"
                        
                        # Check if we've seen this repo before or if it's been updated
                        repo_updated = repo.get('updated_at', '')
                        if (repo_id not in self.last_processed or 
                            repo_updated > self.last_processed[repo_id]):
                            
                            logger.info(f"Found new/updated GitHub repo: {repo_id}")
                            
                            # Prepare item data
                            item_data = {
                                'id': repo_id,
                                'source': 'github',
                                'title': repo['full_name'],
                                'abstract': repo.get('description', '') or '',
                                'content': repo.get('description', ''),
                                'created_at': time.time(),
                                'metadata': {
                                    'owner': repo['owner']['login'],
                                    'name': repo['name'],
                                    'full_name': repo['full_name'],
                                    'description': repo.get('description', ''),
                                    'language': repo.get('language', ''),
                                    'stars': repo.get('stargazers_count', 0),
                                    'forks': repo.get('forks_count', 0),
                                    'issues': repo.get('open_issues_count', 0),
                                    'updated_at': repo.get('updated_at'),
                                    'created_at': repo.get('created_at'),
                                    'html_url': repo.get('html_url', ''),
                                    'clone_url': repo.get('clone_url', ''),
                                    'size': repo.get('size', 0),
                                    'default_branch': repo.get('default_branch', 'main')
                                }
                            }
                            
                            # Insert into database
                            try:
                                upsert_item(item_data)
                                logger.info(f"Inserted GitHub repo: {repo_id}")
                                
                                # Queue for further processing (summarization, embedding)
                                # Create a proper job in the database
                                from ..store.db import insert_job

                                # Create summarize job
                                summarize_job_id = f"job_sum_{repo['id']}_{int(time.time())}"
                                summarize_job_data = {
                                    'job_id': summarize_job_id,
                                    'job_type': 'summarize_github',
                                    'payload': {
                                        'repo_id': repo_id, 
                                        'content': repo.get('description', ''),
                                        'readme_url': f"{repo['html_url']}/blob/{repo.get('default_branch', 'main')}/README.md"
                                    },
                                    'priority': 10,  # High priority for new repos
                                    'status': 'pending',
                                    'progress': 0,
                                    'result': {},
                                    'created_at': time.time(),
                                }
                                insert_job(summarize_job_data)

                                # Send to Celery hot queue
                                celery_app.send_task(
                                    'src.agential_researcher.queue.tasks.summarize_task',
                                    args=[repo.get('description', ''), summarize_job_id],
                                    queue='hot'
                                )

                                # Create embed job
                                embed_job_id = f"job_emb_{repo['id']}_{int(time.time())}"
                                embed_job_data = {
                                    'job_id': embed_job_id,
                                    'job_type': 'embed_github',
                                    'payload': {
                                        'repo_id': repo_id, 
                                        'content': repo.get('description', ''),
                                        'repo_url': repo.get('html_url', '')
                                    },
                                    'priority': 10,  # High priority for new repos
                                    'status': 'pending',
                                    'progress': 0,
                                    'result': {},
                                    'created_at': time.time(),
                                }
                                insert_job(embed_job_data)

                                # Send to Celery hot queue
                                celery_app.send_task(
                                    'src.agential_researcher.queue.tasks.embed_task',
                                    args=[repo.get('description', ''), repo_id, embed_job_id],
                                    queue='hot'
                                )

                                new_entries += 1
                            except Exception as e:
                                logger.error(f"Failed to insert GitHub repo {repo_id}: {e}")

                            self.last_processed[repo_id] = repo_updated

                    logger.info(f"Polled GitHub, found {new_entries} new/updated repositories")
                else:
                    logger.error(f"GitHub API returned status {response.status_code}: {response.text}")
                    
        except Exception as e:
            logger.error(f"Error in GitHub polling: {e}")

    async def get_repo_readme(self, owner: str, repo: str) -> str:
        """
        Get README content for a repository
        """
        try:
            async with httpx.AsyncClient() as client:
                url = f"https://api.github.com/repos/{owner}/{repo}/readme"
                response = await client.get(url, headers=self.headers)
                
                if response.status_code == 200:
                    data = response.json()
                    # Return decoded content (base64 encoded in GitHub API)
                    import base64
                    content = base64.b64decode(data['content']).decode('utf-8')
                    return content
                else:
                    logger.warning(f"Could not fetch README for {owner}/{repo}: {response.status_code}")
                    return ""
        except Exception as e:
            logger.error(f"Error fetching README for {owner}/{repo}: {e}")
            return ""

    async def poll_all(self):
        """
        Main polling loop for GitHub integration
        """
        logger.info("Starting GitHub polling service...")
        
        while True:
            try:
                await self.poll_github_trending()
                
                # Wait before next polling cycle (respect rate limits)
                # GitHub has a rate limit of 10 requests per minute for unauthenticated requests
                await asyncio.sleep(settings.arxiv_poll_interval * 5)  # More conservative for GitHub
                
            except Exception as e:
                logger.error(f"Error in GitHub polling cycle: {e}")
                await asyncio.sleep(settings.arxiv_poll_interval * 10)  # Longer wait on error


def start_github_poller():
    """Synchronous function to start the GitHub poller"""
    github_ingester = GitHubIngester()
    asyncio.run(github_ingester.poll_all())


if __name__ == "__main__":
    start_github_poller()