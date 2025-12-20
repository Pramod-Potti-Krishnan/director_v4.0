"""
Text Service Coordination Client for Director Agent v4.0

Handles Text Service v1.2 coordination endpoints for intelligent variant selection
and content negotiation during strawman generation.

Coordination Endpoints:
- GET /v1.2/capabilities: Service capabilities and content signals
- POST /v1.2/can-handle: Content negotiation with confidence scoring
- POST /v1.2/recommend-variant: Variant recommendations based on content and space

This client is separate from TextServiceClientV1_2 which handles actual content generation.
The coordination client is used during strawman enhancement to determine IF and HOW
Text Service should handle each slide.

Author: Director v4.0 Multi-Service Coordination
Date: December 2024
"""

import httpx
from typing import Dict, Any, Optional, List
from src.utils.logger import setup_logger
from src.models.content_hints import (
    ContentHints,
    CanHandleResponse,
    VariantRecommendation,
    RecommendVariantResponse
)
from config.settings import get_settings

logger = setup_logger(__name__)


class TextServiceCapabilities:
    """Text Service capabilities response."""
    def __init__(self, data: Dict[str, Any]):
        self.service = data.get("service", "text-service")
        self.version = data.get("version", "1.2.0")
        self.status = data.get("status", "unknown")

        capabilities = data.get("capabilities", {})
        self.slide_types = capabilities.get("slide_types", [])
        self.variants = capabilities.get("variants", [])
        self.max_items_per_slide = capabilities.get("max_items_per_slide", 8)
        self.supports_themes = capabilities.get("supports_themes", False)
        self.parallel_generation = capabilities.get("parallel_generation", True)

        content_signals = data.get("content_signals", {})
        self.handles_well = content_signals.get("handles_well", [])
        self.handles_poorly = content_signals.get("handles_poorly", [])
        self.keywords = content_signals.get("keywords", [])


class TextServiceCoordinationClient:
    """
    Client for Text Service v1.2 coordination endpoints.

    Provides intelligent variant selection and content negotiation based on:
    - Slide content (title, topics)
    - Content hints (has_numbers, is_comparison, etc.)
    - Available space from Layout Service

    Usage:
        client = TextServiceCoordinationClient()

        # Check if Text Service can handle content
        can_handle = await client.can_handle(
            slide_content={"title": "Q4 Revenue", "topics": [...], "topic_count": 3},
            content_hints=ContentHints(has_numbers=True),
            available_space={"width": 1800, "height": 720, "layout_id": "L25"}
        )

        if can_handle.can_handle and can_handle.confidence >= 0.7:
            # Get variant recommendation
            variants = await client.recommend_variant(
                slide_content=slide_content,
                available_space=available_space
            )
            best_variant = variants.recommended_variants[0]
    """

    def __init__(self, base_url: Optional[str] = None, timeout: Optional[int] = None):
        """
        Initialize Text Service coordination client.

        Args:
            base_url: Override default Text Service URL
            timeout: Override default request timeout (default: 10s)
        """
        settings = get_settings()
        self.base_url = base_url or getattr(
            settings, 'TEXT_SERVICE_URL',
            'https://web-production-5daf.up.railway.app'
        )
        self.timeout = timeout or getattr(settings, 'TEXT_SERVICE_COORDINATION_TIMEOUT', 10)
        self.enabled = getattr(settings, 'USE_TEXT_SERVICE_COORDINATION', False)

        logger.info(
            "TextServiceCoordinationClient initialized",
            extra={
                "base_url": self.base_url,
                "timeout": self.timeout,
                "enabled": self.enabled
            }
        )

    async def health_check(self) -> bool:
        """
        Check if Text Service coordination endpoints are available.

        Returns:
            True if service is healthy, False otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                response = await client.get(f"{self.base_url}/v1.2/capabilities")

                if response.status_code == 200:
                    logger.debug("Text Service coordination health check: OK")
                    return True
                else:
                    logger.warning(
                        f"Text Service coordination health check failed: {response.status_code}"
                    )
                    return False
        except Exception as e:
            logger.warning(
                f"Cannot reach Text Service coordination: {str(e)}",
                extra={"error": str(e), "url": self.base_url}
            )
            return False

    async def get_capabilities(self) -> TextServiceCapabilities:
        """
        Fetch Text Service capabilities and content signals.

        GET /v1.2/capabilities

        Returns:
            TextServiceCapabilities with service info, variants, and content signals
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/v1.2/capabilities")
                response.raise_for_status()

                data = response.json()
                logger.info(
                    "Text Service capabilities fetched",
                    extra={
                        "version": data.get("version"),
                        "variants_count": len(data.get("capabilities", {}).get("variants", []))
                    }
                )

                return TextServiceCapabilities(data)

        except httpx.HTTPError as e:
            logger.error(
                f"Failed to fetch Text Service capabilities: {str(e)}",
                extra={"url": f"{self.base_url}/v1.2/capabilities"}
            )
            raise

    async def can_handle(
        self,
        slide_content: Dict[str, Any],
        content_hints: ContentHints,
        available_space: Dict[str, Any]
    ) -> CanHandleResponse:
        """
        Check if Text Service can handle the given content.

        POST /v1.2/can-handle

        Uses content analysis and space constraints to determine if Text Service
        is the right choice for this slide's content generation.

        Args:
            slide_content: Dict with title, topics, topic_count
            content_hints: ContentHints from ContentAnalyzer
            available_space: Dict with width, height, layout_id, optional sub_zones

        Returns:
            CanHandleResponse with confidence score and recommendation
        """
        payload = {
            "slide_content": slide_content,
            "content_hints": {
                "has_numbers": content_hints.has_numbers,
                "is_comparison": content_hints.is_comparison,
                "is_time_based": content_hints.is_time_based,
                "detected_keywords": content_hints.detected_keywords
            },
            "available_space": available_space
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/v1.2/can-handle",
                    json=payload
                )
                response.raise_for_status()

                data = response.json()

                result = CanHandleResponse(
                    can_handle=data.get("can_handle", False),
                    confidence=data.get("confidence", 0.0),
                    reason=data.get("reason", ""),
                    suggested_approach=data.get("suggested_approach"),
                    space_utilization=data.get("space_utilization")
                )

                logger.info(
                    f"Text Service can-handle: {result.can_handle} (confidence: {result.confidence:.2f})",
                    extra={
                        "can_handle": result.can_handle,
                        "confidence": result.confidence,
                        "reason": result.reason
                    }
                )

                return result

        except httpx.HTTPError as e:
            logger.error(
                f"Text Service can-handle failed: {str(e)}",
                extra={"slide_content": slide_content}
            )
            # Return negative response on error
            return CanHandleResponse(
                can_handle=False,
                confidence=0.0,
                reason=f"Service error: {str(e)}",
                suggested_approach=None,
                space_utilization=None
            )

    async def recommend_variant(
        self,
        slide_content: Dict[str, Any],
        available_space: Dict[str, Any]
    ) -> RecommendVariantResponse:
        """
        Get ranked variant recommendations for the content.

        POST /v1.2/recommend-variant

        Returns variants sorted by suitability for the given content and space.

        Args:
            slide_content: Dict with title, topics, topic_count
            available_space: Dict with width, height, layout_id

        Returns:
            RecommendVariantResponse with ranked recommendations
        """
        payload = {
            "slide_content": slide_content,
            "available_space": available_space
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/v1.2/recommend-variant",
                    json=payload
                )
                response.raise_for_status()

                data = response.json()

                # Parse recommendations
                recommended = []
                for rec in data.get("recommended_variants", []):
                    recommended.append(VariantRecommendation(
                        variant_id=rec.get("variant_id", ""),
                        confidence=rec.get("confidence", 0.0),
                        reason=rec.get("reason", ""),
                        requires_space=rec.get("requires_space")
                    ))

                result = RecommendVariantResponse(
                    recommended_variants=recommended,
                    not_recommended=data.get("not_recommended")
                )

                if recommended:
                    logger.info(
                        f"Text Service variant recommendation: {recommended[0].variant_id} "
                        f"(confidence: {recommended[0].confidence:.2f})",
                        extra={
                            "top_variant": recommended[0].variant_id,
                            "confidence": recommended[0].confidence,
                            "total_recommendations": len(recommended)
                        }
                    )
                else:
                    logger.warning(
                        "Text Service returned no variant recommendations",
                        extra={"slide_content": slide_content}
                    )

                return result

        except httpx.HTTPError as e:
            logger.error(
                f"Text Service recommend-variant failed: {str(e)}",
                extra={"slide_content": slide_content}
            )
            # Return empty response on error
            return RecommendVariantResponse(
                recommended_variants=[],
                not_recommended=None
            )

    async def get_best_variant(
        self,
        slide_content: Dict[str, Any],
        content_hints: ContentHints,
        available_space: Dict[str, Any],
        confidence_threshold: float = 0.70
    ) -> Optional[str]:
        """
        Convenience method: Get best variant if Text Service can handle content.

        Combines can_handle() and recommend_variant() into a single call.
        Returns None if Text Service cannot handle with sufficient confidence.

        Args:
            slide_content: Dict with title, topics, topic_count
            content_hints: ContentHints from ContentAnalyzer
            available_space: Dict with width, height, layout_id
            confidence_threshold: Minimum confidence to accept (default: 0.70)

        Returns:
            Best variant_id if confident, None otherwise
        """
        # First check if Text Service can handle this content
        can_handle_result = await self.can_handle(
            slide_content, content_hints, available_space
        )

        if not can_handle_result.can_handle:
            logger.debug(
                f"Text Service cannot handle content: {can_handle_result.reason}"
            )
            return None

        if can_handle_result.confidence < confidence_threshold:
            logger.debug(
                f"Text Service confidence ({can_handle_result.confidence:.2f}) "
                f"below threshold ({confidence_threshold})"
            )
            return None

        # Get variant recommendation
        recommend_result = await self.recommend_variant(
            slide_content, available_space
        )

        if not recommend_result.recommended_variants:
            return None

        best = recommend_result.recommended_variants[0]
        return best.variant_id


# Convenience function
async def get_text_service_coordination_client(
    base_url: Optional[str] = None
) -> TextServiceCoordinationClient:
    """
    Create and validate Text Service coordination client.

    Args:
        base_url: Optional Text Service URL override

    Returns:
        TextServiceCoordinationClient instance

    Raises:
        Exception: If service is not healthy
    """
    client = TextServiceCoordinationClient(base_url)

    # Perform health check
    is_healthy = await client.health_check()
    if not is_healthy:
        raise Exception(
            f"Text Service coordination at {client.base_url} is not healthy"
        )

    return client
