"""
规则基类
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from ...core.models import Document


class BaseRule(ABC):
    """规则基类（具体实现）"""

    @abstractmethod
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.weight = config.get("weight", 1.0)
        self.name = self.__class__.__name__

    @abstractmethod
    def calculate_score(self, document: Document, query: Optional[str] = None) -> float:
        pass

    def get_description(self) -> str:
        return f"{self.name} (weight: {self.weight})"