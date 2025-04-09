"""
Core crawler functionality for fetching product pages from e-commerce websites.
"""

from .base import BaseCrawler
from .content_filter import ContentFilter

__all__ = ["BaseCrawler", "ContentFilter"] 