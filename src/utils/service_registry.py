"""
Service Registry for Director v3.4
===================================

Central registry managing routing between multiple content generation services:
- Text Service v1.2 (10 content types, 34 platinum variants + 3 hero types)
- Illustrator Service v1.0 (pyramid, future visualizations)
- Hero Service (currently using Text Service endpoints)

This registry enables:
1. Dynamic service routing based on slide type
2. Service discovery and health checking
3. Endpoint configuration management
4. Future service extensibility (funnel, SWOT, BCG matrix, etc.)

Architecture:
- Service-based taxonomy (slides grouped by owning service)
- Pluggable architecture (easy to add new services)
- Configuration-driven (no hardcoded routing logic)

Author: Director v3.4 Integration Team
Updated: January 15, 2025 (Illustrator Service integration)
"""

from typing import Dict, Optional, List, Any
from dataclasses import dataclass, field
from enum import Enum
from src.utils.logger import setup_logger
from config.settings import get_settings

logger = setup_logger(__name__)


class ServiceType(str, Enum):
    """Enumeration of available content generation services."""
    TEXT_SERVICE = "text_service"
    ILLUSTRATOR_SERVICE = "illustrator_service"
    ANALYTICS_SERVICE = "analytics_service"
    HERO_SERVICE = "hero_service"


@dataclass
class ServiceEndpoint:
    """
    Configuration for a service endpoint.

    Attributes:
        path: API endpoint path (e.g., "/v1.2/generate")
        method: HTTP method (GET, POST, etc.)
        timeout: Request timeout in seconds
        requires_session: Whether endpoint requires session context
    """
    path: str
    method: str = "POST"
    timeout: int = 300
    requires_session: bool = True


@dataclass
class ServiceConfig:
    """
    Configuration for a content generation service.

    Attributes:
        enabled: Whether service is enabled
        base_url: Service base URL
        slide_types: List of slide types this service handles
        endpoints: Dict mapping endpoint names to ServiceEndpoint configs
        version: Service version
        health_endpoint: Health check endpoint path
    """
    enabled: bool
    base_url: str
    slide_types: List[str]
    endpoints: Dict[str, ServiceEndpoint] = field(default_factory=dict)
    version: Optional[str] = None
    health_endpoint: str = "/health"


class ServiceRegistry:
    """
    Central registry for content generation services.

    Manages routing logic, service discovery, and configuration for all
    content generation services used by Director Agent.

    14 Slide Types → 3 Services:
    - Text Service v1.2: 10 content types (34 variants) + 3 hero types
    - Illustrator Service v1.0: 1 visualization type (pyramid)
    - Hero Service: 3 hero types (currently uses Text Service)

    Usage:
        registry = ServiceRegistry()
        service = registry.get_service_for_slide_type("pyramid")
        endpoint = registry.get_endpoint("illustrator_service", "pyramid")
    """

    def __init__(self):
        """Initialize service registry with configuration from settings."""
        settings = get_settings()
        self._services: Dict[str, ServiceConfig] = {}
        self._slide_type_map: Dict[str, str] = {}  # slide_type -> service_name

        self._initialize_services(settings)
        self._build_slide_type_map()

        logger.info(
            "ServiceRegistry initialized",
            extra={
                "services": list(self._services.keys()),
                "enabled_services": [k for k, v in self._services.items() if v.enabled],
                "total_slide_types": len(self._slide_type_map)
            }
        )

    def _initialize_services(self, settings) -> None:
        """
        Initialize service configurations from settings.

        Args:
            settings: Application settings instance
        """
        # Text Service v1.2 Configuration
        # Handles 10 content types with 34 platinum variants + 3 hero types
        self._services["text_service"] = ServiceConfig(
            enabled=settings.TEXT_SERVICE_ENABLED,
            base_url=settings.TEXT_SERVICE_URL,
            version="1.2",
            slide_types=[
                # 10 content slide types (34 total variants)
                "bilateral_comparison",    # 4 variants
                "matrix_2x2",             # 3 variants
                "sequential_3col",        # 3 variants
                "asymmetric_8_4",         # 3 variants
                "hybrid_1_2x2",           # 4 variants
                "single_column",          # 3 variants
                "impact_quote",           # 3 variants
                "metrics_grid",           # 4 variants
                "styled_table",           # 4 variants
                "grid_3x3",               # 3 variants
                # 3 hero slide types
                "hero_title",
                "hero_section",
                "hero_closing"
            ],
            endpoints={
                # Unified content generation endpoint (v1.2)
                "generate": ServiceEndpoint(
                    path="/v1.2/generate",
                    method="POST",
                    timeout=settings.TEXT_SERVICE_TIMEOUT,
                    requires_session=True
                ),
                # Hero slide endpoints (v1.2)
                "hero_title": ServiceEndpoint(
                    path="/v1.2/hero/title",
                    method="POST",
                    timeout=60,
                    requires_session=True
                ),
                "hero_section": ServiceEndpoint(
                    path="/v1.2/hero/section",
                    method="POST",
                    timeout=60,
                    requires_session=True
                ),
                "hero_closing": ServiceEndpoint(
                    path="/v1.2/hero/closing",
                    method="POST",
                    timeout=60,
                    requires_session=True
                )
            }
        )

        # Illustrator Service v1.0 Configuration
        # Handles data visualizations (pyramid, future: funnel, SWOT, etc.)
        self._services["illustrator_service"] = ServiceConfig(
            enabled=settings.ILLUSTRATOR_SERVICE_ENABLED,
            base_url=settings.ILLUSTRATOR_SERVICE_URL,
            version="1.0",
            slide_types=[
                "pyramid",
                # Future visualization types (planned):
                # "funnel",
                # "swot",
                # "bcg_matrix",
                # "venn_diagram",
                # "timeline"
            ],
            endpoints={
                "pyramid": ServiceEndpoint(
                    path="/v1.0/pyramid/generate",
                    method="POST",
                    timeout=settings.ILLUSTRATOR_SERVICE_TIMEOUT,
                    requires_session=False  # Stateless, Director manages context
                )
                # Future endpoints will be added here as new visualizations are added
            }
        )

        # Analytics Service v3 Configuration
        # Handles L01, L02, L03 analytics layouts with interactive charts + AI observations
        self._services["analytics_service"] = ServiceConfig(
            enabled=settings.ANALYTICS_SERVICE_ENABLED,
            base_url=settings.ANALYTICS_SERVICE_URL,
            version="3.0",
            slide_types=[
                "analytics",
                "chart",
                "graph",
                "revenue_over_time",
                "quarterly_comparison",
                "market_share",
                "yoy_growth",
                "kpi_metrics"
            ],
            endpoints={
                # L02 endpoints (Chart left + Observations right)
                "revenue_over_time_L02": ServiceEndpoint(
                    path="/api/v1/analytics/L02/revenue_over_time",
                    method="POST",
                    timeout=settings.ANALYTICS_SERVICE_TIMEOUT,
                    requires_session=False  # Stateless, Director manages context
                ),
                "quarterly_comparison_L02": ServiceEndpoint(
                    path="/api/v1/analytics/L02/quarterly_comparison",
                    method="POST",
                    timeout=settings.ANALYTICS_SERVICE_TIMEOUT,
                    requires_session=False
                ),
                "market_share_L02": ServiceEndpoint(
                    path="/api/v1/analytics/L02/market_share",
                    method="POST",
                    timeout=settings.ANALYTICS_SERVICE_TIMEOUT,
                    requires_session=False
                ),
                "yoy_growth_L02": ServiceEndpoint(
                    path="/api/v1/analytics/L02/yoy_growth",
                    method="POST",
                    timeout=settings.ANALYTICS_SERVICE_TIMEOUT,
                    requires_session=False
                ),
                "kpi_metrics_L02": ServiceEndpoint(
                    path="/api/v1/analytics/L02/kpi_metrics",
                    method="POST",
                    timeout=settings.ANALYTICS_SERVICE_TIMEOUT,
                    requires_session=False
                )
                # L01 and L03 endpoints can be added when needed
            }
        )

        # Hero Service Configuration
        # Note: Currently using Text Service endpoints, structured for future separation
        self._services["hero_service"] = ServiceConfig(
            enabled=settings.TEXT_SERVICE_ENABLED,  # Using Text Service for now
            base_url=settings.TEXT_SERVICE_URL,
            version="1.2",
            slide_types=["hero_title", "hero_section", "hero_closing"],
            endpoints={
                "title": ServiceEndpoint(
                    path="/v1.2/hero/title",
                    method="POST",
                    timeout=60
                ),
                "section": ServiceEndpoint(
                    path="/v1.2/hero/section",
                    method="POST",
                    timeout=60
                ),
                "closing": ServiceEndpoint(
                    path="/v1.2/hero/closing",
                    method="POST",
                    timeout=60
                )
            }
        )

    def _build_slide_type_map(self) -> None:
        """Build reverse mapping from slide types to services."""
        for service_name, config in self._services.items():
            if config.enabled:
                for slide_type in config.slide_types:
                    # Handle potential conflicts (same slide type in multiple services)
                    if slide_type in self._slide_type_map:
                        existing_service = self._slide_type_map[slide_type]
                        # Prefer specialized services over generic ones
                        if service_name == "illustrator_service":
                            logger.info(
                                f"Overriding slide type '{slide_type}': {existing_service} → {service_name}"
                            )
                            self._slide_type_map[slide_type] = service_name
                    else:
                        self._slide_type_map[slide_type] = service_name

    def get_service_for_slide_type(self, slide_type: str) -> Optional[ServiceConfig]:
        """
        Get the service configuration responsible for a slide type.

        Args:
            slide_type: Slide type identifier (e.g., "pyramid", "bilateral_comparison")

        Returns:
            ServiceConfig if found, None otherwise
        """
        service_name = self._slide_type_map.get(slide_type)
        if not service_name:
            logger.warning(f"No service found for slide type: {slide_type}")
            return None

        service = self._services.get(service_name)
        if not service or not service.enabled:
            logger.warning(
                f"Service '{service_name}' for slide type '{slide_type}' is not enabled"
            )
            return None

        return service

    def get_endpoint(
        self,
        service_name: str,
        endpoint_name: str
    ) -> Optional[ServiceEndpoint]:
        """
        Get endpoint configuration for a service.

        Args:
            service_name: Service identifier (e.g., "illustrator_service")
            endpoint_name: Endpoint name (e.g., "pyramid", "generate")

        Returns:
            ServiceEndpoint if found, None otherwise
        """
        service = self._services.get(service_name)
        if not service:
            logger.error(f"Service not found: {service_name}")
            return None

        if not service.enabled:
            logger.error(f"Service '{service_name}' is not enabled")
            return None

        endpoint = service.endpoints.get(endpoint_name)
        if not endpoint:
            logger.error(
                f"Endpoint '{endpoint_name}' not found in service '{service_name}'"
            )
            return None

        return endpoint

    def get_full_url(self, service_name: str, endpoint_name: str) -> Optional[str]:
        """
        Get full URL for a service endpoint.

        Args:
            service_name: Service identifier
            endpoint_name: Endpoint name

        Returns:
            Full URL (base_url + endpoint_path) or None if not found
        """
        service = self._services.get(service_name)
        if not service:
            return None

        endpoint = service.endpoints.get(endpoint_name)
        if not endpoint:
            return None

        return f"{service.base_url}{endpoint.path}"

    def is_service_enabled(self, service_name: str) -> bool:
        """
        Check if a service is enabled.

        Args:
            service_name: Service identifier

        Returns:
            True if enabled, False otherwise
        """
        service = self._services.get(service_name)
        return bool(service and service.enabled)

    def get_enabled_services(self) -> List[str]:
        """
        Get list of enabled service names.

        Returns:
            List of enabled service names
        """
        return [
            name for name, config in self._services.items()
            if config.enabled
        ]

    def get_supported_slide_types(self, service_name: Optional[str] = None) -> List[str]:
        """
        Get list of supported slide types.

        Args:
            service_name: Optional service name to filter by

        Returns:
            List of supported slide type identifiers
        """
        if service_name:
            service = self._services.get(service_name)
            return service.slide_types if service else []

        # Return all slide types from all enabled services
        all_types = []
        for config in self._services.values():
            if config.enabled:
                all_types.extend(config.slide_types)
        return all_types

    def route_slide(self, slide_type: str) -> Optional[Dict[str, Any]]:
        """
        Get routing information for a slide type.

        Args:
            slide_type: Slide type identifier

        Returns:
            Dict with routing info:
                - service_name: Name of the service
                - service_config: ServiceConfig object
                - endpoint_name: Recommended endpoint name
                - full_url: Full endpoint URL (if available)
        """
        service_name = self._slide_type_map.get(slide_type)
        if not service_name:
            logger.error(f"Cannot route slide type '{slide_type}': no service mapping")
            return None

        service = self._services.get(service_name)
        if not service or not service.enabled:
            logger.error(
                f"Cannot route slide type '{slide_type}': "
                f"service '{service_name}' not available"
            )
            return None

        # Determine endpoint name based on service type
        endpoint_name = self._get_default_endpoint(service_name, slide_type)
        full_url = None

        if endpoint_name:
            endpoint = service.endpoints.get(endpoint_name)
            if endpoint:
                full_url = f"{service.base_url}{endpoint.path}"

        return {
            "service_name": service_name,
            "service_config": service,
            "endpoint_name": endpoint_name,
            "full_url": full_url,
            "slide_type": slide_type
        }

    def _get_default_endpoint(self, service_name: str, slide_type: str) -> Optional[str]:
        """
        Get default endpoint name for a service and slide type.

        Args:
            service_name: Service identifier
            slide_type: Slide type identifier

        Returns:
            Default endpoint name
        """
        # Text Service: Use unified "generate" endpoint for content slides
        if service_name == "text_service":
            if slide_type in ["hero_title", "hero_section", "hero_closing"]:
                return slide_type
            return "generate"

        # Illustrator Service: Endpoint name matches slide type
        elif service_name == "illustrator_service":
            return slide_type  # "pyramid" -> "pyramid" endpoint

        # Hero Service: Endpoint name is slide type without "hero_" prefix
        elif service_name == "hero_service":
            return slide_type.replace("hero_", "")

        return None

    def get_service_info(self, service_name: str) -> Optional[Dict[str, Any]]:
        """
        Get complete information about a service.

        Args:
            service_name: Service identifier

        Returns:
            Dict with service details or None if not found
        """
        service = self._services.get(service_name)
        if not service:
            return None

        return {
            "name": service_name,
            "enabled": service.enabled,
            "base_url": service.base_url,
            "version": service.version,
            "slide_types": service.slide_types,
            "endpoints": list(service.endpoints.keys()),
            "health_endpoint": service.health_endpoint
        }

    def get_all_services_info(self) -> Dict[str, Dict[str, Any]]:
        """
        Get information about all registered services.

        Returns:
            Dict mapping service names to service info dicts
        """
        return {
            name: self.get_service_info(name)
            for name in self._services.keys()
        }


# Example usage and testing
if __name__ == "__main__":
    print("Service Registry - Multi-Service Integration (v3.4)")
    print("=" * 80)

    registry = ServiceRegistry()

    print("\n📋 Registered Services:")
    for service_name in registry.get_enabled_services():
        info = registry.get_service_info(service_name)
        print(f"\n  🔹 {service_name} (v{info['version']})")
        print(f"     URL: {info['base_url']}")
        print(f"     Slide Types: {len(info['slide_types'])}")
        print(f"     Endpoints: {', '.join(info['endpoints'])}")

    print("\n\n🎯 Slide Type Routing:")
    test_types = ["pyramid", "bilateral_comparison", "hero_title", "matrix_2x2"]
    for slide_type in test_types:
        routing = registry.route_slide(slide_type)
        if routing:
            print(f"  {slide_type:25s} → {routing['service_name']:20s} ({routing['endpoint_name']})")

    print("\n\n📊 Service Statistics:")
    print(f"  Total services: {len(registry._services)}")
    print(f"  Enabled services: {len(registry.get_enabled_services())}")
    print(f"  Total slide types: {len(registry.get_supported_slide_types())}")

    print("\n" + "=" * 80)
