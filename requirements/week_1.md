# Week 1 Requirements - Spine Online

## Objective
Establish the foundational infrastructure and basic pipeline for the agential researcher system.

## Core Components

### 1. Repository and Configuration Baseline
- Set up project structure with proper configuration management
- Implement SQLite FTS5 for lexical search capabilities
- Implement LanceDB schemas for vector embeddings
- Version control for configuration and schema (CONFIG_VERSION=v1)

### 2. Queue System
- Configure RabbitMQ with priority queues
- Implement following queue priorities:
  - `hot` (priority 10): arXiv/HF/GH new → summarize → embed → link
  - `backfill` (priority 1): historical ingestion & reindex
  - `vlm_ocr` (priority 5): PDF OCR/VLM pages
  - `maintenance` (priority 2): nightly KG recompute, compaction
- Implement Celery workers for: ingest, summarize, embed, vlm_ocr, kg_link, reindex

### 3. FastAPI Daemon
- Implement `/health` endpoint: returns provider status, queue depths
- Implement `/enqueue` endpoint: accepts {type, payload, priority} → returns {job_id}
- Implement `/status/{job_id}` endpoint: returns {state, progress, output_ref}

### 4. Data Polling Systems
- Implement arXiv poller with 3-second cadence
- Implement Hugging Face list monitoring (based on lastModified timestamps)
- Wire both systems to hot queue for priority processing

### 5. Language Model Infrastructure
- Set up vLLM text server with 7B model
- Implement OpenAI-compatible router with:
  - vLLM as primary provider
  - Ollama as fallback provider
  - Startup health probes to detect provider status
  - Automatic failover between providers

### 6. Basic Pipeline
- Implement ingest → summarize → embed pipeline
- Ensure first batch can be processed successfully
- Implement database export functionality (CSV/XLS)

## Acceptance Criteria
- [ ] Ingest → summarize → embed pipeline processes first batch successfully
- [ ] Prometheus metrics show TTFT (Time to First Token) and TPS (Tokens Per Second)
- [ ] CSV/XLS export functionality works from database
- [ ] Queue system prioritizes hot jobs over backfill
- [ ] API endpoints respond correctly
- [ ] Health checks accurately report system status
- [ ] Provider failover works between vLLM and Ollama

## Key Design Decisions
- Providers: vLLM on GPU for throughput; Ollama on CPU for convenience
- Storage: SQLite FTS5 (BM25) + LanceDB (embeddings)
- One OpenAI-style router with startup probes and clean failover
- Queue priority: hot always preempts backfill; VLM/OCR on separate worker

## Metrics to Monitor
- TTFT (p50/p95)
- Tokens/sec aggregate
- Queue wait time
- arXiv request cadence (3-sec rule compliance)