"""
缓存组件工厂 - 专门负责创建缓存实例
"""
from typing import Dict, Any, Type
import importlib
from .base import BaseCache
from ..utils.logger import get_logger


class CacheFactory:
    """缓存工厂类 - 专门负责缓存组件的创建"""

    @staticmethod
    def create(config: Dict[str, Any]) -> BaseCache:
        """
        创建缓存实例

        Args:
            config: 缓存配置，必须包含 type 字段指定缓存类型

        Returns:
            BaseCache: 缓存实例

        Raises:
            ValueError: 配置无效或创建失败时抛出
        """
        logger = get_logger(__name__)

        # 获取缓存类型
        cache_type = config.get("type", "redis")
        logger.info(f"Creating cache of type: {cache_type}")

        # 验证配置
        if not cache_type:
            raise ValueError("Cache type must be specified in config")

        # 缓存类型到模块名的映射
        cache_module_map = {
            "redis": "redis_cache",
            "memory": "memory_cache",
            "null": "null_cache"
        }

        if cache_type not in cache_module_map:
            raise ValueError(f"Unsupported cache type: {cache_type}. "
                             f"Supported types: {list(cache_module_map.keys())}")

        # 获取模块名
        module_name = cache_module_map[cache_type]

        try:
            # 动态导入对应的缓存模块
            module_path = f"multistage_rag.components.cache.{module_name}"
            module = importlib.import_module(module_path)

            # 查找BaseCache的子类（类名遵循约定：模块名转驼峰 + "Cache"）
            expected_class_name = f"{module_name.replace('_', ' ').title().replace(' ', '')}Cache"
            logger.debug(f"Looking for cache class: {expected_class_name}")

            # 查找继承自BaseCache的具体实现类
            cache_class = None
            for attr_name in dir(module):
                attr = getattr(module, attr_name)

                if (isinstance(attr, type) and
                        issubclass(attr, BaseCache) and
                        attr != BaseCache):

                    # 如果类名符合预期，优先使用
                    if attr.__name__ == expected_class_name:
                        cache_class = attr
                        break
                    # 否则记录找到的其他实现
                    elif cache_class is None:
                        cache_class = attr

            if cache_class is None:
                raise ValueError(f"No valid cache implementation found in module: {module_path}")

            # 提取该类型的配置
            type_config = config.get(cache_type, {})

            # 创建缓存实例
            instance = cache_class(type_config)
            logger.info(f"Successfully created cache: {cache_type} ({cache_class.__name__})")

            return instance

        except ImportError as e:
            logger.error(f"Failed to import cache module '{module_name}': {str(e)}")
            raise ValueError(f"Cache type '{cache_type}' is not available. "
                             f"Make sure the required dependencies are installed.")
        except Exception as e:
            logger.error(f"Failed to create cache '{cache_type}': {str(e)}")
            raise

    @staticmethod
    def create_default() -> BaseCache:
        """
        创建默认缓存实例（Redis）

        Returns:
            BaseCache: 默认缓存实例
        """
        default_config = {
            "type": "redis",
            "redis": {
                "host": "localhost",
                "port": 6379,
                "db": 0
            }
        }
        return CacheFactory.create(default_config)

    @staticmethod
    def get_available_cache_types() -> Dict[str, Dict[str, Any]]:
        """
        获取所有可用的缓存类型及其信息

        Returns:
            Dict[str, Dict[str, Any]]: 缓存类型信息字典
        """
        return {
            "redis": {
                "description": "Redis缓存，适用于生产环境",
                "dependencies": ["redis>=5.0.0"],
                "config_fields": ["host", "port", "db", "password", "key_prefix"]
            },
            "memory": {
                "description": "内存缓存，适用于开发或测试环境",
                "dependencies": [],
                "config_fields": ["max_size", "default_ttl"]
            },
            "null": {
                "description": "空缓存，用于禁用缓存功能",
                "dependencies": [],
                "config_fields": []
            }
        }

    @staticmethod
    def validate_config(config: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证缓存配置

        Args:
            config: 待验证的配置

        Returns:
            Dict[str, Any]: 验证后的配置

        Raises:
            ValueError: 配置无效时抛出
        """
        if not isinstance(config, dict):
            raise ValueError("Cache config must be a dictionary")

        # 检查必填字段
        cache_type = config.get("type")
        if not cache_type:
            raise ValueError("Cache config must contain 'type' field")

        # 检查类型是否支持
        available_types = CacheFactory.get_available_cache_types()
        if cache_type not in available_types:
            raise ValueError(f"Unsupported cache type: {cache_type}. "
                             f"Supported types: {list(available_types.keys())}")

        # 检查类型特定配置
        type_config = config.get(cache_type, {})

        # Redis配置验证
        if cache_type == "redis":
            if not isinstance(type_config, dict):
                raise ValueError("Redis config must be a dictionary")

            # 设置默认值
            type_config.setdefault("host", "localhost")
            type_config.setdefault("port", 6379)
            type_config.setdefault("db", 0)
            type_config.setdefault("key_prefix", "multistage_rag:")

        # 内存缓存配置验证
        elif cache_type == "memory":
            if not isinstance(type_config, dict):
                raise ValueError("Memory cache config must be a dictionary")

            type_config.setdefault("max_size", 1000)
            type_config.setdefault("default_ttl", 300)

        # 空缓存不需要配置

        # 返回验证后的配置
        validated_config = config.copy()
        validated_config[cache_type] = type_config
        return validated_config


# 工厂别名，用于统一访问
create_cache = CacheFactory.create