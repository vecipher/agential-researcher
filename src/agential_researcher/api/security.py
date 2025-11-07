from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from fastapi import Request
import time
import secrets
from typing import List

from .config import settings

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

# In-memory storage for API keys (in production, use a secure store)
API_KEYS = settings.api_keys if settings.api_keys != ["sk-..."] else [secrets.token_urlsafe(32) for _ in range(3)]

def verify_api_key(api_key: str) -> bool:
    """Verify if the provided API key is valid"""
    return api_key in API_KEYS

def add_security_headers(response):
    """Add security headers to response"""
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

# Rate limiting configuration
RATE_LIMITS = {
    "default": f"{settings.rate_limit_requests}/{settings.rate_limit_window}seconds",
    "health": "100/minute",  # Health endpoint has higher limits
    "search": "50/hour",     # Search might be expensive
    "ingest": "20/hour"      # Ingestion endpoints limited to prevent spam
}

def get_rate_limit_for_endpoint(endpoint_name: str) -> str:
    """Get appropriate rate limit for an endpoint"""
    return RATE_LIMITS.get(endpoint_name, RATE_LIMITS["default"])

# For now, let's create a basic auth middleware file since we need the security to be integrated.
# We'll update the main.py file to include these security measures properly.