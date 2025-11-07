# Queue Topology and Worker Specifications

## Overview
The system uses RabbitMQ with a topic exchange and multiple priority queues to handle different types of processing jobs. This document details the queue configuration, worker responsibilities, and routing patterns.

## Exchange Configuration

### Topic Exchange: `jobs.topic`
- Type: Topic exchange for flexible routing
- Durability: Durable
- Auto-delete: False

## Queue Configuration

### 1. Hot Queue (`hot`)
- **Priority**: 10 (highest)
- **Purpose**: High-priority, time-sensitive jobs
- **Routing Key Pattern**: `hot.*`
- **Target Jobs**: 
  - arXiv new entries → summarize → embed → link
  - HuggingFace new entries → summarize → embed → link
  - GitHub new entries → summarize → embed → link
  - Webhook-triggered processing
- **Consumer**: All worker types may consume from this queue first
- **Message TTL**: 1 hour (to prevent stale jobs)
- **Max Length**: 1000 messages (with dead lettering)

### 2. Backfill Queue (`backfill`)
- **Priority**: 1 (lowest)
- **Purpose**: Historical data ingestion and bulk operations
- **Routing Key Pattern**: `backfill.*`
- **Target Jobs**:
  - Historical arXiv backfill
  - Bulk reindexing operations
  - Historical GitHub/HF data ingestion
- **Consumer**: Backfill-specific workers or general workers when hot queue is empty
- **Message TTL**: 24 hours
- **Max Length**: 10000 messages

### 3. VLM/OCR Queue (`vlm_ocr`)
- **Priority**: 5 (medium)
- **Purpose**: Visual Language Model and OCR processing
- **Routing Key Pattern**: `vlm_ocr.*`
- **Target Jobs**:
  - PDF OCR operations
  - VLM figure/table processing
  - Image analysis tasks
- **Consumer**: Specialized VLM/OCR workers
- **Message TTL**: 4 hours
- **Max Length**: 100 messages (GPU-bound, prevent overloading)

### 4. Maintenance Queue (`maintenance`)
- **Priority**: 2 (low)
- **Purpose**: System maintenance and housekeeping operations
- **Routing Key Pattern**: `maintenance.*`
- **Target Jobs**:
  - Nightly KG recomputation
  - Database compaction
  - Cleanup operations
  - Schema migrations
- **Consumer**: Maintenance workers or general workers during low load
- **Message TTL**: 48 hours
- **Max Length**: 1000 messages

## Dead Letter Queue (`jobs.dead`)

- **Purpose**: Capture failed messages that exceeded retry attempts
- **Consumer**: Manual redrive process
- **Message TTL**: 7 days (to allow for debugging and manual redriving)

## Worker Specifications

### 1. Ingest Worker (`ingest_worker`)
- **Primary Queue**: `hot` (first priority), `backfill` (second priority)
- **Responsibilities**:
  - Fetch raw data from sources (arXiv, HuggingFace, GitHub)
  - Validate and sanitize data
  - Prepare content for summarization
- **Resource Requirements**: Moderate CPU, Network
- **Concurrency**: 2-4 processes depending on queue depth

### 2. Summarize Worker (`summarize_worker`)
- **Primary Queue**: `hot` (first priority), `backfill` (second priority)
- **Responsibilities**:
  - Generate content summaries using LLM
  - Extract key information from documents
  - Prepare content for embedding
- **Resource Requirements**: GPU (for LLM inference), Memory
- **Concurrency**: 1-2 processes (GPU-bound)

### 3. Embed Worker (`embed_worker`)
- **Primary Queue**: `hot` (first priority), `backfill` (second priority)
- **Responsibilities**:
  - Generate vector embeddings for content
  - Store embeddings in LanceDB
  - Update search indices
- **Resource Requirements**: GPU (for embedding model), Memory
- **Concurrency**: 1-2 processes (GPU-bound)

### 4. VLM/OCR Worker (`vlm_ocr_worker`)
- **Primary Queue**: `vlm_ocr`
- **Responsibilities**:
  - Process PDFs with OCR for text extraction
  - Analyze figures and tables with VLM
  - Generate image descriptions
- **Resource Requirements**: GPU (for VLM/OCR), High Memory
- **Concurrency**: 1 process (GPU-bound, prevent overloading)

### 5. KG Link Worker (`kg_link_worker`)
- **Primary Queue**: `hot` (first priority), `maintenance` (second priority)
- **Responsibilities**:
  - Build knowledge graph edges
  - Compute similarity relationships
  - Update graph database
- **Resource Requirements**: Moderate CPU, High Memory
- **Concurrency**: 1-2 processes

### 6. Reindex Worker (`reindex_worker`)
- **Primary Queue**: `backfill`, `maintenance`
- **Responsibilities**:
  - Recompute search indices
  - Update embeddings for changed content
  - Perform bulk maintenance operations
- **Resource Requirements**: High Memory, Moderate CPU
- **Concurrency**: 1-2 processes

## Message Structure

All queue messages follow this JSON structure:

```json
{
  "job_id": "unique_job_identifier",
  "job_type": "ingest_arxiv|summarize_content|embed_content|ocr_pdf|etc",
  "priority": 10,
  "payload": {
    // Job-specific data
  },
  "metadata": {
    "created_at": "2025-11-07T09:00:00Z",
    "source": "arxiv|github|huggingface|user",
    "attempts": 0,
    "max_attempts": 3
  }
}
```

## Retry Policy

### Exponential Backoff
- Initial delay: 5 seconds
- Multiplier: 2 (doubles each attempt)
- Max delay: 5 minutes
- Max attempts: 3

### Retry Conditions
- Non-2xx HTTP responses from external services
- Network timeouts
- Processing errors
- Resource exhaustion (GPU/CPU)

### Failover Logic
- Messages that exceed max attempts are sent to dead letter queue
- Dead letter queue allows for manual inspection and redriving
- Failed jobs can be retried with modified parameters

## Queue Management

### Monitoring
- Queue depths for each priority level
- Processing rates for each worker type
- Error rates and failure patterns
- Consumer lag metrics

### Scaling
- Worker instances can be scaled based on queue depth
- Priority-based consumption ensures hot jobs are processed first
- Auto-scaling based on processing metrics

### Maintenance
- Regular cleanup of expired messages
- Queue length monitoring with alerts
- Performance tuning based on usage patterns