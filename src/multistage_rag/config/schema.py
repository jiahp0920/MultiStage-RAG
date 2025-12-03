"""
配置数据模型 - 使用Pydantic进行验证
"""
from pydantic import BaseModel, Field, validator, field_validator
from typing import Dict, List, Optional, Any
from enum import Enum


class StageType(str, Enum):
    """阶段类型"""
    RECALL = "recall"
    PRE_RANK = "pre_rank"
    RE_RANK = "re_rank"


class VectorStoreType(str, Enum):
    """向量存储类型"""
    CHROMA = "chroma"
    FAISS = "faiss"
    MILVUS = "milvus"


class RerankerType(str, Enum):
    """重排序器类型"""
    BAILIAN = "bailian"
    BGE = "bge"
    COHERE = "cohere"


class CacheType(str, Enum):
    """缓存类型"""
    REDIS = "redis"
    MEMORY = "memory"
    NULL = "null"


class LLMType(str, Enum):
    """LLM类型"""
    OPENAI = "openai"
    QWEN = "qwen"


class StageConfig(BaseModel):
    """阶段配置基类"""
    enabled: bool = Field(default=True, description="是否启用该阶段")
    top_k: int = Field(default=100, ge=1, le=1000, description="返回文档数量")


class RecallConfig(StageConfig):
    """召回阶段配置"""
    top_k: int = Field(default=100, ge=1, le=500, description="召回文档数量")
    score_threshold: float = Field(default=0.0, ge=0.0, le=1.0, description="分数阈值")


class PreRankConfig(StageConfig):
    """粗排阶段配置"""
    top_k: int = Field(default=20, ge=1, le=200, description="粗排文档数量")
    bm25_weight: float = Field(default=0.7, ge=0.0, le=1.0, description="BM25权重")
    rule_weight: float = Field(default=0.3, ge=0.0, le=1.0, description="规则权重")
    bm25_k1: float = Field(default=1.5, description="BM25 k1参数")
    bm25_b: float = Field(default=0.75, description="BM25 b参数")


class ReRankConfig(StageConfig):
    """精排阶段配置"""
    top_k: int = Field(default=5, ge=1, le=50, description="精排文档数量")
    cache_ttl: int = Field(default=3600, ge=0, description="缓存过期时间(秒)")
    timeout: int = Field(default=3, ge=1, le=30, description="API超时时间(秒)")


class RetrievalConfig(BaseModel):
    """检索配置"""
    enabled_stages: Dict[str, bool] = Field(
        default_factory=lambda: {
            "recall": True,
            "pre_rank": True,
            "re_rank": True
        },
        description="启用哪些阶段"
    )

    stage_params: Dict[str, Dict[str, Any]] = Field(
        default_factory=lambda: {
            "recall": {"top_k": 100, "score_threshold": 0.0},
            "pre_rank": {"top_k": 20, "bm25_weight": 0.7, "rule_weight": 0.3},
            "re_rank": {"top_k": 5, "cache_ttl": 3600, "timeout": 3}
        },
        description="各阶段参数"
    )

    @field_validator('enabled_stages')
    def validate_enabled_stages(cls, v):
        valid_stages = {"recall", "pre_rank", "re_rank"}
        for stage in v.keys():
            if stage not in valid_stages:
                raise ValueError(f"Invalid stage: {stage}. Valid stages: {valid_stages}")
        return v


class VectorStoreConfig(BaseModel):
    """向量存储配置"""
    type: VectorStoreType = Field(default=VectorStoreType.CHROMA, description="向量存储类型")
    chroma: Dict[str, Any] = Field(
        default_factory=lambda: {
            "persist_directory": "./data/chroma_db",
            "collection_name": "documents"
        },
        description="ChromaDB配置"
    )
    faiss: Dict[str, Any] = Field(
        default_factory=lambda: {
            "index_path": "./data/faiss_index",
            "dimension": 384
        },
        description="FAISS配置"
    )
    milvus: Dict[str, Any] = Field(
        default_factory=lambda: {
            "host": "localhost",
            "port": 19530,
            "collection_name": "documents"
        },
        description="Milvus配置"
    )


class RerankerConfig(BaseModel):
    """重排序器配置"""
    type: RerankerType = Field(default=RerankerType.BAILIAN, description="重排序器类型")
    bailian: Dict[str, Any] = Field(
        default_factory=lambda: {
            "api_key": "",
            "endpoint": "https://dashscope.aliyuncs.com/api/v1/services/rerank",
            "model": "bailian-rerank-v1",
            "timeout": 3
        },
        description="阿里百炼配置"
    )
    bge: Dict[str, Any] = Field(
        default_factory=lambda: {
            "model_name": "BAAI/bge-reranker-large",
            "device": "cpu",
            "batch_size": 32
        },
        description="BGE配置"
    )
    cohere: Dict[str, Any] = Field(
        default_factory=lambda: {
            "api_key": "",
            "model": "rerank-english-v2.0"
        },
        description="Cohere配置"
    )


class RuleEngineConfig(BaseModel):
    """规则引擎配置"""
    enabled_rules: List[str] = Field(
        default_factory=lambda: ["recency", "authority", "keyword"],
        description="启用的规则列表"
    )
    rule_params: Dict[str, Dict[str, Any]] = Field(
        default_factory=lambda: {
            "recency": {"weight": 0.2, "recent_days": 7},
            "authority": {"weight": 0.3, "source_weights": {}},
            "keyword": {"weight": 0.5, "mandatory_keywords": []},
            "length": {"weight": 0.1, "ideal_min_length": 100, "ideal_max_length": 2000}
        },
        description="各规则参数"
    )


class CacheConfig(BaseModel):
    """缓存配置"""
    type: CacheType = Field(default=CacheType.REDIS, description="缓存类型")
    redis: Dict[str, Any] = Field(
        default_factory=lambda: {
            "host": "localhost",
            "port": 6379,
            "db": 0,
            "key_prefix": "multistage_rag:"
        },
        description="Redis配置"
    )
    memory: Dict[str, Any] = Field(
        default_factory=lambda: {
            "max_size": 1000,
            "default_ttl": 300
        },
        description="内存缓存配置"
    )
    null: Dict[str, Any] = Field(default_factory=dict, description="空缓存配置")


class LLMConfig(BaseModel):
    """LLM配置"""
    type: LLMType = Field(default=LLMType.OPENAI, description="LLM类型")
    openai: Dict[str, Any] = Field(
        default_factory=lambda: {
            "api_key": "",
            "model": "gpt-3.5-turbo",
            "temperature": 0.1,
            "max_tokens": 1000
        },
        description="OpenAI配置"
    )
    qwen: Dict[str, Any] = Field(
        default_factory=lambda: {
            "api_key": "",
            "model": "qwen-max",
            "temperature": 0.1,
            "max_tokens": 1000
        },
        description="通义千问配置"
    )


class MonitoringConfig(BaseModel):
    """监控配置"""
    enabled: bool = Field(default=True, description="是否启用监控")
    metrics_port: int = Field(default=9090, ge=1024, le=65535, description="指标端口")
    push_interval: int = Field(default=30, ge=1, description="推送间隔(秒)")


class FallbackConfig(BaseModel):
    """降级配置"""
    enabled: bool = Field(default=True, description="是否启用降级")
    strategy: str = Field(default="hybrid", description="降级策略")
    hybrid_weights: Dict[str, float] = Field(
        default_factory=lambda: {"vector": 0.4, "bm25": 0.4, "rule": 0.2},
        description="混合权重"
    )
    circuit_breaker: Dict[str, Any] = Field(
        default_factory=lambda: {
            "failure_threshold": 5,
            "recovery_timeout": 30,
            "timeout_threshold": 2000
        },
        description="熔断器配置"
    )


class AppConfig(BaseModel):
    """应用配置总模型"""
    app: Dict[str, Any] = Field(
        default_factory=lambda: {
            "name": "MultiStage-RAG",
            "version": "1.0.0",
            "log_level": "INFO",
            "environment": "production"
        },
        description="应用配置"
    )

    retrieval: RetrievalConfig = Field(default_factory=RetrievalConfig, description="检索配置")
    vector_store: VectorStoreConfig = Field(default_factory=VectorStoreConfig, description="向量存储配置")
    reranker: RerankerConfig = Field(default_factory=RerankerConfig, description="重排序器配置")
    rule_engine: RuleEngineConfig = Field(default_factory=RuleEngineConfig, description="规则引擎配置")
    cache: CacheConfig = Field(default_factory=CacheConfig, description="缓存配置")
    llm: LLMConfig = Field(default_factory=LLMConfig, description="LLM配置")
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig, description="监控配置")
    fallback: FallbackConfig = Field(default_factory=FallbackConfig, description="降级配置")

    class Config:
        json_schema_extra = {
            "example": {
                "app": {"name": "MultiStage-RAG", "version": "1.0.0"},
                "retrieval": {
                    "enabled_stages": {"recall": True, "pre_rank": True, "re_rank": True}
                }
            }
        }