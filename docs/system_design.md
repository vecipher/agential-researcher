# Comprehensive System Design: Agential Researcher

## Executive Summary

This document outlines the comprehensive system design for the agential researcher system, incorporating all architectural decisions, risk considerations, and implementation strategies. The system follows a tri-layered architecture with offline/online processing separation, optimized compute utilization, dual storage approach, and secure coding sandbox.

## System Overview

### Core Objectives
1. Real-time monitoring and processing of research content from arXiv, Hugging Face, and GitHub
2. Advanced search and retrieval with both lexical and semantic capabilities
3. Knowledge graph construction and maintenance
4. Secure, isolated environment for dynamic code execution and data analysis
5. Scalable architecture optimized for both online and offline processing

### Key Design Principles
- Separation of online (real-time) and offline (batch) processing
- Compute optimization with planned expansion capabilities
- Dual storage system (SQLite FTS5 + LanceDB) for different access patterns
- Containerized security sandbox for code execution
- Tri-layered architecture for clear separation of concerns

## Architecture Layers

### Layer 1: Scraper Daemon
#### Components
- arXiv Poller: Monitors arXiv API with 3-second cadence
- Hugging Face Webhook Handler: Processes HF model/dataset updates
- GitHub Webhook Handler: Processes repository updates
- Content Validator: Verifies content integrity and format
- Priority Queue Publisher: Routes content to appropriate queues

#### Offline vs. Online Split
- **Online**: Real-time webhook processing, immediate queue placement
- **Offline**: Historical backfill operations, scheduled bulk processing

#### Performance Requirements
- arXiv compliance: 3-second minimum between requests
- Webhook processing: <5 second latency from receipt to queue placement
- Content validation: <2 second processing time per document

### Layer 2: Task Queue System
#### Components
- RabbitMQ Broker: Priority queue management
- Celery Workers: Distributed processing tasks
- Ollama Daemon: Local LLM inference
- vLLM Daemon: High-throughput GPU inference on 5090
- Router: Load balancing between inference engines

#### Queue Hierarchy
1. **Hot Queue (Priority 10)**: Real-time processing from webhooks
2. **VLM/OCR Queue (Priority 5)**: Visual processing tasks
3. **Maintenance Queue (Priority 2)**: Recomputation, cleanup tasks
4. **Backfill Queue (Priority 1)**: Historical data processing

#### Resource Management
- Online processing: Guaranteed minimum resource allocation
- Offline processing: Best-effort scheduling during low-demand periods
- GPU quota management: Maximum 60% utilization during online operations
- Auto-scaling: Dynamic worker adjustment based on queue depth

### Layer 3: LLM Daemons and API Interface
#### Components
- vLLM Service: High-throughput inference on 5090 GPU
- Ollama Service: Local inference on M2
- Router Service: OpenAI-compatible API with failover
- FastAPI Application: Primary API endpoints
- CLI Interface: Command-line access via Typer

#### Compute Optimization
- Planned expansion: Ability to increase compute limits when permitted
- Load balancing: Intelligent routing based on model type and current load
- Resource isolation: Separate processes for text vs. VLM models
- Performance optimization: Batch scheduling and quantization

## Storage Architecture

### Dual Storage System
#### SQLite FTS5 (Lexical Search)
- Purpose: BM25 text search, metadata storage, transactional operations
- Schema: Document metadata, user data, configuration
- Performance: Optimized for text search and ACID operations
- Backup: Standard database backup procedures

#### LanceDB (Vector Storage)
- Purpose: Embedding storage, semantic similarity search
- Schema: Document embeddings, vector indices
- Performance: Optimized for vector operations and similarity search
- Maintenance: Compaction and snapshot procedures

### Data Synchronization
- Consistent IDs across both systems
- Change data capture for real-time synchronization
- Atomic operations where cross-storage consistency is critical
- Conflict resolution procedures for concurrent updates

### Migration Strategy
- Phase 1: Dual storage implementation
- Phase 2: Query optimization and performance tuning
- Phase 3: Scaling preparation (PostgreSQL + pgvector if needed)

## Offline vs. Online Systems

### Online System (Real-time)
#### Components
- Real-time API endpoints
- Hot queue processing
- Immediate search and retrieval
- Live webhook processing
- High-availability services

#### Performance Requirements
- 99.9% uptime during peak hours
- <200ms response time for search operations
- <1 second for content retrieval
- Immediate webhook processing (<5 seconds)

#### Resource Allocation
- Guaranteed minimum resources for online operations
- Auto-scaling based on demand
- Load shedding during resource constraints

### Offline System (Batch Processing)
#### Components
- Historical backfill operations
- Heavy VLM/OCR reprocessing
- Knowledge graph refreshment and recomputation
- Database maintenance operations
- Quality assessment and validation

#### Scheduling Strategy
- Off-peak execution: 11 PM - 6 AM (configurable)
- Resource quotas: Maximum 40% of total compute during online hours
- Dynamic scheduling: Pause if online system is stressed
- Completion guarantees: Resumable operations for long-running tasks

#### Heavy Processing Tasks
1. **VLM/OCR Reprocessing**: Retrospective analysis of existing documents
2. **Knowledge Graph Recomputation**: Periodic centrality and relationship updates
3. **Embedding Regeneration**: Re-computation with updated models
4. **Quality Validation**: Retrieval accuracy and summary quality assessment

## Coding Sandbox Architecture

### Isolation Strategy
#### Containerization
- Docker-based isolation for each code execution
- Non-root user execution within containers
- Resource limits (CPU, memory, disk, network)
- Read-only filesystem where possible

#### Security Controls
- Network isolation with limited egress
- File system isolation from host system
- Time limits for execution (prevents infinite loops)
- Input validation for all code and parameters

### Integration Points
#### Storage Layer APIs
- Secure, authenticated access to SQLite and LanceDB
- Query validation and sanitization
- Rate limiting for data access
- Audit logging for all operations

#### Functionality
- Dynamic code generation for analysis
- Data visualization capabilities
- Statistical analysis and modeling
- Report generation

### Safety Mechanisms
- Code execution sandboxing
- Resource quota enforcement
- Network traffic monitoring
- Regular security updates

## Compute Optimization Strategy

### Current Resources
- **5090 GPU**: Primary for vLLM high-throughput inference
- **M2 CPU**: Secondary for Ollama local inference
- **System Memory**: Adequate for model loading and data processing

### Planned Expansion
- Compute limit increases when infrastructure permits
- GPU scaling for increased VLM/OCR capacity
- Memory expansion for larger embedding models
- Storage scaling for increased document corpus

### Optimization Techniques
- Model quantization (AWQ/INT4) for memory efficiency
- Batch size optimization for throughput
- Model caching to reduce loading times
- Intelligent model selection based on task requirements

### Workload Distribution
- Real-time requests: Primary vLLM on 5090
- Offline processing: Scheduling during low-demand periods
- Fallback processing: Ollama for secondary inference
- Auto-scaling: Dynamic resource allocation based on demand

## Risk Management and Mitigation

### High-Priority Risks
1. **Resource Contention**: Mitigated through quotas and scheduling
2. **Security Breaches**: Mitigated through isolation and validation
3. **Service Availability**: Mitigated through redundancy and failover
4. **Data Consistency**: Mitigated through atomic operations and validation

### Monitoring and Alerting
- Resource utilization (CPU, GPU, memory, disk)
- Queue depths and processing times
- Service availability and response times
- Security events and sandbox activities
- Data consistency and integrity checks

## Implementation Roadmap

### Phase 1: Foundation (Weeks 1-2)
- Core tri-layered architecture implementation
- Basic offline/online system separation
- Dual storage setup (SQLite + LanceDB)
- Essential API endpoints and CLI

### Phase 2: Processing Enhancement (Weeks 3-4)
- Advanced queue management
- Offline processing scheduling
- VLM/OCR capabilities
- Initial knowledge graph implementation

### Phase 3: Security and Analysis (Weeks 5-6)
- Coding sandbox implementation
- Security hardening
- Advanced search and retrieval
- Performance optimization

### Phase 4: Scale and Optimize (Weeks 7-8)
- Compute optimization and scaling
- Production deployment
- Advanced monitoring and alerting
- Performance tuning and validation

## Success Metrics

### Performance Metrics
- Online system: <200ms average response time
- Queue processing: <30 second average time to completion
- Search accuracy: >90% relevant results in top 5
- System availability: >99.9% uptime

### Operational Metrics
- Resource utilization: <80% average during peak hours
- Security events: Zero successful sandbox escapes
- Data consistency: 100% cross-storage synchronization
- Error rates: <0.1% for all operations

### Business Metrics
- Content processing throughput: 1000+ documents per hour
- Search quality: User satisfaction >4.5/5.0
- System scalability: Handle 10x increase in load
- Development velocity: Feature deployment time <24 hours