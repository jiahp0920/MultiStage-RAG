"""
向量存储工厂
"""
from typing import Dict, Any
import importlib
from .base import VectorStore
from ...utils.logger import get_logger


class VectorStoreFactory:
    """向量存储工厂类"""

    @staticmethod
    def create(config: Dict[str, Any]) -> VectorStore:
        """创建向量存储实例"""
        logger = get_logger(__name__)

        # 获取向量存储类型
        store_type = config.get("type", "chroma")
        logger.info(f"Creating vector store of type: {store_type}")

        # 动态导入对应的模块
        try:
            module_name = f"multistage_rag.components.vector_store.{store_type}_store"
            module = importlib.import_module(module_name)

            # 查找VectorStore的子类
            for attr_name in dir(module):
                attr = getattr(module, attr_name)

                if (isinstance(attr, type) and
                        issubclass(attr, VectorStore) and
                        attr != VectorStore):
                    # 提取该类型的配置
                    type_config = config.get(store_type, {})

                    # 创建实例
                    instance = attr(type_config)
                    logger.info(f"Successfully created vector store: {store_type}")
                    return instance

            raise ValueError(f"No VectorStore implementation found for type: {store_type}")

        except ImportError as e:
            logger.error(f"Failed to import vector store module: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Failed to create vector store: {str(e)}")
            raise