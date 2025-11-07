# Project Guardrails

This document establishes the critical guardrails and best practices to follow during the development of the agential researcher system. These guardrails are designed to prevent common issues and ensure consistent, maintainable code.

## ID & Deduplication Guardrails

### Canonical ID Format
- Use consistent ID patterns across all sources:
  - arXiv: `arxiv:<id>` (e.g., `arxiv:2103.00020`)
  - Hugging Face Model: `hf:model:<owner>/<name>` (e.g., `hf:model:mistralai/Mistral-7B`)
  - Hugging Face Dataset: `hf:dataset:<owner>/<name>` (e.g., `hf:dataset:bigscience/P3`)
  - GitHub Repository: `gh:repo:<owner>/<repo>` (e.g., `gh:repo:pytorch/pytorch`)
  - DOI when present: `doi:<identifier>` (e.g., `doi:10.1145/3292500.3330972`)

### arXiv ID Handling
- Strip arXiv version suffixes for identity (e.g., `2103.00020v1` → `2103.00020`)
- Store version history separately in metadata
- Always use the canonical ID for deduplication

### Content Hashing
- Generate content hashes for PDFs, READMEs, and other content
- Implement idempotent upserts everywhere (check hash before processing)
- Use SHA-256 for content integrity verification

## Schema & Versioning Guardrails

### Configuration Versioning
- Pin `CONFIG_VERSION` and `SCHEMA_VERSION` constants
- Implement forward-only migrations with clear Definition of Done (DoD)
- Document schema changes with version numbers and migration procedures
- Never break backward compatibility without proper versioning

### Content Versioning
- Store `summary_version` and `embed_model` for each processed item
- Only re-run summarization/embedding when version actually changes
- Maintain content history for debugging and reproducibility

## Rate Limiting & Terms of Service Guardrails

### API Usage Policy
- Always use official APIs before considering scraping
- Implement conditional requests using ETag/If-None-Match for GitHub
- Use Hugging Face webhooks instead of polling when available
- Maintain arXiv 3-second cadence as per their ToS
- Never implement IP rotation - use backoff and jitter instead

### Quota Management
- Implement centralized quota monitoring
- Use exponential backoff with jitter for rate-limited APIs
- Log quota usage for capacity planning
- Implement circuit breakers to prevent API abuse

## Queues & Backpressure Guardrails

### Queue Management
- Implement hard caps on queue lengths to prevent system overload
- Use priority lanes: hot > vlm/ocr > backfill > maintenance
- Implement "archive only" mode when backlogged
- Use dead-letter queue with redrive policy for failed messages
- Monitor queue health continuously

### Resource Management
- Prevent GPU starvation by separating VLM/OCR from text processing
- Only run background OCR when hot queue < N items and GPU < 60% utilization
- Implement resource quotas for different worker types
- Schedule heavy offline processing (VLM/OCR reprocessing, KG recomputation) during off-peak hours
- Ensure offline processing doesn't impact online system performance
- Plan for increasing compute limits when permitted to handle heavy workloads

## GPU Planning Guardrails

### Resource Allocation
- Run one model per vLLM process to prevent resource conflicts
- Use separate servers for text vs VLM processing
- Implement quantization policy (e.g., AWQ/INT4) per model
- Set batch size ceilings per model to prevent GPU OOM

### Performance Optimization
- Monitor GPU utilization and adjust worker counts accordingly
- Implement proper warm-up procedures for GPU models
- Test performance with different batch sizes and concurrency levels

## Quality & Evaluation Guardrails

### Testing Requirements
- Maintain a small golden set for TL;DR prompt evaluation
- Implement regression tests for summary length, coverage, and hallucination detection
- Create retrieval sanity tests where top-K must contain known neighbors
- Use deterministic seeds for ranker tests to ensure reproducibility

### Quality Metrics
- Monitor summary quality against baseline scores
- Track retrieval accuracy metrics continuously
- Implement early warning for quality degradation

## Search & Ranking Guardrails

### Fusion Ranking
- Implement proper z-score normalization for BM25 and cosine scores
- Keep tunable thresholds τ1/τ2 per focus area
- Support field boosts (title > abstract > content)
- Consider language tags for analyzer selection

### Performance Considerations
- Optimize for both precision and recall
- Implement early dropping for low-ranked items to save resources
- Monitor search performance under different load conditions

## Knowledge Graph Guardrails

### Edge Types
- Implement typed edges: similar, topical, coauthor, cites
- Plan for periodic recomputation of centrality metrics
- Create snapshot metrics for "maturity" charts
- Validate edge consistency and accuracy regularly

### Graph Maintenance
- Schedule regular graph validation tasks
- Implement graph compaction and optimization
- Monitor graph growth and performance

## PDF Pipeline Guardrails

### Processing Order
- Follow: Nougat/Marker → OCR fallback → VLM for figures only
- Target specific pages/regions to avoid whole-document VLM runs
- Optimize for processing time vs accuracy trade-offs
- Handle various PDF types and quality levels appropriately

### Content Extraction
- Preserve document structure during parsing
- Extract metadata and references properly
- Handle embedded images and tables separately

## Security & Isolation Guardrails

### Access Control
- Implement API keys with per-route scopes
- Lock down CORS policy appropriately
- Implement rate limiting on public endpoints
- Use proper authentication for admin routes

### Code Execution Safety
- Sandbox untrusted LLM-generated code using nsjail/gVisor/Firecracker
- Implement egress allow-list to daemon only
- Never execute arbitrary code from LLM outputs without validation

### Secrets Management
- Store secrets via environment variables or secret manager
- Never log API tokens or sensitive information
- Use proper secret rotation procedures
- Implement secret validation at startup

## Observability Guardrails

### Metrics Collection
- Monitor queue depth, TTFT, tokens/sec, error rates continuously
- Implement distributed tracing for job chains (ingest→summarize→embed→link)
- Set up alerts for lag and failure spikes
- Track external API request cadence (e.g., arXiv 3-sec rule)

### Logging Standards
- Log at appropriate levels (DEBUG, INFO, WARN, ERROR)
- Include correlation IDs for tracing requests
- Avoid logging sensitive information
- Structure logs consistently for analysis

## Testing & CI Guardrails

### Test Strategy
- Only run offline tests (no network calls in CI)
- Create fixtures for API payloads and PDF samples
- Implement performance smoke tests on target hardware
- Use deterministic seeds for test reproducibility

### Quality Gates
- Require passing tests before merge
- Implement performance benchmarks as quality gates
- Check code coverage metrics
- Validate schema compatibility in tests

## Storage Operations Guardrails

### Database Management
- Use SQLite FTS5 for lexical search (BM25) alongside LanceDB for vector embeddings
- Implement dual storage approach: SQLite for metadata/text search, LanceDB for semantic similarity
- Implement LanceDB compaction and snapshot procedures
- Set retention policies for raw artifacts (PDF cache TTL)
- Handle schema migrations safely with data validation
- Plan for synchronization between SQLite and LanceDB systems
- Maintain data consistency between online and offline processing systems

### Data Consistency
- Use transactions where data consistency is critical
- Implement data integrity checks
- Validate data before writing to storage
- Handle database connection pooling properly

## Focus/Planner Guardrails

### DSL Safety
- Keep Focus DSL declarative (topics/tags/windows only)
- Only allow LLM planner to emit filters you can execute
- Implement guardrails: planner can enqueue jobs but not mutate config
- Validate DSL syntax before execution

### Execution Safety
- Sanitize focus queries before execution
- Implement query limits to prevent resource exhaustion
- Validate parameter ranges and constraints

## Failure Mode Guardrails

### Resilience
- Implement health probes for provider availability
- Design automatic failover between vLLM↔Ollama
- Use outbox/inbox pattern for webhooks to avoid missed events
- Make all retries idempotent to prevent duplication

### Error Handling
- Implement proper error propagation with context
- Use circuit breakers to prevent cascading failures
- Log errors with sufficient context for debugging
- Return meaningful error messages to clients

## UX & Operations Guardrails

### User Experience
- Create minimal triage dashboard showing last 48h activity
- Show drops vs keeps, top topics, and GPU utilization
- Implement CLI `--open` flag to launch local files
- Provide clear error surfaces when providers are down

### Operational Clarity
- Document error conditions and remediation steps
- Provide clear operational metrics and dashboards
- Create runbooks for common operational tasks
- Implement proper service health indicators

## Coding Sandbox Guardrails

### Security Implementation
- Use Docker containerization with non-root users for all sandbox operations
- Implement strict resource limits (CPU, memory, disk, network) for each sandbox instance
- Apply network isolation with limited egress capabilities to essential services only
- Implement file system isolation to prevent host system access
- Regular security scanning of container images before deployment
- Time limits for code execution to prevent infinite loops or resource exhaustion
- Input validation for all code executed in the sandbox environment

### Integration Safety
- Secure APIs to storage layers with proper authentication and authorization
- Validate all data access requests from sandbox to prevent unauthorized data exposure
- Implement audit logging for all sandbox activities
- Limit sandbox access to necessary data only
- Regular updates and patching of sandbox environment

## Legal/Ethics Guardrails

### Compliance
- Respect robots.txt and site terms of service
- Attribute sources properly in all outputs
- Store and respect licenses from Hugging Face cards
- Avoid scraping endpoints that prohibit automated access
- Consider copyright and fair use implications

### Ethical Considerations
- Implement bias detection in model outputs
- Provide transparency about data sources and processing
- Consider privacy implications of scraped content
- Be transparent about AI system capabilities and limitations

## Pre-Flight Checklist for Releases

Before each release, verify:

### Functionality
- [ ] All API endpoints return expected responses
- [ ] Queue system handles priority correctly
- [ ] Ingest→summarize→embed pipeline completes successfully
- [ ] Search returns relevant results
- [ ] All external service integrations work
- [ ] Security features (auth, rate limiting) are functional

### Performance
- [ ] System handles expected load without degradation
- [ ] Response times meet SLA requirements
- [ ] Resource utilization is within limits
- [ ] GPU utilization is optimized
- [ ] Database queries perform adequately

### Reliability
- [ ] Error handling works correctly
- [ ] Failover mechanisms function properly
- [ ] Backup and recovery procedures are tested
- [ ] Monitoring and alerting are working
- [ ] Log aggregation functions correctly

### Security
- [ ] API authentication is enforced
- [ ] Input validation prevents injection attacks
- [ ] Sensitive data is not exposed in logs
- [ ] Secrets are properly managed
- [ ] Rate limiting functions properly

### Compliance
- [ ] Terms of service are respected
- [ ] Rate limits are properly implemented
- [ ] Data handling is compliant with policies
- [ ] Attribution requirements are met
- [ ] Copyright considerations are addressed