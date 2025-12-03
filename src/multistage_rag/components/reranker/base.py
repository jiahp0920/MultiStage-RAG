"""
重排序器基类
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from ...core.models import Document


class BaseReranker(ABC):
    """重排序器基类（具体实现）"""

    @abstractmethod
    def __init__(self, config: Dict[str, Any]):
        pass

    @abstractmethod
    async def rerank(self, query: str, documents: List[Document], top_k: int) -> List[Document]:
        pass

    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def close(self):
        pass