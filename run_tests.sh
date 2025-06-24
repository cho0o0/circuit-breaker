#!/bin/bash
set -e

echo "🔧 Installing dependencies..."
pip install -e .
pip install pytest pytest-cov ruff mypy

echo "🧹 Running linting checks..."
ruff check src/ tests/

echo "🔍 Running type checking..."
mypy src/circuit_breaker/ --ignore-missing-imports

echo "🧪 Running tests with coverage..."
python -m pytest tests/ -v --cov=circuit_breaker --cov-report=term-missing

echo "✅ All checks passed!"