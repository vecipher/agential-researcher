import httpx
import asyncio
import logging
import time
import requests
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor
import threading

from ..config import settings
from ..utils.metrics import time_llm_request, count_tokens, PROVIDER_ERRORS

logger = logging.getLogger(__name__)

class LLMProviderRouter:
    def __init__(self):
        self.primary_provider = "vllm"
        self.secondary_provider = "ollama"
        self.primary_url = settings.vllm_url
        self.secondary_url = settings.ollama_url
        self.primary_healthy = False
        self.secondary_healthy = False
        # Use a thread pool for sync operations from async contexts
        self.executor = ThreadPoolExecutor(max_workers=4)
        
    def startup_probe_sync(self):
        """
        Synchronous version of startup probe for use in sync contexts like Celery
        """
        logger.info("Running startup health probes...")
        
        # Test primary (vLLM)
        self.primary_healthy = self._probe_provider_sync(self.primary_url)
        logger.info(f"Primary (vLLM) health: {self.primary_healthy}")
        
        # Test secondary (Ollama)  
        self.secondary_healthy = self._probe_provider_sync(self.secondary_url)
        logger.info(f"Secondary (Ollama) health: {self.secondary_healthy}")
        
        # If primary is down but secondary is up, swap
        if not self.primary_healthy and self.secondary_healthy:
            logger.warning("Primary provider down, swapping to secondary as primary")
            self.primary_provider = "ollama"
            self.secondary_provider = "vllm"
            self.primary_url = settings.ollama_url
            self.secondary_url = settings.vllm_url
        elif not self.primary_healthy and not self.secondary_healthy:
            logger.error("Both providers are down!")
    
    async def startup_probe(self):
        """
        On boot: 1-token /v1/chat/completions probe to each provider.
        If primary fails and secondary passes, swap.
        """
        # For now, just call the sync version
        self.startup_probe_sync()
    
    def _probe_provider_sync(self, provider_url: str) -> bool:
        """Send a minimal probe to test provider availability - synchronous version"""
        try:
            # Create a minimal request to test the provider
            test_payload = {
                "model": "test-model",  # Will be ignored by provider
                "messages": [{"role": "user", "content": "Hi"}],
                "max_tokens": 1,
                "temperature": 0
            }
            
            # Use requests for sync HTTP calls
            try:
                response = requests.post(
                    f"{provider_url}/v1/chat/completions",
                    json=test_payload,
                    timeout=10
                )
                return response.status_code in [200, 400, 404]  # 400/404 means service is up
            except:
                # Try Ollama endpoint as fallback
                ollama_test_payload = {
                    "model": "llama2",
                    "messages": [{"role": "user", "content": "Hi"}],
                    "stream": False
                }
                response = requests.post(
                    f"{provider_url}/api/chat",
                    json=ollama_test_payload,
                    timeout=10
                )
                return response.status_code in [200, 400, 404]
                    
        except Exception as e:
            logger.error(f"Provider probe failed: {e}")
            return False

    def route_request_sync(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Synchronous version of route_request for use in Celery tasks
        """
        start_time = time.time()
        primary_error = None
        secondary_error = None
        
        # Try primary provider first
        try:
            response = self._call_provider_sync(self.primary_url, payload)
            if response:
                # Record metrics for successful request
                duration = time.time() - start_time
                time_llm_request(self.primary_provider, payload.get('model', 'unknown'), 
                               'chat/completions', duration)
                
                # Record token usage if available
                usage = response.get('usage', {})
                if usage:
                    count_tokens(self.primary_provider, 
                               usage.get('prompt_tokens', 0), 
                               usage.get('completion_tokens', 0))
                
                logger.info(f"Request successful via primary ({self.primary_provider}) provider")
                return response
        except Exception as e:
            primary_error = str(e)
            PROVIDER_ERRORS.labels(provider=self.primary_provider, error_type=type(e).__name__).inc()
            logger.warning(f"Primary provider failed: {primary_error}")
        
        # If primary failed, try secondary
        try:
            if self.primary_provider == "vllm":
                secondary_url = self.secondary_url  # Ollama
                secondary_provider_name = "ollama"
            else:
                secondary_url = self.secondary_url  # vLLM (since primary was Ollama)
                secondary_provider_name = "vllm"
                
            response = self._call_provider_sync(secondary_url, payload)
            if response:
                # Record metrics for successful request
                duration = time.time() - start_time
                time_llm_request(secondary_provider_name, payload.get('model', 'unknown'), 
                               'chat/completions', duration)
                
                # Record token usage if available
                usage = response.get('usage', {})
                if usage:
                    count_tokens(secondary_provider_name, 
                               usage.get('prompt_tokens', 0), 
                               usage.get('completion_tokens', 0))
                
                logger.info(f"Request successful via secondary ({secondary_provider_name}) provider")
                return response
        except Exception as e:
            secondary_error = str(e)
            PROVIDER_ERRORS.labels(provider=secondary_provider_name, error_type=type(e).__name__).inc()
            logger.warning(f"Secondary provider failed: {secondary_error}")
        
        # Both failed, return explicit error with both causes
        error_msg = "Both LLM providers failed:\n"
        if primary_error:
            error_msg += f"Primary ({self.primary_provider}): {primary_error}\n"
        if secondary_error:
            error_msg += f"Secondary ({secondary_provider_name}): {secondary_error}"
            
        logger.error(error_msg)
        raise Exception(error_msg)

    def _call_provider_sync(self, provider_url: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Make the actual call to a provider - synchronous version"""
        try:
            # Determine if we're calling vLLM or Ollama endpoint
            if "chat" in provider_url or "vllm" in provider_url.split(":")[0]:
                # This is likely a vLLM endpoint
                response = requests.post(
                    f"{provider_url}/v1/chat/completions",
                    json=payload,
                    timeout=120  # 2 minute timeout for longer requests
                )
            else:
                # Assume it's an Ollama endpoint
                ollama_payload = {
                    "model": payload.get("model", "llama2"),
                    "messages": payload.get("messages", []),
                    "stream": payload.get("stream", False),
                    "options": {
                        "temperature": payload.get("temperature", 0.7),
                        "num_predict": payload.get("max_tokens", 150)
                    }
                }
                response = requests.post(
                    f"{provider_url}/api/chat",
                    json=ollama_payload,
                    timeout=120  # 2 minute timeout
                )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Provider returned status {response.status_code}: {response.text}")
                return None
        except requests.Timeout:
            logger.error(f"Provider call timed out: {provider_url}")
            return None
        except Exception as e:
            logger.error(f"Provider call failed: {e}")
            return None

    # Async versions for FastAPI
    async def route_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Per call: try primary; on non-2xx or timeout, try secondary;
        if both fail return a single, explicit error with both causes.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, self.route_request_sync, payload)

# Global instance
llm_router = LLMProviderRouter()

# Simple OpenAI-compatible proxy endpoint
async def chat_completions_proxy(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Proxy function that routes chat completion requests"""
    return await llm_router.route_request(payload)

@asynccontextmanager
async def lifespan():
    """Lifespan context manager to run startup probe"""
    await llm_router.startup_probe()
    yield
    # Cleanup code would go here