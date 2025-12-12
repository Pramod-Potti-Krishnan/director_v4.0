"""
v1.2 Request Transformer for Director v3.4
===========================================

Transforms Director's Slide model to Text Service v1.2 request format.

Transformation Flow:
  Director Slide Model
  ├── variant_id: "matrix_2x3" (randomly selected)
  ├── generated_title: "Our Strategic Pillars" (50 chars max)
  ├── generated_subtitle: "Building blocks for success" (90 chars max)
  ├── narrative: "Here's our approach..."
  ├── key_points: ["Point A", "Point B", "Point C"]
  └── content_guidance: {tone, density, emphasis}

  ↓ TRANSFORM ↓

  v1.2 GenerationRequest
  {
    "variant_id": "matrix_2x3",
    "slide_spec": {
      "slide_title": "Our Strategic Pillars",
      "slide_purpose": "Here's our approach...",
      "key_message": "Point A",
      "target_points": ["Point A", "Point B", "Point C"],
      "tone": "professional",
      "audience": "business stakeholders"
    },
    "presentation_spec": {
      "presentation_title": "Q4 Business Review",
      "presentation_type": "Informative and data-driven",
      "prior_slides_summary": "Previously covered...",
      "current_slide_number": 3,
      "total_slides": 10
    },
    "enable_parallel": true,
    "validate_character_counts": true
  }
"""

from typing import Dict, Any, Optional, List
from src.models.agents import Slide, PresentationStrawman
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class V1_2_Transformer:
    """
    Transforms Director's Slide model to Text Service v1.2 request format.

    Key responsibilities:
    - Map slide fields → v1.2 SlideSpecification
    - Build presentation context for v1.2 PresentationSpecification
    - Handle prior slides summary for narrative flow
    - Pass variant_id from Director's random selection
    """

    @staticmethod
    def transform_slide_to_v1_2_request(
        slide: Slide,
        strawman: PresentationStrawman,
        slide_number: int,
        prior_slides_summary: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Transform a single slide to v1.2 generation request.

        Args:
            slide: Slide with variant_id, generated_title, narrative, etc.
            strawman: Full presentation for context
            slide_number: Current slide position (1-indexed)
            prior_slides_summary: Optional summary of previous slides

        Returns:
            V1_2_GenerationRequest dict ready for POST /v1.2/generate

        Raises:
            ValueError: If required fields missing (variant_id, generated_title)
        """
        # Validate required fields
        if not slide.variant_id:
            raise ValueError(
                f"Slide {slide.slide_id} missing variant_id. "
                "Ensure GENERATE_STRAWMAN assigns variant_id via VariantSelector."
            )

        if not slide.generated_title:
            logger.warning(
                f"Slide {slide.slide_id} missing generated_title. "
                "Using original title as fallback."
            )
            slide.generated_title = slide.title[:50]  # Truncate if needed

        # Build SlideSpecification
        slide_spec = V1_2_Transformer._build_slide_spec(slide, strawman)

        # Build PresentationSpecification
        presentation_spec = V1_2_Transformer._build_presentation_spec(
            strawman=strawman,
            slide_number=slide_number,
            prior_slides_summary=prior_slides_summary
        )

        # Assemble complete request
        request = {
            "variant_id": slide.variant_id,
            "slide_spec": slide_spec,
            "presentation_spec": presentation_spec,
            "enable_parallel": True,  # Use parallel processing for speed
            "validate_character_counts": True  # Validate against baseline ± 5%
        }

        logger.debug(
            f"Transformed slide {slide.slide_id} ({slide.variant_id}) "
            f"to v1.2 request for Text Service"
        )

        return request

    @staticmethod
    def _build_slide_spec(slide: Slide, strawman: PresentationStrawman) -> Dict[str, Any]:
        """
        Build SlideSpecification dict for v1.2.

        Args:
            slide: Slide to build spec from
            strawman: Presentation for context

        Returns:
            SlideSpecification dict
        """
        # Extract tone from content_guidance or use default
        tone = "professional"
        if slide.content_guidance:
            tone = slide.content_guidance.tone_indicator

        # Build target_points from key_points
        target_points = slide.key_points if slide.key_points else None

        # Extract key_message (first key point or narrative excerpt)
        key_message = slide.narrative
        if slide.key_points:
            key_message = slide.key_points[0]

        slide_spec = {
            "slide_title": slide.generated_title,  # Director's title (INPUT)
            "slide_purpose": slide.narrative,
            "key_message": key_message,
            "tone": tone,
            "audience": strawman.target_audience
        }

        # Add optional target_points if available
        if target_points:
            slide_spec["target_points"] = target_points

        return slide_spec

    @staticmethod
    def _build_presentation_spec(
        strawman: PresentationStrawman,
        slide_number: int,
        prior_slides_summary: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Build PresentationSpecification dict for v1.2.

        Args:
            strawman: PresentationStrawman for context
            slide_number: Current slide position (1-indexed)
            prior_slides_summary: Summary of prior slides

        Returns:
            PresentationSpecification dict
        """
        presentation_spec = {
            "presentation_title": strawman.main_title,
            "presentation_type": strawman.overall_theme,
            "current_slide_number": slide_number,
            "total_slides": strawman.total_slides
        }

        # Add optional prior slides summary for narrative flow
        if prior_slides_summary:
            presentation_spec["prior_slides_summary"] = prior_slides_summary

        return presentation_spec

    @staticmethod
    def build_prior_slides_summary(slides: List[Slide], current_index: int) -> str:
        """
        Build summary of slides prior to current slide for context.

        This helps Text Service maintain narrative flow and avoid repetition.

        Args:
            slides: All slides in presentation
            current_index: Index of current slide (0-indexed)

        Returns:
            Summary string of prior slides (or empty if first slide)
        """
        if current_index == 0:
            return ""

        # Get prior slides
        prior_slides = slides[:current_index]

        # Build summary from titles and narratives
        summaries = []
        for slide in prior_slides:
            title = slide.generated_title or slide.title
            summaries.append(f"- {title}")

        # Join with newlines
        summary = "\n".join(summaries)

        logger.debug(f"Built prior slides summary for slide {current_index + 1}")

        return summary

    @staticmethod
    def transform_batch(
        slides: List[Slide],
        strawman: PresentationStrawman
    ) -> List[Dict[str, Any]]:
        """
        Transform multiple slides to v1.2 request batch.

        Args:
            slides: List of slides to transform
            strawman: Presentation context

        Returns:
            List of v1.2 generation requests
        """
        requests = []

        for idx, slide in enumerate(slides):
            slide_number = idx + 1

            # Build prior slides summary for context
            prior_summary = V1_2_Transformer.build_prior_slides_summary(
                slides=slides,
                current_index=idx
            )

            # Transform slide
            request = V1_2_Transformer.transform_slide_to_v1_2_request(
                slide=slide,
                strawman=strawman,
                slide_number=slide_number,
                prior_slides_summary=prior_summary
            )

            requests.append(request)

        logger.info(f"Transformed {len(requests)} slides to v1.2 batch requests")

        return requests


# Convenience functions

def transform_slide_to_v1_2(
    slide: Slide,
    strawman: PresentationStrawman,
    slide_number: int
) -> Dict[str, Any]:
    """Transform single slide (convenience function)."""
    return V1_2_Transformer.transform_slide_to_v1_2_request(
        slide, strawman, slide_number
    )


def transform_batch_to_v1_2(
    slides: List[Slide],
    strawman: PresentationStrawman
) -> List[Dict[str, Any]]:
    """Transform batch of slides (convenience function)."""
    return V1_2_Transformer.transform_batch(slides, strawman)


# Example usage
if __name__ == "__main__":
    from src.models.agents import Slide, PresentationStrawman, ContentGuidance

    print("v1.2 Request Transformer Test")
    print("=" * 70)

    # Create sample presentation
    strawman = PresentationStrawman(
        main_title="Q4 Business Review",
        overall_theme="Informative and data-driven",
        slides=[],  # Will populate
        design_suggestions="Modern professional with blue tones",
        target_audience="Executive team",
        presentation_duration=30,
        footer_text="Q4 2024"  # v1.2 footer
    )

    # Create sample slide
    slide = Slide(
        slide_number=2,
        slide_id="slide_002",
        title="Strategic Pillars",
        slide_type="content_heavy",
        slide_type_classification="matrix_2x2",
        layout_id="L25",
        variant_id="matrix_2x3",  # Random selection
        generated_title="Our Strategic Pillars",  # Director-generated (50 chars)
        generated_subtitle="Building blocks for success",  # Director-generated (90 chars)
        narrative="Our strategy is built on four key pillars that drive growth and innovation.",
        key_points=[
            "Customer focus",
            "Operational excellence",
            "Innovation leadership",
            "Sustainable growth"
        ],
        content_guidance=ContentGuidance(
            content_type="framework",
            visual_complexity="moderate",
            content_density="balanced",
            tone_indicator="professional",
            data_type="strategic_framework",
            emphasis_hierarchy=["structure", "clarity", "impact"],
            generation_instructions="Emphasize strategic importance of each pillar",
            pattern_rationale="Matrix layout shows equal weight of four pillars"
        )
    )

    # Transform to v1.2
    print("\nTransforming slide to v1.2 request...")
    request = V1_2_Transformer.transform_slide_to_v1_2_request(
        slide=slide,
        strawman=strawman,
        slide_number=2
    )

    print("\nGenerated v1.2 Request:")
    print(f"  variant_id: {request['variant_id']}")
    print(f"  slide_title: {request['slide_spec']['slide_title']}")
    print(f"  slide_purpose: {request['slide_spec']['slide_purpose'][:50]}...")
    print(f"  tone: {request['slide_spec']['tone']}")
    print(f"  target_points: {len(request['slide_spec'].get('target_points', []))} points")
    print(f"  presentation_title: {request['presentation_spec']['presentation_title']}")
    print(f"  current_slide_number: {request['presentation_spec']['current_slide_number']}")
    print(f"  enable_parallel: {request['enable_parallel']}")

    print("\n" + "=" * 70)
    print("✅ Transformation test complete!")
