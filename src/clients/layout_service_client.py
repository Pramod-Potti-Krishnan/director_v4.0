"""
Layout Service Client for Director Agent v4.0

Handles communication with Layout Service v7.5+ for intelligent layout/variant
selection during strawman generation. Enables the "Coordinated Strawman" workflow
where layouts are selected based on content requirements rather than hardcoded.

Integration:
- Works with Layout Service v7.5.5+ coordination endpoints
- Provides layout recommendations based on slide type and topic count
- Returns content zone dimensions for optimized text generation
- Falls back gracefully if service is unavailable

Author: Director v4.0 Layout Service Coordination
Date: December 2024
"""

import httpx
from typing import Dict, Any, Optional, List
from src.utils.logger import setup_logger
from src.models.layout import (
    LayoutTemplate,
    LayoutRecommendation,
    CanFitResponse,
    LayoutCapabilities,
    LayoutSlot
)
from config.settings import get_settings

logger = setup_logger(__name__)


class LayoutServiceClient:
    """
    Client for calling Layout Service coordination endpoints.

    The Layout Service provides intelligent layout/variant selection based on
    content requirements. This replaces the hardcoded L25/L29 approach with
    dynamic layout selection considering:
    - Slide type (hero, content, visual)
    - Topic count and content complexity
    - Available space and slot dimensions
    - Supported variants for each layout

    Endpoints Used:
    - GET /capabilities: Service capabilities and layout inventory
    - GET /api/layouts: All available layouts
    - GET /api/layouts/{id}: Specific layout with slot dimensions
    - POST /api/recommend-layout: Layout recommendations
    - POST /api/can-fit: Content fit validation

    Usage:
        client = LayoutServiceClient()

        # Check service availability
        if await client.health_check():
            # Get layout recommendations
            recommendations = await client.recommend_layout(
                slide_type="content",
                topic_count=3,
                content_hints={"has_data": True}
            )

            # Get layout details with slot dimensions
            layout = await client.get_layout("L25")
            print(f"Content zone: {layout.content_zone_width}x{layout.content_zone_height}")
    """

    def __init__(self, base_url: Optional[str] = None, timeout: Optional[int] = None):
        """
        Initialize Layout Service client.

        Args:
            base_url: Override default Layout Service URL
            timeout: Override default request timeout (default: 10s)
        """
        settings = get_settings()
        self.base_url = base_url or getattr(settings, 'LAYOUT_SERVICE_URL', 'http://localhost:8504')
        self.timeout = timeout or getattr(settings, 'LAYOUT_SERVICE_TIMEOUT', 10)
        self.enabled = getattr(settings, 'USE_LAYOUT_SERVICE_COORDINATION', False)

        logger.info(
            "LayoutServiceClient initialized",
            extra={
                "base_url": self.base_url,
                "timeout": self.timeout,
                "enabled": self.enabled
            }
        )

    async def health_check(self) -> bool:
        """
        Check if Layout Service is healthy and reachable.

        Uses the /capabilities endpoint as a health indicator since it's
        lightweight and always available when the service is running.

        Returns:
            True if service is healthy, False otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                response = await client.get(f"{self.base_url}/capabilities")

                if response.status_code == 200:
                    logger.debug("Layout Service health check: OK")
                    return True
                else:
                    logger.warning(
                        f"Layout Service health check failed: {response.status_code}",
                        extra={"status_code": response.status_code}
                    )
                    return False
        except Exception as e:
            logger.warning(
                f"Cannot reach Layout Service: {str(e)}",
                extra={"error": str(e), "url": self.base_url}
            )
            return False

    async def get_capabilities(self) -> LayoutCapabilities:
        """
        Fetch service capabilities and layout inventory.

        GET /capabilities

        Returns:
            LayoutCapabilities with service info and available layouts
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/capabilities")
                response.raise_for_status()

                data = response.json()
                logger.info(
                    "Layout Service capabilities fetched",
                    extra={
                        "version": data.get("version"),
                        "total_layouts": data.get("total_layouts")
                    }
                )

                return LayoutCapabilities(**data)

        except httpx.HTTPError as e:
            logger.error(
                f"Failed to fetch Layout Service capabilities: {str(e)}",
                extra={"url": f"{self.base_url}/capabilities"}
            )
            raise

    async def get_all_layouts(self) -> List[LayoutTemplate]:
        """
        Fetch all available layout templates.

        GET /api/layouts

        Returns:
            List of LayoutTemplate objects
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/api/layouts")
                response.raise_for_status()

                layouts_data = response.json()
                layouts = [self._parse_layout(layout) for layout in layouts_data]

                logger.info(
                    f"Fetched {len(layouts)} layouts from Layout Service",
                    extra={"count": len(layouts)}
                )

                return layouts

        except httpx.HTTPError as e:
            logger.error(
                f"Failed to fetch layouts: {str(e)}",
                extra={"url": f"{self.base_url}/api/layouts"}
            )
            raise

    async def get_layout(self, layout_id: str) -> LayoutTemplate:
        """
        Get a specific layout template with slot dimensions.

        GET /api/layouts/{id}

        This is the key endpoint for content zone integration - it returns
        exact pixel dimensions for each slot, enabling optimized text generation.

        Args:
            layout_id: Layout identifier (e.g., "L25", "L29", "C01")

        Returns:
            LayoutTemplate with slots containing x, y, width, height in pixels
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/api/layouts/{layout_id}")
                response.raise_for_status()

                layout_data = response.json()
                layout = self._parse_layout(layout_data)

                logger.debug(
                    f"Fetched layout {layout_id}",
                    extra={
                        "layout_id": layout_id,
                        "content_zone": f"{layout.content_zone_width}x{layout.content_zone_height}",
                        "slot_count": len(layout.slots)
                    }
                )

                return layout

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"Layout not found: {layout_id}")
                raise ValueError(f"Layout '{layout_id}' not found in Layout Service")
            raise

        except httpx.HTTPError as e:
            logger.error(
                f"Failed to fetch layout {layout_id}: {str(e)}",
                extra={"layout_id": layout_id}
            )
            raise

    async def recommend_layout(
        self,
        slide_type: str,
        topic_count: int,
        content_hints: Optional[Dict[str, Any]] = None
    ) -> List[LayoutRecommendation]:
        """
        Get layout recommendations based on content requirements.

        POST /api/recommend-layout

        The Layout Service analyzes the slide type, topic count, and content hints
        to recommend the most suitable layouts. Returns a ranked list of recommendations.

        Args:
            slide_type: Type of slide - "hero", "content", "visual", "data"
            topic_count: Number of topics/points on the slide (1-6)
            content_hints: Optional hints about content:
                - has_data: bool - Slide contains data/charts
                - has_image: bool - Slide contains images
                - style: str - Requested style
                - complexity: str - "simple", "medium", "complex"

        Returns:
            List of LayoutRecommendation sorted by score (highest first)
        """
        payload = {
            "slide_type": slide_type,
            "topic_count": topic_count,
            "content_hints": content_hints or {}
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/recommend-layout",
                    json=payload
                )
                response.raise_for_status()

                recommendations_data = response.json()

                # Handle both list and dict responses
                if isinstance(recommendations_data, dict):
                    recommendations_data = recommendations_data.get("recommendations", [])

                recommendations = [
                    LayoutRecommendation(**rec) for rec in recommendations_data
                ]

                logger.info(
                    f"Got {len(recommendations)} layout recommendations",
                    extra={
                        "slide_type": slide_type,
                        "topic_count": topic_count,
                        "top_recommendation": recommendations[0].layout_id if recommendations else None
                    }
                )

                return recommendations

        except httpx.HTTPError as e:
            logger.error(
                f"Failed to get layout recommendations: {str(e)}",
                extra={
                    "slide_type": slide_type,
                    "topic_count": topic_count
                }
            )
            raise

    async def can_fit(
        self,
        layout_id: str,
        content_requirements: Dict[str, Any]
    ) -> CanFitResponse:
        """
        Check if content fits within a layout's constraints.

        POST /api/can-fit

        Validates whether the specified content (text length, number of items,
        image requirements) can fit within the layout's slots.

        Args:
            layout_id: Layout to check (e.g., "L25")
            content_requirements: Content specs to validate:
                - text_length: int - Approximate character count
                - bullet_count: int - Number of bullet points
                - has_image: bool - Requires image slot
                - has_chart: bool - Requires chart slot

        Returns:
            CanFitResponse with fits=True/False and details
        """
        payload = {
            "layout_id": layout_id,
            "content_requirements": content_requirements
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/can-fit",
                    json=payload
                )
                response.raise_for_status()

                result = CanFitResponse(**response.json())

                logger.debug(
                    f"Can-fit check for {layout_id}: {result.fits}",
                    extra={
                        "layout_id": layout_id,
                        "fits": result.fits,
                        "details": result.details
                    }
                )

                return result

        except httpx.HTTPError as e:
            logger.error(
                f"Failed to check content fit: {str(e)}",
                extra={"layout_id": layout_id}
            )
            raise

    def _parse_layout(self, data: Dict[str, Any]) -> LayoutTemplate:
        """
        Parse layout data from API response to LayoutTemplate model.

        Handles variations in API response format and provides defaults
        for missing fields.
        """
        # Parse slots if present
        slots = []
        if "slots" in data:
            for slot_data in data["slots"]:
                slots.append(LayoutSlot(
                    id=slot_data.get("id", ""),
                    type=slot_data.get("type", "text"),
                    x=slot_data.get("x", 0),
                    y=slot_data.get("y", 0),
                    width=slot_data.get("width", 0),
                    height=slot_data.get("height", 0),
                    constraints=slot_data.get("constraints")
                ))

        # Extract content zone dimensions
        content_zone = data.get("content_zone", {})
        content_zone_width = content_zone.get("width", data.get("content_zone_width", 1800))
        content_zone_height = content_zone.get("height", data.get("content_zone_height", 720))

        return LayoutTemplate(
            id=data.get("id", data.get("layout_id", "")),
            name=data.get("name", data.get("layout_name", "")),
            series=data.get("series", self._infer_series(data.get("id", ""))),
            category=data.get("category", "content"),
            slots=slots,
            content_zone_width=content_zone_width,
            content_zone_height=content_zone_height,
            supported_variants=data.get("supported_variants", []),
            recommended_for=data.get("recommended_for", [])
        )

    def _infer_series(self, layout_id: str) -> str:
        """
        Infer layout series from ID if not provided.

        Series mapping:
        - H: Hero layouts (H01-H10)
        - C: Content layouts (C01-C10)
        - V: Visual layouts (V01-V10)
        - I: Infographic layouts
        - S: Split layouts
        - B: Blank layouts
        - L: Legacy layouts (L01, L25, L29, etc.)
        """
        if not layout_id:
            return "L"

        first_char = layout_id[0].upper()
        if first_char in ["H", "C", "V", "I", "S", "B", "L"]:
            return first_char

        return "L"  # Default to Legacy series
