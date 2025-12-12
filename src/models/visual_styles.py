"""
Visual Style Models for Director Agent v3.5

Data models for the Visual Style System, enabling hero slides to use
AI-generated background images with three distinct visual styles.

Visual Styles:
- professional: Photorealistic, modern, clean (default)
- illustrated: Ghibli-style, anime illustration, hand-painted aesthetic
- kids: Bright, vibrant, playful, exciting for children

Integration with Text Service v1.2:
- Routes to /v1.2/hero/{type}-with-image endpoints
- Passes visual_style parameter for image generation
"""

from typing import Literal, Optional
from pydantic import BaseModel, Field


class VisualStylePreferences(BaseModel):
    """
    User preferences for visual styles from Stage 2.

    These preferences override AI defaults and are captured during
    the clarifying questions stage.
    """

    visual_style: Literal["professional", "illustrated", "kids"] = Field(
        default="professional",
        description="Preferred visual style for hero slides"
    )

    use_images_for_title: bool = Field(
        default=True,
        description=(
            "Use images for title slide. "
            "Always True per requirements: 'Title slide with image is always preferred'"
        )
    )

    use_images_for_sections: bool = Field(
        default=False,
        description=(
            "Use images for section divider slides. "
            "Note: Section dividers not needed in small decks (≤10 slides)"
        )
    )

    use_images_for_closing: bool = Field(
        default=True,
        description="Use images for closing slide (default: True for memorable impact)"
    )


class VisualStyleAssignmentRules(BaseModel):
    """
    Rules for AI-driven visual style assignment.

    Used when user doesn't specify preferences (hybrid approach).
    AI assigns appropriate visual style based on audience and theme.
    """

    # Keywords for detecting kids/children audience
    kids_audience_keywords: list[str] = Field(
        default=[
            "children", "kids", "students", "elementary",
            "kindergarten", "preschool", "young learners",
            "youth", "teenagers", "teens"
        ],
        description="Keywords indicating children/youth audience → kids style"
    )

    # Keywords for detecting creative themes
    creative_theme_keywords: list[str] = Field(
        default=[
            "creative", "storytelling", "artistic", "imaginative",
            "innovative", "inspiring", "engaging", "narrative",
            "story", "journey", "adventure"
        ],
        description="Keywords indicating creative theme → illustrated style"
    )

    # Keywords for professional/corporate themes
    professional_theme_keywords: list[str] = Field(
        default=[
            "corporate", "business", "professional", "executive",
            "formal", "enterprise", "industry", "corporate",
            "financial", "strategic"
        ],
        description="Keywords indicating professional theme → professional style"
    )

    # Deck size threshold for section dividers
    small_deck_threshold: int = Field(
        default=10,
        description=(
            "Deck size threshold. "
            "Decks ≤10 slides don't need section images by default. "
            "Per user note: 'You don't always need section breaks in small decks'"
        )
    )


class VisualStyleAssignment(BaseModel):
    """
    Result of visual style assignment for a slide.

    Contains the determined visual style and whether to use
    image background for the slide.
    """

    visual_style: Optional[Literal["professional", "illustrated", "kids"]] = Field(
        default=None,
        description="Assigned visual style (None if not using images)"
    )

    use_image_background: bool = Field(
        default=False,
        description="Whether slide should use AI-generated image background"
    )

    assignment_reason: str = Field(
        default="",
        description="Explanation of why this style was assigned (for debugging)"
    )
