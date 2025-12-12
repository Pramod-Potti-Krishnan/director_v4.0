"""
Illustrator Service Adapter

Implements adapter for Illustrator Service v1.0 (LLM-generated visualizations).

Endpoint Pattern: per_variant (dedicated endpoint per variant)
Service Type: llm_generated

Version: 2.0.0
Created: 2025-11-29
"""

from typing import Dict, Any, Optional
from src.models.variant_registry import ServiceConfig, VariantConfig, EndpointPattern
from src.services.adapters.base_adapter import (
    BaseServiceAdapter,
    InvalidRequestError,
    InvalidResponseError,
    EndpointResolutionError
)
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class IllustratorServiceAdapter(BaseServiceAdapter):
    """
    Adapter for Illustrator Service v1.0.

    The Illustrator Service uses dedicated endpoints per variant (per_variant pattern).
    It generates AI-powered visualizations like pyramids, funnels, and concentric circles.

    Request Format (Pyramid Example):
        {
            "num_levels": 4,
            "topic": "Organizational Hierarchy",
            "target_points": ["Leadership", "Management", "Staff"],  # optional
            "context": {                                              # optional
                "presentation_title": "Company Overview",
                "previous_slides": [...]
            }
        }

    Response Format:
        {
            "html_content": "<svg>...</svg>",
            "metadata": {
                "levels_generated": 4,
                "topic": "Organizational Hierarchy"
            }
        }
    """

    def __init__(self, service_config: ServiceConfig):
        """
        Initialize Illustrator Service adapter.

        Args:
            service_config: ServiceConfig from registry

        Raises:
            ValueError: If service doesn't use 'per_variant' endpoint pattern
        """
        super().__init__(service_config)

        # Validate endpoint pattern
        if self.endpoint_pattern != EndpointPattern.PER_VARIANT:
            raise ValueError(
                f"IllustratorServiceAdapter requires 'per_variant' endpoint pattern, "
                f"got '{self.endpoint_pattern}'"
            )

    def build_request(
        self,
        variant: VariantConfig,
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Build Illustrator Service request payload.

        Constructs request with variant-specific parameters based on
        variant.parameters configuration.

        Args:
            variant: VariantConfig from registry
            parameters: Request parameters (num_levels, topic, etc.)
            context: Optional context (presentation_title, previous_slides, etc.)

        Returns:
            Illustrator Service request payload

        Raises:
            InvalidRequestError: If required fields are missing or invalid

        Example (Pyramid):
            Input:
                variant: pyramid
                parameters: {
                    "num_levels": 4,
                    "topic": "Organizational Hierarchy",
                    "target_points": ["Vision", "Strategy", "Tactics", "Execution"]
                }
                context: {
                    "presentation_title": "Company Overview",
                    "previous_slides": [...]
                }

            Output:
                {
                    "num_levels": 4,
                    "topic": "Organizational Hierarchy",
                    "target_points": ["Vision", "Strategy", "Tactics", "Execution"],
                    "context": {
                        "presentation_title": "Company Overview",
                        "previous_slides": [...]
                    }
                }
        """
        request = {}

        # Get variant parameters configuration
        if not variant.parameters:
            raise InvalidRequestError(
                f"Illustrator variant {variant.variant_id} missing parameters config"
            )

        params_config = variant.parameters

        # Add count field (num_levels, num_stages, etc.)
        count_field = params_config.count_field
        if count_field in parameters:
            count_value = parameters[count_field]

            # Validate count range
            if not (params_config.count_range.min <= count_value <= params_config.count_range.max):
                raise InvalidRequestError(
                    f"{count_field} must be between {params_config.count_range.min} "
                    f"and {params_config.count_range.max}, got {count_value}"
                )

            request[count_field] = count_value
        else:
            # Use optimal count as default
            request[count_field] = params_config.optimal_count
            logger.debug(
                f"Using optimal {count_field} for {variant.variant_id}",
                extra={
                    "count_field": count_field,
                    "optimal_count": params_config.optimal_count
                }
            )

        # Add topic (required for all illustrator variants)
        if "topic" not in parameters:
            raise InvalidRequestError(
                f"'topic' is required for {variant.variant_id}"
            )
        request["topic"] = parameters["topic"]

        # Add optional target_points if provided
        if "target_points" in parameters:
            request["target_points"] = parameters["target_points"]

        # Add context if provided
        if context:
            request["context"] = context

        # Add any other parameters not already included
        for key, value in parameters.items():
            if key not in request and key not in ["context"]:
                request[key] = value

        logger.debug(
            f"Built Illustrator Service request for {variant.variant_id}",
            extra={
                "variant_id": variant.variant_id,
                "count_field": count_field,
                "count_value": request.get(count_field),
                "has_target_points": "target_points" in request,
                "has_context": "context" in request
            }
        )

        return request

    def get_endpoint_url(self, variant: VariantConfig) -> str:
        """
        Get endpoint URL for Illustrator Service variant.

        Illustrator Service uses per_variant pattern, so each variant
        has its own dedicated endpoint.

        Args:
            variant: VariantConfig with endpoint field

        Returns:
            Full endpoint URL

        Raises:
            EndpointResolutionError: If variant doesn't have endpoint

        Example (Pyramid):
            base_url: "http://localhost:8000"
            variant.endpoint: "/v1.0/pyramid/generate"
            → "http://localhost:8000/v1.0/pyramid/generate"

        Example (Funnel):
            base_url: "http://localhost:8000"
            variant.endpoint: "/v1.0/funnel/generate"
            → "http://localhost:8000/v1.0/funnel/generate"
        """
        if not variant.endpoint:
            raise EndpointResolutionError(
                f"Illustrator variant {variant.variant_id} missing endpoint config"
            )

        url = f"{self.base_url.rstrip('/')}{variant.endpoint}"

        logger.debug(
            f"Resolved Illustrator Service endpoint",
            extra={
                "variant_id": variant.variant_id,
                "endpoint": variant.endpoint,
                "url": url
            }
        )

        return url

    def validate_response(self, response: Dict[str, Any]) -> bool:
        """
        Validate Illustrator Service response.

        Illustrator Service must return html_content field.
        Optionally includes metadata field.

        Args:
            response: Response from Illustrator Service

        Returns:
            True if valid, False otherwise

        Valid Response:
            {
                "html_content": "<svg>...</svg>",
                "metadata": {...}  # optional
            }

        Invalid Responses:
            {}
            {"error": "Generation failed"}
            {"html_content": ""}  # empty content
        """
        # Check for error field
        if "error" in response:
            logger.error(
                "Illustrator Service returned error",
                extra={"error": response.get("error")}
            )
            return False

        # Check for html_content
        if "html_content" not in response:
            logger.error("Illustrator Service response missing html_content")
            return False

        # Check content is not empty
        html_content = response.get("html_content", "").strip()
        if not html_content:
            logger.error("Illustrator Service returned empty html_content")
            return False

        logger.debug(
            "Illustrator Service response validated successfully",
            extra={"has_metadata": "metadata" in response}
        )
        return True

    def transform_response(
        self,
        response: Dict[str, Any],
        variant: VariantConfig
    ) -> Dict[str, Any]:
        """
        Transform Illustrator Service response to common format.

        Adds variant metadata and service type information.

        Args:
            response: Raw response from Illustrator Service
            variant: VariantConfig for context

        Returns:
            Transformed response with metadata
        """
        transformed = {
            "html_content": response["html_content"],
            "variant_id": variant.variant_id,
            "service_type": "llm_generated"
        }

        # Include metadata if present
        if "metadata" in response:
            transformed["metadata"] = response["metadata"]

        # Include any additional fields from response
        for key, value in response.items():
            if key not in transformed:
                transformed[key] = value

        return transformed

    def get_required_fields(self, variant_id: str) -> list[str]:
        """
        Get required fields for Illustrator Service variant.

        All Illustrator variants require topic and the count field
        (num_levels, num_stages, etc.).

        Args:
            variant_id: Variant identifier

        Returns:
            List of required field names
        """
        variant = self.get_variant(variant_id)
        if not variant or not variant.parameters:
            return ["topic"]

        # Topic is always required
        required = ["topic"]

        # Add count field (though it can use optimal_count as default)
        count_field = variant.parameters.count_field
        if count_field not in required:
            required.append(count_field)

        # Add any additional required fields from config
        if variant.parameters.required_fields:
            for field in variant.parameters.required_fields:
                if field not in required:
                    required.append(field)

        return required

    def get_optional_fields(self, variant_id: str) -> list[str]:
        """
        Get optional fields for Illustrator Service variant.

        Common optional fields: target_points, context

        Args:
            variant_id: Variant identifier

        Returns:
            List of optional field names
        """
        return ["target_points", "context"]

    def get_count_range(self, variant_id: str) -> Optional[Dict[str, int]]:
        """
        Get valid count range for variant.

        Args:
            variant_id: Variant identifier

        Returns:
            Dict with min, max, optimal or None
        """
        variant = self.get_variant(variant_id)
        if not variant or not variant.parameters:
            return None

        params = variant.parameters
        return {
            "min": params.count_range.min,
            "max": params.count_range.max,
            "optimal": params.optimal_count
        }

    def get_element_name(self, variant_id: str) -> Optional[str]:
        """
        Get element name for variant (levels, stages, circles, etc.).

        Args:
            variant_id: Variant identifier

        Returns:
            Element name or None
        """
        variant = self.get_variant(variant_id)
        if not variant or not variant.parameters:
            return None

        return variant.parameters.element_name

    def get_service_specific_config(self, variant_id: str) -> Optional[Dict[str, Any]]:
        """
        Get Illustrator Service-specific configuration for variant.

        Args:
            variant_id: Variant identifier

        Returns:
            Service-specific config dict or None
        """
        variant = self.get_variant(variant_id)
        if not variant or not variant.service_specific:
            return None

        return variant.service_specific.get("illustrator")
