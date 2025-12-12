"""
Content Generation Models - v3.1
=================================

Data models for Stage 6 (Content Generation).
v3.1 scope: TEXT SERVICE ONLY (no images, charts, diagrams)
"""

from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field
from datetime import datetime
from .agents import Slide, PresentationStrawman


class GeneratedText(BaseModel):
    """
    Generated text content from Text Service.

    v3.1: Simple structure - just content and metadata.
    v1.1: Enhanced to support both string (legacy) and dict (structured) content.
    """
    content: Union[str, Dict[str, Any]] = Field(
        description="Generated content - string (HTML/text for v1.0) or dict (structured for v1.1)"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Optional metadata like word_count, generation_time_ms, model_used"
    )


class EnrichedSlide(BaseModel):
    """
    A slide with generated text content attached.

    v3.1 scope: TEXT ONLY
    - original_slide: The full input Slide from strawman
    - generated_text: Generated text content (or None if failed)
    - has_text_failure: Flag indicating if text generation failed
    """
    original_slide: Slide = Field(
        description="The full input slide from strawman"
    )
    slide_id: str = Field(
        description="Slide identifier for easy reference"
    )
    generated_text: Optional[GeneratedText] = Field(
        default=None,
        description="Generated text content (None if generation failed)"
    )
    has_text_failure: bool = Field(
        default=False,
        description="True if text generation failed for this slide"
    )


class EnrichedPresentationStrawman(BaseModel):
    """
    Presentation strawman with generated text content.

    v3.1 scope: TEXT SERVICE ONLY
    - original_strawman: The full input PresentationStrawman from Stage 5
    - enriched_slides: Array of EnrichedSlide with text content
    - generation_metadata: Stats about the text generation process
    """
    original_strawman: PresentationStrawman = Field(
        description="The full input strawman from Director Stage 5"
    )
    enriched_slides: List[EnrichedSlide] = Field(
        description="Slides with generated text content"
    )
    generation_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata about generation process",
        example={
            "total_slides": 10,
            "successful_slides": 9,
            "failed_slides": 1,
            "generation_time_seconds": 45,
            "timestamp": "2025-10-20T12:34:56Z",
            "service_used": "text_service_v1.0"
        }
    )

    @property
    def success_rate(self) -> float:
        """Calculate success rate of text generation."""
        metadata = self.generation_metadata
        total = metadata.get("total_slides", 0)
        if total == 0:
            return 0.0
        successful = metadata.get("successful_slides", 0)
        return (successful / total) * 100

    @property
    def has_failures(self) -> bool:
        """Check if any slides had text generation failures."""
        return any(slide.has_text_failure for slide in self.enriched_slides)
