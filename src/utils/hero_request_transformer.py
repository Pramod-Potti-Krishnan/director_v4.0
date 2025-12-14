"""
Hero Request Transformer for Director v3.4

Transforms Director's slide data into Text Service v1.2 hero endpoint requests.

This module bridges Director v3.4's data structures with Text Service v1.2's
hero slide endpoints (/v1.2/hero/title, /section, /closing).

Architecture:
    Director Slide → HeroRequestTransformer → Text Service v1.2 Hero Request

Example:
    slide = Slide(
        slide_number=1,
        classification="title_slide",
        narrative="AI in Healthcare",
        ...
    )

    transformer = HeroRequestTransformer()
    request_data = transformer.transform_to_hero_request(slide, strawman)

    # Returns:
    # {
    #   "endpoint": "/v1.2/hero/title",
    #   "payload": {
    #     "slide_number": 1,
    #     "slide_type": "title_slide",
    #     "narrative": "AI in Healthcare",
    #     "topics": [...],
    #     "context": {...}
    #   }
    # }
"""

from typing import Dict, Any, Optional
from src.models.agents import Slide, PresentationStrawman
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class HeroRequestTransformer:
    """
    Transforms Director slide data to Text Service v1.2 hero requests.

    Handles mapping from Director's internal slide representation to the
    hero endpoint request format expected by Text Service v1.2.

    v3.5 UPDATE: Supports -with-image endpoints and visual_style parameter.
    Routes to /hero/{type}-with-image when slide.use_image_background=True.
    """

    # v3.5: Map slide classifications to base endpoint names
    # Endpoint variant (-with-image or regular) determined by use_image_background flag
    CLASSIFICATION_TO_BASE_ENDPOINT = {
        "title_slide": "title",
        "section_divider": "section",
        "closing_slide": "closing"
    }

    # v3.0: Keep old name for backward compatibility
    CLASSIFICATION_TO_ENDPOINT = CLASSIFICATION_TO_BASE_ENDPOINT

    def __init__(self):
        """Initialize transformer."""
        logger.debug("HeroRequestTransformer initialized")

    def is_hero_slide(self, classification: str) -> bool:
        """
        Check if slide classification is a hero slide type.

        Args:
            classification: Slide classification string

        Returns:
            True if classification is a hero slide type
        """
        return classification in self.CLASSIFICATION_TO_ENDPOINT

    def transform_to_hero_request(
        self,
        slide: Slide,
        strawman: PresentationStrawman
    ) -> Dict[str, Any]:
        """
        Transform Director slide to hero endpoint request format.

        Creates the payload structure expected by Text Service v1.2 hero
        endpoints, extracting relevant data from slide and strawman objects.

        Args:
            slide: Director's Slide object with slide data
            strawman: PresentationStrawman with presentation-level context

        Returns:
            Dictionary with:
            - endpoint: Hero endpoint path (e.g., "/v1.2/hero/title")
            - payload: Request payload for the endpoint

        Raises:
            ValueError: If slide classification is not a hero slide type
        """
        classification = slide.slide_type_classification

        if not self.is_hero_slide(classification):
            raise ValueError(
                f"Not a hero slide: {classification}. "
                f"Expected one of: {list(self.CLASSIFICATION_TO_BASE_ENDPOINT.keys())}"
            )

        # Get base endpoint name
        base_endpoint = self.CLASSIFICATION_TO_BASE_ENDPOINT[classification]

        # v3.5: Determine endpoint variant based on use_image_background flag
        if slide.use_image_background:
            endpoint = f"/v1.2/hero/{base_endpoint}-with-image"
        else:
            endpoint = f"/v1.2/hero/{base_endpoint}"

        logger.info(
            f"Transforming slide #{slide.slide_number} ({classification}) to {endpoint} "
            f"(use_image: {slide.use_image_background}, visual_style: {slide.visual_style})"
        )

        # Build context from strawman and slide
        context = self._build_context(slide, strawman)

        # Build payload
        payload = {
            "slide_number": slide.slide_number,
            "slide_type": classification,
            "narrative": slide.narrative,
            "topics": self._extract_topics(slide),
            "context": context
        }

        # v3.5: Add visual_style parameter for -with-image endpoints
        if slide.use_image_background and slide.visual_style:
            payload["visual_style"] = slide.visual_style
            logger.debug(f"Added visual_style='{slide.visual_style}' to payload")

        logger.debug(f"Hero request payload: {payload}")

        return {
            "endpoint": endpoint,
            "payload": payload
        }

    def _extract_topics(self, slide: Slide) -> list[str]:
        """
        Extract topics from slide object.

        Args:
            slide: Slide object

        Returns:
            List of topic strings
        """
        topics = []

        # Try multiple possible attribute names
        if hasattr(slide, 'key_points') and slide.key_points:
            if isinstance(slide.key_points, list):
                topics = slide.key_points
            elif isinstance(slide.key_points, str):
                topics = [slide.key_points]

        elif hasattr(slide, 'topics') and slide.topics:
            if isinstance(slide.topics, list):
                topics = slide.topics
            elif isinstance(slide.topics, str):
                topics = [slide.topics]

        elif hasattr(slide, 'content_points') and slide.content_points:
            if isinstance(slide.content_points, list):
                topics = slide.content_points
            elif isinstance(slide.content_points, str):
                topics = [slide.content_points]

        # Fallback: extract from narrative if no topics found
        if not topics and slide.narrative:
            # Use narrative as single topic
            topics = [slide.narrative]

        return topics

    def _build_context(
        self,
        slide: Slide,
        strawman: PresentationStrawman
    ) -> Dict[str, Any]:
        """
        Build context dictionary from slide and strawman data.

        Args:
            slide: Slide object
            strawman: PresentationStrawman object

        Returns:
            Context dictionary for hero request
        """
        context = {}

        # Extract theme
        if hasattr(strawman, 'theme'):
            context["theme"] = strawman.theme
        else:
            context["theme"] = "professional"

        # Extract audience
        if hasattr(strawman, 'audience'):
            context["audience"] = strawman.audience
        elif hasattr(strawman, 'target_audience'):
            context["audience"] = strawman.target_audience
        else:
            context["audience"] = "general business audience"

        # Extract presentation title
        if hasattr(strawman, 'title'):
            context["presentation_title"] = strawman.title

        # Extract contact info (for closing slides)
        if hasattr(strawman, 'contact_info'):
            context["contact_info"] = strawman.contact_info
        elif hasattr(strawman, 'presenter'):
            context["contact_info"] = strawman.presenter

        # Extract presenter name
        if hasattr(strawman, 'presenter_name'):
            context["presenter_name"] = strawman.presenter_name
        elif hasattr(strawman, 'presenter'):
            context["presenter_name"] = strawman.presenter

        # Extract company
        if hasattr(strawman, 'company'):
            context["company"] = strawman.company

        # Add slide-specific context
        if hasattr(slide, 'tone'):
            context["tone"] = slide.tone

        if hasattr(slide, 'style'):
            context["style"] = slide.style

        return context

    def get_hero_endpoint_for_classification(
        self,
        classification: str
    ) -> Optional[str]:
        """
        Get hero endpoint path for a classification.

        Args:
            classification: Slide classification

        Returns:
            Endpoint path (e.g., "/v1.2/hero/title") or None if not hero slide
        """
        hero_type = self.CLASSIFICATION_TO_ENDPOINT.get(classification)
        if hero_type:
            return f"/v1.2/hero/{hero_type}"
        return None
