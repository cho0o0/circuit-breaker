import time
from unittest.mock import MagicMock, patch

import pytest

from circuit_breaker import CircuitBreaker, CircuitBreakerState


class TestCircuitBreaker:
  def test_circuit_breaker_initialization(self):
    """Test circuit breaker initializes with correct defaults"""
    cb = CircuitBreaker()
    assert cb.failure_threshold == 5
    assert cb.base_interval_minutes == 5
    assert cb.fixed_interval_retries == 3
    assert cb.max_exponential_retries == 5
    assert cb.jitter_enabled is True
    assert cb.state == CircuitBreakerState.CLOSED
    assert cb.failure_count == 0
    assert cb.consecutive_circuit_breaks == 0

  def test_custom_initialization(self):
    """Test circuit breaker with custom parameters"""
    cb = CircuitBreaker(
      failure_threshold=2,
      base_interval_minutes=10,
      fixed_interval_retries=5,
      max_exponential_retries=3,
      jitter_enabled=False,
    )
    assert cb.failure_threshold == 2
    assert cb.base_interval_minutes == 10
    assert cb.fixed_interval_retries == 5
    assert cb.max_exponential_retries == 3
    assert cb.jitter_enabled is False

  def test_successful_call(self):
    """Test successful function calls work normally"""
    cb = CircuitBreaker(failure_threshold=2)

    def success_func():
      return "success"

    result = cb.call(success_func)
    assert result == "success"
    assert cb.state == CircuitBreakerState.CLOSED
    assert cb.failure_count == 0

  def test_successful_call_with_arguments(self):
    """Test successful function calls with arguments and kwargs"""
    cb = CircuitBreaker()

    def func_with_args(a, b, c=None):
      return f"{a}-{b}-{c}"

    result = cb.call(func_with_args, "hello", "world", c="test")
    assert result == "hello-world-test"
    assert cb.state == CircuitBreakerState.CLOSED

  def test_circuit_opens_after_threshold_failures(self):
    """Test circuit opens after reaching failure threshold"""
    cb = CircuitBreaker(failure_threshold=2)

    def failing_func():
      raise ValueError("Test failure")

    # First failure
    with pytest.raises(ValueError):
      cb.call(failing_func)
    assert cb.state == CircuitBreakerState.CLOSED
    assert cb.failure_count == 1

    # Second failure - should open circuit
    with pytest.raises(ValueError):
      cb.call(failing_func)
    assert cb.state == CircuitBreakerState.OPEN
    assert cb.failure_count == 2
    assert cb.consecutive_circuit_breaks == 1

  def test_circuit_partial_failures_then_success(self):
    """Test circuit handles partial failures followed by success"""
    cb = CircuitBreaker(failure_threshold=3)

    def failing_func():
      raise ValueError("Test failure")

    def success_func():
      return "success"

    # Two failures (below threshold)
    with pytest.raises(ValueError):
      cb.call(failing_func)
    with pytest.raises(ValueError):
      cb.call(failing_func)

    assert cb.state == CircuitBreakerState.CLOSED
    assert cb.failure_count == 2

    # Success should reset failure count
    result = cb.call(success_func)
    assert result == "success"
    assert cb.failure_count == 0
    assert cb.state == CircuitBreakerState.CLOSED

  def test_circuit_breaker_blocks_calls_when_open(self):
    """Test circuit breaker blocks calls when in OPEN state"""
    cb = CircuitBreaker(failure_threshold=1, base_interval_minutes=1)

    def failing_func():
      raise ValueError("Test failure")

    # Cause circuit to open
    with pytest.raises(ValueError):
      cb.call(failing_func)
    assert cb.state == CircuitBreakerState.OPEN

    # Subsequent calls should be blocked
    with pytest.raises(Exception) as exc_info:
      cb.call(failing_func)
    assert "Circuit breaker is OPEN" in str(exc_info.value)

  @patch("time.time")
  def test_complete_hybrid_pattern_end_to_end(self, mock_time):
    """Test complete hybrid pattern: fixed → exponential → recovery"""
    cb = CircuitBreaker(
      failure_threshold=1,
      base_interval_minutes=5,
      fixed_interval_retries=2,
      max_exponential_retries=2,
      jitter_enabled=False,
    )

    def failing_func():
      raise ValueError("Test failure")

    def success_func():
      return "recovered"

    mock_time.return_value = 0

    # === PHASE 1: Fixed-interval retries ===

    # 1st circuit break - fixed interval (5 min)
    with pytest.raises(ValueError):
      cb.call(failing_func)
    assert cb.consecutive_circuit_breaks == 1
    assert cb._get_current_recovery_timeout_minutes() == 5

    # Wait 5 minutes, try again, fail
    mock_time.return_value = 300  # 5 minutes
    cb.state = CircuitBreakerState.HALF_OPEN  # Simulate timeout
    with pytest.raises(ValueError):
      cb.call(failing_func)
    assert cb.consecutive_circuit_breaks == 2
    assert cb._get_current_recovery_timeout_minutes() == 5  # Still fixed

    # === PHASE 2: Exponential-interval retries ===

    # Wait another 5 minutes, try again, fail - enter exponential phase
    mock_time.return_value = 600  # 10 minutes total
    cb.state = CircuitBreakerState.HALF_OPEN
    with pytest.raises(ValueError):
      cb.call(failing_func)
    assert cb.consecutive_circuit_breaks == 3
    assert cb._get_current_recovery_timeout_minutes() == 25  # 5 * 5^1

    # Wait 25 minutes, try again, fail - second exponential
    mock_time.return_value = 2100  # 35 minutes total
    cb.state = CircuitBreakerState.HALF_OPEN
    with pytest.raises(ValueError):
      cb.call(failing_func)
    assert cb.consecutive_circuit_breaks == 4
    assert cb._get_current_recovery_timeout_minutes() == 125  # 5 * 5^2

    # === PHASE 3: Recovery ===

    # Wait 125 minutes, try again, succeed - should reset completely
    mock_time.return_value = 9600  # 160 minutes total
    cb.state = CircuitBreakerState.HALF_OPEN
    result = cb.call(success_func)

    assert result == "recovered"
    assert cb.state == CircuitBreakerState.CLOSED
    assert cb.failure_count == 0
    assert cb.consecutive_circuit_breaks == 0

  def test_fixed_interval_timeout_calculation(self):
    """Test timeout calculation during fixed-interval phase"""
    cb = CircuitBreaker(
      base_interval_minutes=10, fixed_interval_retries=3, jitter_enabled=False
    )

    # Simulate circuit breaks in fixed-interval phase
    cb.consecutive_circuit_breaks = 1
    assert cb._get_current_recovery_timeout_minutes() == 10

    cb.consecutive_circuit_breaks = 2
    assert cb._get_current_recovery_timeout_minutes() == 10

    cb.consecutive_circuit_breaks = 3
    assert cb._get_current_recovery_timeout_minutes() == 10

  def test_exponential_interval_timeout_calculation(self):
    """Test timeout calculation during exponential-interval phase"""
    cb = CircuitBreaker(
      base_interval_minutes=5,
      fixed_interval_retries=2,
      max_exponential_retries=3,
      jitter_enabled=False,
    )

    # Move to exponential phase
    cb.consecutive_circuit_breaks = 3  # First exponential attempt
    assert cb._get_current_recovery_timeout_minutes() == 25  # 5 * 5^1

    cb.consecutive_circuit_breaks = 4  # Second exponential attempt
    assert cb._get_current_recovery_timeout_minutes() == 125  # 5 * 5^2

    cb.consecutive_circuit_breaks = 5  # Third exponential attempt
    assert cb._get_current_recovery_timeout_minutes() == 625  # 5 * 5^3

  def test_exponential_timeout_capping(self):
    """Test exponential timeout is capped at max_exponential_retries"""
    cb = CircuitBreaker(
      base_interval_minutes=5,
      fixed_interval_retries=1,
      max_exponential_retries=2,
      jitter_enabled=False,
    )

    # Should cap at max_exponential_retries
    cb.consecutive_circuit_breaks = 10  # Way beyond max
    expected_timeout = 5 * (5**2)  # Should be capped at 2nd exponential
    assert cb._get_current_recovery_timeout_minutes() == expected_timeout

  def test_zero_fixed_retries_goes_straight_to_exponential(self):
    """Test behavior when fixed_interval_retries is 0"""
    cb = CircuitBreaker(
      base_interval_minutes=5,
      fixed_interval_retries=0,
      max_exponential_retries=3,
      jitter_enabled=False,
    )

    # First circuit break should go straight to exponential
    cb.consecutive_circuit_breaks = 1
    assert cb._get_current_recovery_timeout_minutes() == 25  # 5 * 5^1

  def test_zero_exponential_retries_stays_fixed(self):
    """Test behavior when max_exponential_retries is 0"""
    cb = CircuitBreaker(
      base_interval_minutes=10,
      fixed_interval_retries=3,
      max_exponential_retries=0,
      jitter_enabled=False,
    )

    # Should stay at fixed interval even beyond fixed_interval_retries
    cb.consecutive_circuit_breaks = 5
    assert cb._get_current_recovery_timeout_minutes() == 10

  def test_very_large_exponential_values(self):
    """Test handling of very large exponential timeout values"""
    cb = CircuitBreaker(
      base_interval_minutes=60,  # 1 hour base
      fixed_interval_retries=1,
      max_exponential_retries=10,
      jitter_enabled=False,
    )

    # Test large exponential values
    cb.consecutive_circuit_breaks = 8  # 7th exponential attempt
    expected = 60 * (60**7)  # Should be a very large number
    actual = cb._get_current_recovery_timeout_minutes()
    assert actual == expected
    assert actual > 1000000  # Should be over 1 million minutes

  @patch("time.time")
  def test_circuit_reset_after_timeout(self, mock_time):
    """Test circuit transitions to HALF_OPEN after timeout"""
    cb = CircuitBreaker(failure_threshold=1, base_interval_minutes=1, jitter_enabled=False)

    def failing_func():
      raise ValueError("Test failure")

    # Set initial time
    mock_time.return_value = 0

    # Cause circuit to open
    with pytest.raises(ValueError):
      cb.call(failing_func)
    assert cb.state == CircuitBreakerState.OPEN

    # Before timeout - should still be blocked
    mock_time.return_value = 30  # 30 seconds (less than 1 minute)
    with pytest.raises(Exception):
      cb.call(failing_func)
    assert cb.state == CircuitBreakerState.OPEN

    # After timeout - should transition to HALF_OPEN
    mock_time.return_value = 70  # 70 seconds (more than 1 minute)
    with pytest.raises(ValueError):  # Call still fails
      cb.call(failing_func)
    # State should have been HALF_OPEN during the call, then back to OPEN

  def test_circuit_recovery_on_success(self):
    """Test circuit resets completely on successful call"""
    cb = CircuitBreaker(failure_threshold=1)

    def failing_func():
      raise ValueError("Test failure")

    def success_func():
      return "success"

    # Cause circuit to open
    with pytest.raises(ValueError):
      cb.call(failing_func)
    assert cb.state == CircuitBreakerState.OPEN
    assert cb.consecutive_circuit_breaks == 1

    # Mock successful recovery
    cb.state = CircuitBreakerState.HALF_OPEN
    result = cb.call(success_func)

    # Should reset completely
    assert result == "success"
    assert cb.state == CircuitBreakerState.CLOSED
    assert cb.failure_count == 0
    assert cb.consecutive_circuit_breaks == 0

  def test_half_open_state_behavior(self):
    """Test HALF_OPEN state allows exactly one call"""
    cb = CircuitBreaker(failure_threshold=1)

    def failing_func():
      raise ValueError("Test failure")

    # Set to HALF_OPEN state manually
    cb.state = CircuitBreakerState.HALF_OPEN
    cb.failure_count = 1
    cb.consecutive_circuit_breaks = 1

    # First call in HALF_OPEN should be allowed but fail
    with pytest.raises(ValueError):
      cb.call(failing_func)

    # Should be back to OPEN state
    assert cb.state == CircuitBreakerState.OPEN

  def test_function_exceptions_are_preserved(self):
    """Test that original function exceptions are preserved"""
    cb = CircuitBreaker()

    def custom_exception_func():
      raise CustomError("Custom message")

    class CustomError(Exception):
      pass

    # Original exception should be preserved
    with pytest.raises(CustomError) as exc_info:
      cb.call(custom_exception_func)
    assert str(exc_info.value) == "Custom message"

  def test_function_return_values_preserved(self):
    """Test that function return values are preserved"""
    cb = CircuitBreaker()

    def complex_return_func():
      return {"status": "ok", "data": [1, 2, 3], "count": 42}

    result = cb.call(complex_return_func)
    expected = {"status": "ok", "data": [1, 2, 3], "count": 42}
    assert result == expected

  def test_callable_objects(self):
    """Test circuit breaker works with callable objects"""
    cb = CircuitBreaker()

    class CallableClass:
      def __call__(self, x, y):
        return x + y

    callable_obj = CallableClass()
    result = cb.call(callable_obj, 5, 3)
    assert result == 8

  def test_lambda_functions(self):
    """Test circuit breaker works with lambda functions"""
    cb = CircuitBreaker()

    result = cb.call(lambda x: x * 2, 21)
    assert result == 42

  def test_jitter_applied_when_enabled(self):
    """Test jitter is applied when enabled"""
    cb = CircuitBreaker(base_interval_minutes=100, jitter_enabled=True)

    cb.consecutive_circuit_breaks = 1

    # Get multiple timeout values - they should vary due to jitter
    timeouts = [cb._get_current_recovery_timeout_minutes() for _ in range(10)]

    # Should have some variation (not all the same)
    assert len(set(timeouts)) > 1

    # All should be within reasonable range (±25% of 100)
    for timeout in timeouts:
      assert 75 <= timeout <= 125

  def test_jitter_disabled(self):
    """Test no jitter when disabled"""
    cb = CircuitBreaker(base_interval_minutes=100, jitter_enabled=False)

    cb.consecutive_circuit_breaks = 1

    # Get multiple timeout values - they should all be the same
    timeouts = [cb._get_current_recovery_timeout_minutes() for _ in range(10)]

    # All should be exactly the same
    assert len(set(timeouts)) == 1
    assert timeouts[0] == 100

  def test_status_info_closed_state(self):
    """Test status info for closed state"""
    cb = CircuitBreaker()
    status = cb.get_status_info()

    assert status["state"] == "closed"
    assert status["failure_count"] == 0
    assert status["consecutive_circuit_breaks"] == 0
    assert status["retry_phase"] == "closed"
    assert status["current_recovery_timeout_minutes"] == 5
    assert status["time_until_retry_minutes"] is None

  def test_status_info_fixed_interval_phase(self):
    """Test status info during fixed-interval phase"""
    cb = CircuitBreaker(fixed_interval_retries=3)
    cb.consecutive_circuit_breaks = 2

    status = cb.get_status_info()
    assert status["retry_phase"] == "fixed-interval (attempt 2/3)"

  def test_status_info_exponential_phase(self):
    """Test status info during exponential-interval phase"""
    cb = CircuitBreaker(fixed_interval_retries=2, max_exponential_retries=5)
    cb.consecutive_circuit_breaks = 4  # 2 exponential attempts

    status = cb.get_status_info()
    assert status["retry_phase"] == "exponential-interval (attempt 2/5)"

  def test_status_info_beyond_max_retries(self):
    """Test status info when beyond max retry limits"""
    cb = CircuitBreaker(fixed_interval_retries=2, max_exponential_retries=3)
    cb.consecutive_circuit_breaks = 10  # Way beyond limits

    status = cb.get_status_info()
    # Should cap at max_exponential_retries (3/3)
    assert status["retry_phase"] == "exponential-interval (attempt 3/3)"

  @patch("time.time")
  def test_time_until_retry_calculation(self, mock_time):
    """Test time until retry calculation"""
    cb = CircuitBreaker(base_interval_minutes=10, jitter_enabled=False)

    # Set circuit to open state
    mock_time.return_value = 100
    cb.state = CircuitBreakerState.OPEN
    cb.last_failure_time = 100
    cb.consecutive_circuit_breaks = 1

    # Check time until retry after 3 minutes
    mock_time.return_value = 280  # 3 minutes later
    status = cb.get_status_info()

    expected_time_until_retry = 10 - 3  # 10 min timeout - 3 min elapsed
    assert abs(status["time_until_retry_minutes"] - expected_time_until_retry) < 0.1

  @patch("time.time")
  def test_time_until_retry_past_timeout(self, mock_time):
    """Test time until retry when past timeout (should be 0)"""
    cb = CircuitBreaker(base_interval_minutes=5, jitter_enabled=False)

    mock_time.return_value = 100
    cb.state = CircuitBreakerState.OPEN
    cb.last_failure_time = 100
    cb.consecutive_circuit_breaks = 1

    # Check time until retry after 10 minutes (past the 5-minute timeout)
    mock_time.return_value = 700  # 10 minutes later
    status = cb.get_status_info()

    assert status["time_until_retry_minutes"] == 0

  def test_edge_case_zero_base_interval(self):
    """Test edge case with zero base interval"""
    cb = CircuitBreaker(base_interval_minutes=0, jitter_enabled=False)

    cb.consecutive_circuit_breaks = 1
    assert cb._get_current_recovery_timeout_minutes() == 0

  def test_edge_case_negative_values(self):
    """Test circuit breaker handles negative configuration values gracefully"""
    # Should not crash, but behavior may be undefined
    cb = CircuitBreaker(
      failure_threshold=-1,
      base_interval_minutes=-5,
      fixed_interval_retries=-2,
      max_exponential_retries=-3,
    )

    # Should still initialize without crashing
    assert cb.state == CircuitBreakerState.CLOSED

  def test_stress_test_many_failures(self):
    """Stress test with many consecutive failures"""
    cb = CircuitBreaker(failure_threshold=1, jitter_enabled=False)

    def failing_func():
      raise ValueError("Stress test failure")

    # Simulate many failures
    for _ in range(100):
      try:
        cb.call(failing_func)
      except Exception:
        pass  # Expected to fail

    # Should still be in a valid state
    assert cb.state in [CircuitBreakerState.OPEN, CircuitBreakerState.HALF_OPEN]
    assert cb.consecutive_circuit_breaks >= 1

  def test_concurrent_access_safety(self):
    """Test basic thread safety (no race conditions in single-threaded test)"""
    cb = CircuitBreaker()

    def sometimes_failing_func(should_fail=False):
      if should_fail:
        raise ValueError("Concurrent failure")
      return "success"

    # Simulate rapid alternating success/failure
    results = []
    for i in range(50):
      try:
        result = cb.call(sometimes_failing_func, should_fail=(i % 3 == 0))
        results.append(result)
      except Exception:
        results.append("failed")

    # Should have some successes and some failures
    assert "success" in results
    assert "failed" in results

  def test_status_info_contains_config(self):
    """Test that status info contains configuration details"""
    cb = CircuitBreaker(
      base_interval_minutes=7,
      fixed_interval_retries=4,
      max_exponential_retries=6,
      jitter_enabled=False,
    )

    status = cb.get_status_info()
    config = status["config"]

    assert config["base_interval_minutes"] == 7
    assert config["fixed_interval_retries"] == 4
    assert config["max_exponential_retries"] == 6
    assert config["jitter_enabled"] is False
