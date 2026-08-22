"""Ingestion module for loading and chunking documents."""

from .loader import DocumentLoader
from .chunker import DocumentChunker

__all__ = ["DocumentLoader", "DocumentChunker"]
