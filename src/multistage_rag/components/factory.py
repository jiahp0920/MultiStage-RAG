"""
组件工厂主类
"""
import importlib
from typing import Dict, Any, Type, Optional
from .base import VectorStore, BaseReranker, BaseCache, BaseRule, BaseLLM
from ..utils.logger import get_logger


class ComponentFactory:
    """组件工厂基类"""

    _logger = get_logger(__name__)

    @classmethod
    def create_vector_store(cls, config: Dict[str, Any]) -> VectorStore:
        """创建向量存储"""
        return cls._create_component("vector_store", config, VectorStore)

    @classmethod
    def create_reranker(cls, config: Dict[str, Any]) -> BaseReranker:
        """创建重排序器"""
        return cls._create_component("reranker", config, BaseReranker)

    @classmethod
    def create_cache(cls, config: Dict[str, Any]) -> BaseCache:
        """创建缓存"""
        return cls._create_component("cache", config, BaseCache)

    @classmethod
    def create_llm(cls, config: Dict[str, Any]) -> BaseLLM:
        """创建LLM"""
        return cls._create_component("llm", config, BaseLLM)

    @classmethod
    def _create_component(cls, comp_type: str, config: Dict[str, Any],
                          base_class: Type) -> Any:
        """创建组件的通用方法"""
        # 获取组件类型名称
        component_name = config.get("type", "default")
        cls._logger.info(f"Creating {comp_type}: {component_name}")

        # 构建模块路径
        module_path = f"multistage_rag.components.{comp_type}.{component_name}"

        try:
            # 动态导入模块
            module = importlib.import_module(module_path)

            # 查找继承自base_class的类
            for attr_name in dir(module):
                attr = getattr(module, attr_name)

                if (isinstance(attr, type) and
                        issubclass(attr, base_class) and
                        attr != base_class):
                    # 提取该组件的配置
                    component_config = config.get(component_name, {})

                    # 创建实例
                    instance = attr(component_config)
                    cls._logger.info(f"Successfully created {comp_type}: {component_name}")
                    return instance

            raise ValueError(f"No valid {comp_type} class found in {module_path}")

        except ImportError as e:
            cls._logger.error(f"Failed to import module {module_path}: {str(e)}")
            # 尝试使用默认组件
            return cls._create_default_component(comp_type, config, base_class)
        except Exception as e:
            cls._logger.error(f"Failed to create {comp_type} {component_name}: {str(e)}")
            return cls._create_default_component(comp_type, config, base_class)

    @classmethod
    def _create_default_component(cls, comp_type: str, config: Dict[str, Any],
                                  base_class: Type) -> Any:
        """创建默认组件"""
        defaults = {
            "vector_store": "chroma",
            "reranker": "bailian",
            "cache": "redis",
            "llm": "openai"
        }

        default_name = defaults.get(comp_type)
        if not default_name:
            raise ValueError(f"No default component defined for {comp_type}")

        cls._logger.warning(f"Using default {comp_type}: {default_name}")

        # 更新配置使用默认组件
        config["type"] = default_name
        if default_name not in config:
            config[default_name] = {}

        # 递归调用，这次应该成功
        return cls._create_component(comp_type, config, base_class)


# 工厂别名，保持向后兼容
VectorStoreFactory = ComponentFactory
RerankerFactory = ComponentFactory
CacheFactory = ComponentFactory
LLMFactory = ComponentFactory