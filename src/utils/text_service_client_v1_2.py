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

    async def generate(self, request: Dict[str, Any], max_retries: int = 2) -> GeneratedText:
        """
        Generate slide content using v1.2 element-based API with retry logic.

        v4.0.17: Added retry logic for transient LLM generation failures.
        When Text Service LLM generates incomplete content (missing sentence_5, etc.),
        it returns HTTP 400/422. This method retries such failures.

        Args:
            request: V1_2_GenerationRequest dict with:
                - variant_id: str (e.g., "matrix_2x3")
                - slide_spec: SlideSpecification dict
                - presentation_spec: PresentationSpecification dict
                - enable_parallel: bool (default: True)
                - validate_character_counts: bool (default: True)
            max_retries: Maximum retry attempts for LLM generation errors (default: 2)

        Returns:
            GeneratedText with:
                - content: Complete HTML string (or dict for structured content)
                - metadata: Generation metadata

        Raises:
            Exception: On API errors or timeouts after all retries exhausted
        """
        last_exception = None

        for attempt in range(max_retries + 1):
            try:
                return await self._generate_once(request)
            except Exception as e:
                last_exception = e
                error_msg = str(e).lower()

                # v4.0.17: Check if this is a retryable LLM generation error
                is_retryable = (
                    "sentence_" in error_msg or
                    "generated_content" in error_msg or
                    "llm generation failed" in error_msg or
                    "elementcontent" in error_msg or
                    "input should be a valid string" in error_msg
                )

                if is_retryable and attempt < max_retries:
                    wait_time = 2 ** attempt  # 1s, 2s exponential backoff
                    logger.warning(
                        f"Text Service LLM generation incomplete "
                        f"(attempt {attempt + 1}/{max_retries + 1}), "
                        f"retrying in {wait_time}s: {str(e)[:150]}"
                    )
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    # Non-retryable or max retries exceeded
                    if attempt > 0:
                        logger.error(
                            f"Text Service failed after {attempt + 1} attempts: {e}"
                        )
                    break

        # All retries failed
        raise last_exception

    async def _generate_once(self, request: Dict[str, Any]) -> GeneratedText:
        """
        Single attempt at content generation (internal method).

        v4.0.17: Extracted from generate() to support retry logic.
        """
        import time
        endpoint = f"{self.base_url}/v1.2/generate"
        start_time = time.time()

        try:
            # v4.0.31: Use print() for Railway visibility
            variant = request.get('variant_id')
            slide_title = request.get('slide_spec', {}).get('slide_title', '')[:30]
            print(f"[TEXT-SVC] POST /v1.2/generate variant={variant}, title='{slide_title}'")

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

                # v4.0.16: Log raw response BEFORE json() parsing - at INFO level for visibility
                raw_body = response.text
                logger.info(f"Text Service raw response ({len(raw_body)} chars): {raw_body[:200]}...")

                result = response.json()

                # v4.0.16: IMMEDIATE null check - must be FIRST thing after json()
                # This catches the case where Text Service returns literal "null"
                if result is None:
                    logger.error(
                        f"⚠️ Text Service returned literal 'null' response!\n"
                        f"  Variant: {request.get('variant_id')}\n"
                        f"  HTTP Status: {response.status_code}\n"
                        f"  Content-Length: {response.headers.get('content-length', 'N/A')}\n"
                        f"  Raw body was: {raw_body[:100]}"
                    )
                    raise Exception("Text Service returned null response body - check Text Service health")

                # v4.0.16: Type check - after null check
                if not isinstance(result, dict):
                    logger.error(
                        f"Text Service returned non-dict: {type(result).__name__} = {str(result)[:200]}"
                    )
                    raise Exception(f"Text Service returned invalid response type: {type(result).__name__}")

                # v4.0.14: Log parsed result structure (safe now - we know result is a dict)
                result_keys = list(result.keys())
                result_success = result.get('success')
                result_html_len = len(result.get('html', '')) if result.get('html') else 0
                logger.info(
                    f"Text Service parsed response:\n"
                    f"  Type: dict\n"
                    f"  Keys: {result_keys}\n"
                    f"  success: {result_success}\n"
                    f"  html length: {result_html_len}"
                )

                if not result.get("success", False):
                    error_detail = result.get("error", result.get("detail", "Unknown error"))
                    logger.error(f"Text Service returned success=false: {error_detail}")
                    raise Exception(f"Text Service error: {error_detail}")

                # v4.0.31: Use print() for Railway visibility
                elapsed_total = time.time() - start_time
                print(f"[TEXT-SVC-OK] /v1.2/generate returned in {elapsed_total:.1f}s ({result_html_len} chars)")

                # v4.0.16: Belt-and-suspenders null check (should never trigger)
                if result is None:
                    raise Exception("Result became None unexpectedly - should have been caught earlier")

                # v4.0.19: Handle character count validation warnings with defensive None check
                # Railway logs showed AttributeError at this line despite earlier null checks
                validation = result.get("validation") if result else None
                if validation and validation.get("valid") is False:
                    violations = validation.get("violations", [])
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
            # v4.0.31: Use print() for Railway visibility
            error_body = e.response.text[:200] if e.response else "No body"
            print(f"[TEXT-SVC-ERROR] HTTP {e.response.status_code} for /v1.2/generate")
            print(f"[TEXT-SVC-ERROR]   Variant: {request.get('variant_id')}")
            print(f"[TEXT-SVC-ERROR]   Body: {error_body}")

            # Include error details in exception message
            error_msg = error_body[:500] if len(error_body) > 500 else error_body
            raise Exception(
                f"Text Service v1.2 HTTP error: {e.response.status_code} - {error_msg}"
            )

        except httpx.RequestError as e:
            # v4.0.31: Use print() for Railway visibility
            print(f"[TEXT-SVC-ERROR] Request error for /v1.2/generate: {str(e)[:100]}")
            raise Exception(f"Text Service v1.2 request error: {str(e)}")

        except Exception as e:
            # v4.0.31: Use print() for Railway visibility
            print(f"[TEXT-SVC-ERROR] {type(e).__name__} for /v1.2/generate: {str(e)[:100]}")
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
        # v4.0.21: Defensive null checks - Text Service may return null for these fields
        v1_2_metadata = v1_2_response.get("metadata") or {}
        validation = v1_2_response.get("validation") or {}

        metadata = {
            "variant_id": v1_2_metadata.get("variant_id"),
            "generation_mode": v1_2_metadata.get("generation_mode"),
            "element_count": v1_2_metadata.get("element_count"),
            "template_path": v1_2_metadata.get("template_path"),
            "character_validation_valid": validation.get("valid", True) if validation else True,
            "character_validation_violations": len(validation.get("violations", [])) if validation else 0,
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
            # v4.0.29: Use print() for Railway visibility (logger not captured)
            print(f"[TEXT-SVC] Calling: {url}")
            print(f"[TEXT-SVC]   slide_type={payload.get('slide_type')}, visual_style={payload.get('visual_style')}")

            # v4.0.30: Hero endpoints need longer timeout for AI image generation
            HERO_TIMEOUT = 180  # 3 minutes - image generation takes 60-120s
            async with httpx.AsyncClient(timeout=HERO_TIMEOUT) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                result = response.json()

                print(f"[TEXT-SVC-OK] Hero endpoint {endpoint} returned successfully")
                return result

        except httpx.HTTPStatusError as e:
            # v4.0.29: Use print() for Railway visibility (logger not captured)
            response_body = e.response.text[:500] if e.response else "No response body"
            print(f"[TEXT-SVC-ERROR] HTTP {e.response.status_code}")
            print(f"[TEXT-SVC-ERROR]   URL: {url}")
            print(f"[TEXT-SVC-ERROR]   Body: {response_body}")
            raise Exception(f"Hero endpoint HTTP {e.response.status_code}: {response_body[:200]}")
        except httpx.TimeoutException as e:
            print(f"[TEXT-SVC-ERROR] TIMEOUT after {HERO_TIMEOUT}s: {url}")
            raise Exception(f"Hero endpoint timeout after {HERO_TIMEOUT}s")
        except httpx.ConnectError as e:
            print(f"[TEXT-SVC-ERROR] CONNECTION FAILED: {url}")
            print(f"[TEXT-SVC-ERROR]   Error: {str(e)}")
            raise Exception(f"Hero endpoint connection error: {str(e)}")
        except Exception as e:
            print(f"[TEXT-SVC-ERROR] {type(e).__name__}: {str(e)}")
            raise Exception(f"Hero endpoint failure: {type(e).__name__}: {str(e)}")

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

    # =========================================================================
    # I-SERIES GENERATION (v4.0 - Image + Text Combined Layouts)
    # =========================================================================

    async def generate_iseries(
        self,
        layout_type: str,
        slide_number: int,
        title: str,
        narrative: str,
        topics: list,
        visual_style: str = "professional",
        content_style: str = "bullets",
        context: Optional[Dict[str, Any]] = None,
        max_bullets: int = 5,
        # v4.5: Theme system params
        theme_config: Optional[Dict] = None,
        content_context: Optional[Dict] = None,
        styling_mode: str = "inline_styles",
        # v4.7: Global brand variables for simplified prompting
        global_brand: Optional[Dict] = None,
        # v4.8: Gold Standard content_variant (Unified Variant System)
        content_variant: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate I-series slide (image + text combined layout).

        I-series layouts provide portrait images (9:16) alongside text content:
        - I1: Wide image left (660×1080), content right (1200×840)
        - I2: Wide image right (660×1080), content left (1140×840)
        - I3: Narrow image left (360×1080), content right (1500×840)
        - I4: Narrow image right (360×1080), content left (1440×840)

        v4.5: Theme system params added (ignored by v1.2.2, used by v1.3.0).
        v4.7: global_brand added for simplified image prompting.
        v4.8: content_variant added for Gold Standard I-series variants.
               The content_variant specifies which text layout template to use
               (e.g., "sequential_3col", "comparison_2col", "single_column_3section").

        Args:
            layout_type: Layout ID (I1, I2, I3, I4)
            slide_number: Slide position in presentation
            title: Slide title
            narrative: Content narrative/summary
            topics: List of key topics/points
            visual_style: Image style (professional, illustrated, kids)
            content_style: Text style (bullets, paragraphs, mixed)
            context: Optional context dict with theme, audience, etc.
            max_bullets: Maximum bullet points (default: 5)
            theme_config: v4.5 - Full theme config
            content_context: v4.5 - Audience/purpose/time config
            styling_mode: v4.5 - "inline_styles" or "css_classes"
            global_brand: v4.7 - Global brand variables dict with:
                - target_demographic: Audience keywords for prompt
                - visual_style: Style phrase for prompt
                - color_palette: Color phrase for prompt
                - lighting_mood: Lighting/mood phrase for prompt
            content_variant: v4.8 - Gold Standard content variant ID.
                Specifies which text template to use for the content area.
                Examples: "sequential_3col", "comparison_2col", "single_column_3section"
                If None, Text Service uses default layout for the layout_type.

        Returns:
            Dict with:
                - image_html: HTML for image section
                - title_html: HTML for title
                - subtitle_html: HTML for subtitle (may be None)
                - content_html: HTML for text content
                - image_url: Generated image URL
                - image_fallback: True if gradient fallback was used
                - metadata: Generation metadata
        """
        import time

        endpoint = f"{self.base_url}/v1.2/iseries/generate"
        start_time = time.time()

        payload = {
            "slide_number": slide_number,
            "layout_type": layout_type,
            "title": title,
            "narrative": narrative,
            "topics": topics,
            "visual_style": visual_style,
            "content_style": content_style,
            "max_bullets": max_bullets,
            "context": context or {}
        }

        # v4.8: Add Gold Standard content_variant if specified
        if content_variant:
            payload["content_variant"] = content_variant

        # v4.5: Add theme system params
        if theme_config:
            payload["theme_config"] = theme_config
        if content_context:
            payload["content_context"] = content_context
        if styling_mode:
            payload["styling_mode"] = styling_mode

        # v4.7: Add global brand variables for simplified prompting
        if global_brand:
            payload["global_brand"] = global_brand

        try:
            # v4.8: Include content_variant in log if specified
            variant_info = f", content_variant={content_variant}" if content_variant else ""
            print(f"[TEXT-SVC] POST /v1.2/iseries/generate layout={layout_type}, style={visual_style}{variant_info}")

            # I-series needs longer timeout for AI image generation
            ISERIES_TIMEOUT = 180  # 3 minutes - image generation takes 60-120s

            async with httpx.AsyncClient(timeout=ISERIES_TIMEOUT) as client:
                response = await client.post(endpoint, json=payload)
                response.raise_for_status()

                result = response.json()

                elapsed = time.time() - start_time
                print(
                    f"[TEXT-SVC-OK] /v1.2/iseries/generate returned in {elapsed:.1f}s "
                    f"(image_fallback={result.get('image_fallback', False)})"
                )

                logger.info(
                    f"I-series generation complete: {layout_type}",
                    extra={
                        "layout_type": layout_type,
                        "elapsed_seconds": elapsed,
                        "image_fallback": result.get("image_fallback", False),
                        "visual_style": visual_style
                    }
                )

                return result

        except httpx.HTTPStatusError as e:
            response_body = e.response.text[:500] if e.response else "No body"
            print(f"[TEXT-SVC-ERROR] HTTP {e.response.status_code} for /v1.2/iseries/generate")
            print(f"[TEXT-SVC-ERROR]   Layout: {layout_type}, Body: {response_body}")
            raise Exception(f"I-series HTTP {e.response.status_code}: {response_body[:200]}")

        except httpx.TimeoutException:
            print(f"[TEXT-SVC-ERROR] TIMEOUT after {ISERIES_TIMEOUT}s for I-series")
            raise Exception(f"I-series timeout after {ISERIES_TIMEOUT}s")

        except Exception as e:
            print(f"[TEXT-SVC-ERROR] {type(e).__name__}: {str(e)[:100]}")
            raise

    async def generate_iseries_i1(
        self,
        slide_number: int,
        title: str,
        narrative: str,
        topics: list,
        visual_style: str = "professional",
        content_style: str = "bullets",
        context: Optional[Dict[str, Any]] = None,
        global_brand: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Generate I1 layout: Wide image left (660×1080), content right (1200×840).

        Best for: Balanced image-text slides, product showcases, team introductions.
        """
        return await self.generate_iseries(
            layout_type="I1",
            slide_number=slide_number,
            title=title,
            narrative=narrative,
            topics=topics,
            visual_style=visual_style,
            content_style=content_style,
            context=context,
            global_brand=global_brand
        )

    async def generate_iseries_i2(
        self,
        slide_number: int,
        title: str,
        narrative: str,
        topics: list,
        visual_style: str = "professional",
        content_style: str = "bullets",
        context: Optional[Dict[str, Any]] = None,
        global_brand: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Generate I2 layout: Wide image right (660×1080), content left (1140×840).

        Best for: Case studies, portfolios, visual storytelling.
        """
        return await self.generate_iseries(
            layout_type="I2",
            slide_number=slide_number,
            title=title,
            narrative=narrative,
            topics=topics,
            visual_style=visual_style,
            content_style=content_style,
            context=context,
            global_brand=global_brand
        )

    async def generate_iseries_i3(
        self,
        slide_number: int,
        title: str,
        narrative: str,
        topics: list,
        visual_style: str = "professional",
        content_style: str = "bullets",
        context: Optional[Dict[str, Any]] = None,
        global_brand: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Generate I3 layout: Narrow image left (360×1080), content right (1500×840).

        Best for: Text-heavy slides with accent image, detailed explanations.
        """
        return await self.generate_iseries(
            layout_type="I3",
            slide_number=slide_number,
            title=title,
            narrative=narrative,
            topics=topics,
            visual_style=visual_style,
            content_style=content_style,
            context=context,
            global_brand=global_brand
        )

    async def generate_iseries_i4(
        self,
        slide_number: int,
        title: str,
        narrative: str,
        topics: list,
        visual_style: str = "professional",
        content_style: str = "bullets",
        context: Optional[Dict[str, Any]] = None,
        global_brand: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Generate I4 layout: Narrow image right (360×1080), content left (1440×840).

        Best for: Content-focused presentations with supporting visual.
        """
        return await self.generate_iseries(
            layout_type="I4",
            slide_number=slide_number,
            title=title,
            narrative=narrative,
            topics=topics,
            visual_style=visual_style,
            content_style=content_style,
            context=context,
            global_brand=global_brand
        )

    async def get_iseries_layouts(self) -> Dict[str, Any]:
        """
        Get I-series layout specifications.

        GET /v1.2/iseries/layouts

        Returns:
            Dict with layout specifications (dimensions, supported styles, etc.)
        """
        try:
            endpoint = f"{self.base_url}/v1.2/iseries/layouts"

            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(endpoint)
                response.raise_for_status()

                layouts = response.json()
                logger.info(f"✅ Retrieved I-series layout specifications")

                return layouts

        except Exception as e:
            logger.error(f"Failed to get I-series layouts: {e}")
            raise

    async def iseries_health_check(self) -> bool:
        """
        Check if I-series endpoints are healthy.

        GET /v1.2/iseries/health

        Returns:
            True if healthy, False otherwise
        """
        try:
            endpoint = f"{self.base_url}/v1.2/iseries/health"

            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(endpoint)
                response.raise_for_status()

                health = response.json()
                status = health.get("status", "unknown")

                logger.info(f"✅ I-series health check: {status}")
                return status == "healthy"

        except Exception as e:
            logger.error(f"❌ I-series health check failed: {e}")
            return False

    # =========================================================================
    # v4.2: STAGE 6 - TITLE/SUBTITLE GENERATION & UNIVERSAL RESPONSE
    # =========================================================================

    async def generate_title(
        self,
        slide_title: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate HTML-enriched slide title using Text Service.

        v4.2: Stage 6 - Used to generate titles for non-Text-Service slides
        (Analytics, Illustrator, Diagram).

        Args:
            slide_title: The plain text slide title
            context: Optional context with audience, tone, slide_purpose

        Returns:
            Dict with:
                - html: HTML-enriched title (e.g., "<h2 class='slide-title'>...</h2>")
                - metadata: Generation metadata
        """
        endpoint = f"{self.base_url}/api/ai/slide/title"

        payload = {
            "prompt": slide_title,
            "context": context or {}
        }

        try:
            print(f"[TEXT-SVC] POST /api/ai/slide/title: '{slide_title[:50]}'")

            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(endpoint, json=payload)
                response.raise_for_status()

                result = response.json()

                print(f"[TEXT-SVC-OK] /api/ai/slide/title returned")
                logger.debug(f"Title generation result: {result}")

                return result

        except httpx.HTTPStatusError as e:
            response_body = e.response.text[:200] if e.response else "No body"
            print(f"[TEXT-SVC-ERROR] HTTP {e.response.status_code} for /api/ai/slide/title")
            logger.error(f"Title generation failed: {response_body}")

            # Return fallback
            return {
                "html": f"<h2 class='slide-title'>{slide_title}</h2>",
                "metadata": {"fallback": True, "error": str(e)}
            }

        except Exception as e:
            logger.error(f"Title generation error: {e}")
            return {
                "html": f"<h2 class='slide-title'>{slide_title}</h2>",
                "metadata": {"fallback": True, "error": str(e)}
            }

    async def generate_subtitle(
        self,
        subtitle_text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate HTML-enriched slide subtitle using Text Service.

        v4.2: Stage 6 - Used to generate subtitles for non-Text-Service slides.

        Args:
            subtitle_text: The plain text subtitle
            context: Optional context with audience, tone

        Returns:
            Dict with:
                - html: HTML-enriched subtitle (e.g., "<p class='slide-subtitle'>...</p>")
                - metadata: Generation metadata
        """
        endpoint = f"{self.base_url}/api/ai/slide/subtitle"

        payload = {
            "prompt": subtitle_text,
            "context": context or {}
        }

        try:
            print(f"[TEXT-SVC] POST /api/ai/slide/subtitle: '{subtitle_text[:50]}'")

            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(endpoint, json=payload)
                response.raise_for_status()

                result = response.json()

                print(f"[TEXT-SVC-OK] /api/ai/slide/subtitle returned")
                logger.debug(f"Subtitle generation result: {result}")

                return result

        except httpx.HTTPStatusError as e:
            response_body = e.response.text[:200] if e.response else "No body"
            print(f"[TEXT-SVC-ERROR] HTTP {e.response.status_code} for /api/ai/slide/subtitle")
            logger.error(f"Subtitle generation failed: {response_body}")

            # Return fallback
            return {
                "html": f"<p class='slide-subtitle'>{subtitle_text}</p>",
                "metadata": {"fallback": True, "error": str(e)}
            }

        except Exception as e:
            logger.error(f"Subtitle generation error: {e}")
            return {
                "html": f"<p class='slide-subtitle'>{subtitle_text}</p>",
                "metadata": {"fallback": True, "error": str(e)}
            }

    async def generate_title_and_subtitle(
        self,
        title: str,
        subtitle: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate both title and subtitle HTML in parallel.

        v4.2: Stage 6 - Convenience method for generating both at once.

        Args:
            title: Plain text title
            subtitle: Plain text subtitle (optional)
            context: Optional context

        Returns:
            Dict with title_html and subtitle_html
        """
        import asyncio

        # Generate title
        title_task = self.generate_title(title, context)

        # Generate subtitle if provided
        if subtitle:
            subtitle_task = self.generate_subtitle(subtitle, context)
            title_result, subtitle_result = await asyncio.gather(title_task, subtitle_task)
        else:
            title_result = await title_task
            subtitle_result = None

        return {
            "title_html": title_result.get("html"),
            "subtitle_html": subtitle_result.get("html") if subtitle_result else None,
            "metadata": {
                "title_metadata": title_result.get("metadata", {}),
                "subtitle_metadata": subtitle_result.get("metadata", {}) if subtitle_result else {}
            }
        }

    def transform_to_universal(
        self,
        text_service_response: Dict[str, Any],
        title_html: Optional[str] = None,
        subtitle_html: Optional[str] = None
    ) -> "UniversalServiceResponse":
        """
        Transform Text Service response to UniversalServiceResponse.

        v4.2: Stage 6 - Converts Text Service output to universal format
        that all services should return.

        Args:
            text_service_response: Response from /v1.2/generate
            title_html: Optional pre-generated title HTML
            subtitle_html: Optional pre-generated subtitle HTML

        Returns:
            UniversalServiceResponse with title_html, subtitle_html, content_html
        """
        from src.models.content import UniversalServiceResponse

        # Extract content HTML
        content_html = text_service_response.get("html", "")

        # If no pre-generated title/subtitle provided, try to extract from content
        # Note: Text Service v1.2 typically returns complete HTML, not separate parts
        # For now, we pass them through if provided, otherwise content has everything
        extracted_title = title_html
        extracted_subtitle = subtitle_html

        # Build metadata
        v1_2_metadata = text_service_response.get("metadata") or {}
        metadata = {
            "variant_id": v1_2_metadata.get("variant_id"),
            "generation_mode": v1_2_metadata.get("generation_mode"),
            "source": "text_service_v1.2",
            **v1_2_metadata
        }

        return UniversalServiceResponse(
            success=text_service_response.get("success", True),
            title_html=extracted_title,
            subtitle_html=extracted_subtitle,
            content_html=content_html,
            metadata=metadata,
            error=text_service_response.get("error")
        )

    # =========================================================================
    # v4.3: UNIFIED SLIDES API (NEW - Text Service v1.2.2)
    # Uses /v1.2/slides/* router - Returns spec-compliant responses
    # =========================================================================

    async def _call_unified_slides(
        self,
        layout: str,
        payload: Dict[str, Any],
        timeout: int = 180
    ) -> Dict[str, Any]:
        """
        Internal method to call unified /v1.2/slides/{layout} endpoint.

        v4.3: Text Service v1.2.2 provides new unified slides router that
        returns spec-compliant responses with correct field names.

        Args:
            layout: Layout ID (H1-generated, H1-structured, H2-section, etc.)
            payload: Request payload
            timeout: Request timeout (default 180s for image generation)

        Returns:
            Dict with spec-compliant response (slide_title, subtitle, body, etc.)
        """
        import time

        endpoint = f"{self.base_url}/v1.2/slides/{layout}"
        start_time = time.time()

        try:
            print(f"[TEXT-SVC] POST /v1.2/slides/{layout}")

            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(endpoint, json=payload)
                response.raise_for_status()

                result = response.json()

                elapsed = time.time() - start_time
                llm_calls = result.get("metadata", {}).get("llm_calls", 1)
                print(f"[TEXT-SVC-OK] /v1.2/slides/{layout} in {elapsed:.1f}s ({llm_calls} LLM calls)")

                logger.info(
                    f"Unified slides generation complete: {layout}",
                    extra={
                        "layout": layout,
                        "elapsed_seconds": elapsed,
                        "llm_calls": llm_calls
                    }
                )

                return result

        except httpx.HTTPStatusError as e:
            response_body = e.response.text[:500] if e.response else "No body"
            print(f"[TEXT-SVC-ERROR] HTTP {e.response.status_code} for /v1.2/slides/{layout}")
            print(f"[TEXT-SVC-ERROR]   Body: {response_body}")
            raise Exception(f"Unified slides HTTP {e.response.status_code}: {response_body[:200]}")

        except httpx.TimeoutException:
            print(f"[TEXT-SVC-ERROR] TIMEOUT after {timeout}s for /v1.2/slides/{layout}")
            raise Exception(f"Unified slides timeout after {timeout}s")

        except Exception as e:
            print(f"[TEXT-SVC-ERROR] {type(e).__name__}: {str(e)[:100]}")
            raise

    async def generate_h1_generated(
        self,
        slide_number: int,
        narrative: str,
        topics: Optional[list] = None,
        presentation_title: Optional[str] = None,
        subtitle: Optional[str] = None,
        visual_style: str = "professional",
        image_prompt_hint: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        # v4.5: Theme system params
        theme_config: Optional[Dict] = None,
        content_context: Optional[Dict] = None,
        styling_mode: str = "inline_styles",
        # v4.7: Global brand for simplified image prompting
        global_brand: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Generate H1-generated (title slide with AI background image).

        v4.3: Uses unified /v1.2/slides/H1-generated endpoint.
        Returns spec-compliant response with hero_content, slide_title, subtitle.

        v4.5: Theme system params added (ignored by v1.2.2, used by v1.3.0).
        v4.7: Global brand added for simplified image prompting.

        Args:
            slide_number: Slide position in presentation
            narrative: Slide narrative/purpose
            topics: Optional list of key topics
            presentation_title: Title for the presentation
            subtitle: Optional subtitle
            visual_style: Image style ("professional", "illustrated", "kids")
            image_prompt_hint: Optional hint for image generation
            context: Optional context dict
            theme_config: v4.5 - Full theme config
            content_context: v4.5 - Audience/purpose/time config
            styling_mode: v4.5 - "inline_styles" or "css_classes"
            global_brand: v4.7 - Global brand variables for simplified prompting

        Returns:
            Dict with:
                - hero_content: Full-slide HTML
                - slide_title: HTML title
                - subtitle: HTML subtitle
                - background_image: Generated image URL or None
                - background_color: None (embedded in hero_content)
                - metadata: Generation metadata
        """
        payload = {
            "slide_number": slide_number,
            "narrative": narrative,
            "topics": topics or [],
            "presentation_title": presentation_title,
            "subtitle": subtitle,
            "visual_style": visual_style,
            "image_prompt_hint": image_prompt_hint,
            "context": context or {}
        }

        # v4.5: Add theme system params
        if theme_config:
            payload["theme_config"] = theme_config
        if content_context:
            payload["content_context"] = content_context
        if styling_mode:
            payload["styling_mode"] = styling_mode
        # v4.7: Add global brand for simplified image prompting
        if global_brand:
            payload["global_brand"] = global_brand

        return await self._call_unified_slides("H1-generated", payload, timeout=180)

    async def generate_h1_structured(
        self,
        slide_number: int,
        narrative: str,
        presentation_title: str,
        subtitle: Optional[str] = None,
        author_name: Optional[str] = None,
        date_info: Optional[str] = None,
        visual_style: str = "professional",
        context: Optional[Dict[str, Any]] = None,
        # v4.5: Theme system params
        theme_config: Optional[Dict] = None,
        content_context: Optional[Dict] = None,
        styling_mode: str = "inline_styles"
    ) -> Dict[str, Any]:
        """
        Generate H1-structured (title slide with gradient background).

        v4.3: Uses unified /v1.2/slides/H1-structured endpoint.
        Returns structured fields instead of full HTML.

        v4.5: Theme system params added (ignored by v1.2.2, used by v1.3.0).

        Args:
            slide_number: Slide position
            narrative: Slide narrative
            presentation_title: Main title
            subtitle: Optional subtitle
            author_name: Author/presenter name
            date_info: Date or event info
            visual_style: Style preference
            context: Optional context
            theme_config: v4.5 - Full theme config
            content_context: v4.5 - Audience/purpose/time config
            styling_mode: v4.5 - "inline_styles" or "css_classes"

        Returns:
            Dict with:
                - slide_title: HTML title
                - subtitle: HTML subtitle
                - author_info: HTML author info
                - background_color: Default #1e3a5f
                - metadata: Generation metadata
        """
        payload = {
            "slide_number": slide_number,
            "narrative": narrative,
            "presentation_title": presentation_title,
            "subtitle": subtitle,
            "author_name": author_name,
            "date_info": date_info,
            "visual_style": visual_style,
            "context": context or {}
        }

        # v4.5: Add theme system params
        if theme_config:
            payload["theme_config"] = theme_config
        if content_context:
            payload["content_context"] = content_context
        if styling_mode:
            payload["styling_mode"] = styling_mode

        return await self._call_unified_slides("H1-structured", payload, timeout=60)

    async def generate_h2_section(
        self,
        slide_number: int,
        narrative: str,
        section_number: Optional[str] = None,
        section_title: Optional[str] = None,
        topics: Optional[list] = None,
        visual_style: str = "professional",
        # v4.5: Theme system params
        theme_config: Optional[Dict] = None,
        content_context: Optional[Dict] = None,
        styling_mode: str = "inline_styles",
        # v4.7: Global brand for simplified image prompting
        global_brand: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Generate H2-section (section divider slide).

        v4.3: Uses unified /v1.2/slides/H2-section endpoint.
        v4.5: Theme system params added (ignored by v1.2.2, used by v1.3.0).
        v4.7: Global brand added for simplified image prompting.

        Args:
            slide_number: Slide position
            narrative: Section narrative
            section_number: Section number ("01", "02", etc.)
            section_title: Section title
            topics: Optional topics for section
            visual_style: Style preference
            theme_config: v4.5 - Full theme config
            content_context: v4.5 - Audience/purpose/time config
            styling_mode: v4.5 - "inline_styles" or "css_classes"
            global_brand: v4.7 - Global brand variables for simplified prompting

        Returns:
            Dict with:
                - section_number: HTML section number
                - slide_title: HTML section title
                - subtitle: HTML subtitle (optional)
                - background_color: Default #374151
                - metadata: Generation metadata
        """
        payload = {
            "slide_number": slide_number,
            "narrative": narrative,
            "section_number": section_number,
            "section_title": section_title,
            "topics": topics or [],
            "visual_style": visual_style
        }

        # v4.5: Add theme system params
        if theme_config:
            payload["theme_config"] = theme_config
        if content_context:
            payload["content_context"] = content_context
        if styling_mode:
            payload["styling_mode"] = styling_mode
        # v4.7: Add global brand for simplified image prompting
        if global_brand:
            payload["global_brand"] = global_brand

        return await self._call_unified_slides("H2-section", payload, timeout=60)

    async def generate_h3_closing(
        self,
        slide_number: int,
        narrative: str,
        closing_message: Optional[str] = None,
        contact_email: Optional[str] = None,
        contact_phone: Optional[str] = None,
        website_url: Optional[str] = None,
        visual_style: str = "professional",
        # v4.5: Theme system params
        theme_config: Optional[Dict] = None,
        content_context: Optional[Dict] = None,
        styling_mode: str = "inline_styles",
        # v4.7: Global brand for simplified image prompting
        global_brand: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Generate H3-closing (closing slide with contact info).

        v4.3: Uses unified /v1.2/slides/H3-closing endpoint.
        v4.5: Theme system params added (ignored by v1.2.2, used by v1.3.0).
        v4.7: Global brand added for simplified image prompting.

        Args:
            slide_number: Slide position
            narrative: Closing narrative
            closing_message: Closing text ("Thank You", "Questions?", etc.)
            contact_email: Contact email
            contact_phone: Contact phone
            website_url: Website URL
            visual_style: Style preference
            theme_config: v4.5 - Full theme config
            content_context: v4.5 - Audience/purpose/time config
            styling_mode: v4.5 - "inline_styles" or "css_classes"
            global_brand: v4.7 - Global brand variables for simplified prompting

        Returns:
            Dict with:
                - slide_title: HTML title
                - subtitle: HTML subtitle
                - contact_info: HTML contact info
                - closing_message: HTML closing message
                - background_color: Default #1e3a5f
                - metadata: Generation metadata
        """
        payload = {
            "slide_number": slide_number,
            "narrative": narrative,
            "closing_message": closing_message,
            "contact_email": contact_email,
            "contact_phone": contact_phone,
            "website_url": website_url,
            "visual_style": visual_style
        }

        # v4.5: Add theme system params
        if theme_config:
            payload["theme_config"] = theme_config
        if content_context:
            payload["content_context"] = content_context
        if styling_mode:
            payload["styling_mode"] = styling_mode
        # v4.7: Add global brand for simplified image prompting
        if global_brand:
            payload["global_brand"] = global_brand

        return await self._call_unified_slides("H3-closing", payload, timeout=60)

    async def generate_c1_text(
        self,
        slide_number: int,
        narrative: str,
        variant_id: str = "bullets",
        slide_title: Optional[str] = None,
        subtitle: Optional[str] = None,
        topics: Optional[list] = None,
        content_style: str = "bullets",
        context: Optional[Dict[str, Any]] = None,
        # v4.5: Theme system params (THEME_SYSTEM_DESIGN.md v2.3)
        # Ignored by v1.2.2, auto-enabled in v1.3.0
        theme_config: Optional[Dict] = None,
        content_context: Optional[Dict] = None,
        styling_mode: str = "inline_styles",
        available_space: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Generate C1-text (content slide with COMBINED generation).

        v4.3: Uses unified /v1.2/slides/C1-text endpoint.
        KEY IMPROVEMENT: 1 LLM call instead of 3 (title + subtitle + body).
        67% efficiency gain per content slide!

        v4.5: Theme system params added. Text Service v1.2.2 ignores these
        (Pydantic extra="ignore"). They will auto-work when v1.3.0 deploys.

        Args:
            slide_number: Slide position
            narrative: Content narrative
            variant_id: One of 34 variants (e.g., "bullets", "matrix_2x2", "comparison_3col")
            slide_title: Optional title override (otherwise AI generates)
            subtitle: Optional subtitle override
            topics: Key topics/points to cover
            content_style: "bullets", "paragraphs", or "mixed"
            context: Optional context with audience, tone, etc.
            theme_config: v4.5 - Full theme config (typography + colors)
            content_context: v4.5 - Audience/purpose/time config
            styling_mode: v4.5 - "inline_styles" or "css_classes"
            available_space: v4.5 - Grid dimensions for multi-step generation

        Returns:
            Dict with:
                - slide_title: HTML title
                - subtitle: HTML subtitle
                - body: HTML body content
                - rich_content: Alias for body (L25 compatibility)
                - background_color: Default #ffffff
                - metadata: Generation metadata (llm_calls=1)
        """
        payload = {
            "slide_number": slide_number,
            "narrative": narrative,
            "variant_id": variant_id,
            "slide_title": slide_title,
            "subtitle": subtitle,
            "topics": topics or [],
            "content_style": content_style,
            "context": context or {}
        }

        # v4.5: Add theme system params (ignored until Text Service v1.3.0)
        if theme_config:
            payload["theme_config"] = theme_config
        if content_context:
            payload["content_context"] = content_context
        if styling_mode:
            payload["styling_mode"] = styling_mode
        if available_space:
            payload["available_space"] = available_space

        return await self._call_unified_slides("C1-text", payload, timeout=60)

    async def generate_slide_unified(
        self,
        layout: str,
        slide_number: int,
        narrative: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generic method to generate any slide via unified API.

        v4.3: Routes to appropriate /v1.2/slides/{layout} endpoint.
        Supports all Text Service layouts: H1-generated, H1-structured,
        H2-section, H3-closing, C1-text, L25, L29, I1-I4.

        Args:
            layout: Layout ID
            slide_number: Slide position
            narrative: Slide narrative
            **kwargs: Layout-specific parameters

        Returns:
            Spec-compliant response dict
        """
        payload = {
            "slide_number": slide_number,
            "narrative": narrative,
            **kwargs
        }

        # Set appropriate timeout based on layout
        timeout = 180 if layout in ["H1-generated", "L29", "I1", "I2", "I3", "I4"] else 60

        return await self._call_unified_slides(layout, payload, timeout=timeout)

    async def unified_slides_health_check(self) -> Dict[str, Any]:
        """
        Check health of unified slides router.

        Returns:
            Health check response with router info
        """
        try:
            endpoint = f"{self.base_url}/v1.2/slides/health"

            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(endpoint)
                response.raise_for_status()

                health = response.json()

                logger.info(
                    f"✅ Unified slides health check passed "
                    f"(version: {health.get('version')}, layouts: {len(health.get('layouts', {}))})"
                )

                return health

        except Exception as e:
            logger.error(f"❌ Unified slides health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}


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
