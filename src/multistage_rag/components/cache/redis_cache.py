"""
Redis缓存实现（默认）
"""
import redis.asyncio as redis
from typing import Optional, Dict, Any
import json
from .base import BaseCache
from ...utils.logger import get_logger


class RedisCache(BaseCache):
    """Redis缓存"""

    def __init__(self, config: Dict[str, Any]):
        self.logger = get_logger(__name__)
        self.config = config

        # 提取配置
        host = config.get("host", "localhost")
        port = config.get("port", 6379)
        db = config.get("db", 0)
        password = config.get("password")
        key_prefix = config.get("key_prefix", "multistage_rag:")

        # 连接Redis
        self.client = redis.Redis(
            host=host,
            port=port,
            db=db,
            password=password,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5
        )

        self.key_prefix = key_prefix
        self.logger.info(f"Redis cache connected to {host}:{port}")

    def _format_key(self, key: str) -> str:
        """格式化键名"""
        return f"{self.key_prefix}{key}"

    async def get(self, key: str) -> Optional[str]:
        """获取缓存"""
        try:
            full_key = self._format_key(key)
            value = await self.client.get(full_key)
            return value
        except Exception as e:
            self.logger.error(f"Redis get failed: {str(e)}")
            return None

    async def set(self, key: str, value: str, ttl: Optional[int] = None) -> bool:
        """设置缓存"""
        try:
            full_key = self._format_key(key)

            if ttl:
                await self.client.setex(full_key, ttl, value)
            else:
                await self.client.set(full_key, value)

            return True
        except Exception as e:
            self.logger.error(f"Redis set failed: {str(e)}")
            return False

    async def delete(self, key: str) -> bool:
        """删除缓存"""
        try:
            full_key = self._format_key(key)
            result = await self.client.delete(full_key)
            return result > 0
        except Exception as e:
            self.logger.error(f"Redis delete failed: {str(e)}")
            return False

    async def exists(self, key: str) -> bool:
        """检查是否存在"""
        try:
            full_key = self._format_key(key)
            result = await self.client.exists(full_key)
            return result > 0
        except Exception as e:
            self.logger.error(f"Redis exists failed: {str(e)}")
            return False

    async def clear(self) -> bool:
        """清空缓存（按前缀）"""
        try:
            pattern = f"{self.key_prefix}*"
            keys = await self.client.keys(pattern)

            if keys:
                await self.client.delete(*keys)

            self.logger.info(f"Cleared {len(keys)} cache keys")
            return True
        except Exception as e:
            self.logger.error(f"Redis clear failed: {str(e)}")
            return False

    async def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        try:
            info = await self.client.info()
            pattern = f"{self.key_prefix}*"
            keys = await self.client.keys(pattern)

            return {
                "type": "redis",
                "key_count": len(keys),
                "memory_used": info.get("used_memory", 0),
                "connected_clients": info.get("connected_clients", 0),
                "key_prefix": self.key_prefix
            }
        except Exception as e:
            self.logger.error(f"Redis stats failed: {str(e)}")
            return {"type": "redis", "error": str(e)}

    async def close(self):
        """关闭连接"""
        try:
            await self.client.close()
            self.logger.info("Redis connection closed")
        except Exception as e:
            self.logger.error(f"Redis close failed: {str(e)}")