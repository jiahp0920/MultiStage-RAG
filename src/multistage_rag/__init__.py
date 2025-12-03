"""
MultiStage-RAG: A configurable multi-stage retrieval system.
"""

__version__ = "1.0.0"
__author__ = "MultiStage-RAG Team"

from .core.retriever import MultiStageRetriever
from .core.models import Document, RetrievalResult
from .api.app import MultiStageRAGAPI

__all__ = [
    "MultiStageRetriever",
    "Document",
    "RetrievalResult",
    "MultiStageRAGAPI",
]