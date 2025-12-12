"""
Service Router for Director v3.4
=================================

Routes slides to specialized Text Service v1.1 endpoints based on classification.
Supports both individual and batch processing modes.
"""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
from src.models.agents import Slide, PresentationStrawman
from src.utils.logger import setup_logger
from src.utils.service_interface import TextServiceInterface
from src.utils.service_registry import ServiceRegistry

logger = setup_logger(__name__)


class ServiceRouter:
    """
    Routes slides to specialized Text Service v1.1 endpoints.

    Features:
    - Automatic routing based on slide_type_classification
    - Batch mode for parallel processing (default)
    - Individual mode for sequential processing (fallback)
    - Comprehensive error handling and reporting
    - Processing statistics and metadata
    """

    def __init__(self, text_service_client: TextServiceInterface):
        """
        Initialize service router.

        Args:
            text_service_client: TextServiceInterface instance
        """
        self.client = text_service_client
        self.use_batch_mode = True  # Default to batch for better performance
        logger.info("ServiceRouter initialized")

    def set_processing_mode(self, use_batch: bool):
        """
        Set processing mode (batch vs individual).

        Args:
            use_batch: True for batch mode, False for individual
        """
        mode = "batch" if use_batch else "individual"
        logger.info(f"Processing mode set to: {mode}")
        self.use_batch_mode = use_batch

    async def route_presentation(
        self,
        strawman: PresentationStrawman,
        session_id: str
    ) -> Dict[str, Any]:
        """
        Route all slides in presentation to appropriate Text Service endpoints.

        Args:
            strawman: PresentationStrawman with classified slides
            session_id: Session identifier for tracking

        Returns:
            Routing result dict with:
            - generated_slides: List of successfully generated slide content
            - failed_slides: List of failed slides with error details
            - metadata: Processing statistics

        Raises:
            ValueError: If slides are not classified
        """
        start_time = datetime.utcnow()
        slides = strawman.slides

        logger.info(
            f"Starting presentation routing: {len(slides)} slides "
            f"(mode={'batch' if self.use_batch_mode else 'individual'})"
        )

        # Validate all slides have classification
        unclassified = [
            s for s in slides if not s.slide_type_classification
        ]
        if unclassified:
            raise ValueError(
                f"{len(unclassified)} slides are missing slide_type_classification. "
                f"Ensure SlideTypeClassifier ran in GENERATE_STRAWMAN stage."
            )

        # Validate slide types against registry
        slide_types = [s.slide_type_classification for s in slides]
        validation = ServiceRegistry.validate_slide_types(slide_types)
        if not validation["valid"]:
            logger.error(f"Invalid slide types detected: {validation['invalid_types']}")
            raise ValueError(
                f"Invalid slide_type_classification found: {validation['invalid_types']}"
            )

        logger.info("✅ All slides have valid classifications")

        # Route based on processing mode
        if self.use_batch_mode:
            result = await self._route_batch(slides, strawman, session_id)
        else:
            result = await self._route_individual(slides, strawman, session_id)

        # Calculate total processing time
        total_time = (datetime.utcnow() - start_time).total_seconds()
        result["metadata"]["total_processing_time_seconds"] = round(total_time, 2)

        logger.info(
            f"✅ Routing complete: {result['metadata']['successful_count']}/{len(slides)} successful "
            f"in {total_time:.2f}s"
        )

        return result

    async def _route_batch(
        self,
        slides: List[Slide],
        strawman: PresentationStrawman,
        session_id: str
    ) -> Dict[str, Any]:
        """
        Route slides using batch endpoint for parallel processing.

        Args:
            slides: List of classified slides
            strawman: Full presentation context
            session_id: Session identifier

        Returns:
            Batch routing result
        """
        logger.info(f"Using batch mode for {len(slides)} slides")

        # Build batch request payloads
        batch_requests = []
        for idx, slide in enumerate(slides):
            request = self._build_slide_request(
                slide=slide,
                strawman=strawman,
                slide_number=idx + 1
            )
            batch_requests.append(request)

        # Call batch endpoint
        try:
            batch_result = await self.client.generate_batch(batch_requests)

            # Parse batch result
            generated_slides = batch_result.get("results", [])
            failed_slides = batch_result.get("errors", [])
            batch_metadata = batch_result.get("metadata", {})

            metadata = {
                "processing_mode": "batch",
                "successful_count": len(generated_slides),
                "failed_count": len(failed_slides),
                "batch_time_seconds": batch_metadata.get("batch_time_seconds", 0),
                "avg_time_per_slide": batch_metadata.get("avg_time_per_slide_seconds", 0),
                "token_usage": batch_metadata.get("token_usage", {}),
                "parallel_efficiency": batch_metadata.get("parallel_efficiency", {})
            }

            return {
                "generated_slides": generated_slides,
                "failed_slides": failed_slides if failed_slides else [],
                "metadata": metadata
            }

        except Exception as e:
            logger.error(f"Batch processing failed: {e}")
            logger.info("Falling back to individual processing mode")

            # Fallback to individual mode
            return await self._route_individual(slides, strawman, session_id)

    async def _route_individual(
        self,
        slides: List[Slide],
        strawman: PresentationStrawman,
        session_id: str
    ) -> Dict[str, Any]:
        """
        Route slides individually (sequential processing).

        Args:
            slides: List of classified slides
            strawman: Full presentation context
            session_id: Session identifier

        Returns:
            Individual routing result
        """
        logger.info(f"Using individual mode for {len(slides)} slides")

        generated_slides = []
        failed_slides = []
        total_tokens = 0
        total_generation_time = 0

        for idx, slide in enumerate(slides):
            slide_number = idx + 1
            try:
                logger.info(
                    f"Generating slide {slide_number}/{len(slides)}: "
                    f"{slide.slide_id} ({slide.slide_type_classification})"
                )

                # Build request
                request = self._build_slide_request(
                    slide=slide,
                    strawman=strawman,
                    slide_number=slide_number
                )

                # Call specialized endpoint
                generated = await self.client.generate_specialized(
                    slide_type_classification=slide.slide_type_classification,
                    request_payload=request
                )

                # Track metadata
                metadata = generated.get("metadata", {})
                total_tokens += metadata.get("total_tokens", 0)
                total_generation_time += metadata.get("generation_time_ms", 0) / 1000

                generated_slides.append(generated)
                logger.info(f"✅ Slide {slide_number} generated successfully")

            except Exception as e:
                logger.error(f"❌ Slide {slide_number} generation failed: {e}")
                failed_slides.append({
                    "slide_number": slide_number,
                    "slide_id": slide.slide_id,
                    "slide_type": slide.slide_type_classification,
                    "error": str(e)
                })

        metadata = {
            "processing_mode": "individual",
            "successful_count": len(generated_slides),
            "failed_count": len(failed_slides),
            "total_tokens": total_tokens,
            "avg_tokens_per_slide": round(total_tokens / len(generated_slides), 1) if generated_slides else 0,
            "sequential_time_seconds": round(total_generation_time, 2)
        }

        return {
            "generated_slides": generated_slides,
            "failed_slides": failed_slides,
            "metadata": metadata
        }

    def _build_slide_request(
        self,
        slide: Slide,
        strawman: PresentationStrawman,
        slide_number: int
    ) -> Dict[str, Any]:
        """
        Build TextGenerationRequest payload for a slide.

        Args:
            slide: Slide with classification and content guidance
            strawman: Full presentation for context
            slide_number: Slide position (1-indexed)

        Returns:
            TextGenerationRequest dict
        """
        # Build context with classification and guidance
        context = {
            "slide_type": slide.slide_type_classification,
            "slide_title": slide.title,
            "layout_id": slide.layout_id,
            "presentation_context": {
                "main_title": strawman.main_title,
                "overall_theme": strawman.overall_theme,
                "target_audience": strawman.target_audience
            }
        }

        # Add content guidance if available
        if slide.content_guidance:
            context["content_guidance"] = {
                "content_type": slide.content_guidance.content_type,
                "visual_complexity": slide.content_guidance.visual_complexity,
                "content_density": slide.content_guidance.content_density,
                "tone_indicator": slide.content_guidance.tone_indicator,
                "generation_instructions": slide.content_guidance.generation_instructions
            }

        # Add asset needs
        if slide.analytics_needed:
            context["analytics_needed"] = slide.analytics_needed
        if slide.diagrams_needed:
            context["diagrams_needed"] = slide.diagrams_needed
        if slide.tables_needed:
            context["tables_needed"] = slide.tables_needed

        # Build request payload
        return self.client.build_request_payload(
            slide_id=slide.slide_id,
            narrative=slide.narrative,
            topics=slide.key_points,
            context=context,
            slide_number=slide_number
        )


# Convenience function

async def route_presentation_to_text_service(
    strawman: PresentationStrawman,
    text_service_url: str,
    session_id: str,
    use_batch: bool = True
) -> Dict[str, Any]:
    """
    Route presentation slides to Text Service (convenience function).

    Args:
        strawman: PresentationStrawman with classified slides
        text_service_url: Text Service base URL
        session_id: Session identifier
        use_batch: Use batch mode for parallel processing (default: True)

    Returns:
        Routing result dict
    """
    # Create client
    client = TextServiceInterface(text_service_url)

    try:
        # Create router
        router = ServiceRouter(client)
        router.set_processing_mode(use_batch)

        # Route presentation
        result = await router.route_presentation(strawman, session_id)

        return result

    finally:
        await client.close()


# Example usage
if __name__ == "__main__":
    print("Service Router - Slide Routing to Text Service v1.1")
    print("=" * 70)

    print("\nRouting Strategy:")
    print("  1. Validate slide classifications")
    print("  2. Build specialized requests for each slide")
    print("  3. Route to appropriate endpoints:")
    print("     - Batch mode: Single call to /api/v1/generate/batch (parallel)")
    print("     - Individual mode: Sequential calls to specialized endpoints")
    print("  4. Collect results and errors")
    print("  5. Return comprehensive metadata")

    print("\nBatch Mode Benefits:")
    print("  • Parallel processing for faster generation")
    print("  • Shared context optimization")
    print("  • Better resource utilization")
    print("  • Comprehensive error handling with partial failures")

    print("\nIndividual Mode Benefits:")
    print("  • Fallback when batch fails")
    print("  • Per-slide error isolation")
    print("  • Sequential processing for debugging")

    print("\n" + "=" * 70)
    print("Router ready for Stage 6 (CONTENT_GENERATION)")
