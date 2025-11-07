# Week 4 Requirements - KG Edges, Focus DSL, Ops

## Objective
Implement knowledge graph functionality, declarative focus system, and operational dashboards.

## Core Components

### 1. Knowledge Graph (KG) Edges
- Implement similar(cos) edges based on cosine similarity
- Implement topical(tags) edges based on topic modeling
- Prepare for coauthor edges (when OpenAlex integration is added)
- Typed edges: similar, topical, coauthor (later), cites (when OpenAlex added)
- Periodic recompute of centrality metrics

### 2. Focus Domain-Specific Language (DSL)
- Create YAML-based Focus DSL
- Support topics/tags/date windows specifications
- Implement `/focus/run` endpoint that compiles DSL to filters and executes
- Focus DSL is declarative (topics/tags/windows)
- LLM planner can only emit filters you can execute
- Guardrails: planner can enqueue jobs but not mutate config

### 3. Operational Dashboards
- Grafana dashboards for queue lag, TTFT, tokens/sec
- Alerting system for operational metrics
- Maturity charts showing "snapshot KG metrics"
- Operational visibility into system performance

### 4. Continuous Operations
- Daily focus digest emitting top K items
- System stability under burst loads
- Performance monitoring and alerting

## Acceptance Criteria
- [ ] Daily focus digest successfully emits top K items based on DSL
- [ ] Dashboards remain stable under burst load conditions
- [ ] Knowledge graph edges are accurate and meaningful
- [ ] Focus DSL correctly compiles to executable filters
- [ ] Alerts trigger appropriately for operational issues
- [ ] System handles sustained high load without degradation

## Key Design Decisions
- Knowledge Graph: Typed edges system with periodic recomputation
- Focus DSL: Declarative approach with execution guards
- Operational: Grafana dashboards with comprehensive monitoring
- Failure modes: Provider health probes with automatic failover

## Metrics to Monitor
- Queue lag (p50/p95)
- TTFT (p50/p95) with alerting
- Tokens/sec aggregate with alerting
- KG centrality metrics and maturity indicators
- Focus digest quality and relevance