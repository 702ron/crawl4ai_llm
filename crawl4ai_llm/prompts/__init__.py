"""
Prompt templates for LLM-based extraction.
"""

from .product_extraction import (FALLBACK_EXTRACTION_PROMPT,
                                 LLM_EXTRACTION_PROMPT,
                                 SCHEMA_GENERATION_PROMPT)

__all__ = [
    "SCHEMA_GENERATION_PROMPT",
    "LLM_EXTRACTION_PROMPT",
    "FALLBACK_EXTRACTION_PROMPT",
]
