# Agential Researcher - Week 1 Completion Summary

## Overview
This document summarizes the implementation status for Week 1 requirements: "Spine Online".

## Completed Components

### 1. Repository and Configuration Baseline
- ✅ Project structure with proper configuration management
- ✅ SQLite FTS5 for lexical search capabilities
- ✅ LanceDB schemas for vector embeddings
- ✅ Version control for configuration and schema

### 2. Queue System
- ✅ RabbitMQ with priority queues
- ✅ Queue priorities:
  - `hot` (priority 10): arXiv/HF/GH new → summarize → embed → link
  - `backfill` (priority 1): historical ingestion & reindex
  - `vlm_ocr` (priority 5): PDF OCR/VLM pages
  - `maintenance` (priority 2): nightly KG recompute, compaction
- ✅ Celery workers for: ingest, summarize, embed, vlm_ocr, kg_link, reindex

### 3. FastAPI Daemon
- ✅ `/health` endpoint: returns provider status, queue depths
- ✅ `/enqueue` endpoint: accepts {type, payload, priority} → returns {job_id}
- ✅ `/status/{job_id}` endpoint: returns {state, progress, output_ref}

### 4. Data Polling Systems
- ✅ arXiv poller with 3-second cadence
- ✅ Hugging Face list monitoring (based on lastModified timestamps)
- ✅ GitHub repository polling
- ✅ All systems wired to hot queue for priority processing

### 5. Language Model Infrastructure
- ✅ vLLM text server integration
- ✅ OpenAI-compatible router with:
  - vLLM as primary provider
  - Ollama as fallback provider
  - Startup health probes to detect provider status
  - Automatic failover between providers

### 6. Basic Pipeline
- ✅ ingest → summarize → embed pipeline implemented
- ✅ Database export functionality (CSV/XLS) implemented

## Week 1 Acceptance Criteria

All acceptance criteria have been met:

- ✅ Ingest → summarize → embed pipeline processes first batch successfully
- ✅ Prometheus metrics show TTFT (Time to First Token) and TPS (Tokens Per Second)
- ✅ CSV/XLS export functionality works from database
- ✅ Queue system prioritizes hot jobs over backfill
- ✅ API endpoints respond correctly
- ✅ Health checks accurately report system status
- ✅ Provider failover works between vLLM and Ollama

## Key Design Decisions Implemented

- Providers: vLLM on GPU for throughput; Ollama on CPU for convenience
- Storage: SQLite FTS5 (BM25) + LanceDB (embeddings)
- One OpenAI-style router with startup probes and clean failover
- Queue priority: hot always preempts backfill; VLM/OCR on separate worker

## Metrics Being Monitored

- TTFT (p50/p95)
- Tokens/sec aggregate
- Queue wait time
- arXiv request cadence (3-sec rule compliance)

## Next Steps (Week 2)

The system is ready to move to Week 2 requirements focusing on PDFs, VLM, and ranking.