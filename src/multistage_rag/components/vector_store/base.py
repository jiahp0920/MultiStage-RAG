"""
向量存储基类
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from ...core.models import Document


class VectorStore(ABC):
    """向量存储基类（具体实现）"""

    @abstractmethod
    def __init__(self, config: Dict[str, Any]):
        pass

    @abstractmethod
    def search(self, query: str, top_k: int, filters: Optional[Dict] = None) -> List[Document]:
        pass

    @abstractmethod
    def add_documents(self, documents: List[Document]) -> List[str]:
        pass

    @abstractmethod
    def delete_documents(self, document_ids: List[str]) -> bool:
        pass

    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    def close(self):
        pass