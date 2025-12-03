from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class StageType(str, Enum):
    """检索阶段类型"""
    RECALL = "recall"
    PRE_RANK = "pre_rank"
    RE_RANK = "re_rank"
    FALLBACK = "fallback"


@dataclass
class Document:
    """文档数据结构"""
    id: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    # 各阶段分数
    vector_score: float = 0.0
    bm25_score: float = 0.0
    rule_score: float = 0.0
    rerank_score: float = 0.0
    final_score: float = 0.0

    # 时间戳
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["created_at"] = self.created_at.isoformat()
        data["updated_at"] = self.updated_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Document":
        data = data.copy()
        for time_field in ["created_at", "updated_at"]:
            if time_field in data and isinstance(data[time_field], str):
                data[time_field] = datetime.fromisoformat(data[time_field])
        return cls(**data)


@dataclass
class RetrievalResult:
    """检索结果"""
    query: str
    documents: List[Document]
    stage: StageType
    latency_ms: float
    cache_hit: bool = False
    fallback_triggered: bool = False
    metrics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result["stage"] = self.stage.value
        result["documents"] = [doc.to_dict() for doc in self.documents]
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RetrievalResult":
        data = data.copy()
        data["stage"] = StageType(data["stage"])
        data["documents"] = [Document.from_dict(doc) for doc in data["documents"]]
        return cls(**data)


@dataclass
class StageMetrics:
    """阶段性能指标"""
    stage_name: str
    latency_ms: float
    input_count: int
    output_count: int
    success: bool = True
    error_message: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)


# API 数据模型
class RetrievalRequest(BaseModel):
    """检索请求"""
    query: str = Field(..., min_length=1, max_length=1000)
    top_k: Optional[int] = Field(None, ge=1, le=100)
    filters: Optional[Dict[str, Any]] = None
    use_cache: bool = True
    enable_stages: Optional[Dict[str, bool]] = None


class RetrievalResponse(BaseModel):
    """检索响应"""
    success: bool
    data: Optional[RetrievalResult] = None
    error: Optional[str] = None
    request_id: str


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str
    version: str
    components: Dict[str, str]
    timestamp: datetime