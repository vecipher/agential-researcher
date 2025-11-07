# Agential Researcher Operator Guide

This guide provides instructions for operating and maintaining the Agential Researcher system.

## System Overview

The Agential Researcher system consists of multiple services that work together:

- **API**: Main entry point for all requests
- **Queue System**: RabbitMQ message broker
- **Workers**: Celery workers processing different types of jobs
- **LLM Providers**: vLLM and Ollama for inference
- **Database**: SQLite for metadata and LanceDB for embeddings
- **Monitoring**: Prometheus and Grafana for observability

## Starting and Stopping the System

### Development Environment

To start the development environment:

```bash
make dev-up
```

To stop the system:

```bash
make dev-down
```

To view logs:

```bash
make dev-logs
```

### Production Environment

For production deployments, use the docker-compose directly:

```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# Check status of all services
docker-compose ps
```

## Queue Management

### Queue Priorities

The system uses four priority queues:

1. **Hot (Priority 10)**: New arXiv/HF/GH entries → high priority processing
2. **VLM/OCR (Priority 5)**: PDF OCR and visual processing
3. **Backfill (Priority 1)**: Historical data ingestion
4. **Maintenance (Priority 2)**: Cleanup and recompute operations

### Queue Monitoring

Monitor queue depths through:
- Grafana dashboard: "Queue Depths" panel
- RabbitMQ management UI: `http://localhost:15672` (guest/guest)
- API health endpoint: Shows queue depths in the response

### Queue Troubleshooting

If queues become backed up:

1. Check the RabbitMQ management UI for any dead letters
2. Verify worker processes are running with `docker-compose ps`
3. Review worker logs with `docker-compose logs worker-*`
4. If needed, scale up workers: `docker-compose up --scale worker-hot=2`

## Dashboards and Monitoring

### Accessing Dashboards

Grafana dashboard: `http://localhost:3000` (admin/admin)
Prometheus: `http://localhost:9090`

### Key Metrics to Monitor

#### Performance Metrics
- **TTFT (Time to First Token)**: Should be < 1 second for 7B models
- **Tokens/sec**: Monitor for throughput requirements
- **Queue wait time**: Should be < 5 seconds for hot queue
- **API response times**: Should be < 200ms for simple operations

#### System Health
- **Service availability**: All services should show as UP
- **GPU utilization**: Monitor for both text and VLM models
- **Disk space**: Monitor SQLite and LanceDB storage
- **Memory usage**: Especially for embedding operations

### Setting Up Alerts

Key alerts to configure:

1. Queue depth > threshold for hot queue
2. API response time > 1 second
3. GPU utilization > 90% for extended periods
4. Service downtime > 30 seconds
5. Database connection errors

## Routine Issues and Solutions

### Common Issues

#### Issue: "Both LLM providers failed"
**Cause**: vLLM or Ollama services are down or misconfigured
**Solution**: 
1. Check `docker-compose logs vllm-text` and `docker-compose logs ollama`
2. Verify GPU access if using GPU-accelerated models
3. Ensure models are downloaded and loaded

#### Issue: Queue Backlog
**Cause**: Workers can't keep up with incoming requests
**Solution**:
1. Scale up worker instances
2. Check for slow-running tasks
3. Verify resource availability (GPU, memory, disk)

#### Issue: High Memory Usage
**Cause**: Large embedding operations or many concurrent tasks
**Solution**:
1. Implement resource quotas for batch operations
2. Reduce concurrent processing limits
3. Check for memory leaks in processing tasks

#### Issue: Rate Limiting
**Cause**: Exceeded configured rate limits
**Solution**:
1. Adjust rate limiting configuration in settings
2. Implement rate limiting at the client level
3. Monitor rate limit metrics

### Scheduled Maintenance

#### Daily Tasks
- Monitor queue depths and processing times
- Check service availability and error rates
- Review logs for any anomalies

#### Weekly Tasks
- Review system performance metrics
- Check database growth and optimize if needed
- Update model versions if required
- Backup database (see backup strategy below)

#### Monthly Tasks
- Review and tune performance parameters
- Update dependencies and security patches
- Review usage patterns and adjust capacity

## Backup and Restore

### Database Backup

SQLite database backup:
```bash
docker-compose exec api cp data/agential_researcher.db /backup/agential_researcher_$(date +%Y%m%d).db
```

### Database Restore

To restore from backup:
```bash
docker-compose stop api
docker cp /path/to/backup/agential_researcher.db agential-researcher-api:/app/data/agential_researcher.db
docker-compose start api
```

### Data Retention

- Processed items: Retained indefinitely
- Job audit trail: Retained for 30 days
- Logs: Retained for 7 days
- Temporary processing artifacts: Retained for 24 hours

## Scaling Guidelines

### Vertical Scaling
- **CPU/Memory**: Increase resources based on queue depth and processing times
- **GPU**: Add more GPU resources for increased inference throughput
- **Storage**: Monitor SQLite and LanceDB growth

### Horizontal Scaling
- **API instances**: Scale based on request volume
- **Workers**: Scale specific worker types based on queue types
- **vLLM/Ollama**: Run multiple instances for different models

### Performance Tuning
- **Batch sizes**: Adjust based on GPU memory and performance
- **Concurrent processing**: Tune based on resource availability
- **Cache sizes**: Adjust for frequently accessed data

## Security Considerations

### API Keys
- Rotate API keys regularly
- Monitor API key usage
- Implement proper access controls

### Network Security
- Restrict access to internal services
- Use TLS for all external communications
- Implement proper firewall rules

### Data Security
- Encrypt sensitive data at rest
- Secure model outputs and intermediate results
- Implement proper data retention policies

## Troubleshooting

### Service Debugging

Check service status:
```bash
docker-compose ps
```

View service logs:
```bash
docker-compose logs api
docker-compose logs rabbitmq
docker-compose logs worker-hot
```

Access service shells:
```bash
make shell-api
make shell-worker
```

### Database Debugging

Access SQLite database:
```bash
make db-shell
```

Check database health:
```sql
PRAGMA integrity_check;
```

### Performance Debugging

Profile API performance:
```bash
# Add performance monitoring middleware
# Monitor specific endpoints for bottlenecks
```

Monitor resource usage:
```bash
docker stats
```

## Contact and Support

For issues not covered in this guide:
- Development team: development@agential-researcher.com
- Production issues: ops@agential-researcher.com
- Security issues: security@agential-researcher.com