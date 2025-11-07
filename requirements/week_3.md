# Week 3 Requirements - Webhooks, Security, Deploy

## Objective
Implement secure external integrations, production deployment setup, and command-line interface.

## Core Components

### 1. Webhook Integration
- Implement Hugging Face webhooks feeding into hot queue
- Implement GitHub webhooks feeding into hot queue
- Use APScheduler for nightly OAI-PMH backfill operations
- Implement outbox/inbox pattern for webhooks to avoid missed events
- Ensure retries are idempotent

### 2. Security Implementation
- API key authentication with per-route scopes
- CORS policy locked down appropriately
- Rate limiting on public API edge
- Implement sandbox for untrusted LLM-generated code (nsjail/gVisor/Firecracker)
- Egress allow-list to daemon only
- Secrets management via environment/manager; never log tokens

### 3. Deployment Infrastructure
- Reverse proxy with TLS (Traefik/Nginx)
- Production-ready deployment configuration
- Proper service orchestration and monitoring

### 4. Command-Line Interface
- Typer CLI that mirrors API functionality
- `--open` flag to pop files in OS file explorer
- Consistent with API surface design

## Acceptance Criteria
- [ ] Public API accessible behind TLS with proper certificates
- [ ] 401 Unauthorized responses behave correctly for invalid API keys
- [ ] 429 Rate Limit responses behave correctly when limits exceeded
- [ ] Backfill operations complete within 24 hours
- [ ] Webhooks successfully trigger processing
- [ ] CLI provides equivalent functionality to API endpoints

## Key Design Decisions
- Rate limits: Use ETag/If-None-Match (GitHub), Hub webhooks (HF), arXiv 3-sec cadence
- No IP rotation; instead use backoff + jitter; centralized quota monitor
- Security: API keys + per-route scopes; CORS locked down; rate limiting on public edge
- Sandboxing: nsjail/gVisor/Firecracker for untrusted code execution

## Metrics to Monitor
- API request rates and error rates
- Webhook processing success rates
- Rate limit hit frequency
- Backfill operation duration