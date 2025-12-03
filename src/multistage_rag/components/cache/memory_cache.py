"""
内存缓存实现
"""
import time
from typing import Optional, Dict, Any
import asyncio
from collections import OrderedDict
from .base import BaseCache
from ...utils.logger import get_logger


class MemoryCache(BaseCache):
    """内存缓存（LRU策略）"""

    def __init__(self, config: Dict[str, Any]):
        self.logger = get_logger(__name__)
        self.config = config

        # 提取配置
        max_size = config.get("max_size", 1000)
        self.ttl = config.get("default_ttl", 300)  # 默认5分钟

        # 使用OrderedDict实现LRU缓存
        self.cache = OrderedDict()
        self.max_size = max_size

        # 缓存统计
        self.stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "evictions": 0
        }

        self.logger.info(f"Memory cache initialized with max_size={max_size}")

    async def get(self, key: str) -> Optional[str]:
        """获取缓存"""
        try:
            if key in self.cache:
                entry = self.cache[key]

                # 检查是否过期
                if entry["expires_at"] and time.time() > entry["expires_at"]:
                    del self.cache[key]
                    self.stats["misses"] += 1
                    return None

                # 移动到最近使用位置（LRU）
                self.cache.move_to_end(key)
                self.stats["hits"] += 1
                return entry["value"]
            else:
                self.stats["misses"] += 1
                return None

        except Exception as e:
            self.logger.error(f"Memory cache get failed: {str(e)}")
            return None

    async def set(self, key: str, value: str, ttl: Optional[int] = None) -> bool:
        """设置缓存"""
        try:
            # 计算过期时间
            expires_at = None
            if ttl is not None:
                expires_at = time.time() + ttl
            elif self.ttl is not None:
                expires_at = time.time() + self.ttl

            # 如果缓存已满，移除最旧的条目
            if len(self.cache) >= self.max_size:
                oldest_key = next(iter(self.cache))
                del self.cache[oldest_key]
                self.stats["evictions"] += 1

            # 设置新条目
            self.cache[key] = {
                "value": value,
                "expires_at": expires_at,
                "created_at": time.time(),
                "access_count": 0
            }

            self.stats["sets"] += 1
            return True

        except Exception as e:
            self.logger.error(f"Memory cache set failed: {str(e)}")
            return False

    async def delete(self, key: str) -> bool:
        """删除缓存"""
        try:
            if key in self.cache:
                del self.cache[key]
                self.stats["deletes"] += 1
                return True
            return False
        except Exception as e:
            self.logger.error(f"Memory cache delete failed: {str(e)}")
            return False

    async def exists(self, key: str) -> bool:
        """检查是否存在"""
        try:
            if key in self.cache:
                entry = self.cache[key]
                # 检查是否过期
                if entry["expires_at"] and time.time() > entry["expires_at"]:
                    del self.cache[key]
                    return False
                return True
            return False
        except Exception as e:
            self.logger.error(f"Memory cache exists failed: {str(e)}")
            return False

    async def clear(self) -> bool:
        """清空缓存"""
        try:
            count = len(self.cache)
            self.cache.clear()
            self.logger.info(f"Cleared {count} cache entries")
            return True
        except Exception as e:
            self.logger.error(f"Memory cache clear failed: {str(e)}")
            return False

    def _clean_expired(self):
        """清理过期条目"""
        expired_keys = []
        current_time = time.time()

        for key, entry in self.cache.items():
            if entry["expires_at"] and current_time > entry["expires_at"]:
                expired_keys.append(key)

        for key in expired_keys:
            del self.cache[key]

        return len(expired_keys)

    async def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        try:
            # 清理过期条目
            expired_count = self._clean_expired()

            hits = self.stats["hits"]
            misses = self.stats["misses"]
            total = hits + misses
            hit_rate = hits / total if total > 0 else 0

            return {
                "type": "memory",
                "current_size": len(self.cache),
                "max_size": self.max_size,
                "hit_rate": hit_rate,
                "hits": hits,
                "misses": misses,
                "sets": self.stats["sets"],
                "deletes": self.stats["deletes"],
                "evictions": self.stats["evictions"],
                "expired_cleaned": expired_count
            }
        except Exception as e:
            self.logger.error(f"Memory cache stats failed: {str(e)}")
            return {"type": "memory", "error": str(e)}

    async def close(self):
        """关闭缓存"""
        self.logger.info("Memory cache closed")
        self.cache.clear()