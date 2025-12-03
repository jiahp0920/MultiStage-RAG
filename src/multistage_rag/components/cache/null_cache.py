"""
空缓存实现（用于测试或禁用缓存）
"""
from typing import Optional, Dict, Any
from .base import BaseCache
from ...utils.logger import get_logger


class NullCache(BaseCache):
    """空缓存（所有操作都返回空或成功）"""

    def __init__(self, config: Dict[str, Any]):
        self.logger = get_logger(__name__)
        self.config = config
        self.logger.info("Null cache initialized (caching disabled)")

    async def get(self, key: str) -> Optional[str]:
        """获取缓存 - 总是返回None"""
        return None

    async def set(self, key: str, value: str, ttl: Optional[int] = None) -> bool:
        """设置缓存 - 总是返回成功"""
        return True

    async def delete(self, key: str) -> bool:
        """删除缓存 - 总是返回成功"""
        return True

    async def exists(self, key: str) -> bool:
        """检查是否存在 - 总是返回False"""
        return False

    async def clear(self) -> bool:
        """清空缓存 - 总是返回成功"""
        return True

    async def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        return {
            "type": "null",
            "message": "Caching is disabled",
            "size": 0
        }

    async def close(self):
        """关闭缓存"""
        self.logger.info("Null cache closed")