"""
Text Service v1.2 Client for Director v3.4
===========================================

Client for Text Service v1.2 with element-based generation and 34 platinum variants.

Service Details:
- Production URL: https://web-production-5daf.up.railway.app
- Version: 1.2.0
- Architecture: Deterministic Assembly with Element-Based Generation
- Variants: 34 platinum variants across 10 slide types
- Response time: 2-5 seconds (parallel mode), up to 15s (sequential)
- Character count validation: Baseline ± 5%
"""

import asyncio
import json
import httpx
from typing import Dict, Any, Optional
from src.utils.logger import setup_logger
from src.models.content import GeneratedText

logger = setup_logger(__name__)


class TextServiceClientV1_2:
    """
    Text Service v1.2 client with element-based generation.

    Features:
    - Single unified endpoint: POST /v1.2/generate
    - Accepts variant_id + SlideSpecification + PresentationSpecification
    - Returns complete HTML for rich_content
    - Character count validation
    - Parallel element generation for speed
    """

    def __init__(self, base_url: str = None, timeout: int = 300):
        """
        Initialize Text Service v1.2 client.

        Args:
            base_url: Text Service v1.2 base URL
                Default: https://web-production-5daf.up.railway.app
            timeout: Request timeout in seconds (default: 300 for safety)
        """
        self.base_url = base_url or "https://web-production-5daf.up.railway.app"
        self.timeout = timeout

        logger.info(
            f"TextServiceClientV1_2 initialized "
            f"(url: {self.base_url}, timeout: {self.timeout}s)"
        )

    async def generate(self, request: Dict[str, Any]) -> GeneratedText:
        """
        Generate slide content using v1.2 element-based API.

        Args:
            request: V1_2_GenerationRequest dict with:
                - variant_id: str (e.g., "matrix_2x3")
                - slide_spec: SlideSpecification dict
                - presentation_spec: PresentationSpecification dict
                - enable_parallel: bool (default: True)
                - validate_character_counts: bool (default: True)

        Returns:
            GeneratedText with:
                - content: Complete HTML string (or dict for structured content)
                - metadata: Generation metadata

        Raises:
            Exception: On API errors or timeouts
        """
        endpoint = f"{self.base_url}/v1.2/generate"

        # v4.0.14: Add timing
        import time
        start_time = time.time()

        try:
            # v4.0.9: Log request details for debugging
            logger.info(
                f"Calling v1.2 generate endpoint for variant '{request.get('variant_id')}'"
            )
            logger.debug(f"Request payload: {json.dumps(request, indent=2)}")

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(endpoint, json=request)

                # v4.0.14: Log HTTP response details before parsing
                elapsed_http = time.time() - start_time
                logger.info(
                    f"Text Service HTTP response received ({elapsed_http:.2f}s):\n"
                    f"  Status: {response.status_code}\n"
                    f"  Content-Length: {response.headers.get('content-length', 'N/A')}\n"
                    f"  Content-Type: {response.headers.get('content-type', 'N/A')}"
                )

                response.raise_for_status()

                # v4.0.14: Log raw body before parsing (for debugging)
                raw_body = response.text
                logger.debug(f"Raw response body ({len(raw_body)} chars): {raw_body[:500]}...")

                result = response.json()

                # v4.0.14: Log parsed result structure
                result_type = type(result).__name__
                result_keys = list(result.keys()) if isinstance(result, dict) else 'N/A'
                result_success = result.get('success') if isinstance(result, dict) else 'N/A'
                result_html_len = len(result.get('html', '')) if isinstance(result, dict) and result.get('html') else 0
                logger.info(
                    f"Text Service parsed response:\n"
                    f"  Type: {result_type}\n"
                    f"  Keys: {result_keys}\n"
                    f"  success: {result_success}\n"
                    f"  html length: {result_html_len}"
                )

                # v4.0.12: Defensive check for null/empty response
                if result is None:
                    logger.error(
                        f"Text Service returned null response for variant '{request.get('variant_id')}'\n"
                        f"HTTP Status: {response.status_code}\n"
                        f"Response headers: {dict(response.headers)}"
                    )
                    raise Exception("Text Service returned null response - check Text Service logs")

                if not isinstance(result, dict):
                    logger.error(
                        f"Text Service returned non-dict: {type(result).__name__} = {str(result)[:200]}"
                    )
                    raise Exception(f"Text Service returned invalid response type: {type(result).__name__}")

                if not result.get("success", False):
                    error_detail = result.get("error", result.get("detail", "Unknown error"))
                    logger.error(f"Text Service returned success=false: {error_detail}")
                    raise Exception(f"Text Service error: {error_detail}")

                # v4.0.14: Include timing in success log
                elapsed_total = time.time() - start_time
                logger.info(
                    f"✅ v1.2 generation successful "
                    f"(variant: {request.get('variant_id')}, "
                    f"time: {elapsed_total:.2f}s, "
                    f"html_size: {result_html_len} chars, "
                    f"mode: {result.get('metadata', {}).get('generation_mode', 'unknown')})"
                )

                # Handle character count validation warnings
                if result.get("validation", {}).get("valid") is False:
                    violations = result["validation"].get("violations", [])
                    logger.warning(
                        f"Character count violations detected: {len(violations)} violations"
                    )
                    for violation in violations:
                        logger.warning(
                            f"  - {violation.get('element_id')}.{violation.get('field')}: "
                            f"{violation.get('actual_count')} chars "
                            f"(expected {violation.get('required_min')}-{violation.get('required_max')})"
                        )

                # Transform to GeneratedText
                return self._transform_response(result)

        except httpx.HTTPStatusError as e:
            # v4.0.9: Enhanced error logging for 422 validation errors
            error_body = e.response.text
            try:
                error_json = e.response.json()
                error_body = json.dumps(error_json, indent=2)
            except Exception:
                pass  # Keep raw text if JSON parsing fails

            logger.error(
                f"HTTP {e.response.status_code} error calling v1.2:\n"
                f"  URL: {endpoint}\n"
                f"  Variant: {request.get('variant_id')}\n"
                f"  Response: {error_body}"
            )

            # Include error details in exception message
            error_msg = error_body[:500] if len(error_body) > 500 else error_body
            raise Exception(
                f"Text Service v1.2 HTTP error: {e.response.status_code} - {error_msg}"
            )

        except httpx.RequestError as e:
            logger.error(f"Request error calling v1.2: {str(e)}")
            raise Exception(f"Text Service v1.2 request error: {str(e)}")

        except Exception as e:
            logger.error(f"Unexpected error calling v1.2: {str(e)}")
            raise

    def _transform_response(self, v1_2_response: Dict[str, Any]) -> GeneratedText:
        """
        Transform v1.2 response to GeneratedText model.

        v1.2 Response Format:
        {
          "success": true,
          "html": "<div>...complete HTML...</div>",
          "elements": [...],
          "validation": {
            "valid": true,
            "violations": []
          },
          "metadata": {
            "variant_id": "matrix_2x3",
            "template_path": "...",
            "element_count": 4,
            "generation_mode": "parallel"
          }
        }

        Args:
            v1_2_response: Response dict from v1.2 API

        Returns:
            GeneratedText with content and metadata
        """
        # v4.0.14: Log transform input
        logger.debug(
            f"Transforming Text Service response:\n"
            f"  success: {v1_2_response.get('success')}\n"
            f"  html present: {bool(v1_2_response.get('html'))}\n"
            f"  html length: {len(v1_2_response.get('html', ''))}\n"
            f"  metadata: {v1_2_response.get('metadata', {})}"
        )

        # Extract HTML (primary content)
        html_content = v1_2_response.get("html", "")

        # Build metadata
        v1_2_metadata = v1_2_response.get("metadata", {})
        validation = v1_2_response.get("validation", {})

        metadata = {
            "variant_id": v1_2_metadata.get("variant_id"),
            "generation_mode": v1_2_metadata.get("generation_mode"),
            "element_count": v1_2_metadata.get("element_count"),
            "template_path": v1_2_metadata.get("template_path"),
            "character_validation_valid": validation.get("valid", True),
            "character_validation_violations": len(validation.get("violations", [])),
            "source": "text_service_v1.2"
        }

        # v4.0.14: Log extracted content
        logger.debug(
            f"Transform complete:\n"
            f"  HTML content length: {len(html_content)} chars\n"
            f"  Variant: {metadata.get('variant_id')}\n"
            f"  Mode: {metadata.get('generation_mode')}\n"
            f"  Validation valid: {metadata.get('character_validation_valid')}"
        )

        return GeneratedText(
            content=html_content,  # Complete HTML string
            metadata=metadata
        )

    async def health_check(self) -> bool:
        """
        Check if Text Service v1.2 is healthy.

        Returns:
            True if healthy, False otherwise
        """
        try:
            endpoint = f"{self.base_url}/health"

            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(endpoint)
                response.raise_for_status()

                health = response.json()

                logger.info(
                    f"✅ v1.2 health check passed "
                    f"(status: {health.get('status')}, version: {health.get('version')})"
                )

                return True

        except Exception as e:
            logger.error(f"❌ v1.2 health check failed: {e}")
            return False

    async def call_hero_endpoint(
        self,
        endpoint: str,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Call Text Service v1.2 hero slide endpoint.

        Args:
            endpoint: Hero endpoint path (e.g., "/v1.2/hero/title")
            payload: Hero request payload

        Returns:
            Hero response dictionary with content and metadata
        """
        url = f"{self.base_url}{endpoint}"

        try:
            logger.info(f"Calling hero endpoint: {endpoint}")

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                result = response.json()

                logger.info(f"✅ Hero endpoint {endpoint} returned successfully")
                return result

        except httpx.HTTPStatusError as e:
            logger.error(f"Hero endpoint HTTP error: {e.response.status_code}")
            raise Exception(f"Hero endpoint error: {e.response.status_code}")
        except Exception as e:
            logger.error(f"Hero endpoint call failed: {str(e)}")
            raise Exception(f"Hero endpoint failure: {str(e)}")

    async def get_variants(self) -> Dict[str, Any]:
        """
        Get all available variants from v1.2.

        Returns:
            Variants catalog dict
        """
        try:
            endpoint = f"{self.base_url}/v1.2/variants"

            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(endpoint)
                response.raise_for_status()

                variants = response.json()

                logger.info(
                    f"✅ Retrieved {variants.get('total_variants', 0)} variants from v1.2"
                )

                return variants

        except Exception as e:
            logger.error(f"Failed to get variants: {e}")
            raise

    async def get_variant_details(self, variant_id: str) -> Dict[str, Any]:
        """
        Get details for a specific variant.

        Args:
            variant_id: Variant identifier (e.g., "matrix_2x3")

        Returns:
            Variant details dict
        """
        try:
            endpoint = f"{self.base_url}/v1.2/variant/{variant_id}"

            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(endpoint)
                response.raise_for_status()

                details = response.json()

                logger.info(f"✅ Retrieved details for variant '{variant_id}'")

                return details

        except Exception as e:
            logger.error(f"Failed to get variant details: {e}")
            raise


# Convenience function
async def create_v1_2_client(base_url: Optional[str] = None) -> TextServiceClientV1_2:
    """
    Create and validate v1.2 client (convenience function).

    Args:
        base_url: Optional Text Service URL override

    Returns:
        TextServiceClientV1_2 instance

    Raises:
        Exception: If service is not healthy
    """
    client = TextServiceClientV1_2(base_url)

    # Perform health check
    is_healthy = await client.health_check()
    if not is_healthy:
        raise Exception(f"Text Service v1.2 at {client.base_url} is not healthy")

    return client


# Example usage
if __name__ == "__main__":
    async def test_client():
        print("Text Service v1.2 Client Test")
        print("=" * 70)

        # Initialize client
        client = TextServiceClientV1_2()

        # Health check
        print("\nHealth Check:")
        healthy = await client.health_check()
        print(f"  Service healthy: {healthy}")

        # Get variants
        print("\nFetching variants:")
        try:
            variants = await client.get_variants()
            print(f"  Total variants: {variants.get('total_variants')}")
            print(f"  Slide types: {len(variants.get('slide_types', {}))}")
        except Exception as e:
            print(f"  Error: {e}")

        # Test generation (example request)
        print("\nTest Generation Request:")
        test_request = {
            "variant_id": "matrix_2x2",
            "slide_spec": {
                "slide_title": "Strategic Pillars",
                "slide_purpose": "Present our four strategic pillars",
                "key_message": "Customer focus, innovation, excellence, growth",
                "tone": "professional",
                "audience": "Executive team"
            },
            "presentation_spec": {
                "presentation_title": "Q4 Business Review",
                "presentation_type": "Strategic overview",
                "current_slide_number": 3,
                "total_slides": 10
            },
            "enable_parallel": True,
            "validate_character_counts": True
        }

        try:
            result = await client.generate(test_request)
            print(f"  ✅ Generation successful")
            print(f"  Content length: {len(result.content)} chars")
            print(f"  Variant: {result.metadata.get('variant_id')}")
            print(f"  Mode: {result.metadata.get('generation_mode')}")
            print(f"  Valid: {result.metadata.get('character_validation_valid')}")
        except Exception as e:
            print(f"  ❌ Generation failed: {e}")

        print("\n" + "=" * 70)
        print("Test complete!")

    asyncio.run(test_client())
