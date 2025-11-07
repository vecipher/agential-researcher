import typer
import requests
import json
from typing import Optional
import webbrowser
import os
from pathlib import Path

from ..config import settings

app = typer.Typer()

# Default API URL (can be overridden by environment variable)
API_URL = os.getenv("API_URL", f"http://localhost:{settings.api_port}")


def get_headers():
    """Get default headers with API key if available"""
    headers = {"Content-Type": "application/json"}
    if settings.api_keys and settings.api_keys[0] != "sk-...":
        headers["Authorization"] = f"Bearer {settings.api_keys[0]}"
    return headers


@app.command()
def health():
    """Check the health status of the system"""
    try:
        response = requests.get(f"{API_URL}/health", headers=get_headers())
        if response.status_code == 200:
            health_data = response.json()
            print(f"Status: {health_data.get('status', 'unknown')}")
            print("Providers:")
            for provider, status in health_data.get('providers', {}).items():
                print(f"  {provider}: {status}")
            print("Queues:")
            for queue, depth in health_data.get('queues', {}).items():
                print(f"  {queue}: {depth}")
        else:
            print(f"Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Error connecting to API: {e}")


@app.command()
def enqueue(
    job_type: str = typer.Argument(..., help="Type of job to enqueue"),
    payload: str = typer.Argument(..., help="JSON payload for the job"),
    priority: int = typer.Option(10, "--priority", "-p", help="Priority (1-10)")
):
    """Enqueue a new job for processing"""
    try:
        payload_json = json.loads(payload)
        data = {
            "type": job_type,
            "payload": payload_json,
            "priority": priority
        }
        
        response = requests.post(f"{API_URL}/v1/enqueue", json=data, headers=get_headers())
        if response.status_code == 200:
            result = response.json()
            print(f"Job enqueued successfully: {result['job_id']}")
        else:
            print(f"Error: {response.status_code} - {response.text}")
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON payload: {payload}")
    except Exception as e:
        print(f"Error connecting to API: {e}")


@app.command()
def status(job_id: str = typer.Argument(..., help="Job ID to check status for")):
    """Check the status of a specific job"""
    try:
        response = requests.get(f"{API_URL}/v1/status/{job_id}", headers=get_headers())
        if response.status_code == 200:
            result = response.json()
            print(f"Job ID: {result['job_id']}")
            print(f"State: {result['state']}")
            print(f"Progress: {result['progress']}%")
            if result.get('output_ref'):
                print(f"Output: {result['output_ref']}")
            print(f"Created: {result.get('created_at', 'N/A')}")
            print(f"Completed: {result.get('completed_at', 'N/A')}")
        else:
            print(f"Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Error connecting to API: {e}")


@app.command()
def search(
    query: str = typer.Argument(..., help="Search query"),
    limit: int = typer.Option(10, "--limit", "-l", help="Maximum results to return")
):
    """Search for items in the database"""
    try:
        params = {"query": query, "limit": limit}
        response = requests.get(f"{API_URL}/v1/search", params=params, headers=get_headers())
        if response.status_code == 200:
            result = response.json()
            print(f"Found {result.get('total_hits', 0)} results for query: '{query}'")
            for i, item in enumerate(result.get('results', []), 1):
                print(f"{i}. {item.get('title', 'No title')}")
                print(f"   ID: {item.get('id', 'N/A')}")
                print(f"   Source: {item.get('source', 'N/A')}")
                print(f"   Summary: {item.get('summary', '')[:100]}...")
                print()
        else:
            print(f"Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Error connecting to API: {e}")


@app.command()
def export_csv(
    item_type: str = typer.Option("items", "--type", "-t", help="Type of data to export (items/jobs)"),
    limit: int = typer.Option(1000, "--limit", "-l", help="Maximum items to export"),
    source: Optional[str] = typer.Option(None, "--source", "-s", help="Filter by source"),
    open_file: bool = typer.Option(False, "--open", help="Open the exported file after creation")
):
    """Export data to CSV format"""
    try:
        params = {"item_type": item_type, "limit": limit}
        if source:
            params["source"] = source
            
        response = requests.get(f"{API_URL}/v1/export/csv", params=params, headers=get_headers())
        if response.status_code == 200:
            result = response.json()
            file_path = result.get('file', '')
            print(f"Exported {item_type} to: {file_path}")
            
            if open_file and file_path:
                abs_path = Path(file_path).resolve()
                if abs_path.exists():
                    webbrowser.open(f'file://{abs_path}')
                    print(f"Opened {abs_path} in file explorer")
                else:
                    print(f"Could not find file: {abs_path}")
        else:
            print(f"Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Error connecting to API: {e}")


@app.command()
def export_xlsx(
    limit: int = typer.Option(1000, "--limit", "-l", help="Maximum items to export"),
    source: Optional[str] = typer.Option(None, "--source", "-s", help="Filter by source"),
    open_file: bool = typer.Option(False, "--open", help="Open the exported file after creation")
):
    """Export data to Excel format"""
    try:
        params = {"limit": limit}
        if source:
            params["source"] = source
            
        response = requests.get(f"{API_URL}/v1/export/xlsx", params=params, headers=get_headers())
        if response.status_code == 200:
            result = response.json()
            file_path = result.get('file', '')
            print(f"Exported items to: {file_path}")
            
            if open_file and file_path:
                abs_path = Path(file_path).resolve()
                if abs_path.exists():
                    webbrowser.open(f'file://{abs_path}')
                    print(f"Opened {abs_path} in file explorer")
                else:
                    print(f"Could not find file: {abs_path}")
        else:
            print(f"Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Error connecting to API: {e}")


@app.command()
def arxiv_poll():
    """Trigger arXiv polling (admin function)"""
    try:
        response = requests.post(f"{API_URL}/v1/ingest/arxiv", headers=get_headers())
        if response.status_code == 200:
            result = response.json()
            print(f"arXiv polling triggered. Job ID: {result.get('job_id', 'N/A')}")
        else:
            print(f"Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Error connecting to API: {e}")


@app.command()
def ingest_content(
    title: str = typer.Option(..., "--title", "-t", help="Title of the content"),
    abstract: str = typer.Option("", "--abstract", "-a", help="Abstract of the content"),
    content: str = typer.Option(..., "--content", "-c", help="Full content"),
    source: str = typer.Option("manual", "--source", "-s", help="Source identifier")
):
    """Ingest specific content with full pipeline: content → summarize → embed"""
    try:
        payload = {
            "title": title,
            "abstract": abstract,
            "content": content,
            "source": source
        }
        
        response = requests.post(f"{API_URL}/v1/ingest/content", json=payload, headers=get_headers())
        if response.status_code == 200:
            result = response.json()
            print(f"Content ingested with ID: {result.get('item_id', 'N/A')}")
            print(f"Summarize job: {result.get('summarize_job_id', 'N/A')}")
            print(f"Embed job: {result.get('embed_job_id', 'N/A')}")
        else:
            print(f"Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Error connecting to API: {e}")


@app.command()
def root():
    """Show API root information"""
    try:
        response = requests.get(f"{API_URL}/", headers=get_headers())
        if response.status_code == 200:
            result = response.json()
            print(f"Agential Researcher API")
            print(f"Version: {result.get('version', 'N/A')}")
            print(f"Message: {result.get('message', 'N/A')}")
        else:
            print(f"Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Error connecting to API: {e}")


if __name__ == "__main__":
    app()