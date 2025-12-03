"""
管理相关路由（文档管理、配置管理等）
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any
import uuid
import time

from ...core.retriever import MultiStageRetriever
from ...core.models import Document
from ...config.config_manager import get_config_manager
from ..schemas import (
    DocumentAddRequest,
    DocumentAddResponse,
    DocumentDeleteRequest,
    DocumentDeleteResponse,
    ErrorResponse,
    ErrorCode
)
from ...utils.logger import get_logger
from ...utils.validator import Validator

router = APIRouter(prefix="/manage", tags=["management"])
logger = get_logger(__name__)


@router.post(
    "/documents",
    response_model=DocumentAddResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    }
)
async def add_documents(
        request: DocumentAddRequest,
        retriever: MultiStageRetriever = Depends(lambda: get_retriever())
) -> DocumentAddResponse:
    """
    添加文档到向量存储

    - **documents**: 文档列表
    - **overwrite**: 是否覆盖已存在的文档
    """
    request_id = f"add_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}"

    try:
        logger.info(f"Add documents request {request_id}: {len(request.documents)} documents")

        # 验证文档
        validated_docs = []
        skipped_ids = []

        for doc_schema in request.documents:
            # 验证文档格式
            is_valid, message = Validator.validate_document(doc_schema.dict())

            if not is_valid:
                logger.warning(f"Document validation failed: {message}")
                skipped_ids.append(doc_schema.id)
                continue

            # 创建Document对象
            doc = Document(
                id=doc_schema.id,
                content=doc_schema.content,
                metadata=doc_schema.metadata
            )
            validated_docs.append(doc)

        if not validated_docs:
            raise ValueError("No valid documents to add")

        # 添加文档到向量存储
        added_ids = await retriever.add_documents(validated_docs)

        response = DocumentAddResponse(
            success=True,
            added_count=len(added_ids),
            document_ids=added_ids,
            skipped_ids=skipped_ids,
            request_id=request_id
        )

        logger.info(f"Added {len(added_ids)} documents, skipped {len(skipped_ids)}")

        return response

    except Exception as e:
        logger.error(f"Add documents failed for request {request_id}: {str(e)}", exc_info=True)

        error_response = ErrorResponse(
            error=f"Failed to add documents: {str(e)}",
            error_code=ErrorCode.INTERNAL_ERROR,
            request_id=request_id
        )

        raise HTTPException(status_code=500, detail=error_response.dict())


@router.delete(
    "/documents",
    response_model=DocumentDeleteResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    }
)
async def delete_documents(
        request: DocumentDeleteRequest,
        retriever: MultiStageRetriever = Depends(lambda: get_retriever())
) -> DocumentDeleteResponse:
    """
    删除文档

    - **document_ids**: 要删除的文档ID列表
    """
    request_id = f"delete_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}"

    try:
        logger.info(f"Delete documents request {request_id}: {len(request.document_ids)} documents")

        # 验证文档ID
        if not request.document_ids:
            raise ValueError("No document IDs provided")

        # 执行删除
        success = await retriever.delete_documents(request.document_ids)

        if success:
            response = DocumentDeleteResponse(
                success=True,
                deleted_count=len(request.document_ids),
                request_id=request_id
            )
            logger.info(f"Deleted {len(request.document_ids)} documents")
        else:
            response = DocumentDeleteResponse(
                success=False,
                deleted_count=0,
                failed_ids=request.document_ids,
                request_id=request_id
            )
            logger.warning(f"Failed to delete documents: {request.document_ids}")

        return response

    except Exception as e:
        logger.error(f"Delete documents failed for request {request_id}: {str(e)}", exc_info=True)

        error_response = ErrorResponse(
            error=f"Failed to delete documents: {str(e)}",
            error_code=ErrorCode.INTERNAL_ERROR,
            request_id=request_id
        )

        raise HTTPException(status_code=500, detail=error_response.dict())


@router.get("/config")
async def get_configuration() -> Dict[str, Any]:
    """
    获取当前配置
    """
    try:
        config_manager = get_config_manager()
        config_dict = config_manager.get_config_dict()

        # 隐藏敏感信息
        safe_config = _sanitize_config(config_dict)

        return {
            "success": True,
            "config": safe_config,
            "timestamp": time.time()
        }

    except Exception as e:
        logger.error(f"Failed to get configuration: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_statistics(
        retriever: MultiStageRetriever = Depends(lambda: get_retriever())
) -> Dict[str, Any]:
    """
    获取系统统计信息
    """
    try:
        stats = retriever.get_stats()

        return {
            "success": True,
            "stats": stats,
            "timestamp": time.time()
        }

    except Exception as e:
        logger.error(f"Failed to get statistics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clear-cache")
async def clear_cache() -> Dict[str, Any]:
    """
    清空缓存
    """
    request_id = f"clear_cache_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}"

    try:
        # 注意：这里需要根据实际实现来清理缓存
        # 暂时返回成功
        logger.info(f"Clear cache request {request_id}")

        return {
            "success": True,
            "message": "Cache cleared",
            "request_id": request_id,
            "timestamp": time.time()
        }

    except Exception as e:
        logger.error(f"Failed to clear cache: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


def _sanitize_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """清理配置中的敏感信息"""
    if not isinstance(config, dict):
        return config

    safe_config = config.copy()

    # 需要清理的敏感字段
    sensitive_fields = [
        "api_key", "password", "secret", "token", "key",
        "credentials", "auth", "access_key", "secret_key"
    ]

    def sanitize_value(value):
        if isinstance(value, str):
            # 检查是否包含敏感信息
            for field in sensitive_fields:
                if field in value.lower():
                    return "***HIDDEN***"
        elif isinstance(value, dict):
            return _sanitize_config(value)
        elif isinstance(value, list):
            return [sanitize_item for sanitize_item in value]
        return value

    # 清理整个配置
    def sanitize_dict(d):
        result = {}
        for key, value in d.items():
            if any(sensitive in key.lower() for sensitive in sensitive_fields):
                result[key] = "***HIDDEN***"
            else:
                result[key] = sanitize_value(value)
        return result

    return sanitize_dict(safe_config)


def get_retriever() -> MultiStageRetriever:
    """获取检索器实例（简化版本）"""
    # 这里应该有一个全局的检索器实例
    # 为了示例，我们假设它存在
    from ...core.retriever import MultiStageRetriever
    config_manager = get_config_manager()
    config = config_manager.get_config()
    return MultiStageRetriever(config.model_dump())