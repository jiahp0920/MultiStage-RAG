"""
所有组件的抽象基类定义
遵循开闭原则：对扩展开放，对修改关闭
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union
from ..core.models import Document


class VectorStore(ABC):
    """向量存储基类"""

    @abstractmethod
    def search(self, query: str, top_k: int, filters: Optional[Dict] = None) -> List[Document]:
        """搜索相似文档"""
        pass

    @abstractmethod
    def add_documents(self, documents: List[Document]) -> List[str]:
        """添加文档"""
        pass

    @abstractmethod
    def delete_documents(self, document_ids: List[str]) -> bool:
        """删除文档"""
        pass

    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        pass

    @abstractmethod
    def close(self):
        """关闭连接"""
        pass


class BaseReranker(ABC):
    """重排序器基类"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    @abstractmethod
    async def rerank(self, query: str, documents: List[Document], top_k: int) -> List[Document]:
        """对文档进行重排序"""
        pass

    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        pass

    @abstractmethod
    async def close(self):
        """关闭资源"""
        pass


class BaseCache(ABC):
    """缓存基类"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    @abstractmethod
    async def get(self, key: str) -> Optional[str]:
        """获取缓存"""
        pass

    @abstractmethod
    async def set(self, key: str, value: str, ttl: Optional[int] = None) -> bool:
        """设置缓存"""
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """删除缓存"""
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """检查是否存在"""
        pass

    @abstractmethod
    async def clear(self) -> bool:
        """清空缓存"""
        pass

    @abstractmethod
    async def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        pass

    @abstractmethod
    async def close(self):
        """关闭连接"""
        pass


class BaseRule(ABC):
    """规则基类"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.weight = config.get("weight", 1.0)
        self.name = self.__class__.__name__

    @abstractmethod
    def calculate_score(self, document: Document, query: Optional[str] = None) -> float:
        """计算规则分数"""
        pass

    def get_description(self) -> str:
        """获取规则描述"""
        return f"Rule: {self.name}, Weight: {self.weight}"


class BaseLLM(ABC):
    """LLM基类"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> str:
        """生成文本"""
        pass

    @abstractmethod
    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """对话"""
        pass

    @abstractmethod
    async def close(self):
        """关闭连接"""
        pass