"""API endpoints for system metrics and monitoring.

This module provides endpoints for retrieving system performance metrics,
particularly focused on polling operations, background jobs, and API performance.
"""

import logging
from typing import Any

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from kiremisu.core.error_handler import create_standardized_error_response
from kiremisu.core.metrics import SystemMetrics, metrics_collector
from kiremisu.database.schemas import ErrorResponse

router = APIRouter(prefix="/api/metrics", tags=["metrics"])
logger = logging.getLogger(__name__)


class PollingMetricsResponse(BaseModel):
    """Schema for polling metrics response."""

    metrics: list[dict[str, Any]] = Field(..., description="List of polling metrics")
    total_operations: int = Field(..., description="Total number of operations")
    operation_type_filter: str | None = Field(None, description="Applied operation type filter")
    success_rate: float = Field(..., description="Success rate percentage")
    average_duration_ms: float = Field(
        ..., description="Average operation duration in milliseconds"
    )


class PerformanceStatsResponse(BaseModel):
    """Schema for performance statistics response."""

    metric_name: str = Field(..., description="Name of the performance metric")
    stats: dict[str, float] = Field(..., description="Performance statistics")


class SystemMetricsResponse(BaseModel):
    """Schema for system metrics response."""

    system_metrics: SystemMetrics = Field(..., description="Aggregated system metrics")
    timestamp: str = Field(..., description="Metrics timestamp")
    uptime_info: dict[str, Any] = Field(..., description="System uptime information")


@router.get(
    "/system",
    response_model=SystemMetricsResponse,
    responses={500: {"model": ErrorResponse, "description": "Internal server error"}},
)
async def get_system_metrics() -> SystemMetricsResponse:
    """Get comprehensive system metrics.

    Returns aggregated metrics including:
    - Polling operation statistics
    - API performance metrics
    - Background job statistics
    - Watching system metrics
    - System health indicators
    """
    try:
        system_metrics = metrics_collector.get_system_metrics()

        return SystemMetricsResponse(
            system_metrics=system_metrics,
            timestamp=system_metrics.last_updated.isoformat(),
            uptime_info={
                "metrics_collection_enabled": True,
                "total_metrics_collected": (
                    system_metrics.total_polling_operations + system_metrics.total_api_requests
                ),
            },
        )
    except Exception as e:
        logger.error(f"Error getting system metrics: {e}")
        error_response = create_standardized_error_response(
            status_code=500,
            message="Failed to retrieve system metrics",
            error_code="SYSTEM_METRICS_ERROR",
        )
        return JSONResponse(status_code=500, content=error_response)


@router.get(
    "/polling",
    response_model=PollingMetricsResponse,
    responses={500: {"model": ErrorResponse, "description": "Internal server error"}},
)
async def get_polling_metrics(
    operation_type: str | None = Query(None, description="Filter by operation type"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of metrics to return"),
) -> PollingMetricsResponse:
    """Get polling operation metrics.

    Returns detailed metrics for polling operations including:
    - Watching system polling
    - MangaDx API polling
    - Notification generation
    - Background job processing

    Args:
        operation_type: Filter metrics by operation type (e.g., 'watching_schedule_checks')
        limit: Maximum number of metrics to return
    """
    try:
        metrics = metrics_collector.get_polling_metrics(operation_type, limit)

        # Calculate summary statistics
        total_operations = len(metrics)
        successful_operations = sum(1 for m in metrics if m.get("success", False))
        success_rate = (
            (successful_operations / total_operations * 100) if total_operations > 0 else 0
        )

        durations = [m["duration_ms"] for m in metrics if m.get("duration_ms") is not None]
        average_duration = sum(durations) / len(durations) if durations else 0

        return PollingMetricsResponse(
            metrics=metrics,
            total_operations=total_operations,
            operation_type_filter=operation_type,
            success_rate=success_rate,
            average_duration_ms=average_duration,
        )
    except Exception as e:
        logger.error(f"Error getting polling metrics: {e}")
        error_response = create_standardized_error_response(
            status_code=500,
            message="Failed to retrieve polling metrics",
            error_code="POLLING_METRICS_ERROR",
        )
        return JSONResponse(status_code=500, content=error_response)


@router.get(
    "/performance/{metric_name}",
    response_model=PerformanceStatsResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Metric not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def get_performance_stats(metric_name: str) -> PerformanceStatsResponse:
    """Get performance statistics for a specific metric.

    Returns statistical analysis including:
    - Min/max/mean values
    - Median and percentiles (p95, p99)
    - Sample count

    Common metric names:
    - `polling.total.duration` - All polling operation durations
    - `polling.watching_schedule_checks.duration` - Watching check durations
    - `api.total.duration` - All API request durations
    - `api./api/series.duration` - Specific endpoint durations

    Args:
        metric_name: Name of the performance metric to analyze
    """
    try:
        stats = metrics_collector.get_performance_stats(metric_name)

        if not stats:
            error_response = create_standardized_error_response(
                status_code=404,
                message=f"Performance metric '{metric_name}' not found or has no data",
                error_code="METRIC_NOT_FOUND",
            )
            return JSONResponse(status_code=404, content=error_response)

        return PerformanceStatsResponse(metric_name=metric_name, stats=stats)
    except Exception as e:
        logger.error(f"Error getting performance stats for metric '{metric_name}': {e}")
        error_response = create_standardized_error_response(
            status_code=500,
            message="Failed to retrieve performance statistics",
            error_code="PERFORMANCE_STATS_ERROR",
        )
        return JSONResponse(status_code=500, content=error_response)


@router.get(
    "/watching",
    response_model=dict,
    responses={500: {"model": ErrorResponse, "description": "Internal server error"}},
)
async def get_watching_metrics() -> dict:
    """Get watching system specific metrics.

    Returns metrics focused on the watching/polling system:
    - Number of watched series
    - Update check frequency and success rate
    - Notification generation statistics
    - Job scheduling performance
    """
    try:
        system_metrics = metrics_collector.get_system_metrics()
        watching_polling_metrics = metrics_collector.get_polling_metrics(
            "watching_schedule_checks", 50
        )

        # Calculate watching-specific statistics
        recent_checks = [m for m in watching_polling_metrics if m.get("success") is not None]
        success_rate = 0
        if recent_checks:
            successful_checks = sum(1 for m in recent_checks if m.get("success", False))
            success_rate = (successful_checks / len(recent_checks)) * 100

        return {
            "watched_series_count": system_metrics.watched_series_count,
            "series_checked_last_hour": system_metrics.series_checked_last_hour,
            "notifications_sent_last_hour": system_metrics.notifications_sent_last_hour,
            "update_check_success_rate": success_rate,
            "recent_polling_operations": len(watching_polling_metrics),
            "average_polling_duration_ms": system_metrics.average_polling_duration_ms,
            "active_background_jobs": system_metrics.active_background_jobs,
            "pending_background_jobs": system_metrics.pending_background_jobs,
        }
    except Exception as e:
        logger.error(f"Error getting watching metrics: {e}")
        error_response = create_standardized_error_response(
            status_code=500,
            message="Failed to retrieve watching system metrics",
            error_code="WATCHING_METRICS_ERROR",
        )
        return JSONResponse(status_code=500, content=error_response)


@router.get(
    "/counters",
    response_model=dict,
    responses={500: {"model": ErrorResponse, "description": "Internal server error"}},
)
async def get_metrics_counters() -> dict:
    """Get raw metrics counters and gauges.

    Returns the raw counter and gauge values collected by the metrics system.
    Useful for detailed monitoring and debugging.
    """
    try:
        with metrics_collector._lock:
            counters = dict(metrics_collector.counters)
            gauges = dict(metrics_collector.gauges)

        return {
            "counters": counters,
            "gauges": gauges,
            "metrics_history_size": {
                "polling_metrics": len(metrics_collector.polling_metrics),
                "api_metrics": len(metrics_collector.api_metrics),
                "max_history_size": metrics_collector.max_history_size,
            },
        }
    except Exception as e:
        logger.error(f"Error getting metrics counters: {e}")
        error_response = create_standardized_error_response(
            status_code=500,
            message="Failed to retrieve metrics counters",
            error_code="METRICS_COUNTERS_ERROR",
        )
        return JSONResponse(status_code=500, content=error_response)


@router.post(
    "/reset",
    response_model=dict,
    responses={
        200: {"description": "Metrics reset successfully"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def reset_metrics() -> dict:
    """Reset all collected metrics.

    **Warning**: This will clear all historical metrics data.
    This endpoint is primarily intended for testing and development.

    In production, metrics should typically not be reset to maintain
    historical performance data.
    """
    try:
        metrics_collector.reset_metrics()

        logger.warning("All metrics have been reset via API request")

        return {
            "status": "success",
            "message": "All metrics have been reset",
            "timestamp": metrics_collector.get_system_metrics().last_updated.isoformat(),
            "warning": "Historical metrics data has been cleared",
        }
    except Exception as e:
        logger.error(f"Error resetting metrics: {e}")
        error_response = create_standardized_error_response(
            status_code=500, message="Failed to reset metrics", error_code="METRICS_RESET_ERROR"
        )
        return JSONResponse(status_code=500, content=error_response)


@router.get("/health", response_model=dict)
async def get_metrics_health() -> dict:
    """Get metrics system health status.

    Returns information about the metrics collection system health
    and configuration.
    """
    try:
        system_metrics = metrics_collector.get_system_metrics()

        # Simple health checks
        is_healthy = True
        health_issues = []

        # Check if metrics are being collected
        if system_metrics.total_polling_operations == 0 and system_metrics.total_api_requests == 0:
            health_issues.append("No metrics have been collected yet")

        # Check metrics collection capacity
        with metrics_collector._lock:
            polling_utilization = (
                len(metrics_collector.polling_metrics) / metrics_collector.max_history_size
            )
            api_utilization = (
                len(metrics_collector.api_metrics) / metrics_collector.max_history_size
            )

        if polling_utilization > 0.9 or api_utilization > 0.9:
            health_issues.append("Metrics history approaching capacity limits")

        if health_issues:
            is_healthy = False

        return {
            "healthy": is_healthy,
            "issues": health_issues,
            "metrics_collection_active": True,
            "history_utilization": {
                "polling_metrics": f"{polling_utilization:.2%}",
                "api_metrics": f"{api_utilization:.2%}",
                "max_capacity": metrics_collector.max_history_size,
            },
            "last_metrics_update": system_metrics.last_updated.isoformat(),
        }
    except Exception as e:
        logger.error(f"Error checking metrics health: {e}")
        return {
            "healthy": False,
            "issues": [f"Metrics system error: {str(e)}"],
            "metrics_collection_active": False,
            "error": str(e),
        }
