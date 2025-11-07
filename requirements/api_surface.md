# API Surface Documentation

## Overview
The agential researcher system provides a comprehensive API surface for both internal operations and external integration.

## Health and Status Endpoints

### GET /health
Returns the current status of system components.

**Response:**
```json
{
  "status": "healthy",
  "providers": {
    "vllm": "healthy",
    "ollama": "degraded",
    "sqlite": "healthy",
    "lancedb": "healthy",
    "rabbitmq": "healthy"
  },
  "queues": {
    "hot_depth": 0,
    "backfill_depth": 5,
    "vlm_ocr_depth": 2,
    "maintenance_depth": 1
  },
  "timestamp": "2025-11-07T09:00:00Z"
}
```

## Job Management Endpoints

### POST /enqueue
Enqueues a new job for processing with specified type, payload, and priority.

**Request:**
```json
{
  "type": "ingest_arxiv",
  "payload": {
    "id": "2103.00020",
    "source": "arxiv"
  },
  "priority": 10
}
```

**Response:**
```json
{
  "job_id": "job_1234567890"
}
```

### GET /status/{job_id}
Gets the status of a specific job.

**Response:**
```json
{
  "job_id": "job_1234567890",
  "state": "completed",
  "progress": 100,
  "output_ref": "/results/job_1234567890.json",
  "created_at": "2025-11-07T09:00:00Z",
  "completed_at": "2025-11-07T09:02:15Z"
}
```

## Ingestion Endpoints

### POST /ingest/arxiv
Triggers immediate arXiv backfill or polling (admin-gated).

**Request:**
```json
{
  "query": "cs.AI",
  "max_results": 100,
  "start_date": "2025-11-01"
}
```

**Response:**
```json
{
  "job_id": "job_ingest_arxiv_123"
}
```

## PDF Processing Endpoints

### POST /pdf/parse
Parse and store markdown from a PDF.

**Request:**
```json
{
  "pdf_url": "https://arxiv.org/pdf/2103.00020.pdf",
  "id": "arxiv:2103.00020"
}
```

**Response:**
```json
{
  "job_id": "job_pdf_parse_123",
  "parsed_content_ref": "/content/arxiv_2103.00020.md"
}
```

### POST /ocr/run
Perform targeted OCR on specific pages or regions.

**Request:**
```json
{
  "pdf_url": "https://arxiv.org/pdf/2103.00020.pdf",
  "page_ranges": [[3, 5]],
  "regions": [{"page": 4, "bbox": [100, 100, 500, 200]}]
}
```

**Response:**
```json
{
  "job_id": "job_ocr_123",
  "ocr_results_ref": "/ocr/ocr_results_123.json"
}
```

## Graph and Knowledge Endpoints

### POST /graph/link
Build knowledge graph edges for specified IDs.

**Request:**
```json
{
  "ids": ["arxiv:2103.00020", "arxiv:2012.05671"],
  "link_types": ["similar", "cites"]
}
```

**Response:**
```json
{
  "job_id": "job_graph_link_123",
  "edges_created": 5
}
```

## Focus System Endpoints

### POST /focus/run
Execute a focus YAML specification.

**Request:**
```yaml
# This would be sent as text in the request body
name: "daily_ai_research"
topics:
  - "large language models"
  - "transformer architecture"
date_window: "last_24h"
max_results: 10
rank_threshold: 0.7
```

**Response:**
```json
{
  "job_id": "job_focus_123",
  "results_ref": "/focus/daily_ai_research_2025-11-07.json",
  "result_count": 8
}
```

## Language Model Endpoints

### POST /v1/chat/completions
OpenAI-compatible endpoint that proxies to vLLM with Ollama fallback.

**Request:**
```json
{
  "model": "llm-model",
  "messages": [
    {"role": "user", "content": "Summarize this paper..."}
  ],
  "temperature": 0.7
}
```

**Response:**
```json
{
  "id": "chat_12345",
  "object": "chat.completion",
  "created": 1730974800,
  "model": "llm-model",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "The paper discusses..."
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 50,
    "completion_tokens": 100,
    "total_tokens": 150
  }
}
```

## Search Endpoints

### GET /search
Perform lexical and vector fusion search.

**Query Parameters:**
- `q`: Search query
- `limit`: Number of results (default: 10)
- `offset`: Pagination offset (default: 0)
- `min_score`: Minimum relevance score (default: 0.0)

**Response:**
```json
{
  "query": "attention mechanism transformers",
  "results": [
    {
      "id": "arxiv:1706.03762",
      "title": "Attention Is All You Need",
      "abstract": "The dominant sequence transduction models...",
      "score": 0.95,
      "source": "arxiv",
      "published_date": "2017-06-12"
    }
  ],
  "total_hits": 1,
  "execution_time_ms": 45
}
```

## Authentication and Rate Limiting

All endpoints (except `/health`) require API key authentication via the `Authorization` header:

```
Authorization: Bearer YOUR_API_KEY
```

Rate limits are enforced per API key, with different limits for different endpoint categories.

## Error Handling

All endpoints return appropriate HTTP status codes:

- 200: Success
- 201: Created
- 400: Bad Request (invalid parameters)
- 401: Unauthorized (missing/invalid API key)
- 404: Not Found
- 429: Too Many Requests (rate limited)
- 500: Internal Server Error
- 503: Service Unavailable (temporary overload)

Error responses follow this format:

```json
{
  "error": {
    "type": "invalid_request_error",
    "message": "The request parameters were invalid...",
    "code": "invalid_parameters"
  }
}
```