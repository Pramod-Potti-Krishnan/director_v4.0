"""
Base Service Adapter - Abstract Interface

Defines the common interface that all service adapters must implement.
Provides core functionality for request building, endpoint resolution,
and response handling based on the unified variant registry.

Version: 2.0.0
Created: 2025-11-29
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from src.models.variant_registry import ServiceConfig, VariantConfig
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class BaseServiceAdapter(ABC):
    """
    Abstract base class for service adapters.

    Each service (Text, Illustrator, Analytics) implements this interface
    to provide service-specific request building and response handling.

    The adapter pattern allows the unified router to work with all services
    through a common interface while encapsulating service-specific logic.

    Responsibilities:
    - Build service-specific requests from generic parameters
    - Resolve endpoint URLs based on endpoint pattern
    - Validate service responses
    - Transform responses to common format
    - Handle service-specific errors

    Lifecycle:
    1. Initialize adapter with ServiceConfig from registry
    2. For each request:
       a. get_endpoint_url() - resolve endpoint
       b. build_request() - construct request payload
       c. [Director makes HTTP call]
       d. validate_response() - check response validity
       e. transform_response() - normalize to common format
    """

    def __init__(self, service_config: ServiceConfig):
        """
        Initialize adapter with service configuration.

        Args:
            service_config: ServiceConfig from unified registry
        """
        self.service_config = service_config
        self.base_url = str(service_config.base_url)
        self.service_type = service_config.service_type
        self.endpoint_pattern = service_config.endpoint_pattern
        self.timeout = service_config.timeout

        logger.info(
            f"{self.__class__.__name__} initialized",
            extra={
                "service_type": str(self.service_type),
                "endpoint_pattern": str(self.endpoint_pattern),
                "base_url": self.base_url,
                "variant_count": len(service_config.variants)
            }
        )

    @abstractmethod
    def build_request(
        self,
        variant: VariantConfig,
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Build service-specific request payload.

        This method transforms generic parameters into the specific
        format expected by the service API.

        Args:
            variant: VariantConfig from registry
            parameters: Generic parameters from Director
            context: Optional context (presentation_title, previous_slides, etc.)

        Returns:
            Service-specific request payload

        Example (Text Service):
            Input:
                variant: bilateral_comparison
                parameters: {"title": "AWS vs GCP", "key_points": [...]}
                context: {"tone": "professional"}

            Output:
                {
                    "variant_id": "bilateral_comparison",
                    "title": "AWS vs GCP",
                    "key_points": [...],
                    "tone": "professional"
                }

        Example (Illustrator Service):
            Input:
                variant: pyramid
                parameters: {"topic": "Org Structure", "num_levels": 4}
                context: {"presentation_title": "Company Overview"}

            Output:
                {
                    "num_levels": 4,
                    "topic": "Org Structure",
                    "context": {
                        "presentation_title": "Company Overview"
                    }
                }
        """
        pass

    @abstractmethod
    def get_endpoint_url(self, variant: VariantConfig) -> str:
        """
        Resolve endpoint URL for variant based on endpoint pattern.

        Handles three endpoint patterns:
        1. single: Use default_endpoint (variant_id in request body)
        2. per_variant: Use variant.endpoint
        3. typed: Use endpoints[endpoint_key] from service_specific

        Args:
            variant: VariantConfig from registry

        Returns:
            Full endpoint URL (base_url + endpoint_path)

        Example (single pattern - Text Service):
            base_url: "https://text-service.com"
            default_endpoint: "/v1.2/generate"
            → "https://text-service.com/v1.2/generate"

        Example (per_variant pattern - Illustrator):
            base_url: "http://localhost:8000"
            variant.endpoint: "/v1.0/pyramid/generate"
            → "http://localhost:8000/v1.0/pyramid/generate"

        Example (typed pattern - Analytics):
            base_url: "http://localhost:8006"
            endpoints["chartjs"]: "/analytics/v3/chartjs/generate"
            → "http://localhost:8006/analytics/v3/chartjs/generate"
        """
        pass

    @abstractmethod
    def validate_response(self, response: Dict[str, Any]) -> bool:
        """
        Validate service response structure and content.

        Checks that the response contains required fields and
        conforms to expected format.

        Args:
            response: Raw response from service

        Returns:
            True if response is valid, False otherwise

        Example (Text Service):
            Valid: {"html_content": "<div>...</div>"}
            Invalid: {} or {"error": "Failed"}

        Example (Illustrator):
            Valid: {"html_content": "<svg>...</svg>", "metadata": {...}}
            Invalid: {"error": "Generation failed"}

        Example (Analytics):
            Valid: {"element_3": "<div>chart</div>", "element_2": "observations"}
            Invalid: {"error": "Invalid data"}
        """
        pass

    def transform_response(
        self,
        response: Dict[str, Any],
        variant: VariantConfig
    ) -> Dict[str, Any]:
        """
        Transform service response to common format.

        Optional method that can be overridden to normalize responses
        from different services into a common structure.

        Default implementation returns response unchanged.

        Args:
            response: Raw response from service
            variant: VariantConfig for context

        Returns:
            Transformed response

        Example:
            Input (Analytics L02):
                {"element_3": "<div>chart</div>", "element_2": "observations"}

            Output (normalized):
                {
                    "html_content": "<div>chart</div>",
                    "observations": "observations",
                    "layout": "L02"
                }
        """
        # Default: no transformation
        return response

    def get_timeout(self, variant: Optional[VariantConfig] = None) -> int:
        """
        Get request timeout for variant.

        Can be overridden to provide variant-specific timeouts.

        Args:
            variant: Optional VariantConfig for variant-specific timeout

        Returns:
            Timeout in seconds
        """
        return self.timeout

    def handle_error(
        self,
        error: Exception,
        variant: VariantConfig,
        request: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle service errors and provide fallback response.

        Can be overridden to provide service-specific error handling.

        Args:
            error: Exception that occurred
            variant: VariantConfig being requested
            request: Request that failed

        Returns:
            Error response dict

        Default implementation returns basic error info.
        """
        logger.error(
            f"Service error for {variant.variant_id}",
            extra={
                "variant_id": variant.variant_id,
                "error": str(error),
                "error_type": type(error).__name__
            }
        )

        return {
            "error": True,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "variant_id": variant.variant_id
        }

    def get_variant(self, variant_id: str) -> Optional[VariantConfig]:
        """
        Get variant configuration by ID.

        Convenience method for accessing variants from the service config.

        Args:
            variant_id: Variant identifier

        Returns:
            VariantConfig if found, None otherwise
        """
        return self.service_config.variants.get(variant_id)

    def list_variants(self) -> list[str]:
        """
        List all variant IDs for this service.

        Returns:
            List of variant IDs
        """
        return list(self.service_config.variants.keys())

    def is_variant_enabled(self, variant_id: str) -> bool:
        """
        Check if variant is enabled (not disabled or deprecated).

        Args:
            variant_id: Variant identifier

        Returns:
            True if variant is production or beta, False otherwise
        """
        variant = self.get_variant(variant_id)
        if not variant:
            return False

        from src.models.variant_registry import VariantStatus
        return variant.status in [VariantStatus.PRODUCTION, VariantStatus.BETA]

    def get_required_fields(self, variant_id: str) -> list[str]:
        """
        Get required fields for variant request.

        Can be overridden for service-specific logic.

        Args:
            variant_id: Variant identifier

        Returns:
            List of required field names
        """
        variant = self.get_variant(variant_id)
        if not variant:
            return []

        # Return from variant config if available
        if variant.required_fields:
            return variant.required_fields

        # Service-specific defaults
        return []

    def get_optional_fields(self, variant_id: str) -> list[str]:
        """
        Get optional fields for variant request.

        Can be overridden for service-specific logic.

        Args:
            variant_id: Variant identifier

        Returns:
            List of optional field names
        """
        variant = self.get_variant(variant_id)
        if not variant:
            return []

        # Return from variant config if available
        if variant.optional_fields:
            return variant.optional_fields

        # Service-specific defaults
        return []

    def __repr__(self) -> str:
        """String representation of adapter."""
        return (
            f"{self.__class__.__name__}("
            f"service_type={self.service_type}, "
            f"variants={len(self.service_config.variants)})"
        )


class ServiceAdapterError(Exception):
    """Base exception for service adapter errors."""
    pass


class InvalidRequestError(ServiceAdapterError):
    """Raised when request parameters are invalid."""
    pass


class InvalidResponseError(ServiceAdapterError):
    """Raised when service response is invalid."""
    pass


class EndpointResolutionError(ServiceAdapterError):
    """Raised when endpoint URL cannot be resolved."""
    pass
