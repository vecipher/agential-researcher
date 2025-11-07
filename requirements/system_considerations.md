# System Architecture Considerations

This document addresses key architectural decisions and considerations raised during planning, including offline/online systems, compute optimization, storage choices, and sandboxing requirements.

## Offline vs. Online Systems

### Online System Components
The online system handles real-time requests and must maintain high availability:

#### Real-time Processing
- arXiv poller with 3-second cadence
- Hugging Face and GitHub webhook processing
- Hot queue processing for immediate results
- API endpoints for user interactions
- Search and retrieval operations

#### Requirements for Online System
- Must maintain 99.9% availability during peak hours
- Sub-second response times for search operations
- Immediate processing of high-priority content
- Real-time health monitoring and alerting

### Offline System Components
The offline system handles batch processing, heavy computation, and maintenance:

#### Batch Processing
- Historical backfill operations
- Heavy VLM/OCR reprocessing of scraped data
- Knowledge graph refreshment and recomputation
- Database maintenance and optimization
- Quality assessment and validation

#### Requirements for Offline System
- Scheduled batch processing during off-peak hours
- Efficient resource utilization during computation-heavy tasks
- Automated scheduling for maintenance operations
- Ability to pause/continue operations based on system load
- Proper resource isolation from online components

### Synchronization Strategy
- Use consistent data models between online and offline systems
- Implement change data capture to keep both systems synchronized
- Allow offline processing to update online system data
- Implement proper conflict resolution for concurrent updates

## Compute Optimization Strategy

### Current Compute Resources
- 5090 GPU for vLLM throughput
- M2 for Ollama convenience
- Plans for potentially increasing compute limits

### Compute Usage Maximization
#### Resource Scheduling
- Dynamic scheduling based on online/offline priorities
- GPU reservation systems to prevent resource conflicts
- Time-shifting of non-critical tasks to low-demand periods
- Load balancing across available compute resources

#### Heavy Processing Considerations
- VLM/OCR reprocessing during low-demand periods
- Batch processing of large datasets when system load is low
- Implementation of compute quotas to prevent resource exhaustion
- Monitoring of GPU utilization and thermal conditions

#### Compute Scaling Strategy
- Plan for increasing compute limits as needed
- Containerization to enable easy scaling
- Auto-scaling policies for different workload types
- Cost optimization through spot instances or on-demand scheduling

## Storage Architecture Decision

### SQLite vs. LanceDB Considerations

#### SQLite FTS5 Benefits
- Simple deployment and management
- ACID properties and transactional integrity
- Proven performance for text search
- Lower resource requirements
- Easy backup and migration

#### LanceDB Benefits
- Optimized for vector similarity search
- Better performance for embedding operations
- Built-in vector indexing
- Designed for ML workloads
- Better scalability for embeddings

#### Hybrid Approach Recommendation
- Continue with SQLite FTS5 for BM25 lexical search
- Mainline LanceDB for vector embeddings
- Use SQLite for metadata and text search
- Use LanceDB for semantic similarity and vector operations
- Implement data synchronization between both systems

#### Migration Strategy
- Phase 1: Implement dual storage (SQLite + LanceDB)
- Phase 2: Optimize queries for each storage type
- Phase 3: Plan for future scaling if needed (PostgreSQL + pgvector)

## Coding Sandbox Architecture

### Isolated Environment Requirements
- Docker-based containerization for security
- Resource limits to prevent sandbox escape
- Network isolation to prevent unauthorized access
- File system isolation to prevent host system access

### Sandbox Features
- Dynamic code execution for data analysis
- APIs to storage layers (SQLite + LanceDB)
- Integration with LLM daemons for code generation
- Visualization capabilities for data presentation
- Safe execution of user-generated code

### Security Implementation
- Use container security best practices (non-root users, read-only root)
- Implement resource quotas (CPU, memory, disk)
- Network policy enforcement
- File system access controls
- Regular container image updates and vulnerability scanning

### Integration Points
- Direct APIs to storage layer for data access
- Integration with worker queue for long-running processes
- Secure communication with main application
- Authentication and authorization for sandbox access

## Tri-Layered System Architecture

### Layer 1: Scraper Daemon
#### Components
- arXiv poller with 3-second cadence
- Hugging Face and GitHub webhook processors
- External API integrations
- Content download and validation

#### Responsibilities
- Monitor external sources for new content
- Download and validate content
- Queue content for processing
- Track source health and availability
- Implement rate limiting and ToS compliance

#### Performance Requirements
- Low-latency source monitoring
- Efficient content downloading
- Proper deduplication and validation
- Error handling and retry logic

### Layer 2: Task Queue System
#### Components
- RabbitMQ with priority queues
- Celery worker processes
- Ollama daemon for local inference
- vLLM daemon for high-throughput inference

#### Responsibilities
- Process content through ingestion pipeline
- Manage priority-based job execution
- Interface with LLM daemons for processing
- Handle failures and retries
- Monitor queue health and performance

#### Scaling Considerations
- Dynamic worker scaling based on queue depth
- Load balancing across multiple inference engines
- Resource isolation between different processing types
- Priority-based preemption for critical tasks

### Layer 3: LLM Daemons
#### Components
- vLLM for high-throughput inference (5090 GPU)
- Ollama for local convenience (M2)
- OpenAI-compatible router with failover
- Inference optimization and batching

#### Responsibilities
- Process inference requests from queue system
- Manage model loading and unloading
- Optimize inference performance
- Handle model versioning and updates

#### Performance Requirements
- High throughput for batch processing
- Low latency for real-time requests
- Efficient GPU utilization
- Auto-scaling based on demand

### API and Interface Layer
#### Components
- FastAPI application
- CLI interface via Typer
- External hosting for internet access
- Authentication and rate limiting

#### Responsibilities
- Expose system functionality to users
- Integrate all three layers
- Manage authentication and authorization
- Provide monitoring and health checks
- Handle API rate limiting and quotas

## Alignment and Integration Considerations

### System Integration Points
- APIs between all three layers
- Shared configuration management
- Consistent monitoring and logging
- Cross-layer health checks
- Unified authentication

### Performance Alignment
- Ensure each layer can keep up with the others
- Implement proper backpressure mechanisms
- Monitor and optimize bottlenecks
- Plan for scaling individual layers independently

### Maintenance and Operations
- Automated deployment pipelines
- Rolling updates to minimize downtime
- Comprehensive monitoring and alerting
- Disaster recovery and backup procedures
- Regular security updates and patching

## Implementation Roadmap

### Phase 1: Foundation
- Implement core tri-layered architecture
- Basic scraper daemon with priority queues
- Minimal LLM integration with vLLM/Ollama
- Essential API endpoints

### Phase 2: Offline Systems
- Batch processing capabilities
- Heavy VLM/OCR operations
- Knowledge graph recomputation
- Maintenance automation

### Phase 3: Sandbox and Advanced Features
- Isolated coding sandbox implementation
- Advanced search and retrieval
- Enhanced monitoring and optimization
- Security hardening

### Phase 4: Scaling and Optimization
- Compute optimization and scaling
- Performance tuning
- Advanced sandbox capabilities
- Production-hardened deployment