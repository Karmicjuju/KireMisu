"""Metrics collection and monitoring system for KireMisu.

This module provides comprehensive metrics collection for monitoring system performance,
particularly focused on polling operations, background jobs, and API performance.
"""

import logging
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from threading import Lock
from typing import Dict, List, Optional, Any, Deque
from dataclasses import dataclass, field
from uuid import UUID

logger = logging.getLogger(__name__)


@dataclass
class PollingMetric:
    """Represents a single polling operation metric."""

    operation_type: str  # e.g., "watching_check", "mangadx_fetch", "notification_poll"
    start_time: float
    end_time: Optional[float] = None
    success: bool = False
    error_message: Optional[str] = None
    series_id: Optional[UUID] = None
    series_count: int = 0
    chapters_processed: int = 0
    notifications_created: int = 0
    external_api_calls: int = 0

    @property
    def duration_ms(self) -> Optional[float]:
        """Calculate operation duration in milliseconds."""
        if self.end_time is None:
            return None
        return (self.end_time - self.start_time) * 1000

    @property
    def is_complete(self) -> bool:
        """Check if the operation is complete."""
        return self.end_time is not None


@dataclass
class APIMetric:
    """Represents an API endpoint performance metric."""

    endpoint: str
    method: str
    start_time: float
    end_time: Optional[float] = None
    status_code: Optional[int] = None
    response_size_bytes: int = 0
    user_id: Optional[UUID] = None  # For future user tracking

    @property
    def duration_ms(self) -> Optional[float]:
        """Calculate request duration in milliseconds."""
        if self.end_time is None:
            return None
        return (self.end_time - self.start_time) * 1000


@dataclass
class SystemMetrics:
    """Aggregated system metrics."""

    # Polling metrics
    total_polling_operations: int = 0
    successful_polling_operations: int = 0
    failed_polling_operations: int = 0
    average_polling_duration_ms: float = 0.0

    # API metrics
    total_api_requests: int = 0
    api_requests_by_status: Dict[int, int] = field(default_factory=dict)
    average_api_response_time_ms: float = 0.0

    # Job metrics
    active_background_jobs: int = 0
    pending_background_jobs: int = 0
    completed_jobs_last_hour: int = 0

    # Watching system metrics
    watched_series_count: int = 0
    series_checked_last_hour: int = 0
    notifications_sent_last_hour: int = 0

    # System health
    memory_usage_mb: Optional[float] = None
    cpu_usage_percent: Optional[float] = None
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class MetricsCollector:
    """Collects and aggregates metrics for monitoring system performance."""

    def __init__(self, max_history_size: int = 10000):
        self.max_history_size = max_history_size
        self._lock = Lock()

        # Polling metrics history
        self.polling_metrics: Deque[PollingMetric] = deque(maxlen=max_history_size)

        # API metrics history
        self.api_metrics: Deque[APIMetric] = deque(maxlen=max_history_size)

        # Real-time counters
        self.counters: Dict[str, int] = defaultdict(int)
        self.gauges: Dict[str, float] = {}

        # Performance tracking
        self.performance_buckets: Dict[str, List[float]] = defaultdict(list)

        logger.info(f"MetricsCollector initialized with history size: {max_history_size}")

    def record_polling_start(
        self, operation_type: str, series_id: Optional[UUID] = None, series_count: int = 0
    ) -> PollingMetric:
        """Start tracking a polling operation.

        Args:
            operation_type: Type of polling operation
            series_id: Optional series being polled
            series_count: Number of series being processed

        Returns:
            PollingMetric instance for tracking
        """
        metric = PollingMetric(
            operation_type=operation_type,
            start_time=time.time(),
            series_id=series_id,
            series_count=series_count,
        )

        with self._lock:
            self.counters[f"polling.{operation_type}.started"] += 1
            self.counters["polling.total.started"] += 1

        logger.debug(f"Started polling operation: {operation_type}")
        return metric

    def record_polling_end(
        self,
        metric: PollingMetric,
        success: bool = True,
        error_message: Optional[str] = None,
        chapters_processed: int = 0,
        notifications_created: int = 0,
        external_api_calls: int = 0,
    ):
        """Finish tracking a polling operation.

        Args:
            metric: PollingMetric instance from record_polling_start
            success: Whether the operation succeeded
            error_message: Error message if failed
            chapters_processed: Number of chapters processed
            notifications_created: Number of notifications created
            external_api_calls: Number of external API calls made
        """
        metric.end_time = time.time()
        metric.success = success
        metric.error_message = error_message
        metric.chapters_processed = chapters_processed
        metric.notifications_created = notifications_created
        metric.external_api_calls = external_api_calls

        with self._lock:
            self.polling_metrics.append(metric)

            # Update counters
            status = "success" if success else "failure"
            self.counters[f"polling.{metric.operation_type}.{status}"] += 1
            self.counters[f"polling.total.{status}"] += 1

            # Track performance
            if metric.duration_ms:
                self.performance_buckets[f"polling.{metric.operation_type}.duration"].append(
                    metric.duration_ms
                )
                self.performance_buckets["polling.total.duration"].append(metric.duration_ms)

            # Update gauges
            self.gauges[f"polling.{metric.operation_type}.last_duration_ms"] = (
                metric.duration_ms or 0
            )
            self.gauges["polling.chapters_processed.total"] = (
                self.gauges.get("polling.chapters_processed.total", 0) + chapters_processed
            )
            self.gauges["polling.notifications_created.total"] = (
                self.gauges.get("polling.notifications_created.total", 0) + notifications_created
            )

        logger.debug(
            f"Completed polling operation: {metric.operation_type} (duration: {metric.duration_ms:.2f}ms, success: {success})"
        )

    @asynccontextmanager
    async def track_polling_operation(
        self, operation_type: str, series_id: Optional[UUID] = None, series_count: int = 0
    ):
        """Context manager for tracking polling operations.

        Usage:
            async with metrics.track_polling_operation("watching_check", series_id=uuid, series_count=5) as tracker:
                # Perform polling operation
                tracker.chapters_processed = 10
                tracker.notifications_created = 2
                # Operation success/failure is automatically detected
        """
        metric = self.record_polling_start(operation_type, series_id, series_count)

        # Create a tracker object for updating metrics
        class PollingTracker:
            def __init__(self):
                self.chapters_processed = 0
                self.notifications_created = 0
                self.external_api_calls = 0

        tracker = PollingTracker()

        try:
            yield tracker
            # If we get here, operation was successful
            self.record_polling_end(
                metric,
                success=True,
                chapters_processed=tracker.chapters_processed,
                notifications_created=tracker.notifications_created,
                external_api_calls=tracker.external_api_calls,
            )
        except Exception as e:
            # Operation failed
            self.record_polling_end(
                metric,
                success=False,
                error_message=str(e),
                chapters_processed=tracker.chapters_processed,
                notifications_created=tracker.notifications_created,
                external_api_calls=tracker.external_api_calls,
            )
            raise

    def record_api_request_start(
        self, endpoint: str, method: str, user_id: Optional[UUID] = None
    ) -> APIMetric:
        """Start tracking an API request.

        Args:
            endpoint: API endpoint path
            method: HTTP method
            user_id: Optional user ID

        Returns:
            APIMetric instance for tracking
        """
        metric = APIMetric(
            endpoint=endpoint, method=method, start_time=time.time(), user_id=user_id
        )

        with self._lock:
            self.counters[f"api.{method.lower()}.started"] += 1
            self.counters["api.total.started"] += 1

        return metric

    def record_api_request_end(
        self, metric: APIMetric, status_code: int, response_size_bytes: int = 0
    ):
        """Finish tracking an API request.

        Args:
            metric: APIMetric instance from record_api_request_start
            status_code: HTTP status code
            response_size_bytes: Response size in bytes
        """
        metric.end_time = time.time()
        metric.status_code = status_code
        metric.response_size_bytes = response_size_bytes

        with self._lock:
            self.api_metrics.append(metric)

            # Update counters
            self.counters[f"api.{metric.method.lower()}.{status_code}"] += 1
            self.counters[f"api.total.{status_code}"] += 1

            # Track performance
            if metric.duration_ms:
                self.performance_buckets[f"api.{metric.endpoint}.duration"].append(
                    metric.duration_ms
                )
                self.performance_buckets["api.total.duration"].append(metric.duration_ms)

            # Update gauges
            self.gauges[f"api.{metric.endpoint}.last_duration_ms"] = metric.duration_ms or 0
            self.gauges["api.total_response_bytes"] = (
                self.gauges.get("api.total_response_bytes", 0) + response_size_bytes
            )

    def increment_counter(self, name: str, value: int = 1):
        """Increment a named counter.

        Args:
            name: Counter name
            value: Increment value (default: 1)
        """
        with self._lock:
            self.counters[name] += value

    def set_gauge(self, name: str, value: float):
        """Set a named gauge value.

        Args:
            name: Gauge name
            value: Gauge value
        """
        with self._lock:
            self.gauges[name] = value

    def get_system_metrics(self) -> SystemMetrics:
        """Get aggregated system metrics.

        Returns:
            SystemMetrics with current aggregated data
        """
        with self._lock:
            # Calculate polling metrics
            total_polling = len(self.polling_metrics)
            successful_polling = sum(1 for m in self.polling_metrics if m.success)
            failed_polling = total_polling - successful_polling

            avg_polling_duration = 0.0
            if self.polling_metrics:
                durations = [
                    m.duration_ms for m in self.polling_metrics if m.duration_ms is not None
                ]
                if durations:
                    avg_polling_duration = sum(durations) / len(durations)

            # Calculate API metrics
            total_api = len(self.api_metrics)
            api_status_counts = defaultdict(int)
            for metric in self.api_metrics:
                if metric.status_code:
                    api_status_counts[metric.status_code] += 1

            avg_api_duration = 0.0
            if self.api_metrics:
                durations = [m.duration_ms for m in self.api_metrics if m.duration_ms is not None]
                if durations:
                    avg_api_duration = sum(durations) / len(durations)

        return SystemMetrics(
            total_polling_operations=total_polling,
            successful_polling_operations=successful_polling,
            failed_polling_operations=failed_polling,
            average_polling_duration_ms=avg_polling_duration,
            total_api_requests=total_api,
            api_requests_by_status=dict(api_status_counts),
            average_api_response_time_ms=avg_api_duration,
            active_background_jobs=self.gauges.get("jobs.active", 0),
            pending_background_jobs=self.gauges.get("jobs.pending", 0),
            completed_jobs_last_hour=self.counters.get("jobs.completed.last_hour", 0),
            watched_series_count=self.gauges.get("watching.series_count", 0),
            series_checked_last_hour=self.counters.get("watching.checks.last_hour", 0),
            notifications_sent_last_hour=self.counters.get("notifications.sent.last_hour", 0),
        )

    def get_polling_metrics(
        self, operation_type: Optional[str] = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get recent polling metrics.

        Args:
            operation_type: Filter by operation type
            limit: Maximum number of metrics to return

        Returns:
            List of polling metric dictionaries
        """
        with self._lock:
            metrics = list(self.polling_metrics)

        if operation_type:
            metrics = [m for m in metrics if m.operation_type == operation_type]

        # Take most recent metrics
        metrics = metrics[-limit:]

        return [
            {
                "operation_type": m.operation_type,
                "duration_ms": m.duration_ms,
                "success": m.success,
                "error_message": m.error_message,
                "series_id": str(m.series_id) if m.series_id else None,
                "series_count": m.series_count,
                "chapters_processed": m.chapters_processed,
                "notifications_created": m.notifications_created,
                "external_api_calls": m.external_api_calls,
                "timestamp": datetime.fromtimestamp(m.start_time, tz=timezone.utc).isoformat(),
            }
            for m in metrics
        ]

    def get_performance_stats(self, metric_name: str) -> Dict[str, float]:
        """Get performance statistics for a metric.

        Args:
            metric_name: Name of the performance metric

        Returns:
            Dictionary with performance statistics
        """
        with self._lock:
            values = self.performance_buckets.get(metric_name, [])

        if not values:
            return {}

        sorted_values = sorted(values)
        count = len(sorted_values)

        return {
            "count": count,
            "min": sorted_values[0],
            "max": sorted_values[-1],
            "mean": sum(sorted_values) / count,
            "median": sorted_values[count // 2],
            "p95": sorted_values[int(count * 0.95)] if count > 0 else 0,
            "p99": sorted_values[int(count * 0.99)] if count > 0 else 0,
        }

    def reset_metrics(self):
        """Reset all collected metrics (useful for testing)."""
        with self._lock:
            self.polling_metrics.clear()
            self.api_metrics.clear()
            self.counters.clear()
            self.gauges.clear()
            self.performance_buckets.clear()

        logger.info("All metrics have been reset")


# Global metrics collector instance
metrics_collector = MetricsCollector()
