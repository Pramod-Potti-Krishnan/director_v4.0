"""
Deck-Builder API Client.

HTTP client for creating presentations via deck-builder API.
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
