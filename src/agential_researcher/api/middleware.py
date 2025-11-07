from fastapi import Request, Response
from fastapi.routing import Match
from prometheus_client import Counter, Histogram
import time

# HTTP request metrics
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

REQUEST_DURATION = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint']
)

async def metrics_middleware(request: Request, call_next):
    start_time = time.time()
    
    response = await call_next(request)
    
    duration = time.time() - start_time
    
    # Determine the endpoint/route name
    route_name = "unknown"
    for route in request.app.routes:
        match, _ = route.matches(request.scope)
        if match == Match.FULL:
            route_name = route.name or route.path
            break
    
    # Record metrics
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=route_name,
        status=response.status_code
    ).inc()
    
    REQUEST_DURATION.labels(
        method=request.method,
        endpoint=route_name
    ).observe(duration)
    
    return response