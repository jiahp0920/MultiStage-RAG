"""
监控相关路由
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import time
import psutil
import os

from ..schemas import (
    HealthCheckResponse,
    MetricsResponse,
    ErrorResponse,
    ErrorCode
)
from ...utils.logger import get_logger

router = APIRouter(prefix="/monitor", tags=["monitoring"])
logger = get_logger(__name__)

# 服务启动时间
_start_time = time.time()


@router.get(
    "/health",
    response_model=HealthCheckResponse,
    responses={
        500: {"model": ErrorResponse},
        503: {"model": ErrorResponse}
    }
)
async def health_check() -> HealthCheckResponse:
    """
    健康检查端点

    返回服务状态和组件健康状态
    """
    try:
        uptime = time.time() - _start_time

        # 检查关键组件状态
        components = {
            "api": "healthy",
            "memory": "healthy",
            "disk": "healthy"
        }

        # 检查内存使用
        memory_info = psutil.virtual_memory()
        if memory_info.percent > 90:
            components["memory"] = "warning"
            logger.warning(f"High memory usage: {memory_info.percent}%")

        # 检查磁盘使用
        disk_info = psutil.disk_usage('/')
        if disk_info.percent > 90:
            components["disk"] = "warning"
            logger.warning(f"High disk usage: {disk_info.percent}%")

        # 总体状态
        overall_status = "healthy"
        if "warning" in components.values():
            overall_status = "warning"

        response = HealthCheckResponse(
            status=overall_status,
            version="1.0.0",
            uptime_seconds=uptime,
            components=components
        )

        return response

    except Exception as e:
        logger.error(f"Health check failed: {str(e)}", exc_info=True)

        error_response = ErrorResponse(
            error=f"Health check failed: {str(e)}",
            error_code=ErrorCode.INTERNAL_ERROR
        )

        raise HTTPException(status_code=500, detail=error_response.dict())


@router.get(
    "/metrics",
    response_model=MetricsResponse,
    responses={500: {"model": ErrorResponse}}
)
async def get_metrics() -> MetricsResponse:
    """
    获取系统指标

    返回系统性能指标和检索统计
    """
    try:
        # 系统指标
        system_metrics = _get_system_metrics()

        # 检索指标（示例，实际应从检索器获取）
        retrieval_metrics = {
            "total_requests": 0,
            "average_latency_ms": 0,
            "cache_hit_rate": 0,
            "fallback_rate": 0
        }

        # 缓存指标（示例）
        cache_metrics = {
            "size": 0,
            "hit_rate": 0,
            "eviction_count": 0
        }

        response = MetricsResponse(
            retrieval_metrics=retrieval_metrics,
            cache_metrics=cache_metrics,
            system_metrics=system_metrics
        )

        return response

    except Exception as e:
        logger.error(f"Failed to get metrics: {str(e)}", exc_info=True)

        error_response = ErrorResponse(
            error=f"Failed to get metrics: {str(e)}",
            error_code=ErrorCode.INTERNAL_ERROR
        )

        raise HTTPException(status_code=500, detail=error_response.dict())


@router.get("/version")
async def get_version() -> Dict[str, Any]:
    """
    获取服务版本信息
    """
    return {
        "service": "MultiStage-RAG API",
        "version": "1.0.0",
        "build_date": "2024-01-01",
        "api_version": "v1"
    }


@router.get("/info")
async def get_service_info() -> Dict[str, Any]:
    """
    获取服务详细信息
    """
    try:
        # 系统信息
        system_info = {
            "python_version": os.sys.version,
            "platform": os.sys.platform,
            "processor": os.uname().machine if hasattr(os, 'uname') else "unknown",
            "hostname": os.uname().nodename if hasattr(os, 'uname') else "unknown"
        }

        # 进程信息
        process = psutil.Process()
        process_info = {
            "pid": process.pid,
            "create_time": process.create_time(),
            "cpu_percent": process.cpu_percent(),
            "memory_percent": process.memory_percent(),
            "num_threads": process.num_threads()
        }

        # 服务信息
        service_info = {
            "uptime_seconds": time.time() - _start_time,
            "start_time": time.ctime(_start_time),
            "current_time": time.ctime()
        }

        return {
            "success": True,
            "system": system_info,
            "process": process_info,
            "service": service_info,
            "timestamp": time.time()
        }

    except Exception as e:
        logger.error(f"Failed to get service info: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


def _get_system_metrics() -> Dict[str, Any]:
    """获取系统指标"""
    try:
        # CPU使用率
        cpu_percent = psutil.cpu_percent(interval=0.1)

        # 内存使用
        memory = psutil.virtual_memory()

        # 磁盘使用
        disk = psutil.disk_usage('/')

        # 网络IO
        net_io = psutil.net_io_counters()

        # 加载平均值（仅Linux/Unix）
        load_avg = psutil.getloadavg() if hasattr(psutil, 'getloadavg') else (0, 0, 0)

        return {
            "cpu": {
                "percent": cpu_percent,
                "cores": psutil.cpu_count(),
                "load_avg": load_avg
            },
            "memory": {
                "total_gb": memory.total / (1024 ** 3),
                "available_gb": memory.available / (1024 ** 3),
                "percent": memory.percent,
                "used_gb": memory.used / (1024 ** 3)
            },
            "disk": {
                "total_gb": disk.total / (1024 ** 3),
                "used_gb": disk.used / (1024 ** 3),
                "free_gb": disk.free / (1024 ** 3),
                "percent": disk.percent
            },
            "network": {
                "bytes_sent": net_io.bytes_sent,
                "bytes_recv": net_io.bytes_recv,
                "packets_sent": net_io.packets_sent,
                "packets_recv": net_io.packets_recv
            }
        }

    except Exception as e:
        logger.error(f"Failed to get system metrics: {str(e)}")
        return {
            "error": str(e),
            "timestamp": time.time()
        }