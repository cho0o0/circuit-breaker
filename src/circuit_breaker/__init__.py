"""
Circuit Breaker Library

A hybrid circuit breaker implementation with configurable fixed and exponential retry intervals.
Designed for fault tolerance and service resilience in distributed systems.
"""

from .circuit_breaker import CircuitBreaker, CircuitBreakerState

__version__ = "1.0.0"
__all__ = ["CircuitBreaker", "CircuitBreakerState"]
