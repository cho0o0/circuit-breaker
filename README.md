# Circuit Breaker Library

A hybrid circuit breaker implementation with configurable fixed and exponential retry intervals, designed for fault tolerance and service resilience in distributed systems.

## Features

- **Hybrid Retry Pattern**: Combines fixed-interval retries for transient issues with exponential-interval retries for persistent failures
- **Async Support**: Works with both synchronous and asynchronous functions via `call()` and `async_call()` methods
- **Configurable Parameters**: Fully customizable failure thresholds, intervals, and retry counts
- **Jitter Support**: Optional randomization to prevent thundering herd problems
- **Detailed Monitoring**: Comprehensive status information for observability
- **Type Safe**: Full type hints for better IDE support and code quality

## Installation

### Using uv (Recommended)

#### Install from GitHub

```bash
uv add git+https://github.com/cho0o0/circuit-breaker.git
```

#### Install from local development

Add to your `pyproject.toml`:

```toml
[project]
dependencies = [
    # ... your other dependencies
    "circuit-breaker",
]

[tool.uv.sources]
circuit-breaker = { git = "https://github.com/cho0o0/circuit-breaker.git" }
```

Or for local development:

```toml
[tool.uv.sources]
circuit-breaker = { path = "../path/to/circuit_breaker", editable = true }
```

### Using pip (Alternative)

```bash
# Install from GitHub
pip install git+https://github.com/cho0o0/circuit-breaker.git

# Install from local directory (in development)
pip install -e /path/to/circuit_breaker/
```

## Usage

### Basic Usage (Synchronous)

```python
from circuit_breaker import CircuitBreaker
import requests

# Initialize with default settings
cb = CircuitBreaker()

def risky_api_call():
    response = requests.get("https://api.example.com/data")
    response.raise_for_status()
    return response.json()

try:
    result = cb.call(risky_api_call)
    print(f"Success: {result}")
except Exception as e:
    print(f"Failed: {e}")
```

### Basic Usage (Asynchronous)

```python
from circuit_breaker import CircuitBreaker
import aiohttp

cb = CircuitBreaker()

async def async_api_call():
    async with aiohttp.ClientSession() as session:
        async with session.get("https://api.example.com/data") as response:
            response.raise_for_status()
            return await response.json()

# Use async_call for async functions
try:
    result = await cb.async_call(async_api_call)
    print(f"Success: {result}")
except Exception as e:
    print(f"Failed: {e}")
```

### Mixed Sync/Async Usage

The same `CircuitBreaker` instance can be used for both synchronous and asynchronous calls. The circuit state is shared between both:

```python
cb = CircuitBreaker()

# Sync call
result = cb.call(sync_function)

# Async call (shares the same circuit state)
result = await cb.async_call(async_function)
```

### Advanced Configuration

```python
from circuit_breaker import CircuitBreaker

# Hybrid pattern configuration
cb = CircuitBreaker(
    failure_threshold=3,              # Failures before opening circuit
    base_interval_minutes=5,          # Base interval (5 minutes)
    fixed_interval_retries=3,         # First 3 retries at fixed intervals
    max_exponential_retries=5,        # Up to 5 exponential retries
    jitter_enabled=True              # Add randomization
)
```

## Retry Pattern

### Phase 1: Fixed-Interval Retries (Transient Issues)
- **Attempt 1**: Fail → Wait **5 minutes** → Retry
- **Attempt 2**: Fail → Wait **5 minutes** → Retry
- **Attempt 3**: Fail → Wait **5 minutes** → Retry

### Phase 2: Exponential-Interval Retries (Persistent Failures)
- **Attempt 4**: Fail → Wait **25 minutes** (5 × 5¹) → Retry
- **Attempt 5**: Fail → Wait **125 minutes** (5 × 5²) → Retry
- **Attempt 6**: Fail → Wait **625 minutes** (5 × 5³) → Retry
- **Attempt 7**: Fail → Wait **3125 minutes** (5 × 5⁴) → Retry
- **Attempt 8**: Fail → Wait **15625 minutes** (5 × 5⁵) → Retry (capped)

## Monitoring

```python
# Get detailed status information
status = cb.get_status_info()
print(status)
```

Example output:
```json
{
  "state": "open",
  "failure_count": 3,
  "consecutive_circuit_breaks": 2,
  "retry_phase": "exponential-interval (attempt 2/5)",
  "current_recovery_timeout_minutes": 125,
  "time_until_retry_minutes": 87.5,
  "config": {
    "base_interval_minutes": 5,
    "fixed_interval_retries": 3,
    "max_exponential_retries": 5,
    "jitter_enabled": true
  }
}
```

## States

- **CLOSED**: Normal operation, all calls pass through
- **OPEN**: Circuit is open, calls fail immediately with exception
- **HALF_OPEN**: Testing state, allows one call to test if service recovered

## API Reference

### CircuitBreaker

#### Constructor Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `failure_threshold` | int | 5 | Number of failures before opening the circuit |
| `base_interval_minutes` | int | 5 | Base interval for recovery timeout (in minutes) |
| `fixed_interval_retries` | int | 3 | Number of retries at fixed intervals before exponential backoff |
| `max_exponential_retries` | int | 5 | Maximum number of exponential retry attempts |
| `jitter_enabled` | bool | True | Enable randomization (±10%) to prevent thundering herd |

#### Methods

| Method | Description |
|--------|-------------|
| `call(func, *args, **kwargs)` | Execute a synchronous function with circuit breaker protection |
| `async_call(func, *args, **kwargs)` | Execute an async function with circuit breaker protection |
| `get_status_info()` | Get detailed status information for monitoring |

## Development

### Setup

```bash
# Clone the repository
git clone https://github.com/cho0o0/circuit-breaker.git
cd circuit-breaker

# Install dependencies with uv
uv sync --group dev
```

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v

# Run specific test file
uv run pytest tests/test_circuit_breaker.py

# Run with coverage
uv run pytest --cov=src
```

### Code Quality

```bash
# Run linter
uv run ruff check src tests

# Run formatter
uv run ruff format src tests

# Run type checker
uv run mypy src
```

## License

Apache License 2.0