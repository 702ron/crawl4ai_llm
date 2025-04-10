"""
API module for the Crawl4AI LLM system.

This module contains the FastAPI application and related functions for
running the REST API server that provides extraction, processing, and storage
functionality.
"""

from .app import app, start_server

__all__ = ["app", "start_server"]
