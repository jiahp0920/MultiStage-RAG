import numpy as np
from typing import List
from ..core.models import Document


class BM25Ranker:
    """BM25排序器"""

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.avg_doc_length = 0
        self.doc_lengths = []
        self.term_freqs = []
        self.doc_freqs = {}
        self.total_docs = 0

    def _tokenize(self, text: str) -> List[str]:
        """分词（简化版）"""
        # 生产环境应该用jieba等分词器
        return text.lower().split()

    def build_index(self, documents: List[Document]):
        """构建索引"""
        self.total_docs = len(documents)
        self.doc_lengths = []
        self.term_freqs = []
        self.doc_freqs = {}

        for doc in documents:
            tokens = self._tokenize(doc.content)
            self.doc_lengths.append(len(tokens))

            term_freq = {}
            for token in tokens:
                term_freq[token] = term_freq.get(token, 0) + 1
                self.doc_freqs[token] = self.doc_freqs.get(token, 0) + 1

            self.term_freqs.append(term_freq)

        self.avg_doc_length = sum(self.doc_lengths) / max(1, self.total_docs)

    def _idf(self, term: str) -> float:
        """逆文档频率"""
        if term not in self.doc_freqs:
            return 0
        df = self.doc_freqs[term]
        return np.log((self.total_docs - df + 0.5) / (df + 0.5) + 1.0)

    def score(self, query: str, doc_index: int) -> float:
        """计算BM25分数"""
        if doc_index >= self.total_docs:
            return 0.0

        query_tokens = self._tokenize(query)
        total_score = 0.0

        for token in query_tokens:
            if token not in self.term_freqs[doc_index]:
                continue

            tf = self.term_freqs[doc_index][token]
            idf = self._idf(token)
            doc_length = self.doc_lengths[doc_index]

            numerator = tf * (self.k1 + 1)
            denominator = tf + self.k1 * (1 - self.b + self.b * doc_length / self.avg_doc_length)
            total_score += idf * numerator / max(denominator, 1e-9)

        return total_score

    def rank(self, query: str, documents: List[Document]) -> List[Document]:
        """对文档进行BM25排序"""
        self.build_index(documents)

        for i, doc in enumerate(documents):
            doc.bm25_score = self.score(query, i)

        # 按BM25分数排序
        return sorted(documents, key=lambda x: x.bm25_score, reverse=True)