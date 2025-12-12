"""
Service Health Checker

Utilities for checking health and availability of content generation services.

Services can use these utilities to provide health check endpoints that
Director can use to monitor service status and route around failures.

Version: 1.0.0
Created: 2025-11-29
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from enum import Enum
import asyncio
import aiohttp
from pydantic import BaseModel, Field


class ServiceStatus(str, Enum):
    """Service health status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class HealthCheckResult(BaseModel):
    """Result of a health check"""
    status: ServiceStatus = Field(..., description="Overall service status")
    service_name: str = Field(..., description="Service name")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    response_time_ms: Optional[float] = Field(None, description="Response time in milliseconds")

    # Detailed status
    is_available: bool = Field(..., description="Whether service is reachable")
    is_responsive: bool = Field(..., description="Whether service responds quickly")
    error_message: Optional[str] = Field(None, description="Error message if unhealthy")

    # Additional info
    version: Optional[str] = Field(None, description="Service version")
    uptime_seconds: Optional[float] = Field(None, description="Service uptime in seconds")
    active_connections: Optional[int] = Field(None, description="Active connections")

    # Variant availability
    available_variants: List[str] = Field(default_factory=list, description="Available variants")
    unavailable_variants: List[str] = Field(default_factory=list, description="Unavailable variants")

    # Metrics
    metrics: Dict[str, Any] = Field(default_factory=dict, description="Additional metrics")

    def is_healthy(self) -> bool:
        """Check if service is healthy"""
        return self.status == ServiceStatus.HEALTHY

    def is_usable(self) -> bool:
        """Check if service is usable (healthy or degraded)"""
        return self.status in [ServiceStatus.HEALTHY, ServiceStatus.DEGRADED]

    def get_summary(self) -> str:
        """Get human-readable summary"""
        icon = {
            ServiceStatus.HEALTHY: "✅",
            ServiceStatus.DEGRADED: "⚠️",
            ServiceStatus.UNHEALTHY: "❌",
            ServiceStatus.UNKNOWN: "❓"
        }[self.status]

        summary = f"{icon} {self.service_name}: {self.status.value.upper()}"

        if self.response_time_ms:
            summary += f" ({self.response_time_ms:.0f}ms)"

        if self.error_message:
            summary += f"\n  Error: {self.error_message}"

        if self.available_variants:
            summary += f"\n  Variants: {len(self.available_variants)} available"

        if self.unavailable_variants:
            summary += f", {len(self.unavailable_variants)} unavailable"

        return summary


class ServiceHealthChecker:
    """
    Health checker for content generation services.

    Performs health checks by calling service health endpoints and
    analyzing responses to determine service status.

    Usage:
        checker = ServiceHealthChecker()

        # Check single service
        result = await checker.check_service(
            service_name="analytics_service_v3",
            base_url="https://analytics.example.com",
            health_endpoint="/health"
        )

        if result.is_healthy():
            print("Service is healthy!")

        # Check multiple services
        results = await checker.check_multiple_services({
            "analytics_service_v3": "https://analytics.example.com",
            "text_service_v1.2": "https://text.example.com"
        })
    """

    def __init__(
        self,
        timeout_seconds: float = 5.0,
        slow_threshold_ms: float = 1000.0
    ):
        """
        Initialize health checker.

        Args:
            timeout_seconds: Request timeout in seconds
            slow_threshold_ms: Threshold for considering response slow (degraded)
        """
        self.timeout_seconds = timeout_seconds
        self.slow_threshold_ms = slow_threshold_ms

    async def check_service(
        self,
        service_name: str,
        base_url: str,
        health_endpoint: str = "/health",
        check_variants: bool = False,
        variant_endpoint: Optional[str] = None
    ) -> HealthCheckResult:
        """
        Check health of a single service.

        Args:
            service_name: Service identifier
            base_url: Service base URL
            health_endpoint: Health check endpoint path
            check_variants: Whether to check variant availability
            variant_endpoint: Endpoint for variant listing (e.g., "/api/metadata")

        Returns:
            HealthCheckResult with status and details
        """
        start_time = datetime.utcnow()

        try:
            # Prepare health check URL
            url = f"{base_url.rstrip('/')}{health_endpoint}"

            # Make request
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=self.timeout_seconds) as response:
                    # Calculate response time
                    response_time_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

                    # Get response data
                    try:
                        data = await response.json()
                    except:
                        data = {}

                    # Determine status
                    is_available = response.status == 200
                    is_responsive = response_time_ms < self.slow_threshold_ms

                    if is_available and is_responsive:
                        status = ServiceStatus.HEALTHY
                    elif is_available:
                        status = ServiceStatus.DEGRADED  # Slow response
                    else:
                        status = ServiceStatus.UNHEALTHY

                    # Extract variant info if requested
                    available_variants = []
                    unavailable_variants = []

                    if check_variants and variant_endpoint:
                        variant_info = await self._check_variants(
                            base_url,
                            variant_endpoint,
                            session
                        )
                        available_variants = variant_info.get("available", [])
                        unavailable_variants = variant_info.get("unavailable", [])

                    return HealthCheckResult(
                        status=status,
                        service_name=service_name,
                        response_time_ms=response_time_ms,
                        is_available=is_available,
                        is_responsive=is_responsive,
                        version=data.get("version"),
                        uptime_seconds=data.get("uptime"),
                        active_connections=data.get("active_connections"),
                        available_variants=available_variants,
                        unavailable_variants=unavailable_variants,
                        metrics=data.get("metrics", {})
                    )

        except asyncio.TimeoutError:
            return HealthCheckResult(
                status=ServiceStatus.UNHEALTHY,
                service_name=service_name,
                is_available=False,
                is_responsive=False,
                error_message=f"Timeout after {self.timeout_seconds}s"
            )

        except aiohttp.ClientError as e:
            return HealthCheckResult(
                status=ServiceStatus.UNHEALTHY,
                service_name=service_name,
                is_available=False,
                is_responsive=False,
                error_message=f"Connection error: {str(e)}"
            )

        except Exception as e:
            return HealthCheckResult(
                status=ServiceStatus.UNKNOWN,
                service_name=service_name,
                is_available=False,
                is_responsive=False,
                error_message=f"Unexpected error: {str(e)}"
            )

    async def check_multiple_services(
        self,
        services: Dict[str, str],
        health_endpoint: str = "/health"
    ) -> Dict[str, HealthCheckResult]:
        """
        Check health of multiple services concurrently.

        Args:
            services: Dict mapping service_name -> base_url
            health_endpoint: Health check endpoint path

        Returns:
            Dict mapping service_name -> HealthCheckResult
        """
        tasks = []

        for service_name, base_url in services.items():
            task = self.check_service(service_name, base_url, health_endpoint)
            tasks.append((service_name, task))

        results = {}

        # Execute all health checks concurrently
        for service_name, task in tasks:
            result = await task
            results[service_name] = result

        return results

    async def _check_variants(
        self,
        base_url: str,
        variant_endpoint: str,
        session: aiohttp.ClientSession
    ) -> Dict[str, List[str]]:
        """
        Check variant availability.

        Args:
            base_url: Service base URL
            variant_endpoint: Variant listing endpoint
            session: aiohttp session

        Returns:
            Dict with "available" and "unavailable" variant lists
        """
        try:
            url = f"{base_url.rstrip('/')}{variant_endpoint}"

            async with session.get(url, timeout=self.timeout_seconds) as response:
                if response.status == 200:
                    data = await response.json()

                    # Extract variants based on metadata format
                    variants = data.get("variants", {})
                    if isinstance(variants, dict):
                        available = []
                        unavailable = []

                        for variant_id, variant_data in variants.items():
                            status = variant_data.get("status", "production")
                            if status in ["production", "beta"]:
                                available.append(variant_id)
                            else:
                                unavailable.append(variant_id)

                        return {
                            "available": available,
                            "unavailable": unavailable
                        }

        except:
            pass

        return {"available": [], "unavailable": []}

    def get_aggregate_status(
        self,
        results: Dict[str, HealthCheckResult]
    ) -> ServiceStatus:
        """
        Get aggregate status from multiple health check results.

        Args:
            results: Dict of health check results

        Returns:
            Aggregate ServiceStatus
        """
        if not results:
            return ServiceStatus.UNKNOWN

        statuses = [r.status for r in results.values()]

        # If any unhealthy, aggregate is unhealthy
        if ServiceStatus.UNHEALTHY in statuses:
            return ServiceStatus.UNHEALTHY

        # If any degraded, aggregate is degraded
        if ServiceStatus.DEGRADED in statuses:
            return ServiceStatus.DEGRADED

        # If all healthy, aggregate is healthy
        if all(s == ServiceStatus.HEALTHY for s in statuses):
            return ServiceStatus.HEALTHY

        return ServiceStatus.UNKNOWN

    def get_summary_report(
        self,
        results: Dict[str, HealthCheckResult]
    ) -> str:
        """
        Get human-readable summary report.

        Args:
            results: Dict of health check results

        Returns:
            Formatted summary report
        """
        aggregate = self.get_aggregate_status(results)

        report_lines = [
            f"Service Health Report ({datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')})",
            f"Aggregate Status: {aggregate.value.upper()}",
            "",
            "Services:"
        ]

        for service_name, result in results.items():
            report_lines.append(f"  {result.get_summary()}")

        # Statistics
        total = len(results)
        healthy = sum(1 for r in results.values() if r.status == ServiceStatus.HEALTHY)
        degraded = sum(1 for r in results.values() if r.status == ServiceStatus.DEGRADED)
        unhealthy = sum(1 for r in results.values() if r.status == ServiceStatus.UNHEALTHY)

        report_lines.extend([
            "",
            "Statistics:",
            f"  Total services: {total}",
            f"  Healthy: {healthy}",
            f"  Degraded: {degraded}",
            f"  Unhealthy: {unhealthy}"
        ])

        return "\n".join(report_lines)


class HealthCheckCache:
    """
    Cache for health check results to avoid excessive checking.

    Usage:
        cache = HealthCheckCache(ttl_seconds=60)

        # Check with caching
        result = await cache.get_or_check(
            service_name="analytics_service_v3",
            check_func=lambda: checker.check_service(...)
        )
    """

    def __init__(self, ttl_seconds: float = 60.0):
        """
        Initialize cache.

        Args:
            ttl_seconds: Time-to-live for cached results
        """
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, tuple[HealthCheckResult, datetime]] = {}

    async def get_or_check(
        self,
        service_name: str,
        check_func
    ) -> HealthCheckResult:
        """
        Get cached result or perform new check.

        Args:
            service_name: Service identifier
            check_func: Async function that performs health check

        Returns:
            HealthCheckResult (cached or fresh)
        """
        # Check cache
        if service_name in self._cache:
            result, timestamp = self._cache[service_name]

            # Check if still valid
            age = (datetime.utcnow() - timestamp).total_seconds()
            if age < self.ttl_seconds:
                return result

        # Cache miss or expired - perform check
        result = await check_func()

        # Update cache
        self._cache[service_name] = (result, datetime.utcnow())

        return result

    def invalidate(self, service_name: Optional[str] = None):
        """
        Invalidate cache for specific service or all services.

        Args:
            service_name: Service to invalidate (None = all)
        """
        if service_name:
            self._cache.pop(service_name, None)
        else:
            self._cache.clear()

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        now = datetime.utcnow()

        valid_count = 0
        expired_count = 0

        for result, timestamp in self._cache.values():
            age = (now - timestamp).total_seconds()
            if age < self.ttl_seconds:
                valid_count += 1
            else:
                expired_count += 1

        return {
            "total_entries": len(self._cache),
            "valid_entries": valid_count,
            "expired_entries": expired_count,
            "ttl_seconds": self.ttl_seconds
        }


async def check_service_health(
    service_name: str,
    base_url: str,
    health_endpoint: str = "/health",
    timeout_seconds: float = 5.0
) -> HealthCheckResult:
    """
    Convenience function to check service health.

    Args:
        service_name: Service identifier
        base_url: Service base URL
        health_endpoint: Health check endpoint
        timeout_seconds: Request timeout

    Returns:
        HealthCheckResult

    Example:
        result = await check_service_health(
            "analytics_service_v3",
            "https://analytics.example.com"
        )

        if result.is_healthy():
            print("Service is healthy!")
    """
    checker = ServiceHealthChecker(timeout_seconds=timeout_seconds)
    return await checker.check_service(service_name, base_url, health_endpoint)
