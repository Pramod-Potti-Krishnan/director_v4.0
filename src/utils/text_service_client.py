"""
Text & Table Builder Service Client - v3.4
===========================================

Integration with Text & Table Builder v1.2 Railway service.

Service Details:
- Production URL: https://web-production-5daf.up.railway.app (v1.2)
- Synchronous API (5-15s response time)
- v1.2: Element-based content generation + hero slide endpoints
- LLM-powered with Gemini via Vertex AI with ADC
"""

import asyncio
from typing import Dict, Any
import requests
import httpx
from src.utils.logger import setup_logger
from src.models.content import GeneratedText  # Use Pydantic model

logger = setup_logger(__name__)


class TextServiceClient:
    """
    Text & Table Builder service client for v3.1.

    DEPRECATED: Use TextServiceClientV1_2 for new code.
    This client is kept for backward compatibility only.
    """

    def __init__(self, base_url: str = None):
        """
        Initialize text service client.

        Args:
            base_url: Override URL (default: production Railway URL)
        """
        self.base_url = base_url or "https://web-production-5daf.up.railway.app"
        self.api_base = f"{self.base_url}/api/v1"
        self.timeout = 60  # 60 seconds timeout

        logger.info(f"TextServiceClient initialized (url: {self.base_url}, timeout: {self.timeout}s)")

    async def generate(self, request: Dict[str, Any]) -> GeneratedText:
        """
        Generate text/table content from production service.

        Args:
            request: Request with topics, narrative, context, constraints
                Expected keys:
                - topics: List[str] - Topics to expand
                - narrative: str - Context/narrative
                - context: Dict - Presentation and slide context
                - constraints: Dict - Word count, tone, format constraints
                - slide_id: str - Slide identifier
                - slide_number: int - Slide position
                - presentation_id: str - Presentation identifier (for session tracking)

        Returns:
            GeneratedText with content and metadata

        Raises:
            Exception: On API errors or timeouts
        """
        # Transform request to service format
        service_request = self._transform_request(request)

        # Run synchronous HTTP request in executor (non-blocking)
        loop = asyncio.get_event_loop()
        try:
            response = await loop.run_in_executor(
                None,
                self._sync_generate_text,
                service_request
            )
        except Exception as e:
            logger.error(f"Text Service call failed: {str(e)}")
            raise

        # Transform response to our format
        return self._transform_response(response)

    def _sync_generate_text(self, request: Dict) -> Dict:
        """
        Synchronous HTTP request to Text service.

        Args:
            request: Service-formatted request

        Returns:
            Service response dict

        Raises:
            requests.HTTPError: On API errors
            requests.Timeout: On timeout
        """
        endpoint = f"{self.api_base}/generate/text"

        try:
            logger.info(f"Calling Text Service: {endpoint}")
            response = requests.post(
                endpoint,
                json=request,
                timeout=self.timeout
            )
            response.raise_for_status()
            logger.info(f"Text Service responded: {response.status_code}")
            return response.json()

        except requests.Timeout as e:
            logger.error(f"Text service timeout after {self.timeout}s")
            raise Exception(f"Text Service timeout after {self.timeout}s")
        except requests.HTTPError as e:
            logger.error(f"Text service HTTP error: {e.response.status_code} - {e.response.text}")
            raise Exception(f"Text Service HTTP error: {e.response.status_code}")
        except Exception as e:
            logger.error(f"Text service request failed: {str(e)}")
            raise

    def _transform_request(self, orchestrator_request: Dict) -> Dict:
        """
        Transform orchestrator request to Text service format.

        Text Service API expects:
        {
            "presentation_id": str,
            "slide_id": str,
            "slide_number": int,
            "topics": List[str],
            "narrative": str,
            "context": {
                "presentation_context": str,
                "slide_context": str,
                "previous_slides": List[Dict]
            },
            "constraints": {
                "word_count": int,
                "tone": str,
                "format": str
            }
        }
        """
        return {
            "presentation_id": orchestrator_request.get("presentation_id", "default_pres"),
            "slide_id": orchestrator_request.get("slide_id", "unknown"),
            "slide_number": orchestrator_request.get("slide_number", 1),
            "topics": orchestrator_request.get("topics", []),
            "narrative": orchestrator_request.get("narrative", ""),
            "context": {
                "presentation_context": orchestrator_request.get("context", {}).get("presentation_context", ""),
                "slide_context": orchestrator_request.get("context", {}).get("slide_context", ""),
                "previous_slides": orchestrator_request.get("context", {}).get("previous_slides", [])
            },
            "constraints": {
                "word_count": orchestrator_request.get("constraints", {}).get("word_count", 150),
                "tone": orchestrator_request.get("constraints", {}).get("tone", "professional"),
                "format": orchestrator_request.get("constraints", {}).get("format", "paragraph")
            }
        }

    def _transform_response(self, service_response: Dict) -> GeneratedText:
        """
        Transform Text service response to our format.

        Service response format:
        {
            "content": str (HTML),
            "metadata": {
                "word_count": int,
                "generation_time_ms": int,
                "model_used": str
            },
            "session_id": str
        }

        Returns:
            GeneratedText object
        """
        return GeneratedText(
            content=service_response["content"],
            metadata={
                "word_count": service_response["metadata"]["word_count"],
                "generation_time_ms": service_response["metadata"]["generation_time_ms"],
                "model_used": service_response["metadata"]["model_used"],
                "session_id": service_response.get("session_id"),
                "source": "text_service_v1.0"
            }
        )

    async def call_hero_endpoint(
        self,
        endpoint: str,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Call Text Service v1.2 hero slide endpoint.

        NEW in v3.4: Supports hero slide generation via specialized endpoints.

        Args:
            endpoint: Hero endpoint path (e.g., "/v1.2/hero/title")
            payload: Hero request payload:
                - slide_number: int
                - slide_type: str ("title_slide", "section_divider", "closing_slide")
                - narrative: str
                - topics: List[str]
                - context: Dict (theme, audience, etc.)

        Returns:
            Hero response dictionary:
                - content: str (complete HTML structure)
                - metadata: Dict (validation results, character counts, etc.)

        Raises:
            Exception: On API errors or timeouts

        Example:
            response = await client.call_hero_endpoint(
                endpoint="/v1.2/hero/title",
                payload={
                    "slide_number": 1,
                    "slide_type": "title_slide",
                    "narrative": "AI in Healthcare",
                    "topics": ["Diagnostic AI", "Patient Outcomes"],
                    "context": {"theme": "professional", "audience": "healthcare executives"}
                }
            )
            # Returns: {"content": "<div class='title-slide'>...</div>", "metadata": {...}}
        """
        url = f"{self.base_url}{endpoint}"

        logger.info(f"Calling hero endpoint: {url}")
        logger.debug(f"Hero payload: {payload}")

        try:
            # Use httpx for async HTTP requests
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()

                result = response.json()
                logger.info(f"Hero endpoint responded: {response.status_code}")
                logger.debug(f"Hero response: {result}")

                return result

        except httpx.TimeoutException as e:
            logger.error(f"Hero endpoint timeout after {self.timeout}s: {url}")
            raise Exception(f"Hero endpoint timeout: {endpoint}")

        except httpx.HTTPStatusError as e:
            logger.error(f"Hero endpoint HTTP error: {e.response.status_code} - {e.response.text}")
            raise Exception(f"Hero endpoint error: {e.response.status_code}")

        except Exception as e:
            logger.error(f"Hero endpoint call failed: {str(e)}")
            raise Exception(f"Hero endpoint failure: {str(e)}")
