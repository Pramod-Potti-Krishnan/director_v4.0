"""
Service Router v1.2 for Director v3.4
======================================

Routes slides to appropriate content generation services:
- Pyramid slides (L25) → Illustrator Service /v1.0/pyramid/generate (v3.4-pyramid)
- Hero slides (L29) → Text Service /v1.2/hero/title, /section, /closing endpoints
- Content slides (L25) → Text Service /v1.2/generate endpoint

Key features:
- Pyramid support (v3.4-pyramid): Routes pyramid slides to Illustrator Service
- Hero slide support (v3.4): Routes title/section/closing slides to specialized hero endpoints
- Content slide support: Uses unified /v1.2/generate endpoint for 10 content variants
- Multi-service routing with automatic error handling
- Prior slides context for narrative flow
"""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
from src.models.agents import Slide, PresentationStrawman
from src.utils.logger import setup_logger
from src.utils.text_service_client_v1_2 import TextServiceClientV1_2
from src.utils.v1_2_transformer import V1_2_Transformer
from src.utils.hero_request_transformer import HeroRequestTransformer
from src.clients.illustrator_client import IllustratorClient
from src.clients.analytics_client import AnalyticsClient

logger = setup_logger(__name__)


class ServiceRouterV1_2:
    """
    Routes slides to appropriate content generation services.

    Features:
    - Multi-service routing (Text v1.2 + Illustrator v1.0 + Analytics v3)
    - Analytics slide support (v3.4-analytics)
    - Pyramid slide support (v3.4-pyramid)
    - Sequential processing with automatic error handling
    - Prior slides context for narrative flow
    - Processing statistics and metadata
    """

    def __init__(
        self,
        text_service_client: TextServiceClientV1_2,
        illustrator_client: Optional[IllustratorClient] = None,
        analytics_client: Optional[AnalyticsClient] = None
    ):
        """
        Initialize service router for v1.2 with multi-service support.

        Args:
            text_service_client: TextServiceClientV1_2 instance
            illustrator_client: Optional IllustratorClient instance for pyramid generation
            analytics_client: Optional AnalyticsClient instance for chart generation
        """
        self.client = text_service_client
        self.illustrator_client = illustrator_client
        self.analytics_client = analytics_client
        self.hero_transformer = HeroRequestTransformer()

        # Build status message
        services = ["hero slide support"]
        if illustrator_client:
            services.append("pyramid support (Illustrator)")
        if analytics_client:
            services.append("analytics support (Analytics v3)")

        logger.info(f"ServiceRouterV1_2 initialized with {', '.join(services)}")

    def _classify_error(
        self,
        error: Exception,
        response: Optional[Any] = None
    ) -> Dict[str, str]:
        """
        Classify error into actionable categories for debugging.

        Args:
            error: Exception that occurred
            response: Optional HTTP response object

        Returns:
            Dict with:
            - error_type: Exception class name
            - error_category: timeout|http_4xx|http_5xx|connection|validation|unknown
            - suggested_action: User-friendly remediation suggestion
            - http_status: HTTP status code if applicable
        """
        import httpx

        error_type = type(error).__name__
        error_msg = str(error).lower()

        # Timeout errors
        if isinstance(error, (httpx.TimeoutException, asyncio.TimeoutError)) or "timeout" in error_msg:
            return {
                "error_type": error_type,
                "error_category": "timeout",
                "suggested_action": "Service may be overloaded or slow. Retry or increase timeout settings.",
                "http_status": None
            }

        # HTTP status errors
        if isinstance(error, httpx.HTTPStatusError) and response:
            status = response.status_code
            if 400 <= status < 500:
                return {
                    "error_type": error_type,
                    "error_category": "http_4xx",
                    "suggested_action": f"Client error ({status}). Check request payload, authentication, or endpoint URL.",
                    "http_status": status
                }
            elif 500 <= status < 600:
                return {
                    "error_type": error_type,
                    "error_category": "http_5xx",
                    "suggested_action": f"Server error ({status}). Service may be experiencing issues or bugs. Check service logs.",
                    "http_status": status
                }

        # Connection errors
        if "connection" in error_msg or "refused" in error_msg or "unreachable" in error_msg:
            return {
                "error_type": error_type,
                "error_category": "connection",
                "suggested_action": "Cannot reach service. Check service URL, network connectivity, and ensure service is running.",
                "http_status": None
            }

        # Validation errors
        if "validation" in error_msg or "invalid" in error_msg or "missing" in error_msg:
            return {
                "error_type": error_type,
                "error_category": "validation",
                "suggested_action": "Request payload validation failed. Check required fields and data formats.",
                "http_status": None
            }

        # Unknown errors
        return {
            "error_type": error_type,
            "error_category": "unknown",
            "suggested_action": f"Unknown error: {error_type}. Check logs for full traceback and contact support.",
            "http_status": None
        }

    def _generate_error_summary(self, failed_slides: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate comprehensive error summary from failed slides (Tier 2 debugging).

        Analyzes all failures to identify patterns, count errors by category/service,
        and provide actionable recommendations for debugging and resolution.

        Args:
            failed_slides: List of failed slide records with error classification

        Returns:
            Dict with:
            - total_failures: Total number of failed slides
            - by_category: Error counts grouped by category (timeout, http_4xx, etc.)
            - by_service: Error counts grouped by service (analytics_v3, text_service_v1.2, etc.)
            - by_endpoint: Error counts grouped by endpoint
            - critical_issues: List of high-priority issues requiring attention
            - recommended_actions: Prioritized list of remediation steps
            - failure_details: Complete failure records for support tickets
        """
        if not failed_slides:
            return {
                "total_failures": 0,
                "by_category": {},
                "by_service": {},
                "by_endpoint": {},
                "critical_issues": [],
                "recommended_actions": [],
                "failure_details": []
            }

        # Aggregate by category
        by_category = {}
        for failure in failed_slides:
            category = failure.get("error_category", "unknown")
            by_category[category] = by_category.get(category, 0) + 1

        # Aggregate by service
        by_service = {}
        for failure in failed_slides:
            service = failure.get("service", "unknown")
            by_service[service] = by_service.get(service, 0) + 1

        # Aggregate by endpoint
        by_endpoint = {}
        for failure in failed_slides:
            endpoint = failure.get("endpoint", "unknown")
            if endpoint:  # Skip None endpoints
                by_endpoint[endpoint] = by_endpoint.get(endpoint, 0) + 1

        # Identify critical issues (>= 50% failure rate or specific patterns)
        critical_issues = []
        total_failures = len(failed_slides)

        # Critical: Validation errors (missing clients)
        validation_count = by_category.get("validation", 0)
        if validation_count > 0:
            critical_issues.append({
                "severity": "high",
                "issue": "Service client not initialized",
                "count": validation_count,
                "impact": "Slides cannot be generated without proper service clients",
                "action": "Check ServiceRouter initialization and ensure all required clients are provided"
            })

        # Critical: Timeout errors (service performance issues)
        timeout_count = by_category.get("timeout", 0)
        if timeout_count > 0:
            critical_issues.append({
                "severity": "medium",
                "issue": "Service timeout errors",
                "count": timeout_count,
                "impact": "Services are taking too long to respond or hanging",
                "action": "Check service health, increase timeout settings, or optimize service performance"
            })

        # Critical: HTTP 5xx errors (service bugs)
        http_5xx_count = by_category.get("http_5xx", 0)
        if http_5xx_count > 0:
            critical_issues.append({
                "severity": "high",
                "issue": "Server-side service errors (5xx)",
                "count": http_5xx_count,
                "impact": "Services are experiencing internal errors or bugs",
                "action": "Review service logs, check for service crashes, and investigate root cause"
            })

        # Critical: HTTP 4xx errors (invalid requests)
        http_4xx_count = by_category.get("http_4xx", 0)
        if http_4xx_count > 0:
            critical_issues.append({
                "severity": "medium",
                "issue": "Client request errors (4xx)",
                "count": http_4xx_count,
                "impact": "Invalid request payloads, authentication issues, or incorrect endpoints",
                "action": "Validate request schemas, check authentication tokens, and verify endpoint URLs"
            })

        # Generate prioritized recommended actions
        recommended_actions = []

        # Priority 1: Fix validation errors first (blocking all slides of that type)
        if validation_count > 0:
            recommended_actions.append({
                "priority": 1,
                "action": "Initialize missing service clients in ServiceRouter configuration",
                "rationale": f"{validation_count} slides blocked by missing clients"
            })

        # Priority 2: Fix HTTP 5xx errors (service bugs)
        if http_5xx_count > 0:
            recommended_actions.append({
                "priority": 2,
                "action": "Investigate and fix server-side service errors",
                "rationale": f"{http_5xx_count} slides failing due to service bugs or crashes"
            })

        # Priority 3: Optimize timeouts
        if timeout_count > 0:
            recommended_actions.append({
                "priority": 3,
                "action": "Optimize service performance or increase timeout settings",
                "rationale": f"{timeout_count} slides timing out during generation"
            })

        # Priority 4: Fix request validation
        if http_4xx_count > 0:
            recommended_actions.append({
                "priority": 4,
                "action": "Review and fix request payloads, schemas, or authentication",
                "rationale": f"{http_4xx_count} slides rejected by services due to invalid requests"
            })

        return {
            "total_failures": total_failures,
            "by_category": by_category,
            "by_service": by_service,
            "by_endpoint": by_endpoint,
            "critical_issues": critical_issues,
            "recommended_actions": sorted(recommended_actions, key=lambda x: x["priority"]),
            "failure_details": failed_slides  # Include full records for support tickets
        }

    async def route_presentation(
        self,
        strawman: PresentationStrawman,
        session_id: str
    ) -> Dict[str, Any]:
        """
        Route all slides in presentation to Text Service v1.2.

        Args:
            strawman: PresentationStrawman with variant_id and generated titles
            session_id: Session identifier for tracking

        Returns:
            Routing result dict with:
            - generated_slides: List of successfully generated slide content
            - failed_slides: List of failed slides with error details
            - metadata: Processing statistics

        Raises:
            ValueError: If slides are missing variant_id or generated_title
        """
        start_time = datetime.utcnow()
        slides = strawman.slides

        logger.info(f"Starting v1.2 presentation routing: {len(slides)} slides")

        # v3.4 DIAGNOSTIC: Print slide validation details
        import sys
        print("="*80, flush=True)
        print("🔍 VALIDATING SLIDES FOR V1.2 ROUTING", flush=True)
        print(f"   Total slides: {len(slides)}", flush=True)
        for slide in slides:
            print(f"   Slide {slide.slide_number}: id={slide.slide_id}, variant_id={getattr(slide, 'variant_id', 'MISSING')}, generated_title={getattr(slide, 'generated_title', 'MISSING')[:30] if hasattr(slide, 'generated_title') else 'MISSING'}...", flush=True)
        print("="*80, flush=True)
        sys.stdout.flush()

        # Validate all slides have required v1.2 fields
        self._validate_slides(slides)

        # v3.4 DIAGNOSTIC: Validation passed
        print(f"✅ All {len(slides)} slides validated successfully", flush=True)
        sys.stdout.flush()

        # Process slides sequentially
        result = await self._route_sequential(slides, strawman, session_id)

        # Calculate total processing time
        total_time = (datetime.utcnow() - start_time).total_seconds()
        result["metadata"]["total_processing_time_seconds"] = round(total_time, 2)

        logger.info(
            f"✅ v1.2 routing complete: "
            f"{result['metadata']['successful_count']}/{len(slides)} successful "
            f"in {total_time:.2f}s"
        )

        return result

    def _validate_slides(self, slides: List[Slide]):
        """
        Validate slides have required fields for their service type.

        Args:
            slides: List of slides to validate

        Raises:
            ValueError: If validation fails
        """
        errors = []

        for slide in slides:
            # Check slide type
            is_hero = self._is_hero_slide(slide)
            is_pyramid = self._is_pyramid_slide(slide)
            is_analytics = self._is_analytics_slide(slide)

            # v3.4-analytics: Analytics slides don't need variant_id (use Analytics Service)
            # v3.4-pyramid: Pyramid slides don't need variant_id (use Illustrator Service)
            # v3.4 FIX: Hero slides don't need variant_id (they use hero endpoints)
            # Only content slides require variant_id for /v1.2/generate endpoint
            if not is_hero and not is_pyramid and not is_analytics and not slide.variant_id:
                errors.append(
                    f"Slide {slide.slide_id} missing variant_id (required for content slides)"
                )

            if not slide.generated_title:
                errors.append(
                    f"Slide {slide.slide_id} missing generated_title (required for all slides)"
                )

        if errors:
            error_msg = "Slide validation failed:\n" + "\n".join(errors)
            logger.error(error_msg)
            raise ValueError(error_msg)

        logger.info("✅ All slides validated (generated_title present, variant_id present for content slides)")

    async def _route_sequential(
        self,
        slides: List[Slide],
        strawman: PresentationStrawman,
        session_id: str
    ) -> Dict[str, Any]:
        """
        Route slides sequentially to v1.2 endpoint.

        Args:
            slides: List of slides
            strawman: Full presentation context
            session_id: Session identifier

        Returns:
            Sequential routing result
        """
        logger.info(f"Using sequential mode for {len(slides)} slides")

        generated_slides = []
        failed_slides = []
        skipped_slides = []
        total_generation_time = 0

        for idx, slide in enumerate(slides):
            slide_number = idx + 1

            # v3.4 DIAGNOSTIC: Print slide processing start
            import sys
            print("="*80, flush=True)
            print(f"📝 PROCESSING SLIDE {slide_number}/{len(slides)}", flush=True)
            print(f"   Slide ID: {slide.slide_id}", flush=True)
            print(f"   Slide Type: {slide.slide_type_classification}", flush=True)
            print(f"   Variant ID: {slide.variant_id}", flush=True)
            print(f"   Generated Title: {slide.generated_title[:50]}...", flush=True)
            print("="*80, flush=True)
            sys.stdout.flush()

            try:
                # v3.4-analytics: Check if this is an analytics slide (BEFORE pyramid/hero check)
                is_analytics = self._is_analytics_slide(slide)

                if is_analytics:
                    # Generate analytics chart using Analytics Service
                    logger.info(
                        f"📊 Generating analytics slide {slide_number}/{len(slides)}: "
                        f"{slide.slide_id}"
                    )

                    # Check if Analytics client is available
                    if not self.analytics_client:
                        error_msg = "Analytics slide requires AnalyticsClient but none provided"
                        logger.error(error_msg)
                        print(f"   ❌ {error_msg}", flush=True)
                        sys.stdout.flush()
                        failed_slides.append({
                            "slide_number": slide_number,
                            "slide_id": slide.slide_id,
                            "slide_type": slide.slide_type_classification,
                            "error": error_msg,
                            # Tier 1 debugging: Service context
                            "service": "analytics_v3",
                            "endpoint": None,  # No endpoint reached (client missing)
                            "chart_type": getattr(slide, 'chart_id', None),
                            "layout": slide.layout_id,
                            "analytics_type": getattr(slide, 'analytics_type', None),
                            # Error classification
                            "error_category": "validation",
                            "suggested_action": "Ensure AnalyticsClient is properly initialized in ServiceRouter configuration.",
                            "http_status": None
                        })
                        continue

                    try:
                        # v3.8.0: Extract chart_type from slide.chart_id (REQUIRED for synthetic data)
                        chart_type = getattr(slide, 'chart_id', None)
                        if not chart_type:
                            logger.warning(f"Analytics slide {slide.slide_id} missing chart_id, defaulting to 'line'")
                            chart_type = "line"

                        # v3.4.4: Chart status updated based on Analytics Service v3.4.4 fixes
                        # ✅ FIXED in v3.4.4: bar_grouped, bar_stacked, area_stacked
                        # ❌ STILL BROKEN: mixed, d3_sunburst (wrong CDN plugin reference)
                        DISABLED_CHARTS = {
                            # "bar_grouped": "FIXED in v3.4.4 ✅",
                            # "bar_stacked": "FIXED in v3.4.4 ✅",
                            # "area_stacked": "FIXED in v3.4.4 ✅",
                            "mixed": "P0 - Wrong CDN plugin + rendering as line instead of mixed",
                            "d3_sunburst": "P0 - Wrong CDN plugin + rendering as bar instead of sunburst",
                            "d3_choropleth_usa": "P1 - Not implemented",
                            "d3_sankey": "P1 - Plugin not loaded"
                        }

                        if chart_type in DISABLED_CHARTS:
                            logger.warning(
                                f"Analytics slide {slide.slide_id}: chart_type '{chart_type}' is disabled "
                                f"({DISABLED_CHARTS[chart_type]}). Using fallback chart type 'line'."
                            )
                            chart_type = "line"

                        # Map chart_type to analytics_endpoint using chart_type_mappings
                        # This mapping is from config/analytics_variants.json
                        # v3.4.4: Re-enabled bar_grouped, bar_stacked, area_stacked (FIXED ✅)
                        chart_type_mappings = {
                            "line": "revenue_over_time",
                            "bar_vertical": "quarterly_comparison",
                            "bar_horizontal": "category_ranking",
                            "pie": "market_share",
                            "doughnut": "market_share",
                            "scatter": "correlation_analysis",
                            "bubble": "multidimensional_analysis",
                            "radar": "multi_metric_comparison",
                            "polar_area": "radial_composition",
                            "area": "revenue_over_time",
                            "bar_grouped": "quarterly_comparison",  # ✅ RE-ENABLED v3.4.4: Multi-series bug FIXED
                            "bar_stacked": "quarterly_comparison",  # ✅ RE-ENABLED v3.4.4: Multi-series bug FIXED
                            "area_stacked": "revenue_over_time",  # ✅ RE-ENABLED v3.4.4: Multi-series bug FIXED
                            # "mixed": "kpi_metrics",  # DISABLED: P0 - Wrong CDN plugin + renders as line
                            "d3_treemap": "market_share",
                            "d3_sunburst": "market_share"  # STILL BROKEN: P0 - Wrong CDN plugin (renders as bar)
                            # "d3_choropleth_usa": "market_share",  # DISABLED: P1 - Not implemented
                            # "d3_sankey": "market_share"  # DISABLED: P1 - Plugin not loaded
                        }
                        analytics_type = chart_type_mappings.get(chart_type, "revenue_over_time")

                        # Get layout from slide
                        layout = getattr(slide, 'layout_id', None) or "L02"

                        # v3.8.0: Data is now OPTIONAL - Analytics Service can generate synthetic data
                        data = getattr(slide, 'analytics_data', None)

                        # Determine data strategy
                        data_strategy = "director_data" if (data and len(data) > 0) else "synthetic_data"

                        # v3.4 DIAGNOSTIC: Print analytics generation details
                        print(f"   📊 CALLING ANALYTICS SERVICE /api/v1/analytics/{layout}/{analytics_type}", flush=True)
                        print(f"      Topic: {slide.generated_title}", flush=True)
                        print(f"      Chart Type: {chart_type} (v3.8.0)", flush=True)
                        print(f"      Analytics Type: {analytics_type}", flush=True)
                        print(f"      Layout: {layout}", flush=True)
                        print(f"      Data Strategy: {data_strategy}", flush=True)
                        print(f"      Data Points: {len(data) if data else 0} (will use synthetic if 0)", flush=True)
                        sys.stdout.flush()

                        # v3.8.0: Call Analytics Service with chart_type and optional data
                        start = datetime.utcnow()
                        analytics_response = await self.analytics_client.generate_chart(
                            analytics_type=analytics_type,
                            layout=layout,
                            chart_type=chart_type,  # v3.8.0: REQUIRED for synthetic data generation
                            narrative=slide.narrative or slide.generated_title,
                            context={
                                "presentation_title": strawman.main_title,
                                "tone": strawman.overall_theme or "professional",
                                "audience": strawman.target_audience or "general"
                            },
                            data=data if (data and len(data) > 0) else None,  # v3.8.0: OPTIONAL - None triggers synthetic
                            presentation_id=getattr(strawman, 'preview_presentation_id', None),
                            slide_id=slide.slide_id,
                            slide_number=slide_number
                        )
                        duration = (datetime.utcnow() - start).total_seconds()

                        # v3.4 DIAGNOSTIC: Print analytics response
                        print(f"   ✅ Analytics Service returned in {duration:.2f}s", flush=True)
                        content = analytics_response.get('content', {})
                        metadata = analytics_response.get('metadata', {})
                        synthetic_used = metadata.get('synthetic_data_used', False)
                        print(f"      Chart HTML length: {len(content.get('element_3', ''))} chars", flush=True)
                        print(f"      Observations length: {len(content.get('element_2', ''))} chars", flush=True)
                        print(f"      Synthetic Data Used: {synthetic_used} (v3.8.0)", flush=True)
                        sys.stdout.flush()
                        total_generation_time += duration

                        # Build successful result with 2-field response for L02
                        slide_result = {
                            "slide_number": slide_number,
                            "slide_id": slide.slide_id,
                            "content": content,  # Dict with element_3 and element_2 for L02
                            "metadata": {
                                **metadata,
                                "service": "analytics_v3",
                                "slide_type": "analytics",
                                "analytics_type": analytics_type,
                                "chart_type": chart_type,  # v3.8.0: Include chart_type
                                "layout": layout,
                                "data_strategy": data_strategy  # v3.8.0: Track data strategy
                            },
                            "generation_time_ms": int(duration * 1000),
                            "endpoint_used": f"/api/v1/analytics/{layout}/{analytics_type}",
                            "slide_type": "analytics"
                        }

                        generated_slides.append(slide_result)
                        logger.info(
                            f"✅ Analytics slide {slide_number} generated successfully",
                            extra={
                                "slide_id": slide.slide_id,
                                "analytics_type": analytics_type,
                                "chart_type": chart_type,  # v3.8.0: Include chart_type
                                "layout": layout,
                                "data_strategy": data_strategy,  # v3.8.0: Track data strategy
                                "synthetic_data_used": synthetic_used,  # v3.8.0: Track synthetic usage
                                "generation_time_seconds": duration
                            }
                        )
                        continue  # Skip rest of content slide processing

                    except Exception as e:
                        error_msg = f"Failed to generate analytics slide: {str(e)}"

                        # Tier 1: Classify error for debugging
                        error_info = self._classify_error(e, response=analytics_response if 'analytics_response' in locals() else None)

                        logger.error(
                            error_msg,
                            extra={
                                "slide_id": slide.slide_id,
                                "analytics_type": analytics_type,
                                "error": str(e),
                                "error_category": error_info["error_category"]
                            }
                        )
                        print(f"   ❌ Analytics generation failed: {str(e)}", flush=True)
                        print(f"      Error Category: {error_info['error_category']}", flush=True)
                        print(f"      Suggested Action: {error_info['suggested_action']}", flush=True)
                        sys.stdout.flush()

                        failed_slides.append({
                            "slide_number": slide_number,
                            "slide_id": slide.slide_id,
                            "slide_type": "analytics",
                            "error": error_msg,
                            # Tier 1 debugging: Service context
                            "service": "analytics_v3",
                            "endpoint": "/v3/generate-chart",  # Analytics Service endpoint
                            "chart_type": chart_type,
                            "layout": layout,
                            "analytics_type": analytics_type,
                            # Error classification
                            "error_type": error_info["error_type"],
                            "error_category": error_info["error_category"],
                            "suggested_action": error_info["suggested_action"],
                            "http_status": error_info["http_status"]
                        })
                        continue

                # v3.4-pyramid: Check if this is a pyramid slide (BEFORE hero check)
                is_pyramid = self._is_pyramid_slide(slide)

                if is_pyramid:
                    # Generate pyramid using Illustrator Service
                    logger.info(
                        f"🔺 Generating pyramid slide {slide_number}/{len(slides)}: "
                        f"{slide.slide_id}"
                    )

                    # Check if Illustrator client is available
                    if not self.illustrator_client:
                        error_msg = "Pyramid slide requires IllustratorClient but none provided"
                        logger.error(error_msg)
                        print(f"   ❌ {error_msg}", flush=True)
                        sys.stdout.flush()
                        failed_slides.append({
                            "slide_number": slide_number,
                            "slide_id": slide.slide_id,
                            "slide_type": slide.slide_type_classification,
                            "error": error_msg,
                            # Tier 1 debugging: Service context
                            "service": "illustrator_v1.0",
                            "endpoint": None,  # No endpoint reached (client missing)
                            # Error classification
                            "error_category": "validation",
                            "suggested_action": "Ensure IllustratorClient is properly initialized in ServiceRouter configuration.",
                            "http_status": None
                        })
                        continue

                    try:
                        # Build visualization_config from key_points
                        num_levels = len(slide.key_points) if slide.key_points else 4
                        target_points = slide.key_points if slide.key_points else None

                        # v3.4 DIAGNOSTIC: Print pyramid generation details
                        print(f"   🔺 CALLING ILLUSTRATOR SERVICE /v1.0/pyramid/generate", flush=True)
                        print(f"      Topic: {slide.generated_title}", flush=True)
                        print(f"      Num Levels: {num_levels}", flush=True)
                        print(f"      Target Points: {target_points}", flush=True)
                        sys.stdout.flush()

                        # Call Illustrator Service to generate pyramid
                        start = datetime.utcnow()
                        pyramid_response = await self.illustrator_client.generate_pyramid(
                            num_levels=num_levels,
                            topic=slide.generated_title,
                            target_points=target_points,
                            tone=strawman.overall_theme or "professional",
                            audience=strawman.target_audience or "general",
                            presentation_id=getattr(strawman, 'preview_presentation_id', None),
                            slide_id=slide.slide_id,
                            slide_number=slide_number,
                            validate_constraints=True  # Enable auto-retry on constraint violations
                        )
                        duration = (datetime.utcnow() - start).total_seconds()

                        # v3.4 DIAGNOSTIC: Print pyramid response
                        print(f"   ✅ Illustrator Service returned in {duration:.2f}s", flush=True)
                        print(f"      HTML length: {len(pyramid_response.get('html', ''))} chars", flush=True)
                        print(f"      Validation status: {pyramid_response.get('validation', {}).get('status', 'unknown')}", flush=True)
                        sys.stdout.flush()
                        total_generation_time += duration

                        # Build successful result
                        slide_result = {
                            "slide_number": slide_number,
                            "slide_id": slide.slide_id,
                            "content": pyramid_response["html"],  # HTML string directly
                            "metadata": {
                                "generated_content": pyramid_response.get("generated_content", {}),
                                "validation": pyramid_response.get("validation", {}),
                                "service": "illustrator_v1.0",
                                "slide_type": "pyramid"
                            },
                            "generation_time_ms": int(duration * 1000),
                            "endpoint_used": "/v1.0/pyramid/generate",
                            "slide_type": "pyramid"
                        }

                        generated_slides.append(slide_result)
                        logger.info(
                            f"✅ Pyramid slide {slide_number} generated successfully "
                            f"({duration:.2f}s)"
                        )

                    except Exception as pyramid_error:
                        # Tier 1: Classify error for debugging
                        error_info = self._classify_error(pyramid_error, response=pyramid_response if 'pyramid_response' in locals() else None)

                        # v3.4 DIAGNOSTIC: Print pyramid error details
                        print(f"   ❌ PYRAMID GENERATION FAILED", flush=True)
                        print(f"      Error Type: {type(pyramid_error).__name__}", flush=True)
                        print(f"      Error Message: {str(pyramid_error)}", flush=True)
                        print(f"      Error Category: {error_info['error_category']}", flush=True)
                        print(f"      Suggested Action: {error_info['suggested_action']}", flush=True)
                        sys.stdout.flush()

                        logger.error(
                            f"Pyramid slide generation failed: {pyramid_error}",
                            extra={
                                "slide_id": slide.slide_id,
                                "error_category": error_info["error_category"]
                            }
                        )

                        failed_slides.append({
                            "slide_number": slide_number,
                            "slide_id": slide.slide_id,
                            "slide_type": slide.slide_type_classification,
                            "error": str(pyramid_error),
                            # Service context
                            "service": "illustrator_v1.0",
                            "endpoint": "/v1.0/pyramid/generate",
                            # Error classification
                            "error_type": error_info["error_type"],
                            "error_category": error_info["error_category"],
                            "suggested_action": error_info["suggested_action"],
                            "http_status": error_info["http_status"]
                        })

                    continue  # Skip content slide processing

                # Check if this is a hero slide
                is_hero = self._is_hero_slide(slide)

                # v3.4 DIAGNOSTIC: Print hero detection result
                print(f"   Is Hero Slide: {is_hero} (type: {slide.slide_type_classification})", flush=True)
                sys.stdout.flush()

                if is_hero:
                    # NEW v3.4: Generate hero slides using hero endpoints
                    # v3.5: Enhanced logging with visual style information
                    logger.info(
                        f"🎬 Generating hero slide {slide_number}/{len(slides)}: "
                        f"{slide.slide_id} (type: {slide.slide_type_classification}) "
                        f"[use_image: {slide.use_image_background}, style: {slide.visual_style}]"
                    )

                    try:
                        # Transform to hero request
                        hero_request_data = self.hero_transformer.transform_to_hero_request(
                            slide, strawman
                        )

                        # v3.4 DIAGNOSTIC: Print hero endpoint call details
                        # v3.5: Include visual style information
                        print(f"   🎬 CALLING HERO ENDPOINT", flush=True)
                        print(f"      Endpoint: {hero_request_data['endpoint']}", flush=True)
                        print(f"      Use Image: {slide.use_image_background}", flush=True)
                        print(f"      Visual Style: {slide.visual_style}", flush=True)
                        print(f"      Payload keys: {list(hero_request_data['payload'].keys())}", flush=True)
                        sys.stdout.flush()

                        # Call hero endpoint
                        start = datetime.utcnow()
                        hero_response = await self.client.call_hero_endpoint(
                            endpoint=hero_request_data["endpoint"],
                            payload=hero_request_data["payload"]
                        )
                        duration = (datetime.utcnow() - start).total_seconds()

                        # v3.4 DIAGNOSTIC: Print hero response
                        print(f"   ✅ Hero endpoint returned in {duration:.2f}s", flush=True)
                        print(f"      Content length: {len(hero_response.get('content', ''))} chars", flush=True)
                        sys.stdout.flush()
                        total_generation_time += duration

                        # Build successful result
                        # v3.4 fix: Use flat structure like content slides for consistency
                        slide_result = {
                            "slide_number": slide_number,
                            "slide_id": slide.slide_id,
                            "content": hero_response["content"],  # HTML string directly
                            "metadata": hero_response["metadata"],  # Top-level metadata
                            "generation_time_ms": int(duration * 1000),
                            "endpoint_used": hero_request_data["endpoint"],
                            "slide_type": "hero"
                        }

                        generated_slides.append(slide_result)
                        logger.info(
                            f"✅ Hero slide {slide_number} generated successfully "
                            f"({duration:.2f}s)"
                        )

                    except Exception as hero_error:
                        # Tier 1: Classify error for debugging
                        error_info = self._classify_error(hero_error, response=hero_response if 'hero_response' in locals() else None)

                        # v3.4 DIAGNOSTIC: Print hero error details
                        print(f"   ❌ HERO ENDPOINT FAILED", flush=True)
                        print(f"      Error Type: {type(hero_error).__name__}", flush=True)
                        print(f"      Error Message: {str(hero_error)}", flush=True)
                        print(f"      Endpoint: {hero_request_data.get('endpoint', 'unknown')}", flush=True)
                        print(f"      Error Category: {error_info['error_category']}", flush=True)
                        print(f"      Suggested Action: {error_info['suggested_action']}", flush=True)
                        sys.stdout.flush()

                        logger.error(
                            f"Hero slide generation failed: {hero_error}",
                            extra={
                                "slide_id": slide.slide_id,
                                "endpoint": hero_request_data.get("endpoint", "unknown"),
                                "error_category": error_info["error_category"]
                            }
                        )

                        failed_slides.append({
                            "slide_number": slide_number,
                            "slide_id": slide.slide_id,
                            "slide_type": slide.slide_type_classification,
                            "error": str(hero_error),
                            # Service context
                            "service": "text_service_v1.2",
                            "endpoint": hero_request_data.get("endpoint", "unknown"),
                            # Error classification
                            "error_type": error_info["error_type"],
                            "error_category": error_info["error_category"],
                            "suggested_action": error_info["suggested_action"],
                            "http_status": error_info["http_status"]
                        })

                    continue  # Skip content slide processing

                logger.info(
                    f"Generating slide {slide_number}/{len(slides)}: "
                    f"{slide.slide_id} (variant: {slide.variant_id})"
                )

                # Build v1.2 request
                request = self._build_slide_request(
                    slide=slide,
                    strawman=strawman,
                    slide_number=slide_number,
                    slides=slides,
                    current_index=idx
                )

                # v3.4 DIAGNOSTIC: Print content slide HTTP call details
                print(f"   🌐 CALLING TEXT SERVICE /v1.2/generate", flush=True)
                print(f"      Request keys: {list(request.keys())}", flush=True)
                print(f"      Variant ID: {request.get('variant_id')}", flush=True)
                sys.stdout.flush()

                # Call v1.2 generate endpoint
                start = datetime.utcnow()
                generated = await self.client.generate(request)
                duration = (datetime.utcnow() - start).total_seconds()

                # v3.4 DIAGNOSTIC: Print HTTP response
                print(f"   ✅ Text Service returned in {duration:.2f}s", flush=True)
                print(f"      Content length: {len(generated.content) if hasattr(generated, 'content') else 'N/A'} chars", flush=True)
                sys.stdout.flush()

                total_generation_time += duration

                # Build result entry
                slide_result = {
                    "slide_number": slide_number,
                    "slide_id": slide.slide_id,
                    "variant_id": slide.variant_id,
                    "content": generated.content,  # HTML string
                    "metadata": generated.metadata,
                    "generation_time_seconds": round(duration, 2)
                }

                generated_slides.append(slide_result)
                logger.info(f"✅ Slide {slide_number} generated successfully ({duration:.2f}s)")

            except Exception as e:
                # Tier 1: Classify error for debugging
                error_info = self._classify_error(e, response=generated if 'generated' in locals() else None)

                # v3.4 DIAGNOSTIC: Print content slide error details
                print(f"   ❌ CONTENT SLIDE GENERATION FAILED", flush=True)
                print(f"      Error Type: {type(e).__name__}", flush=True)
                print(f"      Error Message: {str(e)}", flush=True)
                print(f"      Variant ID: {slide.variant_id}", flush=True)
                print(f"      Error Category: {error_info['error_category']}", flush=True)
                print(f"      Suggested Action: {error_info['suggested_action']}", flush=True)
                import traceback
                print(f"      Traceback: {traceback.format_exc()}", flush=True)
                sys.stdout.flush()

                logger.error(
                    f"❌ Slide {slide_number} generation failed: {e}",
                    extra={
                        "slide_id": slide.slide_id,
                        "variant_id": slide.variant_id,
                        "error_category": error_info["error_category"]
                    }
                )

                failed_slides.append({
                    "slide_number": slide_number,
                    "slide_id": slide.slide_id,
                    "variant_id": slide.variant_id,
                    "error": str(e),
                    # Tier 1 debugging: Service context
                    "service": "text_service_v1.2",
                    "endpoint": "/v1.2/generate",  # Content slide endpoint
                    "slide_type": slide.slide_type_classification,
                    "layout": slide.layout_id,
                    # Error classification
                    "error_type": error_info["error_type"],
                    "error_category": error_info["error_category"],
                    "suggested_action": error_info["suggested_action"],
                    "http_status": error_info["http_status"]
                })

        metadata = {
            "processing_mode": "sequential",
            "successful_count": len(generated_slides),
            "failed_count": len(failed_slides),
            "skipped_count": len(skipped_slides),
            "sequential_time_seconds": round(total_generation_time, 2),
            "avg_time_per_slide_seconds": (
                round(total_generation_time / len(generated_slides), 2)
                if generated_slides else 0
            )
        }

        # Tier 2: Generate comprehensive error summary for debugging
        error_summary = self._generate_error_summary(failed_slides)

        # Print error summary to Railway logs for customer support
        if error_summary["total_failures"] > 0:
            print("\n" + "="*80, flush=True)
            print("📊 ERROR SUMMARY (Tier 2 Debugging)", flush=True)
            print("="*80, flush=True)
            print(f"Total Failures: {error_summary['total_failures']}", flush=True)
            print(f"\nBy Category:", flush=True)
            for category, count in error_summary["by_category"].items():
                print(f"  • {category}: {count}", flush=True)
            print(f"\nBy Service:", flush=True)
            for service, count in error_summary["by_service"].items():
                print(f"  • {service}: {count}", flush=True)
            if error_summary["by_endpoint"]:
                print(f"\nBy Endpoint:", flush=True)
                for endpoint, count in error_summary["by_endpoint"].items():
                    print(f"  • {endpoint}: {count}", flush=True)
            if error_summary["critical_issues"]:
                print(f"\n🚨 Critical Issues:", flush=True)
                for issue in error_summary["critical_issues"]:
                    print(f"  [{issue['severity'].upper()}] {issue['issue']} ({issue['count']} slides)", flush=True)
                    print(f"    Impact: {issue['impact']}", flush=True)
                    print(f"    Action: {issue['action']}", flush=True)
            if error_summary["recommended_actions"]:
                print(f"\n💡 Recommended Actions (Priority Order):", flush=True)
                for action in error_summary["recommended_actions"]:
                    print(f"  {action['priority']}. {action['action']}", flush=True)
                    print(f"     Rationale: {action['rationale']}", flush=True)
            print("="*80 + "\n", flush=True)
            sys.stdout.flush()

        return {
            "generated_slides": generated_slides,
            "failed_slides": failed_slides,
            "skipped_slides": skipped_slides,
            "metadata": metadata,
            "error_summary": error_summary  # Tier 2: Include error summary for debugging
        }

    def _is_hero_slide(self, slide: Slide) -> bool:
        """
        Check if slide is a hero slide (title, section divider, or closing).

        Hero slides only need generated_title and generated_subtitle,
        not rich HTML content generation.

        Args:
            slide: Slide to check

        Returns:
            True if hero slide, False otherwise
        """
        hero_types = {'title_slide', 'section_divider', 'closing_slide'}
        return slide.slide_type_classification in hero_types

    def _is_pyramid_slide(self, slide: Slide) -> bool:
        """
        Check if slide is a pyramid visualization slide.

        Pyramid slides are generated by Illustrator Service v1.0,
        not Text Service v1.2.

        Args:
            slide: Slide to check

        Returns:
            True if pyramid slide, False otherwise
        """
        return slide.slide_type_classification == 'pyramid'

    def _is_analytics_slide(self, slide: Slide) -> bool:
        """
        Check if slide is an analytics/chart visualization slide.

        Analytics slides are generated by Analytics Service v3,
        not Text Service v1.2.

        CRITICAL v3.4.2: Analytics Service currently only works with L02 layout.
        L01 and L03 are planned for future but not yet configured.
        All other layouts MUST be routed to Text Service.

        Args:
            slide: Slide to check

        Returns:
            True if analytics slide with L02 layout, False otherwise
        """
        # Must have analytics classification
        if slide.slide_type_classification != 'analytics':
            return False

        # v3.4.2 Guard: Analytics Service currently only works with L02 layout
        if hasattr(slide, 'layout_id') and slide.layout_id != 'L02':
            logger.warning(
                f"Analytics slide {getattr(slide, 'slide_id', 'unknown')} has layout "
                f"'{slide.layout_id}' but Analytics requires L02. "
                f"Routing to Text Service instead."
            )
            return False

        return True

    def _build_slide_request(
        self,
        slide: Slide,
        strawman: PresentationStrawman,
        slide_number: int,
        slides: List[Slide],
        current_index: int
    ) -> Dict[str, Any]:
        """
        Build v1.2 generation request for a slide.

        Args:
            slide: Slide to build request for
            strawman: Full presentation for context
            slide_number: Slide position (1-indexed)
            slides: All slides (for prior context)
            current_index: Current slide index (0-indexed)

        Returns:
            V1_2_GenerationRequest dict
        """
        # Build prior slides summary for narrative flow
        prior_summary = V1_2_Transformer.build_prior_slides_summary(
            slides=slides,
            current_index=current_index
        )

        # Transform using V1_2_Transformer
        request = V1_2_Transformer.transform_slide_to_v1_2_request(
            slide=slide,
            strawman=strawman,
            slide_number=slide_number,
            prior_slides_summary=prior_summary
        )

        return request


# Convenience function
async def route_presentation_to_v1_2(
    strawman: PresentationStrawman,
    text_service_url: str,
    session_id: str
) -> Dict[str, Any]:
    """
    Route presentation slides to Text Service v1.2 (convenience function).

    Args:
        strawman: PresentationStrawman with variant_id and generated titles
        text_service_url: Text Service v1.2 base URL
        session_id: Session identifier

    Returns:
        Routing result dict
    """
    # Create v1.2 client
    client = TextServiceClientV1_2(text_service_url)

    # Create router
    router = ServiceRouterV1_2(client)

    # Route presentation
    result = await router.route_presentation(strawman, session_id)

    return result


# Example usage
if __name__ == "__main__":
    from src.models.agents import Slide, PresentationStrawman, ContentGuidance

    async def test_router():
        print("Service Router v1.2 Test")
        print("=" * 70)

        # Create sample presentation
        strawman = PresentationStrawman(
            main_title="Q4 Business Review",
            overall_theme="Informative and data-driven",
            slides=[],
            design_suggestions="Modern professional",
            target_audience="Executive team",
            presentation_duration=30,
            footer_text="Q4 2024"
        )

        # Create sample slides
        slides = [
            Slide(
                slide_number=1,
                slide_id="slide_001",
                title="Opening Slide",
                slide_type="title_slide",
                slide_type_classification="title_slide",
                layout_id="L29",
                variant_id="hero_opening_centered",  # v1.2 hero variant
                generated_title="Q4 Business Review",
                generated_subtitle="Strategic Overview",
                narrative="Welcome to our quarterly review",
                key_points=["Review", "Results", "Next Steps"]
            ),
            Slide(
                slide_number=2,
                slide_id="slide_002",
                title="Strategic Pillars",
                slide_type="content_heavy",
                slide_type_classification="matrix_2x2",
                layout_id="L25",
                variant_id="matrix_2x3",  # Random v1.2 variant
                generated_title="Our Strategic Pillars",
                generated_subtitle="Building blocks for success",
                narrative="Four key pillars drive our strategy",
                key_points=["Customer", "Innovation", "Excellence", "Growth"],
                content_guidance=ContentGuidance(
                    content_type="framework",
                    visual_complexity="moderate",
                    content_density="balanced",
                    tone_indicator="professional",
                    generation_instructions="Emphasize strategic importance",
                    pattern_rationale="Matrix shows equal weight"
                )
            )
        ]

        strawman.slides = slides

        # Create client and router
        print("\nInitializing v1.2 client and router...")
        client = TextServiceClientV1_2()
        router = ServiceRouterV1_2(client)

        # Test health check
        print("\nHealth check:")
        healthy = await client.health_check()
        print(f"  Service healthy: {healthy}")

        if healthy:
            # Test routing (this will make real API calls if service is up)
            print("\nRouting presentation (this will call v1.2 API):")
            try:
                result = await router.route_presentation(strawman, "test_session_123")

                print(f"\n✅ Routing complete:")
                print(f"  Successful: {result['metadata']['successful_count']}")
                print(f"  Failed: {result['metadata']['failed_count']}")
                print(f"  Total time: {result['metadata']['total_processing_time_seconds']}s")

                for slide_result in result['generated_slides']:
                    print(f"\n  Slide {slide_result['slide_number']} ({slide_result['variant_id']}):")
                    print(f"    Content length: {len(slide_result['content'])} chars")
                    print(f"    Generation time: {slide_result['generation_time_seconds']}s")

            except Exception as e:
                print(f"  ❌ Routing failed: {e}")
        else:
            print("  ⚠️  Service not healthy, skipping routing test")

        print("\n" + "=" * 70)
        print("Test complete!")

    asyncio.run(test_router())
