"""
Deck-Builder API Client.

HTTP client for creating presentations via deck-builder API.

v4.0.5: Copied from v3.4 to enable preview generation during strawman phase.
"""
import httpx
from typing import Dict, Any, Optional
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class DeckBuilderClient:
    """HTTP client for deck-builder API."""

    def __init__(self, api_url: str, timeout: int = 30):
        """
        Initialize deck-builder API client.

        Args:
            api_url: Base URL of deck-builder API (e.g., "http://localhost:8000")
            timeout: Request timeout in seconds
        """
        self.api_url = api_url.rstrip('/')  # Remove trailing slash
        self.timeout = timeout
        logger.info(f"DeckBuilderClient initialized with URL: {self.api_url}")

    async def create_presentation(self, presentation_data: Dict[str, Any],
                                 max_retries: int = 3) -> Dict[str, Any]:
        """
        Create a new presentation via deck-builder API.

        Args:
            presentation_data: {
                "title": str,
                "slides": [{"layout": str, "content": dict}]
            }
            max_retries: Maximum number of retry attempts

        Returns:
            {
                "success": bool,
                "id": str,
                "url": str,
                "message": str
            }

        Raises:
            httpx.HTTPError: If API call fails after retries
        """
        endpoint = f"{self.api_url}/api/presentations"

        # Validate presentation data
        self._validate_presentation_data(presentation_data)

        logger.info(f"Creating presentation: '{presentation_data['title']}' "
                   f"with {len(presentation_data['slides'])} slides")

        # Retry logic
        last_exception = None
        for attempt in range(1, max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        endpoint,
                        json=presentation_data
                    )
                    response.raise_for_status()

                    result = response.json()
                    logger.info(f"Presentation created successfully: {result.get('id')}")
                    logger.debug(f"API Response: {result}")

                    return result

            except httpx.TimeoutException as e:
                last_exception = e
                logger.warning(f"Attempt {attempt}/{max_retries}: Request timeout")
                if attempt < max_retries:
                    logger.info(f"Retrying in 2 seconds...")
                    import asyncio
                    await asyncio.sleep(2)

            except httpx.HTTPStatusError as e:
                last_exception = e
                logger.error(f"HTTP error: {e.response.status_code} - {e.response.text}")
                # Don't retry on 4xx errors (client errors)
                if 400 <= e.response.status_code < 500:
                    raise
                if attempt < max_retries:
                    logger.info(f"Retrying in 2 seconds...")
                    import asyncio
                    await asyncio.sleep(2)

            except httpx.RequestError as e:
                last_exception = e
                logger.error(f"Connection error: {str(e)}")
                if attempt < max_retries:
                    logger.info(f"Retrying in 2 seconds...")
                    import asyncio
                    await asyncio.sleep(2)

        # All retries exhausted
        logger.error(f"Failed to create presentation after {max_retries} attempts")
        raise last_exception

    async def create_blank_presentation(
        self,
        timeout_ms: int = 500,
        max_retries: int = 2
    ) -> Dict[str, Any]:
        """
        Create a blank presentation for immediate WebSocket connection.

        v4.10: Implements OPERATING_MODEL_BUILDER_V2 Section 3.1.1 - Immediate Blank Presentation.
        Creates a single title slide (H1-structured) as a blank canvas for user editing.
        Optimized for <500ms latency target.

        Args:
            timeout_ms: Timeout in milliseconds (default 500ms per spec)
            max_retries: Maximum retry attempts (default 2, per spec)

        Returns:
            {
                "success": bool,
                "id": str (presentation ID),
                "url": str (preview URL),
                "is_blank": True
            }

        Error handling per spec:
        - Retry once on failure
        - Return success=False on all failures (fallback to greeting-only)
        """
        import asyncio

        endpoint = f"{self.api_url}/api/presentations"
        timeout_seconds = timeout_ms / 1000.0

        # Minimal blank presentation: single H1-structured title slide
        blank_presentation = {
            "title": "Untitled Presentation",
            "slides": [
                {
                    "layout": "H1-structured",
                    "content": {
                        "slide_title": "",
                        "slide_subtitle": "",
                        "hero_content": ""
                    },
                    "metadata": {
                        "is_blank": True,
                        "variant_id": "H1-structured",
                        "service": "text"
                    }
                }
            ]
        }

        logger.info(f"Creating blank presentation (timeout: {timeout_ms}ms, max_retries: {max_retries})")

        last_exception = None
        for attempt in range(1, max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                    response = await client.post(
                        endpoint,
                        json=blank_presentation
                    )
                    response.raise_for_status()

                    result = response.json()
                    presentation_id = result.get("id", "")
                    url = result.get("url", "")

                    logger.info(f"Blank presentation created successfully: {presentation_id}")

                    return {
                        "success": True,
                        "id": presentation_id,
                        "url": self.get_full_url(url) if url else "",
                        "is_blank": True
                    }

            except httpx.TimeoutException as e:
                last_exception = e
                logger.warning(f"Blank presentation attempt {attempt}/{max_retries}: timeout after {timeout_ms}ms")
                if attempt < max_retries:
                    await asyncio.sleep(0.1)  # Brief delay before retry

            except httpx.HTTPStatusError as e:
                last_exception = e
                logger.error(f"Blank presentation HTTP error: {e.response.status_code}")
                # Don't retry on 4xx errors
                if 400 <= e.response.status_code < 500:
                    break
                if attempt < max_retries:
                    await asyncio.sleep(0.1)

            except httpx.RequestError as e:
                last_exception = e
                logger.error(f"Blank presentation connection error: {str(e)}")
                if attempt < max_retries:
                    await asyncio.sleep(0.1)

        # All retries exhausted - return failure (spec: fallback to greeting-only)
        logger.warning(f"Blank presentation creation failed after {max_retries} attempts, "
                      f"fallback to greeting-only flow")
        return {
            "success": False,
            "id": "",
            "url": "",
            "is_blank": True,
            "error": str(last_exception) if last_exception else "Unknown error"
        }

    async def get_presentation(self, presentation_id: str) -> Optional[Dict[str, Any]]:
        """
        Get presentation data by ID.

        Args:
            presentation_id: Presentation UUID

        Returns:
            Presentation data or None if not found
        """
        endpoint = f"{self.api_url}/api/presentations/{presentation_id}"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(endpoint)
                response.raise_for_status()
                return response.json()

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"Presentation not found: {presentation_id}")
                return None
            raise

        except httpx.RequestError as e:
            logger.error(f"Error fetching presentation: {str(e)}")
            raise

    def get_full_url(self, url_path: str) -> str:
        """
        Convert relative URL path to full URL.

        Args:
            url_path: Path like "/p/uuid"

        Returns:
            Full URL like "http://localhost:8000/p/uuid"
        """
        if url_path.startswith('http'):
            return url_path

        return f"{self.api_url}{url_path}"

    def _validate_presentation_data(self, data: Dict[str, Any]) -> None:
        """
        Validate presentation data before sending to API.

        Raises:
            ValueError: If data is invalid
        """
        if 'title' not in data:
            raise ValueError("Presentation data missing 'title' field")

        if 'slides' not in data:
            raise ValueError("Presentation data missing 'slides' field")

        if not isinstance(data['slides'], list):
            raise ValueError("'slides' must be a list")

        if len(data['slides']) == 0:
            raise ValueError("Presentation must have at least one slide")

        # Validate each slide
        for idx, slide in enumerate(data['slides']):
            if 'layout' not in slide:
                raise ValueError(f"Slide {idx} missing 'layout' field")

            if 'content' not in slide:
                raise ValueError(f"Slide {idx} missing 'content' field")

            if not isinstance(slide['content'], dict):
                raise ValueError(f"Slide {idx} 'content' must be a dictionary")

        logger.debug(f"Presentation data validated: {len(data['slides'])} slides")

    async def get_presentation_state(self, presentation_id: str) -> Optional[Dict[str, Any]]:
        """
        Get presentation state for diff comparison (Stage 5).

        Returns a normalized format suitable for StrawmanDiffer:
        {
            "id": str,
            "title": str,
            "slides": [
                {
                    "slide_id": str,
                    "slide_number": int,
                    "layout": str,
                    "title": str,
                    "topics": List[str],
                    "notes": str,
                    "content": dict,
                    "metadata": dict
                }
            ],
            "updated_at": str,
            "slide_count": int
        }

        Args:
            presentation_id: Presentation UUID

        Returns:
            Normalized presentation state or None if not found
        """
        raw = await self.get_presentation(presentation_id)
        if not raw:
            return None

        # Normalize the response for diff comparison
        slides = []
        for idx, slide in enumerate(raw.get("slides", [])):
            # Extract content fields
            content = slide.get("content", {})

            normalized_slide = {
                "slide_id": slide.get("slide_id", f"slide_{idx + 1}"),
                "slide_number": idx + 1,
                "layout": slide.get("layout", "L25"),
                # Extract title from content or slide-level
                "title": content.get("slide_title") or slide.get("title", ""),
                # Extract topics from content or metadata
                "topics": (
                    slide.get("metadata", {}).get("topics", []) or
                    content.get("topics", [])
                ),
                # Extract notes
                "notes": content.get("notes", "") or slide.get("notes", ""),
                # Keep original content for reference
                "content": content,
                # Keep metadata
                "metadata": slide.get("metadata", {}),
                # Additional fields that might be relevant
                "is_hero": slide.get("metadata", {}).get("is_hero", False),
                "variant_id": slide.get("metadata", {}).get("variant_id"),
            }
            slides.append(normalized_slide)

        return {
            "id": raw.get("id", presentation_id),
            "title": raw.get("title", ""),
            "slides": slides,
            "updated_at": raw.get("updated_at", ""),
            "slide_count": len(slides)
        }

    async def update_slide(
        self,
        presentation_id: str,
        slide_index: int,
        slide_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update a single slide in a presentation.

        Args:
            presentation_id: Presentation UUID
            slide_index: 0-indexed position of the slide
            slide_data: Updated slide data

        Returns:
            Updated presentation data
        """
        endpoint = f"{self.api_url}/api/presentations/{presentation_id}/slides/{slide_index}"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.put(endpoint, json=slide_data)
                response.raise_for_status()
                result = response.json()
                logger.info(f"Slide {slide_index} updated in presentation {presentation_id}")
                return result

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error updating slide: {e.response.status_code}")
            raise DeckBuilderError(f"Failed to update slide: {e.response.text}")

        except httpx.RequestError as e:
            logger.error(f"Connection error updating slide: {str(e)}")
            raise DeckBuilderError(f"Connection error: {str(e)}")

    async def health_check(self) -> bool:
        """
        Check if deck-builder API is available.

        Returns:
            True if API is healthy, False otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{self.api_url}/health")
                return response.status_code == 200
        except Exception as e:
            logger.warning(f"Deck-builder API health check failed: {str(e)}")
            return False


class DeckBuilderError(Exception):
    """Custom exception for deck-builder API errors."""
    pass
