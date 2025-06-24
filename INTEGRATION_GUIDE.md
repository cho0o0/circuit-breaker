# Integration Guide

## Adding Circuit Breaker to Your Service

### 1. Add Dependency

#### Using uv (Recommended)

Add to your service's `pyproject.toml`:

```toml
[project]
dependencies = [
    # ... your other dependencies
    "circuit-breaker",
]

[tool.uv.sources]
circuit-breaker = { path = "../path/to/circuit_breaker", editable = true }
```

#### Using pip (Alternative)

```toml
[project]
dependencies = [
    # ... your other dependencies
    "circuit-breaker @ file:///path/to/circuit_breaker",
]
```

### 2. Import the Circuit Breaker

```python
from circuit_breaker import CircuitBreaker
```

### 3. Configure for Your Use Case

```python
from circuit_breaker import CircuitBreaker

# For external API calls
api_circuit_breaker = CircuitBreaker(
    failure_threshold=3,              # Failures before opening circuit
    base_interval_minutes=5,          # Base interval (5 minutes)
    fixed_interval_retries=3,         # First 3 retries at fixed intervals
    max_exponential_retries=5,        # Up to 5 exponential retries
    jitter_enabled=True              # Add randomization
)

# For database connections (shorter intervals)
db_circuit_breaker = CircuitBreaker(
    failure_threshold=5,
    base_interval_minutes=1,          # 1 minute base interval
    fixed_interval_retries=5,         # More fixed retries for DB
    max_exponential_retries=3,        # Fewer exponential retries
    jitter_enabled=True
)

# For critical services (longer intervals)
critical_service_breaker = CircuitBreaker(
    failure_threshold=2,              # Fail fast for critical services
    base_interval_minutes=10,         # 10 minute base interval
    fixed_interval_retries=2,         # Fewer attempts
    max_exponential_retries=4,        # Longer exponential backoff
    jitter_enabled=True
)
```

### 4. Monitor Circuit Breaker Status

```python
# Get detailed status for monitoring/logging
status = circuit_breaker.get_status_info()
logger.info(f"Circuit breaker status: {status}")

# Example monitoring integration
if status["state"] == "open":
    # Alert monitoring system
    send_alert(f"Circuit breaker OPEN: {status['retry_phase']}")
```

## Configuration Guidelines by Use Case

### Web Applications
- **External API calls**: Use standard configuration (5min intervals)
- **Database operations**: Use shorter intervals (1min base)
- **File uploads/downloads**: Use longer intervals (10min base)

### Data Processing Services
- **Batch operations**: Use longer intervals with fewer retries
- **Real-time processing**: Use shorter intervals for faster recovery

### Microservices
- **Service-to-service calls**: Configure based on criticality and SLA
- **Third-party integrations**: Use longer intervals to avoid rate limiting

## Best Practices

1. **Service-specific configuration**: Don't use the same configuration for all operations
2. **Monitor regularly**: Check circuit breaker status in your monitoring dashboards
3. **Graceful degradation**: Always handle circuit breaker exceptions gracefully
4. **Test failure scenarios**: Ensure your circuit breaker triggers correctly
5. **Documentation**: Document your circuit breaker configuration decisions

## Common Patterns

### API Service with Circuit Breaker
```python
import requests
import logging
from circuit_breaker import CircuitBreaker

logger = logging.getLogger(__name__)

class ExternalAPIService:
    def __init__(self, api_url: str):
        self.api_url = api_url
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=3,
            base_interval_minutes=5,
            fixed_interval_retries=3,
            max_exponential_retries=5
        )

    def _api_call_internal(self, data):
        # Your actual API call logic
        response = requests.post(self.api_url, json=data)
        response.raise_for_status()
        return response.json()

    def api_call(self, data):
        try:
            return self.circuit_breaker.call(self._api_call_internal, data)
        except Exception as e:
            logger.error(f"API call failed: {e}")
            # Return default response or handle gracefully
            return None
```

### Database Service with Circuit Breaker
```python
import logging
from circuit_breaker import CircuitBreaker

logger = logging.getLogger(__name__)

class DatabaseService:
    def __init__(self):
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            base_interval_minutes=1,
            fixed_interval_retries=5,
            max_exponential_retries=3
        )

    def _query_internal(self, query, params):
        with self.get_connection() as conn:
            return conn.execute(query, params).fetchall()

    def query(self, query, params=None):
        try:
            return self.circuit_breaker.call(self._query_internal, query, params)
        except Exception as e:
            logger.error(f"Database query failed: {e}")
            raise DatabaseUnavailableException("Database temporarily unavailable")
```

### HTTP Client with Circuit Breaker
```python
import httpx
import logging
from circuit_breaker import CircuitBreaker

logger = logging.getLogger(__name__)

class HTTPClientService:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=3,
            base_interval_minutes=2,      # Shorter for external services
            fixed_interval_retries=3,
            max_exponential_retries=4
        )
        self.timeout = httpx.Timeout(30.0)

    def _make_request_internal(self, endpoint: str, **kwargs) -> dict:
        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(f"{self.base_url}/{endpoint}", **kwargs)
            response.raise_for_status()
            return response.json()

    def make_request(self, endpoint: str, **kwargs) -> dict | None:
        try:
            return self.circuit_breaker.call(self._make_request_internal, endpoint, **kwargs)
        except Exception as e:
            logger.error(f"HTTP request failed for {endpoint}: {e}")
            return None  # Graceful degradation
```

## Integration Checklist

- [ ] Add circuit-breaker dependency to your project
- [ ] Import CircuitBreaker in your service classes
- [ ] Configure circuit breaker for your specific use case
- [ ] Add monitoring/logging for circuit breaker status
- [ ] Test failure scenarios
- [ ] Implement graceful degradation
- [ ] Update documentation