"""
Unified Service Router

Registry-driven service routing for all content generation services.
Replaces hardcoded service logic with configuration-driven approach.

Version: 2.0.0
Created: 2025-11-29
"""

import asyncio
import httpx
from typing import Dict, Any, Optional, List
from src.models.variant_registry import UnifiedVariantRegistry, ServiceConfig, VariantConfig
from src.services.adapters import (
    BaseServiceAdapter,
    TextServiceAdapter,
    IllustratorServiceAdapter,
    AnalyticsServiceAdapter
)
from src.services.adapters.base_adapter import InvalidRequestError, InvalidResponseError
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class UnifiedServiceRouter:
    """
    Unified router for all content generation services.

    Routes content generation requests to appropriate services using
    configuration from the unified variant registry. Uses service adapters
    to handle service-specific logic.

    Features:
    - Registry-driven routing (zero hardcoded service logic)
    - Automatic adapter selection based on service type
    - Request building via service adapters
    - Response validation and transformation
    - Comprehensive error handling and logging
    - Prior slides context support

    Architecture:
        Registry → Router → Adapter → Service API
        ↓                    ↓
        Variant Config      Request/Response

    Usage:
        registry = load_registry_from_file("config/unified_variant_registry.json")
        router = UnifiedServiceRouter(registry)

        result = await router.generate_content(
            variant_id="pyramid",
            service_name="illustrator_service_v1.0",
            parameters={"num_levels": 4, "topic": "Org Structure"},
            context={"presentation_title": "Company Overview"}
        )
    """

    def __init__(self, registry: UnifiedVariantRegistry):
        """
        Initialize unified service router.

        Args:
            registry: UnifiedVariantRegistry instance with all service configs
        """
        self.registry = registry
        self.adapters: Dict[str, BaseServiceAdapter] = {}

        # Initialize adapters for all enabled services
        self._initialize_adapters()

        logger.info(
            f"UnifiedServiceRouter initialized",
            extra={
                "total_services": len(registry.services),
                "enabled_services": len(self.adapters),
                "total_variants": sum(len(s.variants) for s in registry.services.values())
            }
        )

    def _initialize_adapters(self):
        """Initialize service adapters for all enabled services"""
        for service_name, service_config in self.registry.services.items():
            if not service_config.enabled:
                logger.info(f"Skipping disabled service: {service_name}")
                continue

            try:
                adapter = self._create_adapter(service_config)
                self.adapters[service_name] = adapter
                logger.info(
                    f"Initialized adapter for {service_name}",
                    extra={
                        "adapter_type": type(adapter).__name__,
                        "variant_count": len(service_config.variants)
                    }
                )
            except Exception as e:
                logger.error(
                    f"Failed to initialize adapter for {service_name}: {e}",
                    extra={"error": str(e)}
                )

    def _create_adapter(self, service_config: ServiceConfig) -> BaseServiceAdapter:
        """
        Create appropriate adapter for service type.

        Args:
            service_config: ServiceConfig from registry

        Returns:
            Service-specific adapter instance

        Raises:
            ValueError: If service type not supported
        """
        service_type = service_config.service_type

        if service_type.value == "template_based":
            return TextServiceAdapter(service_config)
        elif service_type.value == "llm_generated":
            return IllustratorServiceAdapter(service_config)
        elif service_type.value == "data_visualization":
            return AnalyticsServiceAdapter(service_config)
        else:
            raise ValueError(f"Unsupported service type: {service_type}")

    async def generate_content(
        self,
        variant_id: str,
        service_name: str,
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate content using specified variant and service.

        This is the main entry point for content generation. It:
        1. Validates variant and service exist
        2. Gets appropriate adapter
        3. Builds request via adapter
        4. Makes HTTP call to service
        5. Validates and transforms response
        6. Returns result or error

        Args:
            variant_id: Variant identifier (e.g., "pyramid", "pie_chart")
            service_name: Service name (e.g., "illustrator_service_v1.0")
            parameters: Variant-specific parameters
            context: Optional context (presentation_title, previous_slides, etc.)

        Returns:
            Dict with:
                - success: bool
                - html_content or chart_html: Generated content
                - variant_id: str
                - service_name: str
                - metadata: Optional dict

            Or on error:
                - success: False
                - error: str
                - error_details: dict

        Example:
            result = await router.generate_content(
                variant_id="pyramid",
                service_name="illustrator_service_v1.0",
                parameters={
                    "num_levels": 4,
                    "topic": "Organizational Hierarchy"
                },
                context={
                    "presentation_title": "Company Overview"
                }
            )

            if result["success"]:
                html = result["html_content"]
            else:
                error = result["error"]
        """
        try:
            # Get adapter for service
            adapter = self.adapters.get(service_name)
            if not adapter:
                return {
                    "success": False,
                    "error": f"Service '{service_name}' not found or not enabled",
                    "variant_id": variant_id,
                    "service_name": service_name
                }

            # Get variant config
            variant = adapter.get_variant(variant_id)
            if not variant:
                return {
                    "success": False,
                    "error": f"Variant '{variant_id}' not found in service '{service_name}'",
                    "variant_id": variant_id,
                    "service_name": service_name
                }

            # Check if variant is enabled
            if not adapter.is_variant_enabled(variant_id):
                return {
                    "success": False,
                    "error": f"Variant '{variant_id}' is not enabled (status: {variant.status})",
                    "variant_id": variant_id,
                    "service_name": service_name
                }

            # Build request via adapter
            try:
                request_payload = adapter.build_request(variant, parameters, context)
            except InvalidRequestError as e:
                return {
                    "success": False,
                    "error": f"Invalid request: {str(e)}",
                    "error_type": "validation",
                    "variant_id": variant_id,
                    "service_name": service_name
                }

            # Get endpoint URL
            endpoint_url = adapter.get_endpoint_url(variant)

            # Log request
            logger.info(
                f"Generating content with {variant_id}",
                extra={
                    "variant_id": variant_id,
                    "service_name": service_name,
                    "endpoint": endpoint_url,
                    "request_keys": list(request_payload.keys())
                }
            )

            # Make HTTP request
            timeout = adapter.get_timeout(variant)
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    endpoint_url,
                    json=request_payload
                )
                response.raise_for_status()
                response_data = response.json()

            # Validate response
            if not adapter.validate_response(response_data):
                return {
                    "success": False,
                    "error": "Service returned invalid response",
                    "error_type": "validation",
                    "variant_id": variant_id,
                    "service_name": service_name,
                    "response_keys": list(response_data.keys()) if isinstance(response_data, dict) else None
                }

            # Transform response
            transformed = adapter.transform_response(response_data, variant)

            # Return success
            result = {
                "success": True,
                "variant_id": variant_id,
                "service_name": service_name,
                **transformed
            }

            logger.info(
                f"Content generation successful for {variant_id}",
                extra={
                    "variant_id": variant_id,
                    "service_name": service_name,
                    "response_keys": list(transformed.keys())
                }
            )

            return result

        except httpx.TimeoutException as e:
            logger.error(
                f"Timeout generating {variant_id}",
                extra={
                    "variant_id": variant_id,
                    "service_name": service_name,
                    "error": str(e)
                }
            )
            return {
                "success": False,
                "error": "Service request timed out",
                "error_type": "timeout",
                "error_details": str(e),
                "variant_id": variant_id,
                "service_name": service_name
            }

        except httpx.HTTPStatusError as e:
            logger.error(
                f"HTTP error generating {variant_id}",
                extra={
                    "variant_id": variant_id,
                    "service_name": service_name,
                    "status_code": e.response.status_code,
                    "error": str(e)
                }
            )
            return {
                "success": False,
                "error": f"Service returned HTTP {e.response.status_code}",
                "error_type": "http_error",
                "error_details": str(e),
                "status_code": e.response.status_code,
                "variant_id": variant_id,
                "service_name": service_name
            }

        except Exception as e:
            logger.error(
                f"Unexpected error generating {variant_id}",
                extra={
                    "variant_id": variant_id,
                    "service_name": service_name,
                    "error_type": type(e).__name__,
                    "error": str(e)
                },
                exc_info=True
            )
            return {
                "success": False,
                "error": f"Unexpected error: {type(e).__name__}",
                "error_type": "unknown",
                "error_details": str(e),
                "variant_id": variant_id,
                "service_name": service_name
            }

    def get_variant_info(self, variant_id: str, service_name: str) -> Optional[Dict[str, Any]]:
        """
        Get comprehensive information about a variant.

        Args:
            variant_id: Variant identifier
            service_name: Service name

        Returns:
            Dict with variant info or None if not found
        """
        adapter = self.adapters.get(service_name)
        if not adapter:
            return None

        variant = adapter.get_variant(variant_id)
        if not variant:
            return None

        return {
            "variant_id": variant.variant_id,
            "display_name": variant.display_name,
            "description": variant.description,
            "status": str(variant.status),
            "service_name": service_name,
            "service_type": str(adapter.service_type),
            "endpoint_pattern": str(adapter.endpoint_pattern),
            "classification_priority": variant.classification.priority,
            "keywords_count": len(variant.classification.keywords),
            "required_fields": adapter.get_required_fields(variant_id),
            "optional_fields": adapter.get_optional_fields(variant_id)
        }

    def list_all_variants(self) -> List[Dict[str, Any]]:
        """
        List all available variants across all services.

        Returns:
            List of variant info dicts
        """
        variants = []

        for service_name, adapter in self.adapters.items():
            for variant_id in adapter.list_variants():
                info = self.get_variant_info(variant_id, service_name)
                if info:
                    variants.append(info)

        # Sort by priority (lower = higher priority)
        variants.sort(key=lambda x: x["classification_priority"])

        return variants

    def list_variants_by_service_type(self, service_type: str) -> List[Dict[str, Any]]:
        """
        List variants filtered by service type.

        Args:
            service_type: "template_based", "llm_generated", or "data_visualization"

        Returns:
            List of variant info dicts
        """
        variants = []

        for service_name, adapter in self.adapters.items():
            if str(adapter.service_type) == service_type:
                for variant_id in adapter.list_variants():
                    info = self.get_variant_info(variant_id, service_name)
                    if info:
                        variants.append(info)

        variants.sort(key=lambda x: x["classification_priority"])
        return variants

    def get_service_stats(self) -> Dict[str, Any]:
        """
        Get statistics about registered services and variants.

        Returns:
            Dict with service statistics
        """
        total_variants = sum(len(adapter.list_variants()) for adapter in self.adapters.values())

        service_breakdown = {}
        for service_name, adapter in self.adapters.items():
            service_breakdown[service_name] = {
                "service_type": str(adapter.service_type),
                "endpoint_pattern": str(adapter.endpoint_pattern),
                "variant_count": len(adapter.list_variants()),
                "variants": adapter.list_variants()
            }

        return {
            "total_services": len(self.adapters),
            "total_variants": total_variants,
            "services": service_breakdown
        }
