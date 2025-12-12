"""
Director Integration Layer for Unified Variant System

Provides backward-compatible integration between Director Agent and the
unified variant registration system. Allows Director to use registry-driven
classification and routing while maintaining existing interfaces.

Version: 2.0.0
Created: 2025-11-29
"""

from typing import Dict, Any, Optional, List
from src.models.agents import Slide, PresentationStrawman
from src.services.registry_loader import get_registry
from src.services.unified_slide_classifier import UnifiedSlideClassifier, ClassificationMatch
from src.services.unified_service_router import UnifiedServiceRouter
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class DirectorIntegrationLayer:
    """
    Integration layer for Director Agent unified system integration.

    Provides methods for:
    - Slide classification using unified classifier
    - Content generation routing using unified router
    - Backward compatibility with existing Director interfaces

    Features:
    - Registry-driven slide classification
    - Multi-service routing (Text, Illustrator, Analytics)
    - Automatic variant selection based on classification
    - Error handling and fallbacks
    - Prior slides context support
    - Comprehensive logging

    Usage (in Director Agent):
        # Initialize once
        integration = DirectorIntegrationLayer()

        # Classify slides (Stage 4)
        classified_slide = integration.classify_slide(
            title=slide.title,
            key_points=slide.key_points,
            description=slide.description
        )

        # Generate content (Stage 6)
        result = await integration.generate_slide_content(
            slide=classified_slide,
            presentation_title=strawman.main_title,
            prior_slides=prior_slides
        )
    """

    def __init__(self):
        """
        Initialize Director integration layer.

        Loads registry and creates classifier and router instances.
        """
        # Load registry
        self.registry = get_registry()

        # Initialize classifier and router
        self.classifier = UnifiedSlideClassifier(self.registry)
        self.router = UnifiedServiceRouter(self.registry)

        logger.info(
            "DirectorIntegrationLayer initialized",
            extra={
                "total_services": len(self.registry.services),
                "total_variants": sum(
                    len(s.variants) for s in self.registry.services.values()
                )
            }
        )

    def classify_slide(
        self,
        title: Optional[str] = None,
        key_points: Optional[List[str]] = None,
        description: Optional[str] = None,
        context: Optional[str] = None,
        min_confidence: float = 0.1,
        max_results: int = 5
    ) -> Dict[str, Any]:
        """
        Classify slide using unified classifier.

        Returns classification results with matched variants.

        Args:
            title: Slide title
            key_points: List of key points
            description: Slide description
            context: Additional context
            min_confidence: Minimum confidence threshold
            max_results: Maximum classification results

        Returns:
            Dict with:
                - matches: List of ClassificationMatch objects
                - best_match: Top classification match (or None)
                - variant_id: Best variant ID (or None)
                - service_name: Service for best variant (or None)
                - confidence: Best match confidence (or 0.0)

        Example:
            result = integration.classify_slide(
                title="Market Share Analysis",
                key_points=["Product A: 45%", "Product B: 30%"],
                description="Q4 revenue distribution"
            )

            if result["best_match"]:
                print(f"Classified as: {result['variant_id']}")
                print(f"Confidence: {result['confidence']:.2%}")
        """
        matches = self.classifier.classify_slide(
            title=title,
            key_points=key_points,
            context=context or description,
            min_confidence=min_confidence,
            max_results=max_results
        )

        best_match = matches[0] if matches else None

        result = {
            "matches": matches,
            "best_match": best_match,
            "variant_id": best_match.variant_id if best_match else None,
            "service_name": best_match.service_name if best_match else None,
            "confidence": best_match.confidence if best_match else 0.0
        }

        if best_match:
            logger.info(
                f"Slide classified",
                extra={
                    "variant_id": best_match.variant_id,
                    "service_name": best_match.service_name,
                    "confidence": f"{best_match.confidence:.2%}",
                    "match_score": best_match.match_score
                }
            )
        else:
            logger.warning(
                f"No classification match found",
                extra={"min_confidence": min_confidence}
            )

        return result

    async def generate_slide_content(
        self,
        variant_id: str,
        service_name: str,
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate content for slide using unified router.

        Args:
            variant_id: Variant identifier (from classification)
            service_name: Service name (from classification)
            parameters: Variant-specific parameters
            context: Optional context (presentation_title, prior_slides, etc.)

        Returns:
            Dict with:
                - success: bool
                - html_content or chart_html: Generated content (if successful)
                - variant_id: str
                - service_name: str
                - error: str (if failed)
                - error_type: str (if failed)

        Example:
            result = await integration.generate_slide_content(
                variant_id="pie_chart",
                service_name="analytics_service_v3",
                parameters={
                    "data": [
                        {"label": "A", "value": 45},
                        {"label": "B", "value": 30}
                    ]
                },
                context={
                    "presentation_title": "Q4 Review",
                    "tone": "professional"
                }
            )

            if result["success"]:
                chart_html = result.get("chart_html")
            else:
                error = result["error"]
        """
        result = await self.router.generate_content(
            variant_id=variant_id,
            service_name=service_name,
            parameters=parameters,
            context=context
        )

        if result["success"]:
            logger.info(
                f"Content generated successfully",
                extra={
                    "variant_id": variant_id,
                    "service_name": service_name,
                    "has_content": "html_content" in result or "chart_html" in result
                }
            )
        else:
            logger.error(
                f"Content generation failed",
                extra={
                    "variant_id": variant_id,
                    "service_name": service_name,
                    "error": result.get("error"),
                    "error_type": result.get("error_type")
                }
            )

        return result

    def classify_and_enrich_slide(
        self,
        slide: Slide,
        presentation_context: Optional[str] = None
    ) -> Slide:
        """
        Classify slide and enrich with classification data.

        Updates slide with:
        - slide_type_classification (best variant_id)
        - variant_id (best variant_id)
        - service_name (service providing the variant)
        - classification_confidence (match confidence)

        Args:
            slide: Slide object to classify
            presentation_context: Optional presentation context

        Returns:
            Enriched Slide object with classification data

        Example:
            enriched_slide = integration.classify_and_enrich_slide(
                slide=slide,
                presentation_context="Q4 Business Review"
            )

            print(f"Slide classified as: {enriched_slide.variant_id}")
            print(f"Will use service: {enriched_slide.service_name}")
        """
        # Classify slide
        result = self.classify_slide(
            title=slide.title,
            key_points=slide.key_points if hasattr(slide, 'key_points') else None,
            description=slide.description if hasattr(slide, 'description') else None,
            context=presentation_context
        )

        # Enrich slide with classification
        if result["best_match"]:
            slide.slide_type_classification = result["variant_id"]
            slide.variant_id = result["variant_id"]

            # Add service_name if not already present
            if not hasattr(slide, 'service_name'):
                slide.service_name = result["service_name"]
            else:
                slide.service_name = result["service_name"]

            # Add confidence if not already present
            if not hasattr(slide, 'classification_confidence'):
                slide.classification_confidence = result["confidence"]
            else:
                slide.classification_confidence = result["confidence"]

            logger.debug(
                f"Slide enriched with classification",
                extra={
                    "slide_id": slide.slide_id if hasattr(slide, 'slide_id') else "unknown",
                    "variant_id": slide.variant_id,
                    "service_name": slide.service_name,
                    "confidence": f"{result['confidence']:.2%}"
                }
            )
        else:
            logger.warning(
                f"Slide could not be classified",
                extra={"slide_id": slide.slide_id if hasattr(slide, 'slide_id') else "unknown"}
            )

        return slide

    async def generate_presentation_content(
        self,
        strawman: PresentationStrawman,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate content for entire presentation.

        Processes all slides in strawman, generating content for each.
        Compatible with Director Stage 6 (CONTENT_GENERATION).

        Args:
            strawman: PresentationStrawman with classified slides
            session_id: Optional session ID for tracking

        Returns:
            Dict with:
                - generated_slides: List of generated slide content
                - failed_slides: List of failed generations
                - skipped_slides: List of skipped slides
                - metadata: Generation metadata

        Example:
            result = await integration.generate_presentation_content(
                strawman=strawman,
                session_id="session_123"
            )

            print(f"Generated: {len(result['generated_slides'])} slides")
            print(f"Failed: {len(result['failed_slides'])} slides")
        """
        generated_slides = []
        failed_slides = []
        skipped_slides = []

        presentation_title = strawman.main_title if hasattr(strawman, 'main_title') else None
        prior_slides = []

        for idx, slide in enumerate(strawman.slides):
            slide_id = slide.slide_id if hasattr(slide, 'slide_id') else f"slide_{idx+1}"

            # Check if slide has classification
            if not hasattr(slide, 'variant_id') or not slide.variant_id:
                logger.warning(f"Slide {slide_id} missing variant_id, skipping")
                skipped_slides.append({
                    "slide_id": slide_id,
                    "reason": "missing_classification"
                })
                continue

            if not hasattr(slide, 'service_name') or not slide.service_name:
                logger.warning(f"Slide {slide_id} missing service_name, skipping")
                skipped_slides.append({
                    "slide_id": slide_id,
                    "reason": "missing_service_name"
                })
                continue

            # Build parameters from slide
            parameters = self._build_parameters_from_slide(slide)

            # Build context
            context = {
                "presentation_title": presentation_title,
                "prior_slides": prior_slides[:5] if prior_slides else None  # Last 5 slides
            }

            # Add tone and audience if available
            if hasattr(strawman, 'tone'):
                context["tone"] = strawman.tone
            if hasattr(strawman, 'target_audience'):
                context["audience"] = strawman.target_audience

            # Generate content
            try:
                result = await self.generate_slide_content(
                    variant_id=slide.variant_id,
                    service_name=slide.service_name,
                    parameters=parameters,
                    context=context
                )

                if result["success"]:
                    generated_slides.append({
                        "slide_id": slide_id,
                        **result
                    })

                    # Add to prior slides for context
                    prior_slides.append({
                        "slide_id": slide_id,
                        "title": slide.title,
                        "variant_id": slide.variant_id
                    })
                else:
                    failed_slides.append({
                        "slide_id": slide_id,
                        "variant_id": slide.variant_id,
                        "error": result.get("error"),
                        "error_type": result.get("error_type")
                    })

            except Exception as e:
                logger.error(
                    f"Unexpected error generating content for slide {slide_id}",
                    extra={"error": str(e)},
                    exc_info=True
                )
                failed_slides.append({
                    "slide_id": slide_id,
                    "variant_id": slide.variant_id,
                    "error": str(e),
                    "error_type": "exception"
                })

        metadata = {
            "total_slides": len(strawman.slides),
            "successful_count": len(generated_slides),
            "failed_count": len(failed_slides),
            "skipped_count": len(skipped_slides),
            "session_id": session_id
        }

        logger.info(
            f"Presentation content generation complete",
            extra=metadata
        )

        return {
            "generated_slides": generated_slides,
            "failed_slides": failed_slides,
            "skipped_slides": skipped_slides,
            "metadata": metadata
        }

    def _build_parameters_from_slide(self, slide: Slide) -> Dict[str, Any]:
        """
        Build request parameters from slide attributes.

        Extracts relevant fields from slide based on variant type.

        Args:
            slide: Slide object

        Returns:
            Dict with variant-specific parameters
        """
        parameters = {}

        # Common fields
        if hasattr(slide, 'title') and slide.title:
            parameters["title"] = slide.title

        if hasattr(slide, 'key_points') and slide.key_points:
            parameters["key_points"] = slide.key_points

        if hasattr(slide, 'description') and slide.description:
            parameters["description"] = slide.description

        # Variant-specific fields
        if hasattr(slide, 'variant_id'):
            variant_id = slide.variant_id

            # Add variant_id for request
            parameters["variant_id"] = variant_id

            # Chart data (for analytics variants)
            if hasattr(slide, 'chart_data') and slide.chart_data:
                parameters["data"] = slide.chart_data

            # Topic (for illustrator variants)
            if hasattr(slide, 'topic') and slide.topic:
                parameters["topic"] = slide.topic

            # Target points (for illustrator variants)
            if hasattr(slide, 'target_points') and slide.target_points:
                parameters["target_points"] = slide.target_points

            # Narrative (for analytics variants)
            if hasattr(slide, 'narrative') and slide.narrative:
                parameters["narrative"] = slide.narrative

        return parameters

    def get_variant_info(self, variant_id: str, service_name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific variant.

        Args:
            variant_id: Variant identifier
            service_name: Service name

        Returns:
            Dict with variant info or None

        Example:
            info = integration.get_variant_info("pie_chart", "analytics_service_v3")
            print(f"Variant: {info['display_name']}")
            print(f"Status: {info['status']}")
        """
        return self.router.get_variant_info(variant_id, service_name)

    def list_all_variants(self) -> List[Dict[str, Any]]:
        """
        List all available variants.

        Returns:
            List of variant info dicts sorted by priority

        Example:
            variants = integration.list_all_variants()
            for variant in variants[:10]:  # Top 10 by priority
                print(f"{variant['variant_id']}: {variant['display_name']}")
        """
        return self.router.list_all_variants()

    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the unified system.

        Returns:
            Dict with comprehensive statistics

        Example:
            stats = integration.get_stats()
            print(f"Total services: {stats['service_stats']['total_services']}")
            print(f"Total variants: {stats['service_stats']['total_variants']}")
            print(f"Unique keywords: {stats['classification_stats']['unique_keywords']}")
        """
        return {
            "service_stats": self.router.get_service_stats(),
            "classification_stats": self.classifier.get_classification_stats(),
            "registry_info": {
                "version": self.registry.version,
                "last_updated": self.registry.last_updated,
                "total_services": len(self.registry.services),
                "total_variants": sum(
                    len(s.variants) for s in self.registry.services.values()
                )
            }
        }
