"""
Service Interface for Director v3.4
====================================

Abstracts Text Service v1.1 API calls with error handling and retries.
Provides methods for individual specialized endpoints and batch processing.
"""

import httpx
import asyncio
from typing import Dict, Any, List, Optional
from src.utils.logger import setup_logger
from src.utils.service_registry import ServiceRegistry

logger = setup_logger(__name__)


class TextServiceInterface:
    """
    Interface for calling Text Service v1.1 specialized endpoints.

    Features:
    - Individual specialized endpoint calls
    - Batch endpoint for parallel processing
    - Automatic retries on failures
    - Comprehensive error handling
    - Request/response validation
    """

    def __init__(self, base_url: str, timeout: int = 300, max_retries: int = 3):
        """
        Initialize Text Service interface.

        Args:
            base_url: Text Service base URL (e.g., "https://text-service.railway.app")
            timeout: Request timeout in seconds (default: 300 for long generations)
            max_retries: Maximum retry attempts (default: 3)
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.client = httpx.AsyncClient(timeout=timeout)
        logger.info(f"TextServiceInterface initialized: {base_url}")

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    async def generate_specialized(
        self,
        slide_type_classification: str,
        request_payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Call specialized Text Service endpoint based on slide type.

        Args:
            slide_type_classification: Slide type from 13-type taxonomy
            request_payload: TextGenerationRequest payload

        Returns:
            GeneratedText response dict

        Raises:
            ValueError: If slide_type_classification is invalid
            Exception: If API call fails after retries
        """
        # Get endpoint for slide type
        endpoint = ServiceRegistry.get_endpoint(slide_type_classification)
        if not endpoint:
            raise ValueError(
                f"Invalid slide_type_classification: '{slide_type_classification}'. "
                f"Valid types: {ServiceRegistry.get_supported_types()}"
            )

        # Build full URL
        url = f"{self.base_url}{endpoint}"

        # Add slide_type to context (required by Text Service)
        if "context" not in request_payload:
            request_payload["context"] = {}
        request_payload["context"]["slide_type"] = slide_type_classification

        logger.info(f"Calling {slide_type_classification} endpoint: {url}")

        # Attempt request with retries
        last_error = None
        for attempt in range(1, self.max_retries + 1):
            try:
                response = await self.client.post(url, json=request_payload)
                response.raise_for_status()

                result = response.json()
                logger.info(f"✅ Generated content for {slide_type_classification} (attempt {attempt})")
                return result

            except httpx.HTTPStatusError as e:
                last_error = e
                logger.error(
                    f"HTTP {e.response.status_code} error for {slide_type_classification} "
                    f"(attempt {attempt}/{self.max_retries}): {e.response.text}"
                )
                if attempt < self.max_retries:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff

            except httpx.RequestError as e:
                last_error = e
                logger.error(
                    f"Request error for {slide_type_classification} "
                    f"(attempt {attempt}/{self.max_retries}): {str(e)}"
                )
                if attempt < self.max_retries:
                    await asyncio.sleep(2 ** attempt)

            except Exception as e:
                last_error = e
                logger.error(
                    f"Unexpected error for {slide_type_classification} "
                    f"(attempt {attempt}/{self.max_retries}): {str(e)}"
                )
                if attempt < self.max_retries:
                    await asyncio.sleep(2 ** attempt)

        # All retries failed
        error_msg = f"Failed to generate content for {slide_type_classification} after {self.max_retries} attempts"
        logger.error(f"{error_msg}: {last_error}")
        raise Exception(f"{error_msg}: {last_error}")

    async def generate_batch(
        self,
        requests: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Call Text Service batch endpoint for parallel generation.

        Args:
            requests: List of TextGenerationRequest payloads

        Returns:
            Batch result dict with:
            - results: List[GeneratedText] - successful generations
            - errors: List[Dict] - failed generations with error details
            - metadata: Dict - batch processing statistics

        Raises:
            Exception: If batch API call fails after retries
        """
        # Ensure each request has slide_type in context
        for i, req in enumerate(requests):
            if "context" not in req:
                req["context"] = {}

            # Validate slide_type_classification exists
            slide_type = req["context"].get("slide_type")
            if not slide_type:
                raise ValueError(f"Request {i} missing slide_type in context")

        # Build batch endpoint URL
        url = f"{self.base_url}{ServiceRegistry.get_batch_endpoint()}"

        logger.info(f"Calling batch endpoint with {len(requests)} slides: {url}")

        # Attempt request with retries
        last_error = None
        for attempt in range(1, self.max_retries + 1):
            try:
                response = await self.client.post(url, json={"requests": requests})
                response.raise_for_status()

                result = response.json()
                logger.info(
                    f"✅ Batch generation complete: {result.get('metadata', {}).get('successful', 0)} successful "
                    f"(attempt {attempt})"
                )
                return result

            except httpx.HTTPStatusError as e:
                last_error = e
                logger.error(
                    f"HTTP {e.response.status_code} error for batch "
                    f"(attempt {attempt}/{self.max_retries}): {e.response.text}"
                )
                if attempt < self.max_retries:
                    await asyncio.sleep(2 ** attempt)

            except httpx.RequestError as e:
                last_error = e
                logger.error(
                    f"Request error for batch "
                    f"(attempt {attempt}/{self.max_retries}): {str(e)}"
                )
                if attempt < self.max_retries:
                    await asyncio.sleep(2 ** attempt)

            except Exception as e:
                last_error = e
                logger.error(
                    f"Unexpected error for batch "
                    f"(attempt {attempt}/{self.max_retries}): {str(e)}"
                )
                if attempt < self.max_retries:
                    await asyncio.sleep(2 ** attempt)

        # All retries failed
        error_msg = f"Failed batch generation after {self.max_retries} attempts"
        logger.error(f"{error_msg}: {last_error}")
        raise Exception(f"{error_msg}: {last_error}")

    async def health_check(self) -> bool:
        """
        Check if Text Service is healthy and responsive.

        Returns:
            True if service is healthy, False otherwise
        """
        try:
            url = f"{self.base_url}/health"
            response = await self.client.get(url, timeout=10)
            response.raise_for_status()
            logger.info("✅ Text Service health check passed")
            return True
        except Exception as e:
            logger.error(f"❌ Text Service health check failed: {e}")
            return False

    def build_request_payload(
        self,
        slide_id: str,
        narrative: str,
        topics: List[str],
        context: Dict[str, Any],
        slide_number: int = 1
    ) -> Dict[str, Any]:
        """
        Build TextGenerationRequest payload for Text Service v1.1.

        Args:
            slide_id: Unique slide identifier
            narrative: Slide narrative/story
            topics: List of key topics/points
            context: Additional context (must include slide_type)
            slide_number: Slide position in presentation

        Returns:
            TextGenerationRequest dict
        """
        return {
            "slide_id": slide_id,
            "narrative": narrative,
            "topics": topics,
            "context": context,
            "slide_number": slide_number
        }


# Convenience function

async def create_text_service_client(base_url: str) -> TextServiceInterface:
    """
    Create and validate Text Service client.

    Args:
        base_url: Text Service base URL

    Returns:
        TextServiceInterface instance

    Raises:
        Exception: If service is not reachable
    """
    client = TextServiceInterface(base_url)

    # Perform health check
    is_healthy = await client.health_check()
    if not is_healthy:
        await client.close()
        raise Exception(f"Text Service at {base_url} is not healthy or reachable")

    return client


# Example usage
if __name__ == "__main__":
    import asyncio

    async def test_interface():
        print("Text Service Interface Test")
        print("=" * 70)

        # Initialize client
        client = TextServiceInterface("http://localhost:8001")

        # Test health check
        print("\nHealth Check:")
        healthy = await client.health_check()
        print(f"  Service healthy: {healthy}")

        # Build sample request
        print("\nBuilding sample request:")
        request = client.build_request_payload(
            slide_id="slide_001",
            narrative="This is a sample narrative about our product launch.",
            topics=["Product features", "Market opportunity", "Competitive advantages"],
            context={"slide_type": "title_slide"},
            slide_number=1
        )
        print(f"  Request payload: {request.keys()}")

        # Test specialized endpoint (would call actual API if running)
        print("\nWould call specialized endpoint:")
        print(f"  Slide type: title_slide")
        print(f"  Endpoint: {ServiceRegistry.get_endpoint('title_slide')}")

        await client.close()
        print("\n✅ Interface test complete")

    asyncio.run(test_interface())
