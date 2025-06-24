import random
import time
from collections.abc import Callable
from enum import Enum
from typing import Any, TypeVar


class CircuitBreakerState(Enum):
  CLOSED = "closed"
  OPEN = "open"
  HALF_OPEN = "half_open"


T = TypeVar("T")


class CircuitBreaker:
  def __init__(
    self,
    failure_threshold: int = 5,
    base_interval_minutes: int = 5,
    fixed_interval_retries: int = 3,
    max_exponential_retries: int = 5,
    jitter_enabled: bool = True,
  ):
    self.failure_threshold = failure_threshold
    self.base_interval_minutes = base_interval_minutes
    self.fixed_interval_retries = fixed_interval_retries
    self.max_exponential_retries = max_exponential_retries
    self.jitter_enabled = jitter_enabled

    self.failure_count = 0
    self.consecutive_circuit_breaks = 0  # Track consecutive circuit breaker trips
    self.last_failure_time: float | None = None
    self.state = CircuitBreakerState.CLOSED

  def call(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    """Execute function with circuit breaker protection"""
    if self.state == CircuitBreakerState.OPEN:
      if self._should_attempt_reset():
        self.state = CircuitBreakerState.HALF_OPEN
      else:
        current_timeout_minutes = self._get_current_recovery_timeout_minutes()
        raise Exception(
          f"Circuit breaker is OPEN. Service unavailable. Next retry in {current_timeout_minutes} minutes."
        )

    try:
      result = func(*args, **kwargs)
      self._on_success()
      return result
    except Exception as e:
      self._on_failure()
      raise e

  def _should_attempt_reset(self) -> bool:
    """Check if enough time has passed to attempt reset"""
    if self.last_failure_time is None:
      return True
    current_timeout_minutes = self._get_current_recovery_timeout_minutes()
    current_timeout_seconds = current_timeout_minutes * 60
    return time.time() - self.last_failure_time >= current_timeout_seconds

  def _get_current_recovery_timeout_minutes(self) -> int:
    """Calculate current recovery timeout using hybrid fixed/exponential pattern"""
    if self.consecutive_circuit_breaks == 0:
      return self.base_interval_minutes

    # Phase 1: Fixed-interval retries (first N attempts)
    if self.consecutive_circuit_breaks <= self.fixed_interval_retries:
      timeout_minutes = self.base_interval_minutes
    else:
      # Phase 2: Exponential-interval retries
      exponential_attempt = self.consecutive_circuit_breaks - self.fixed_interval_retries

      # Cap exponential retries
      if exponential_attempt > self.max_exponential_retries:
        exponential_attempt = self.max_exponential_retries

      # Calculate: base_interval * (base_interval ^ exponential_attempt)
      # For base=5: 5^1=5, 5^2=25, 5^3=125, 5^4=625, etc.
      timeout_minutes = self.base_interval_minutes * (
        self.base_interval_minutes**exponential_attempt
      )

    # Add jitter (±10% randomness) to prevent thundering herd
    if self.jitter_enabled:
      jitter_range = max(1, int(timeout_minutes * 0.1))
      jitter = random.randint(-jitter_range, jitter_range)
      timeout_minutes = max(1, timeout_minutes + jitter)

    return timeout_minutes

  def _on_success(self) -> None:
    """Handle successful call"""
    self.failure_count = 0
    self.consecutive_circuit_breaks = 0  # Reset consecutive breaks on success
    self.state = CircuitBreakerState.CLOSED

  def _on_failure(self) -> None:
    """Handle failed call"""
    self.failure_count += 1
    self.last_failure_time = time.time()

    if self.failure_count >= self.failure_threshold:
      if self.state == CircuitBreakerState.HALF_OPEN:
        # If we failed in HALF_OPEN state, increment consecutive breaks
        self.consecutive_circuit_breaks += 1
      else:
        # First time opening the circuit
        self.consecutive_circuit_breaks = 1
      self.state = CircuitBreakerState.OPEN

  def get_status_info(self) -> dict[str, Any]:
    """Get detailed status information for monitoring"""
    current_timeout_minutes = self._get_current_recovery_timeout_minutes()
    time_until_retry_minutes = None

    if self.state == CircuitBreakerState.OPEN and self.last_failure_time:
      elapsed_seconds = time.time() - self.last_failure_time
      elapsed_minutes = elapsed_seconds / 60
      time_until_retry_minutes = max(0, current_timeout_minutes - elapsed_minutes)

    # Determine current retry phase
    retry_phase = "closed"
    if self.consecutive_circuit_breaks > 0:
      if self.consecutive_circuit_breaks <= self.fixed_interval_retries:
        retry_phase = f"fixed-interval (attempt {self.consecutive_circuit_breaks}/{self.fixed_interval_retries})"
      else:
        exponential_attempt = min(
          self.consecutive_circuit_breaks - self.fixed_interval_retries,
          self.max_exponential_retries,
        )
        retry_phase = f"exponential-interval (attempt {exponential_attempt}/{self.max_exponential_retries})"

    return {
      "state": self.state.value,
      "failure_count": self.failure_count,
      "consecutive_circuit_breaks": self.consecutive_circuit_breaks,
      "retry_phase": retry_phase,
      "current_recovery_timeout_minutes": current_timeout_minutes,
      "time_until_retry_minutes": time_until_retry_minutes,
      "config": {
        "base_interval_minutes": self.base_interval_minutes,
        "fixed_interval_retries": self.fixed_interval_retries,
        "max_exponential_retries": self.max_exponential_retries,
        "jitter_enabled": self.jitter_enabled,
      },
    }
