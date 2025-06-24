# Circuit Breaker Library

A hybrid circuit breaker implementation with configurable fixed and exponential retry intervals, designed for fault tolerance and service resilience in distributed systems.

## Features

- **Hybrid Retry Pattern**: Combines fixed-interval retries for transient issues with exponential-interval retries for persistent failures
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

### Basic Usage

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

## License

Apache License 2.0