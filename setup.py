#!/usr/bin/env python3
"""
Setup script for circuit-breaker library.
"""

from setuptools import setup, find_packages
import pathlib

HERE = pathlib.Path(__file__).parent
README = (HERE / "README.md").read_text(encoding="utf-8")

setup(
  name="circuit-breaker",
  version="1.0.0",
  author="Cyan",
  description="A hybrid circuit breaker library with fixed and exponential retry intervals",
  long_description=README,
  long_description_content_type="text/markdown",
  url="https://github.com/cho0o0/circuit-breaker",
  project_urls={
    "Homepage": "https://github.com/cho0o0/circuit-breaker",
    "Repository": "https://github.com/cho0o0/circuit-breaker",
    "Bug Reports": "https://github.com/cho0o0/circuit-breaker/issues",
  },
  package_dir={"": "src"},
  packages=find_packages(where="src"),
  python_requires=">=3.10",
  classifiers=[
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: Apache Software License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Operating System :: OS Independent",
    "Topic :: Software Development :: Libraries :: Python Modules",
    "Topic :: System :: Networking",
    "Topic :: Internet",
  ],
  keywords=["circuit-breaker", "fault-tolerance", "resilience", "retry"],
  install_requires=[],
  extras_require={
    "dev": ["pytest>=8.3.4"],
  },
  zip_safe=False,
)
