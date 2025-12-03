"""
API数据模型
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field, validator, field_validator


class DocumentSchema(BaseModel):
    """文档模式"""
    id: str = Field(..., description="文档ID")
    content: str = Field(..., min_length=1, max_length=10000, description="文档内容")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="文档元数据")
    score: Optional[float] = Field(None, description="相关性分数", ge=0.0, le=1.0)


class RetrievalRequest(BaseModel):
    """检索请求"""
    query: str = Field(..., min_length=1, max_length=1000, description="查询文本")
    top_k: Optional[int] = Field(5, ge=1, le=100, description="返回文档数量")
    filters: Optional[Dict[str, Any]] = Field(None, description="过滤条件")
    use_cache: bool = Field(True, description="是否使用缓存")
    enable_stages: Optional[Dict[str, bool]] = Field(
        None,
        description="启用哪些阶段，例如: {'recall': True, 'pre_rank': True, 're_rank': True}"
    )

    @field_validator('enable_stages')
    def validate_enable_stages(cls, v):
        if v is not None:
            valid_stages = {'recall', 'pre_rank', 're_rank'}
            for stage in v.keys():
                if stage not in valid_stages:
                    raise ValueError(f"Invalid stage: {stage}. Valid stages: {valid_stages}")
        return v


class RetrievalResponse(BaseModel):
    """检索响应"""
    success: bool = Field(..., description="是否成功")
    query: str = Field(..., description="查询文本")
    documents: List[DocumentSchema] = Field(default_factory=list, description="检索到的文档")
    stage: str = Field(..., description="最终使用的阶段")
    latency_ms: float = Field(..., ge=0, description="耗时(毫秒)")
    cache_hit: bool = Field(False, description="是否命中缓存")
    fallback_triggered: bool = Field(False, description="是否触发降级")
    request_id: str = Field(..., description="请求ID")
    timestamp: datetime = Field(default_factory=datetime.now, description="时间戳")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class BatchRetrievalRequest(BaseModel):
    """批量检索请求"""
    queries: List[str] = Field(
        ...,
        min_items=1,
        max_items=10,
        description="查询列表（最多10个）"
    )
    top_k: Optional[int] = Field(5, ge=1, le=50, description="每个查询返回文档数量")
    filters: Optional[Dict[str, Any]] = Field(None, description="过滤条件")
    use_cache: bool = Field(True, description="是否使用缓存")


class BatchRetrievalResponse(BaseModel):
    """批量检索响应"""
    success: bool = Field(..., description="是否成功")
    results: List[RetrievalResponse] = Field(..., description="检索结果列表")
    total_queries: int = Field(..., description="总查询数量")
    successful_queries: int = Field(..., description="成功查询数量")
    request_id: str = Field(..., description="请求ID")
    timestamp: datetime = Field(default_factory=datetime.now, description="时间戳")


class DocumentAddRequest(BaseModel):
    """添加文档请求"""
    documents: List[DocumentSchema] = Field(
        ...,
        min_items=1,
        max_items=100,
        description="文档列表"
    )
    overwrite: bool = Field(False, description="是否覆盖已存在的文档")


class DocumentAddResponse(BaseModel):
    """添加文档响应"""
    success: bool = Field(..., description="是否成功")
    added_count: int = Field(..., description="添加的文档数量")
    document_ids: List[str] = Field(..., description="文档ID列表")
    skipped_ids: List[str] = Field(default_factory=list, description="跳过的文档ID")
    request_id: str = Field(..., description="请求ID")
    timestamp: datetime = Field(default_factory=datetime.now, description="时间戳")


class DocumentDeleteRequest(BaseModel):
    """删除文档请求"""
    document_ids: List[str] = Field(..., min_items=1, description="要删除的文档ID列表")


class DocumentDeleteResponse(BaseModel):
    """删除文档响应"""
    success: bool = Field(..., description="是否成功")
    deleted_count: int = Field(..., description="删除的文档数量")
    failed_ids: List[str] = Field(default_factory=list, description="删除失败的文档ID")
    request_id: str = Field(..., description="请求ID")
    timestamp: datetime = Field(default_factory=datetime.now, description="时间戳")


class HealthCheckResponse(BaseModel):
    """健康检查响应"""
    status: str = Field(..., description="服务状态")
    version: str = Field(..., description="服务版本")
    uptime_seconds: float = Field(..., description="运行时间(秒)")
    components: Dict[str, str] = Field(..., description="组件状态")
    timestamp: datetime = Field(default_factory=datetime.now, description="时间戳")


class MetricsResponse(BaseModel):
    """指标响应"""
    retrieval_metrics: Dict[str, Any] = Field(..., description="检索指标")
    cache_metrics: Dict[str, Any] = Field(default_factory=dict, description="缓存指标")
    system_metrics: Dict[str, Any] = Field(default_factory=dict, description="系统指标")
    timestamp: datetime = Field(default_factory=datetime.now, description="时间戳")


class ErrorResponse(BaseModel):
    """错误响应"""
    success: bool = Field(False, description="是否成功")
    error: str = Field(..., description="错误信息")
    error_code: str = Field("INTERNAL_ERROR", description="错误代码")
    request_id: Optional[str] = Field(None, description="请求ID")
    timestamp: datetime = Field(default_factory=datetime.now, description="时间戳")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# 错误代码枚举
class ErrorCode:
    """错误代码"""
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    RATE_LIMITED = "RATE_LIMITED"
    INVALID_REQUEST = "INVALID_REQUEST"
    NOT_FOUND = "NOT_FOUND"
    UNAUTHORIZED = "UNAUTHORIZED"