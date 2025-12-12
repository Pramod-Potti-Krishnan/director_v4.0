"""
Text/Table Service Adapter

Implements adapter for Text/Table Service v1.2 (template-based content generation).

Endpoint Pattern: single (default_endpoint + variant_id in body)
Service Type: template_based

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


class TextServiceAdapter(BaseServiceAdapter):
    """
    Adapter for Text/Table Service v1.2.

    The Text Service uses a single endpoint with variant_id in the request body.
    It generates HTML content using predefined templates.

    Request Format:
        {
            "variant_id": "bilateral_comparison",
            "title": "AWS vs GCP",
            "subtitle": "Cloud Provider Comparison",  # optional
            "key_points": ["Point 1", "Point 2"],     # optional
            "tone": "professional",                    # optional
            "audience": "executives"                   # optional
        }

    Response Format:
        {
            "html_content": "<div>...</div>"
        }
    """

    def __init__(self, service_config: ServiceConfig):
        """
        Initialize Text Service adapter.

        Args:
            service_config: ServiceConfig from registry

        Raises:
            ValueError: If service doesn't use 'single' endpoint pattern
        """
        super().__init__(service_config)

        # Validate endpoint pattern
        if self.endpoint_pattern != EndpointPattern.SINGLE:
            raise ValueError(
                f"TextServiceAdapter requires 'single' endpoint pattern, "
                f"got '{self.endpoint_pattern}'"
            )

        # Validate default_endpoint exists
        if not service_config.default_endpoint:
            raise EndpointResolutionError(
                "TextServiceAdapter requires default_endpoint in service config"
            )

        self.default_endpoint = service_config.default_endpoint

    def build_request(
        self,
        variant: VariantConfig,
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Build Text Service request payload.

        Constructs request with variant_id and all provided parameters.

        Args:
            variant: VariantConfig from registry
            parameters: Request parameters (title, subtitle, key_points, etc.)
            context: Optional context (tone, audience, etc.)

        Returns:
            Text Service request payload

        Raises:
            InvalidRequestError: If required fields are missing

        Example:
            Input:
                variant: bilateral_comparison
                parameters: {
                    "title": "AWS vs GCP",
                    "key_points": ["Cost: AWS higher", "ML: GCP better"]
                }
                context: {"tone": "professional"}

            Output:
                {
                    "variant_id": "bilateral_comparison",
                    "title": "AWS vs GCP",
                    "key_points": ["Cost: AWS higher", "ML: GCP better"],
                    "tone": "professional"
                }
        """
        # Start with variant_id (required by Text Service)
        request = {
            "variant_id": variant.variant_id
        }

        # Add all parameters
        request.update(parameters)

        # Add context fields if provided
        if context:
            # Text Service accepts tone, audience, etc. as top-level fields
            for key, value in context.items():
                if key not in request:  # Don't override parameters
                    request[key] = value

        # Validate required fields
        required = self.get_required_fields(variant.variant_id)
        missing = [field for field in required if field not in request]
        if missing:
            raise InvalidRequestError(
                f"Missing required fields for {variant.variant_id}: {missing}"
            )

        logger.debug(
            f"Built Text Service request for {variant.variant_id}",
            extra={
                "variant_id": variant.variant_id,
                "request_keys": list(request.keys())
            }
        )

        return request

    def get_endpoint_url(self, variant: VariantConfig) -> str:
        """
        Get endpoint URL for Text Service.

        Text Service uses single endpoint pattern, so always returns
        base_url + default_endpoint.

        Args:
            variant: VariantConfig (not used for single pattern)

        Returns:
            Full endpoint URL

        Example:
            base_url: "https://web-production-5daf.up.railway.app"
            default_endpoint: "/v1.2/generate"
            → "https://web-production-5daf.up.railway.app/v1.2/generate"
        """
        url = f"{self.base_url.rstrip('/')}{self.default_endpoint}"

        logger.debug(
            f"Resolved Text Service endpoint",
            extra={
                "variant_id": variant.variant_id,
                "url": url
            }
        )

        return url

    def validate_response(self, response: Dict[str, Any]) -> bool:
        """
        Validate Text Service response.

        Text Service must return html_content field.

        Args:
            response: Response from Text Service

        Returns:
            True if valid, False otherwise

        Valid Response:
            {"html_content": "<div>...</div>"}

        Invalid Responses:
            {}
            {"error": "Generation failed"}
            {"html_content": ""}  # empty content
        """
        # Check for error field
        if "error" in response:
            logger.error(
                "Text Service returned error",
                extra={"error": response.get("error")}
            )
            return False

        # Check for html_content
        if "html_content" not in response:
            logger.error("Text Service response missing html_content")
            return False

        # Check content is not empty
        html_content = response.get("html_content", "").strip()
        if not html_content:
            logger.error("Text Service returned empty html_content")
            return False

        logger.debug("Text Service response validated successfully")
        return True

    def transform_response(
        self,
        response: Dict[str, Any],
        variant: VariantConfig
    ) -> Dict[str, Any]:
        """
        Transform Text Service response to common format.

        Text Service response is already in standard format, so this
        just adds metadata.

        Args:
            response: Raw response from Text Service
            variant: VariantConfig for context

        Returns:
            Transformed response with metadata
        """
        transformed = {
            "html_content": response["html_content"],
            "variant_id": variant.variant_id,
            "service_type": "template_based"
        }

        # Include any additional fields from response
        for key, value in response.items():
            if key not in transformed:
                transformed[key] = value

        return transformed

    def get_required_fields(self, variant_id: str) -> list[str]:
        """
        Get required fields for Text Service variant.

        Text Service variants always require variant_id and title.
        Additional required fields come from variant config.

        Args:
            variant_id: Variant identifier

        Returns:
            List of required field names
        """
        variant = self.get_variant(variant_id)
        if not variant:
            return ["variant_id", "title"]

        # Start with standard required fields
        required = ["variant_id", "title"]

        # Add variant-specific required fields
        if variant.required_fields:
            for field in variant.required_fields:
                if field not in required:
                    required.append(field)

        return required

    def get_optional_fields(self, variant_id: str) -> list[str]:
        """
        Get optional fields for Text Service variant.

        Common optional fields: subtitle, key_points, tone, audience

        Args:
            variant_id: Variant identifier

        Returns:
            List of optional field names
        """
        variant = self.get_variant(variant_id)

        # Common optional fields
        optional = ["subtitle", "key_points", "tone", "audience"]

        # Add variant-specific optional fields
        if variant and variant.optional_fields:
            for field in variant.optional_fields:
                if field not in optional:
                    optional.append(field)

        return optional

    def get_service_specific_config(self, variant_id: str) -> Optional[Dict[str, Any]]:
        """
        Get Text Service-specific configuration for variant.

        Args:
            variant_id: Variant identifier

        Returns:
            Service-specific config dict or None
        """
        variant = self.get_variant(variant_id)
        if not variant or not variant.service_specific:
            return None

        return variant.service_specific.get("text_service")
