"""
ChromaDB向量存储实现（默认）
"""
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
import uuid
from ...core.models import Document
from .base import VectorStore
from ...utils.logger import get_logger


class ChromaVectorStore(VectorStore):
    """ChromaDB向量存储"""

    def __init__(self, config: Dict[str, Any]):
        self.logger = get_logger(__name__)
        self.config = config

        # 提取配置
        persist_directory = config.get("persist_directory", "./data/chroma_db")
        collection_name = config.get("collection_name", "documents")
        embedding_model = config.get("embedding_model", "all-MiniLM-L6-v2")

        # 初始化Chroma客户端
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )

        # 创建或获取集合
        self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=embedding_model
        )

        try:
            self.collection = self.client.get_collection(
                name=collection_name,
                embedding_function=self.embedding_function
            )
            self.logger.info(f"Loaded existing collection: {collection_name}")
        except Exception:
            self.collection = self.client.create_collection(
                name=collection_name,
                embedding_function=self.embedding_function,
                metadata={"hnsw:space": "cosine"}
            )
            self.logger.info(f"Created new collection: {collection_name}")

    def search(self, query: str, top_k: int, filters: Optional[Dict] = None) -> List[Document]:
        """搜索相似文档"""
        try:
            # 转换过滤器格式
            where_filter = None
            if filters:
                where_filter = {}
                for key, value in filters.items():
                    if isinstance(value, list):
                        where_filter[key] = {"$in": value}
                    else:
                        where_filter[key] = {"$eq": value}

            # 执行搜索
            results = self.collection.query(
                query_texts=[query],
                n_results=top_k,
                where=where_filter,
                include=["metadatas", "documents", "distances"]
            )

            # 转换为Document对象
            documents = []
            if results["documents"]:
                for i in range(len(results["documents"][0])):
                    doc_id = results["ids"][0][i]
                    content = results["documents"][0][i]
                    metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                    distance = results["distances"][0][i] if results["distances"] else 0

                    # 将距离转换为相似度分数
                    similarity_score = 1.0 - distance if distance <= 1.0 else 1.0 / (1.0 + distance)

                    document = Document(
                        id=doc_id,
                        content=content,
                        metadata=metadata,
                        vector_score=similarity_score
                    )
                    documents.append(document)

            self.logger.debug(f"Search returned {len(documents)} documents")
            return documents

        except Exception as e:
            self.logger.error(f"Search failed: {str(e)}")
            return []

    def add_documents(self, documents: List[Document]) -> List[str]:
        """添加文档"""
        try:
            ids = []
            texts = []
            metadatas = []

            for doc in documents:
                doc_id = doc.id or str(uuid.uuid4())
                ids.append(doc_id)
                texts.append(doc.content)
                metadatas.append(doc.metadata)

            # 批量添加
            self.collection.add(
                ids=ids,
                documents=texts,
                metadatas=metadatas
            )

            self.logger.info(f"Added {len(ids)} documents to ChromaDB")
            return ids

        except Exception as e:
            self.logger.error(f"Failed to add documents: {str(e)}")
            raise

    def delete_documents(self, document_ids: List[str]) -> bool:
        """删除文档"""
        try:
            self.collection.delete(ids=document_ids)
            self.logger.info(f"Deleted {len(document_ids)} documents")
            return True
        except Exception as e:
            self.logger.error(f"Failed to delete documents: {str(e)}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        try:
            count = self.collection.count()
            return {
                "type": "chroma",
                "document_count": count,
                "collection": self.collection.name,
                "config": self.config
            }
        except Exception as e:
            self.logger.error(f"Failed to get stats: {str(e)}")
            return {"type": "chroma", "error": str(e)}

    def close(self):
        """关闭连接"""
        # Chroma持久化客户端会自动保存
        pass