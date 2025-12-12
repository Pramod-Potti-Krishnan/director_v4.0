"""
Analytics Service Adapter

Implements adapter for Analytics Service v3 (data visualization charts).

Endpoint Pattern: typed (multiple endpoints by library type)
Service Type: data_visualization

Version: 2.0.0
Created: 2025-11-29
"""

from typing import Dict, Any, Optional, List
from src.models.variant_registry import ServiceConfig, VariantConfig, EndpointPattern
from src.services.adapters.base_adapter import (
    BaseServiceAdapter,
    InvalidRequestError,
    InvalidResponseError,
    EndpointResolutionError
)
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class AnalyticsServiceAdapter(BaseServiceAdapter):
    """
    Adapter for Analytics Service v3.

    The Analytics Service uses typed endpoints (chartjs, d3) with variant
    specification in the request body. It generates interactive charts with
    AI-generated observations.

    Request Format:
        {
            "chart_type": "pie",
            "data": [
                {"label": "Product A", "value": 45},
                {"label": "Product B", "value": 30},
                {"label": "Product C", "value": 25}
            ],
            "narrative": "Show market share distribution",  # optional
            "context": {                                    # optional
                "presentation_title": "Q4 Review",
                "tone": "professional",
                "audience": "executives"
            }
        }

    Response Format (L02):
        {
            "element_3": "<div>chart HTML</div>",      # chart
            "element_2": "AI-generated observations"    # observations
        }
    """

    def __init__(self, service_config: ServiceConfig):
        """
        Initialize Analytics Service adapter.

        Args:
            service_config: ServiceConfig from registry

        Raises:
            ValueError: If service doesn't use 'typed' endpoint pattern
        """
        super().__init__(service_config)

        # Validate endpoint pattern
        if self.endpoint_pattern != EndpointPattern.TYPED:
            raise ValueError(
                f"AnalyticsServiceAdapter requires 'typed' endpoint pattern, "
                f"got '{self.endpoint_pattern}'"
            )

        # Validate endpoints exist
        if not service_config.endpoints:
            raise EndpointResolutionError(
                "AnalyticsServiceAdapter requires endpoints in service config"
            )

        self.endpoints = service_config.endpoints

    def build_request(
        self,
        variant: VariantConfig,
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Build Analytics Service request payload.

        Args:
            variant: VariantConfig from registry
            parameters: Request parameters (data, narrative, etc.)
            context: Optional context (presentation_title, tone, etc.)

        Returns:
            Analytics Service request payload

        Raises:
            InvalidRequestError: If required fields missing or data invalid

        Example (Pie Chart):
            Input:
                variant: pie_chart
                parameters: {
                    "data": [
                        {"label": "A", "value": 45},
                        {"label": "B", "value": 30}
                    ],
                    "narrative": "Market share breakdown"
                }
                context: {"tone": "professional"}

            Output:
                {
                    "chart_type": "pie",
                    "data": [...],
                    "narrative": "Market share breakdown",
                    "context": {"tone": "professional"}
                }
        """
        request = {}

        # Get chart_type from service_specific config
        service_config = self.get_service_specific_config(variant.variant_id)
        if not service_config or "chart_type" not in service_config:
            raise InvalidRequestError(
                f"Analytics variant {variant.variant_id} missing chart_type in service_specific"
            )

        request["chart_type"] = service_config["chart_type"]

        # Validate and add data (required)
        if "data" not in parameters:
            raise InvalidRequestError(
                f"'data' is required for {variant.variant_id}"
            )

        data = parameters["data"]
        if not isinstance(data, list):
            raise InvalidRequestError(
                f"'data' must be a list for {variant.variant_id}"
            )

        # Validate data against requirements
        if variant.data_requirements:
            req = variant.data_requirements

            # Check min/max items
            if len(data) < req.min_items:
                raise InvalidRequestError(
                    f"Data must have at least {req.min_items} items, got {len(data)}"
                )
            if len(data) > req.max_items:
                raise InvalidRequestError(
                    f"Data must have at most {req.max_items} items, got {len(data)}"
                )

        request["data"] = data

        # Add optional narrative
        if "narrative" in parameters:
            request["narrative"] = parameters["narrative"]

        # Add context if provided
        if context:
            request["context"] = context

        # Add any other parameters not already included
        for key, value in parameters.items():
            if key not in request and key != "context":
                request[key] = value

        logger.debug(
            f"Built Analytics Service request for {variant.variant_id}",
            extra={
                "variant_id": variant.variant_id,
                "chart_type": request["chart_type"],
                "data_items": len(data),
                "has_narrative": "narrative" in request,
                "has_context": "context" in request
            }
        )

        return request

    def get_endpoint_url(self, variant: VariantConfig) -> str:
        """
        Get endpoint URL for Analytics Service variant.

        Analytics Service uses typed pattern with different endpoints
        for different chart libraries (chartjs, d3).

        Args:
            variant: VariantConfig with service_specific.endpoint_key

        Returns:
            Full endpoint URL

        Raises:
            EndpointResolutionError: If endpoint_key not found

        Example (Chart.js - Pie):
            base_url: "http://localhost:8006"
            endpoints["chartjs"]: "/analytics/v3/chartjs/generate"
            → "http://localhost:8006/analytics/v3/chartjs/generate"

        Example (D3 - Treemap):
            base_url: "http://localhost:8006"
            endpoints["d3"]: "/analytics/v3/d3/generate"
            → "http://localhost:8006/analytics/v3/d3/generate"
        """
        # Get endpoint_key from service_specific config
        service_config = self.get_service_specific_config(variant.variant_id)
        if not service_config or "endpoint_key" not in service_config:
            raise EndpointResolutionError(
                f"Analytics variant {variant.variant_id} missing endpoint_key "
                f"in service_specific"
            )

        endpoint_key = service_config["endpoint_key"]

        # Look up endpoint path
        if endpoint_key not in self.endpoints:
            raise EndpointResolutionError(
                f"Analytics endpoint_key '{endpoint_key}' not found in endpoints. "
                f"Available: {list(self.endpoints.keys())}"
            )

        endpoint_path = self.endpoints[endpoint_key]
        url = f"{self.base_url.rstrip('/')}{endpoint_path}"

        logger.debug(
            f"Resolved Analytics Service endpoint",
            extra={
                "variant_id": variant.variant_id,
                "endpoint_key": endpoint_key,
                "endpoint_path": endpoint_path,
                "url": url
            }
        )

        return url

    def validate_response(self, response: Dict[str, Any]) -> bool:
        """
        Validate Analytics Service response.

        Analytics Service L02 returns element_3 (chart) and element_2 (observations).
        L01 returns only element_3.

        Args:
            response: Response from Analytics Service

        Returns:
            True if valid, False otherwise

        Valid Response (L02):
            {
                "element_3": "<div>chart</div>",
                "element_2": "observations text"
            }

        Valid Response (L01):
            {
                "element_3": "<div>chart</div>"
            }

        Invalid Responses:
            {}
            {"error": "Chart generation failed"}
            {"element_3": ""}  # empty chart
        """
        # Check for error field
        if "error" in response:
            logger.error(
                "Analytics Service returned error",
                extra={"error": response.get("error")}
            )
            return False

        # Check for element_3 (chart)
        if "element_3" not in response:
            logger.error("Analytics Service response missing element_3 (chart)")
            return False

        # Check chart is not empty
        chart_html = response.get("element_3", "").strip()
        if not chart_html:
            logger.error("Analytics Service returned empty element_3 (chart)")
            return False

        # element_2 (observations) is optional depending on layout
        logger.debug(
            "Analytics Service response validated successfully",
            extra={"has_observations": "element_2" in response}
        )
        return True

    def transform_response(
        self,
        response: Dict[str, Any],
        variant: VariantConfig
    ) -> Dict[str, Any]:
        """
        Transform Analytics Service response to common format.

        Converts element_3/element_2 to more semantic names.

        Args:
            response: Raw response from Analytics Service
            variant: VariantConfig for context

        Returns:
            Transformed response with semantic names
        """
        transformed = {
            "chart_html": response["element_3"],  # element_3 → chart_html
            "variant_id": variant.variant_id,
            "service_type": "data_visualization"
        }

        # Add observations if present
        if "element_2" in response:
            transformed["observations"] = response["element_2"]

        # Include any additional fields from response
        for key, value in response.items():
            if key not in ["element_3", "element_2"] and key not in transformed:
                transformed[key] = value

        # Also keep original element names for backward compatibility
        transformed["element_3"] = response["element_3"]
        if "element_2" in response:
            transformed["element_2"] = response["element_2"]

        return transformed

    def get_required_fields(self, variant_id: str) -> list[str]:
        """
        Get required fields for Analytics Service variant.

        All Analytics variants require data.

        Args:
            variant_id: Variant identifier

        Returns:
            List of required field names
        """
        return ["data"]

    def get_optional_fields(self, variant_id: str) -> list[str]:
        """
        Get optional fields for Analytics Service variant.

        Common optional fields: narrative, context

        Args:
            variant_id: Variant identifier

        Returns:
            List of optional field names
        """
        return ["narrative", "context"]

    def get_data_requirements(self, variant_id: str) -> Optional[Dict[str, Any]]:
        """
        Get data requirements for variant.

        Args:
            variant_id: Variant identifier

        Returns:
            Dict with structure, min_items, max_items, value_type or None
        """
        variant = self.get_variant(variant_id)
        if not variant or not variant.data_requirements:
            return None

        req = variant.data_requirements
        return {
            "structure": str(req.structure),
            "min_items": req.min_items,
            "max_items": req.max_items,
            "value_type": str(req.value_type),
            "supports_percentages": req.supports_percentages
        }

    def get_chart_library(self, variant_id: str) -> Optional[str]:
        """
        Get chart library for variant (chartjs, d3, etc.).

        Args:
            variant_id: Variant identifier

        Returns:
            Library name or None
        """
        service_config = self.get_service_specific_config(variant_id)
        if not service_config:
            return None

        return service_config.get("library")

    def get_chart_type(self, variant_id: str) -> Optional[str]:
        """
        Get chart type for variant (pie, bar, line, etc.).

        Args:
            variant_id: Variant identifier

        Returns:
            Chart type or None
        """
        service_config = self.get_service_specific_config(variant_id)
        if not service_config:
            return None

        return service_config.get("chart_type")

    def supports_custom_colors(self, variant_id: str) -> bool:
        """
        Check if variant supports custom color palettes.

        Args:
            variant_id: Variant identifier

        Returns:
            True if custom colors supported, False otherwise
        """
        service_config = self.get_service_specific_config(variant_id)
        if not service_config:
            return False

        return service_config.get("supports_custom_colors", False)

    def supports_data_labels(self, variant_id: str) -> bool:
        """
        Check if variant supports data labels on chart.

        Args:
            variant_id: Variant identifier

        Returns:
            True if data labels supported, False otherwise
        """
        service_config = self.get_service_specific_config(variant_id)
        if not service_config:
            return False

        return service_config.get("supports_data_labels", False)

    def get_service_specific_config(self, variant_id: str) -> Optional[Dict[str, Any]]:
        """
        Get Analytics Service-specific configuration for variant.

        Args:
            variant_id: Variant identifier

        Returns:
            Service-specific config dict or None
        """
        variant = self.get_variant(variant_id)
        if not variant or not variant.service_specific:
            return None

        return variant.service_specific.get("analytics")
