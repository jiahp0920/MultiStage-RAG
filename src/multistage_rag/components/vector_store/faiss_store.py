"""
FAISS向量存储实现
"""
from typing import List, Dict, Any, Optional
import numpy as np
import faiss
import pickle
import os
from sentence_transformers import SentenceTransformer
import uuid
from ...core.models import Document
from .base import VectorStore
from ...utils.logger import get_logger


class FAISSVectorStore(VectorStore):
    """FAISS向量存储"""

    def __init__(self, config: Dict[str, Any]):
        self.logger = get_logger(__name__)
        self.config = config

        # 提取配置
        self.index_path = config.get("index_path", "./data/faiss_index")
        self.dimension = config.get("dimension", 384)
        self.embedding_model_name = config.get("embedding_model", "all-MiniLM-L6-v2")

        # 创建目录
        os.makedirs(os.path.dirname(self.index_path), exist_ok=True)

        # 加载嵌入模型
        self.embedding_model = SentenceTransformer(self.embedding_model_name)

        # 加载或创建索引
        self.index = self._load_or_create_index()

        # 存储文档元数据
        self.documents_metadata = {}
        self._load_metadata()

    def _load_or_create_index(self):
        """加载或创建FAISS索引"""
        index_file = f"{self.index_path}.index"
        if os.path.exists(index_file):
            self.logger.info(f"Loading existing FAISS index: {index_file}")
            return faiss.read_index(index_file)
        else:
            self.logger.info(f"Creating new FAISS index with dimension {self.dimension}")
            # 使用内积相似度（余弦相似度）
            index = faiss.IndexFlatIP(self.dimension)
            return index

    def _load_metadata(self):
        """加载元数据"""
        metadata_file = f"{self.index_path}.meta"
        if os.path.exists(metadata_file):
            with open(metadata_file, 'rb') as f:
                self.documents_metadata = pickle.load(f)

    def _save_metadata(self):
        """保存元数据"""
        metadata_file = f"{self.index_path}.meta"
        with open(metadata_file, 'wb') as f:
            pickle.dump(self.documents_metadata, f)

    def _save_index(self):
        """保存索引"""
        index_file = f"{self.index_path}.index"
        faiss.write_index(self.index, index_file)

    def search(self, query: str, top_k: int, filters: Optional[Dict] = None) -> List[Document]:
        """搜索相似文档"""
        try:
            # 生成查询向量
            query_embedding = self.embedding_model.encode([query])
            query_embedding = query_embedding.astype('float32')

            # L2归一化以使用内积计算余弦相似度
            faiss.normalize_L2(query_embedding)

            # 搜索
            distances, indices = self.index.search(query_embedding, top_k)

            # 转换为Document对象
            documents = []
            for i in range(len(indices[0])):
                idx = indices[0][i]
                if idx == -1:  # 没有更多结果
                    continue

                # 获取文档元数据
                doc_id = list(self.documents_metadata.keys())[idx]
                metadata = self.documents_metadata.get(doc_id, {})

                # 获取内容（需要从单独存储中获取）
                content = metadata.get("content", "")

                # 距离转换为相似度分数
                similarity = float(distances[0][i])

                document = Document(
                    id=doc_id,
                    content=content,
                    metadata=metadata,
                    vector_score=similarity
                )
                documents.append(document)

            self.logger.debug(f"FAISS search returned {len(documents)} documents")
            return documents

        except Exception as e:
            self.logger.error(f"FAISS search failed: {str(e)}")
            return []

    def add_documents(self, documents: List[Document]) -> List[str]:
        """添加文档"""
        try:
            ids = []
            embeddings = []

            # 准备批量添加
            batch_size = 32
            for i in range(0, len(documents), batch_size):
                batch = documents[i:i + batch_size]
                batch_texts = [doc.content for doc in batch]

                # 生成嵌入
                batch_embeddings = self.embedding_model.encode(batch_texts)
                batch_embeddings = batch_embeddings.astype('float32')

                # L2归一化
                faiss.normalize_L2(batch_embeddings)

                embeddings.append(batch_embeddings)

                # 存储元数据
                for doc in batch:
                    doc_id = doc.id or str(uuid.uuid4())
                    ids.append(doc_id)

                    # 存储完整文档内容到元数据
                    self.documents_metadata[doc_id] = {
                        **doc.metadata,
                        "content": doc.content,
                        "added_at": np.datetime64('now')
                    }

            # 合并所有嵌入并添加到索引
            if embeddings:
                all_embeddings = np.vstack(embeddings)
                self.index.add(all_embeddings)

                # 保存
                self._save_index()
                self._save_metadata()

            self.logger.info(f"Added {len(ids)} documents to FAISS")
            return ids

        except Exception as e:
            self.logger.error(f"Failed to add documents to FAISS: {str(e)}")
            raise

    def delete_documents(self, document_ids: List[str]) -> bool:
        """删除文档 - FAISS不支持直接删除，需要重建索引"""
        self.logger.warning("FAISS doesn't support direct deletion, need to rebuild index")
        return False

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "type": "faiss",
            "document_count": self.index.ntotal,
            "dimension": self.dimension,
            "embedding_model": self.embedding_model_name,
            "config": self.config
        }

    def close(self):
        """关闭连接"""
        # 保存索引和元数据
        self._save_index()
        self._save_metadata()