"""
Illustrator Service Client for Director Agent v3.4

Handles communication with Illustrator Service v1.0 for pyramid and other
data visualization generation.

Integration:
- Works with Illustrator Service v1.0 aligned to Text Service v1.2 architecture
- Director-managed context (stateless service calls)
- Optional session tracking fields for narrative continuity
- Backward compatible with minimal requests

Author: Director v3.4 Integration Team
Date: January 15, 2025
"""

import httpx
from typing import Dict, Any, Optional, List
from src.utils.logger import setup_logger
from config.settings import get_settings

logger = setup_logger(__name__)


class IllustratorClient:
    """
    Client for calling Illustrator Service v1.0 APIs.

    The Illustrator Service generates data visualizations (pyramids, funnels, etc.)
    with AI-generated content. It follows the same architecture as Text Service v1.2:
    - Stateless service (no server-side sessions)
    - Director passes explicit context via previous_slides
    - Optional session tracking fields for logging/analytics

    Usage:
        client = IllustratorClient()
        result = await client.generate_pyramid(
            num_levels=4,
            topic="Organizational Hierarchy",
            context={
                "presentation_title": "Company Overview",
                "previous_slides": [...],  # For narrative continuity
                "slide_purpose": "Show reporting structure"
            }
        )
    """

    def __init__(self, base_url: Optional[str] = None, timeout: Optional[int] = None):
        """
        Initialize Illustrator client.

        Args:
            base_url: Override default Illustrator service URL
            timeout: Override default request timeout
        """
        settings = get_settings()
        self.base_url = base_url or settings.ILLUSTRATOR_SERVICE_URL
        self.timeout = timeout or settings.ILLUSTRATOR_SERVICE_TIMEOUT
        self.enabled = settings.ILLUSTRATOR_SERVICE_ENABLED

        logger.info(
            f"IllustratorClient initialized",
            extra={
                "base_url": self.base_url,
                "timeout": self.timeout,
                "enabled": self.enabled
            }
        )

    async def health_check(self) -> bool:
        """
        Check if Illustrator service is healthy and reachable.

        Returns:
            True if service is healthy, False otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/health")

                if response.status_code == 200:
                    logger.info("Illustrator service health check: OK")
                    return True
                else:
                    logger.warning(
                        f"Illustrator service health check failed: {response.status_code}",
                        extra={"status_code": response.status_code}
                    )
                    return False
        except Exception as e:
            logger.error(
                f"Cannot reach Illustrator service: {str(e)}",
                extra={"error": str(e), "url": self.base_url}
            )
            return False

    async def generate_pyramid(
        self,
        num_levels: int,
        topic: str,
        presentation_id: Optional[str] = None,
        slide_id: Optional[str] = None,
        slide_number: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None,
        target_points: Optional[List[str]] = None,
        tone: str = "professional",
        audience: str = "general",
        validate_constraints: bool = True
    ) -> Dict[str, Any]:
        """
        Generate a pyramid visualization with AI-generated content.

        The Illustrator service will:
        1. Generate level labels and descriptions using Gemini LLM
        2. Apply character constraints (with auto-retry)
        3. Create HTML visualization with embedded CSS
        4. Consider previous slides context for narrative continuity

        Args:
            num_levels: Number of pyramid levels (3-6)
            topic: Pyramid topic/theme
            presentation_id: Optional presentation identifier (for logging)
            slide_id: Optional slide identifier (for logging)
            slide_number: Optional slide position (for context)
            context: Additional context dict with keys:
                - presentation_title: Overall presentation title
                - previous_slides: List of previous slide summaries (for LLM context)
                - slide_purpose: Purpose of this specific slide
                - industry: Industry context (optional)
                - audience_level: Target audience expertise level (optional)
            target_points: Optional list of point labels (e.g., ["Vision", "Strategy", "Tactics"])
            tone: Content tone (professional, casual, technical, etc.)
            audience: Target audience type
            validate_constraints: Enable character constraint validation

        Returns:
            Dict containing:
                - html: Complete HTML visualization (ready for L25 rich_content)
                - generated_content: Structured pyramid data (levels, labels, descriptions)
                - metadata: Generation metadata (model, time, version)
                - validation: Constraint validation results

        Raises:
            httpx.HTTPError: If API call fails
            ValueError: If response is invalid
        """
        if not self.enabled:
            raise RuntimeError("Illustrator service is disabled in settings")

        # Build request payload
        payload = {
            "num_levels": num_levels,
            "topic": topic,
            "tone": tone,
            "audience": audience,
            "validate_constraints": validate_constraints
        }

        # Add optional session tracking fields (v1.2 alignment)
        if presentation_id:
            payload["presentation_id"] = presentation_id
        if slide_id:
            payload["slide_id"] = slide_id
        if slide_number is not None:
            payload["slide_number"] = slide_number

        # Add context (including previous_slides for narrative continuity)
        if context:
            payload["context"] = context

        # Add target points if provided
        if target_points:
            payload["target_points"] = target_points

        logger.info(
            f"Generating {num_levels}-level pyramid: '{topic}'",
            extra={
                "num_levels": num_levels,
                "topic": topic,
                "presentation_id": presentation_id,
                "slide_id": slide_id,
                "has_previous_context": bool(context and context.get("previous_slides"))
            }
        )

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/v1.0/pyramid/generate",
                    json=payload
                )

                if response.status_code == 200:
                    result = response.json()

                    # Log generation results
                    validation = result.get("validation", {})
                    logger.info(
                        "Pyramid generated successfully",
                        extra={
                            "topic": topic,
                            "html_size": len(result.get("html", "")),
                            "generation_time_ms": result.get("metadata", {}).get("generation_time_ms"),
                            "validation_valid": validation.get("valid"),
                            "violations_count": len(validation.get("violations", []))
                        }
                    )

                    # Log constraint violations if any (expected behavior)
                    if not validation.get("valid"):
                        violations = validation.get("violations", [])
                        logger.warning(
                            f"Pyramid has {len(violations)} character constraint violations (expected)",
                            extra={
                                "topic": topic,
                                "violations": violations
                            }
                        )

                    return result

                elif response.status_code == 422:
                    # Validation error
                    error_detail = response.json().get("detail", "Validation error")
                    logger.error(
                        f"Pyramid validation error: {error_detail}",
                        extra={"topic": topic, "status_code": 422}
                    )
                    raise ValueError(f"Pyramid validation error: {error_detail}")

                else:
                    # Other API error
                    logger.error(
                        f"Illustrator API error: {response.status_code}",
                        extra={
                            "status_code": response.status_code,
                            "response": response.text[:500]
                        }
                    )
                    raise httpx.HTTPError(
                        f"Illustrator API error: {response.status_code} - {response.text[:200]}"
                    )

        except httpx.TimeoutException as e:
            logger.error(
                f"Illustrator service timeout after {self.timeout}s",
                extra={"topic": topic, "timeout": self.timeout}
            )
            raise

        except httpx.HTTPError as e:
            logger.error(
                f"HTTP error calling Illustrator service: {str(e)}",
                extra={"topic": topic}
            )
            raise

        except Exception as e:
            logger.error(
                f"Unexpected error generating pyramid: {str(e)}",
                extra={"topic": topic, "error_type": type(e).__name__}
            )
            raise

    # Future visualization methods will be added here:
    # async def generate_funnel(...) -> Dict[str, Any]: ...
    # async def generate_swot(...) -> Dict[str, Any]: ...
    # async def generate_bcg_matrix(...) -> Dict[str, Any]: ...
