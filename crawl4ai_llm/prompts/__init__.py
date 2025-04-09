"""
Prompt templates for LLM-based extraction.
"""

from .product_extraction import (
    SCHEMA_GENERATION_PROMPT,
    LLM_EXTRACTION_PROMPT,
    FALLBACK_EXTRACTION_PROMPT
)

__all__ = [
    "SCHEMA_GENERATION_PROMPT",
    "LLM_EXTRACTION_PROMPT",
    "FALLBACK_EXTRACTION_PROMPT"
] 