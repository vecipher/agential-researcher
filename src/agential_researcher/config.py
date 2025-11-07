from pydantic_settings import Settings
from pydantic import Field
from typing import Optional


class Settings(Settings):
    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_workers: int = 1
    debug: bool = False
    
    # Database
    sqlite_path: str = "agential_researcher.db"
    lancedb_path: str = "./.lancedb"
    
    # Queue
    broker_url: str = "amqp://guest:guest@localhost:5672//"
    backend_url: str = "rpc://"
    
    # LLM Providers
    vllm_url: str = "http://vllm:8000"  # Default for Docker
    ollama_url: str = "http://ollama:11434"
    
    # API Keys and Security
    api_keys: list[str] = Field(default=["sk-..."])  # Will be overridden by env
    cors_allow_origins: list[str] = ["*"]
    
    # Rate limiting
    rate_limit_requests: int = 100
    rate_limit_window: int = 3600  # 1 hour
    
    # Processing
    max_concurrent_summaries: int = 2
    max_vlm_ocr_queue_size: int = 100
    
    # arXiv
    arxiv_poll_interval: int = 3  # seconds
    arxiv_max_results: int = 100
    
    # Monitoring
    prometheus_port: int = 9090
    
    # Storage
    content_cache_ttl: int = 86400  # 24 hours
    
    class Config:
        env_file = ".env"


# Global settings instance
settings = Settings()