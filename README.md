# Agential Researcher

An intelligent system for monitoring, analyzing, and processing research content from arXiv, Hugging Face, and other sources.

## Status: Week 1 Complete - Spine Online

✅ **Week 1 Accomplishments**:
- Ingest → summarize → embed pipeline processes first batch successfully
- Prometheus metrics show TTFT (Time to First Token) and TPS (Tokens Per Second)
- CSV/XLS export functionality works from database
- Queue system prioritizes hot jobs over backfill
- API endpoints respond correctly
- Health checks accurately report system status
- Provider failover works between vLLM and Ollama

## Architecture

The system follows a tri-layered architecture:

1. **Scraper Daemon Layer**: Monitors external sources (arXiv, Hugging Face, GitHub)
2. **Task Queue System Layer**: Processes content through priority queues using Celery and RabbitMQ
3. **LLM Daemons and API Interface Layer**: Provides LLM inference and API endpoints

## Features

- Real-time monitoring of arXiv, Hugging Face models/datasets/spaces
- Intelligent content processing with LLM summarization and embedding
- Priority-based queue system (hot, backfill, VLM/OCR, maintenance)
- Dual storage (SQLite FTS5 + LanceDB) for lexical and semantic search
- vLLM/Ollama provider routing with automatic failover
- Comprehensive observability with Prometheus and Grafana
- Secure API with key authentication and rate limiting

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.9+
- For GPU acceleration: NVIDIA GPU with CUDA support

### Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd agential-researcher
```

2. Create environment file:
```bash
cp .env.template .env
# Edit .env with your configuration
```

3. Start the development environment:
```bash
make dev-up
```

4. Initialize the database:
```bash
make db-bootstrap
```

### Services

After starting, the following services will be available:

- API: `http://localhost:8080`
- RabbitMQ Management: `http://localhost:15672` (guest/guest)
- Grafana: `http://localhost:3000` (admin/admin)
- Prometheus: `http://localhost:9090`

## Development

### Running Tests

```bash
make test
```

### Code Formatting

```bash
make format
```

### Linting

```bash
make lint
```

### Development Commands

```bash
# View logs
make dev-logs

# Stop development environment
make dev-down

# Access API container shell
make shell-api
```

## API Endpoints

### Health
- `GET /health` - Health check (requires API key)
- `GET /.well-known/health` - Public health check (no auth)

### Jobs
- `POST /v1/enqueue` - Enqueue a processing job
- `GET /v1/status/{job_id}` - Get job status

### Ingestion
- `POST /v1/ingest/arxiv` - Trigger arXiv backfill
- `POST /v1/pdf/parse` - Parse PDF content
- `POST /v1/ocr/run` - Run OCR on documents
- `POST /v1/graph/link` - Create knowledge graph links
- `POST /v1/focus/run` - Execute focus specification
- `GET /v1/search` - Search content

## Configuration

The system is configured through environment variables in `.env`:

- `API_KEYS`: Comma-separated list of valid API keys
- `BROKER_URL`: RabbitMQ connection string
- `VLLM_URL`: vLLM service endpoint
- `OLLAMA_URL`: Ollama service endpoint
- `SQLITE_PATH`: Path to SQLite database
- `LANCEDB_PATH`: Path to LanceDB directory

## Security

- API key authentication required for all endpoints except `/.well-known/health`
- Rate limiting to prevent abuse
- CORS policy configuration
- Secure connection to external services

## Monitoring

The system includes comprehensive monitoring:

- Queue depths and processing times
- API request rates and response times
- LLM performance metrics (TTFT, tokens/sec)
- System resource utilization

Grafana dashboard provides real-time visibility into system performance.

## Deployment

For production deployment:

1. Set up proper authentication and secrets management
2. Configure external database for production use
3. Set up proper TLS termination
4. Configure resource limits and scaling policies
5. Set up proper backup and disaster recovery procedures

## License

MIT License - see LICENSE file for details.