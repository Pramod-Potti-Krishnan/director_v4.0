"""
Layout Selection Model for AI-Powered Layout Matching
======================================================

Pydantic model for AI responses when selecting optimal slide layouts.
"""

from typing import Optional
from pydantic import BaseModel, Field


class LayoutSelection(BaseModel):
    """
    AI response model for layout selection.

    Used by Pydantic AI agent to return structured layout selection
    with reasoning based on semantic analysis of slide content.
    """

    layout_id: str = Field(
        description="Selected layout ID (e.g., 'L07', 'L05', 'L17')"
    )

    reasoning: str = Field(
        description="Brief explanation of why this layout was selected based on content analysis and BestUseCase matching"
    )

    confidence: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Optional confidence score for the selection (0.0 to 1.0)"
    )

    alternative_layout: Optional[str] = Field(
        default=None,
        description="Optional second-best layout ID if confidence is low"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "layout_id": "L07",
                "reasoning": "Slide contains customer testimonial about product impact, which perfectly matches L07's best use case for testimonials and creating dramatic impact with important statements.",
                "confidence": 0.95,
                "alternative_layout": "L04"
            }
        }
