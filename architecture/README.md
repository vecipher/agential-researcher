# Technical Architecture

This document outlines the technical architecture for the agential researcher system.

## High-Level Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   External      │    │   API Gateway    │    │  Queue System   │
│   Sources       │───▶│   (FastAPI)      │───▶│  (RabbitMQ)     │
│                 │    │                  │    │                 │
│ • arXiv         │    │ • /health        │    │ • hot (prio 10) │
│ • HuggingFace   │    │ • /enqueue       │    │ • backfill      │
│ • GitHub        │    │ • /status        │    │   (prio 1)      │
│ • Webhooks      │    │ • /search        │    │ • vlm_ocr       │
└─────────────────┘    │ • /v1/chat/      │    │   (prio 5)      │
                       │   completions    │    │ • maintenance   │
                       └──────────────────┘    │   (prio 2)      │
                              │                └─────────────────┘
                              │                           │
                              ▼                           ▼
                    ┌──────────────────┐        ┌─────────────────┐
                    │  Processing      │───────▶│    Workers      │
                    │  Workers         │        │  (Celery)       │
                    │                  │        │                 │
                    │ • ingest         │        │ • ingest        │
                    │ • summarize      │        │ • summarize     │
                    │ • embed          │        │ • embed         │
                    │ • vlm_ocr        │        │ • vlm_ocr       │
                    │ • kg_link        │        │ • kg_link       │
                    │ • reindex        │        │ • reindex       │
                    └──────────────────┘        └─────────────────┘
                              │
                              ▼
                    ┌──────────────────┐    ┌─────────────────┐
                    │  Storage Layer   │    │  Coding         │
                    │                  │    │  Sandbox        │
                    │ • SQLite FTS5    │    │  (Docker)       │
                    │   (BM25 search)  │    │                 │
                    │ • LanceDB        │    │ • Dynamic code  │
                    │   (embeddings)   │    │   execution     │
                    └──────────────────┘    │ • Data analysis │
                                            │ • Visualization │
                                            └─────────────────┘
                                                    │
                                                    ▼
                    ┌──────────────────┐    ┌─────────────────┐
                    │  LLM Daemons     │───▶│ Computing       │
                    │                  │    │ Resources       │
                    │ • vLLM (5090)    │    │                 │
                    │ • Ollama (M2)    │    │ • 5090 GPU      │
                    │ • Router with    │    │ • M2 CPU        │
                    │   failover       │    │ • Future        │
                    └──────────────────┘    │   expansion     │
```

## Offline vs. Online Systems

### Online System (Real-time Processing)
- API Gateway handles real-time requests
- Hot queue processing for immediate results
- Real-time search and retrieval
- Live webhook processing
- High availability with 99.9% uptime requirement

### Offline System (Batch Processing)
- Backfill queue for historical processing
- Heavy VLM/OCR reprocessing
- Knowledge graph refreshment and recomputation
- Database maintenance operations
- Scheduled batch jobs during off-peak hours

## Tri-Layered System Architecture

### Layer 1: Scraper Daemon
- arXiv poller with 3-second cadence
- Hugging Face and GitHub webhook processors
- Content download and validation
- Priority queuing to hot queue

### Layer 2: Task Queue System
- RabbitMQ with priority queues (hot, backfill, vlm_ocr, maintenance)
- Celery workers for distributed processing
- Ollama daemon for local inference
- vLLM daemon for high-throughput inference

### Layer 3: LLM Daemons and API Interface
- vLLM for high-throughput inference (on 5090 GPU)
- Ollama for convenience (on M2)
- OpenAI-compatible router with failover
- FastAPI for API endpoints and CLI interface

## System Components

### 1. API Gateway (FastAPI)

#### Endpoints
- `GET /health` - Returns provider status, queue depths
- `POST /enqueue` - Accepts {type, payload, priority} → returns {job_id}
- `GET /status/{job_id}` - Returns {state, progress, output_ref}
- `POST /ingest/arxiv` - Backfill/poll now (admin-gated)
- `POST /pdf/parse` - Parse & store markdown
- `POST /ocr/run` - Targeted OCR (page ranges/regions)
- `POST /graph/link` - Build edges for IDs
- `POST /focus/run` - Executes a focus YAML spec
- `POST /v1/chat/completions` - OpenAI-compat proxy → vLLM (fallback: Ollama)
- `GET /search` - Lexical+vector fusion query

#### Security
- API key authentication with per-route scopes
- CORS policy configuration
- Rate limiting implementation
- TLS termination with reverse proxy

### 2. Queue System (RabbitMQ)

#### Queue Configuration
- **Exchange**: jobs.topic
- **Queues**:
  - `hot` (priority 10): arXiv/HF/GH new → summarize → embed → link
  - `backfill` (priority 1): historical ingestion & reindex
  - `vlm_ocr` (priority 5): PDF OCR/VLM pages
  - `maintenance` (priority 2): nightly KG recompute, compaction

#### Retry Policy
- Exponential backoff for failed jobs
- Dead-letter queue for failed jobs with redrive policy
- Idempotent operations to prevent duplicate processing

### 3. Processing Workers (Celery)

#### Worker Types
- **ingest**: Handles initial data ingestion from various sources
- **summarize**: Processes content to create summaries
- **embed**: Generates vector embeddings for search
- **vlm_ocr**: Processes visual content with VLM models
- **kg_link**: Builds knowledge graph edges
- **reindex**: Handles reindexing and maintenance operations

#### Resource Management
- Separate vLLM instances for text vs VLM processing
- GPU utilization thresholds to prevent starvation
- Background processing only when system load is low

### 4. Storage Layer

#### SQLite FTS5 (Lexical Search)
- BM25 scoring for text relevance
- Full-text search capabilities
- Schema versioning for safe migrations

#### LanceDB (Vector Search)
- Embedding storage and similarity search
- Vector index optimization
- Schema versioning and migration support

### 5. Language Model Infrastructure

#### Provider Routing
- OpenAI-compatible router with vLLM primary
- Ollama fallback for availability
- Startup health probes to detect provider status
- Automatic failover between providers

#### Minimal Router Contract
- On boot: 1-token /v1/chat/completions probe to each provider
- If primary fails and secondary passes, swap
- Per call: try primary; on non-2xx or timeout, try secondary
- If both fail, return single explicit error with both causes

## Data Flow Patterns

### 1. Ingestion Pipeline
```
Source → Enqueue (hot queue) → Ingest worker → Summarize worker → Embed worker → Store
```

### 2. PDF Processing
```
PDF Download → Nougat/Marker → DeepSeek-OCR (fallback) → Qwen-VL (figures only) → Store
```

### 3. Search Pipeline
```
Query → Fusion Rank (z(BM25) + z(cosine)) → Threshold Filter → Results
```

### 4. Knowledge Graph Building
```
Content IDs → Similarity Check → Topical Analysis → Edge Creation → Graph Store
```

## Monitoring and Observability

### Metrics to Track
- TTFT (p50/p95) - Time to First Token
- Tokens/sec aggregate
- Queue wait time
- Drop rate from rank thresholds
- OCR/VLM GPU utilization
- arXiv request cadence (3-sec rule compliance)
- Queue depths and lag metrics

### Tracing
- End-to-end tracing for job chains (ingest→summarize→embed→link)
- Performance bottlenecks identification
- Error correlation across services

## Configuration Management

### Versioning Strategy
- CONFIG_VERSION for configuration schema
- SCHEMA_VERSION for database schemas
- SUMMARY_VERSION and EMBED_MODEL for content processing
- Forward-only migrations with clear Definition of Done

### Environment Configuration
- Environment variable-based configuration
- Secure secrets management
- Service discovery and health checking