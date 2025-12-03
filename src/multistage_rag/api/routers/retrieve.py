"""
检索相关路由
"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import Dict, Any, Optional
import uuid
import time

from ...core.retriever import MultiStageRetriever
from ...config.config_manager import get_config_manager
from ..schemas import (
    RetrievalRequest,
    RetrievalResponse,
    BatchRetrievalRequest,
    BatchRetrievalResponse,
    ErrorResponse,
    ErrorCode
)
from ...utils.logger import get_logger

router = APIRouter(prefix="/retrieve", tags=["retrieval"])
logger = get_logger(__name__)

# 全局检索器实例
_retriever: Optional[MultiStageRetriever] = None


def get_retriever() -> MultiStageRetriever:
    """获取检索器实例"""
    global _retriever
    if _retriever is None:
        config_manager = get_config_manager()
        config = config_manager.get_config()
        _retriever = MultiStageRetriever(config.model_dump())
        logger.info("Retriever initialized")
    return _retriever


@router.post(
    "/single",
    response_model=RetrievalResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
        503: {"model": ErrorResponse}
    }
)
async def retrieve_documents(
        request: RetrievalRequest,
        background_tasks: BackgroundTasks,
        retriever: MultiStageRetriever = Depends(get_retriever)
) -> RetrievalResponse:
    """
    检索文档

    - **query**: 查询文本
    - **top_k**: 返回文档数量（默认5）
    - **filters**: 过滤条件
    - **use_cache**: 是否使用缓存
    - **enable_stages**: 启用哪些检索阶段
    """
    request_id = f"req_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}"

    try:
        logger.info(f"Retrieval request {request_id}: {request.query[:50]}...")

        # 执行检索
        result = await retriever.retrieve(
            query=request.query,
            top_k=request.top_k,
            filters=request.filters,
            use_cache=request.use_cache,
            enable_stages=request.enable_stages
        )

        # 转换为响应格式
        documents = []
        for doc in result.documents:
            documents.append({
                "id": doc.id,
                "content": doc.content[:500],  # 限制返回内容长度
                "metadata": doc.metadata,
                "score": doc.final_score
            })

        response = RetrievalResponse(
            success=True,
            query=request.query,
            documents=documents,
            stage=result.stage.value,
            latency_ms=result.latency_ms,
            cache_hit=result.cache_hit,
            fallback_triggered=result.fallback_triggered,
            request_id=request_id
        )

        # 后台记录指标
        background_tasks.add_task(
            log_retrieval_metrics,
            request_id,
            request.query,
            result
        )

        return response

    except Exception as e:
        logger.error(f"Retrieval failed for request {request_id}: {str(e)}", exc_info=True)

        error_response = ErrorResponse(
            error=f"Retrieval failed: {str(e)}",
            error_code=ErrorCode.INTERNAL_ERROR,
            request_id=request_id
        )

        raise HTTPException(status_code=500, detail=error_response.dict())


@router.post(
    "/batch",
    response_model=BatchRetrievalResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    }
)
async def batch_retrieve_documents(
        request: BatchRetrievalRequest,
        background_tasks: BackgroundTasks,
        retriever: MultiStageRetriever = Depends(get_retriever)
) -> BatchRetrievalResponse:
    """
    批量检索文档

    - **queries**: 查询列表（最多10个）
    - **top_k**: 每个查询返回文档数量
    - **filters**: 过滤条件
    - **use_cache**: 是否使用缓存
    """
    request_id = f"batch_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}"

    try:
        logger.info(f"Batch retrieval request {request_id}: {len(request.queries)} queries")

        results = []
        successful_queries = 0

        # 并行执行检索（实际使用时可以考虑使用asyncio.gather）
        for query in request.queries:
            try:
                result = await retriever.retrieve(
                    query=query,
                    top_k=request.top_k,
                    filters=request.filters,
                    use_cache=request.use_cache
                )

                # 转换为响应格式
                documents = []
                for doc in result.documents:
                    documents.append({
                        "id": doc.id,
                        "content": doc.content[:500],
                        "metadata": doc.metadata,
                        "score": doc.final_score
                    })

                retrieval_response = RetrievalResponse(
                    success=True,
                    query=query,
                    documents=documents,
                    stage=result.stage.value,
                    latency_ms=result.latency_ms,
                    cache_hit=result.cache_hit,
                    fallback_triggered=result.fallback_triggered,
                    request_id=f"{request_id}_{query[:10]}"
                )

                results.append(retrieval_response)
                successful_queries += 1

            except Exception as e:
                logger.error(f"Query failed in batch {request_id}: {query[:50]} - {str(e)}")
                # 继续处理其他查询

        response = BatchRetrievalResponse(
            success=successful_queries > 0,
            results=results,
            total_queries=len(request.queries),
            successful_queries=successful_queries,
            request_id=request_id
        )

        # 后台记录批量指标
        background_tasks.add_task(
            log_batch_metrics,
            request_id,
            len(request.queries),
            successful_queries
        )

        return response

    except Exception as e:
        logger.error(f"Batch retrieval failed for request {request_id}: {str(e)}", exc_info=True)

        error_response = ErrorResponse(
            error=f"Batch retrieval failed: {str(e)}",
            error_code=ErrorCode.INTERNAL_ERROR,
            request_id=request_id
        )

        raise HTTPException(status_code=500, detail=error_response.dict())


async def log_retrieval_metrics(request_id: str, query: str, result):
    """记录检索指标（后台任务）"""
    try:
        logger.info(f"Metrics for {request_id}: "
                    f"stage={result.stage.value}, "
                    f"latency={result.latency_ms:.2f}ms, "
                    f"docs={len(result.documents)}, "
                    f"cache_hit={result.cache_hit}, "
                    f"fallback={result.fallback_triggered}")
    except Exception as e:
        logger.error(f"Failed to log metrics for {request_id}: {str(e)}")


async def log_batch_metrics(request_id: str, total_queries: int, successful_queries: int):
    """记录批量检索指标（后台任务）"""
    try:
        success_rate = successful_queries / total_queries if total_queries > 0 else 0
        logger.info(f"Batch metrics for {request_id}: "
                    f"total={total_queries}, "
                    f"successful={successful_queries}, "
                    f"success_rate={success_rate:.2%}")
    except Exception as e:
        logger.error(f"Failed to log batch metrics for {request_id}: {str(e)}")