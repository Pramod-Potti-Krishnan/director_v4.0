"""
Visual Style Assigner for Director Agent v3.5

Assigns visual styles to hero slides with hybrid approach:
- User preferences take precedence (override)
- AI defaults based on audience and theme (fallback)
- Deck size consideration for section dividers

Key Logic:
- Title slides: ALWAYS use image backgrounds (user requirement)
- Section slides: Only for decks >10 slides AND (user request OR creative theme)
- Closing slides: Based on preference (default: True for memorable impact)
- Visual style: professional (default), illustrated (creative/Ghibli), kids (children audience)
"""

import logging
from typing import Optional
from src.models.visual_styles import (
    VisualStylePreferences,
    VisualStyleAssignmentRules,
    VisualStyleAssignment
)
from src.models.agents import Slide, PresentationStrawman

logger = logging.getLogger(__name__)


class VisualStyleAssigner:
    """
    Assign visual styles to hero slides with user override support.

    Implements hybrid approach:
    1. Apply user preferences if provided
    2. Use AI default rules based on audience, theme, and deck size
    3. Determine use_image_background for each hero slide
    4. Assign visual_style (professional, illustrated, kids)
    """

    def __init__(
        self,
        user_preferences: Optional[VisualStylePreferences] = None,
        rules: Optional[VisualStyleAssignmentRules] = None
    ):
        """
        Initialize visual style assigner.

        Args:
            user_preferences: User's explicit visual style preferences from Stage 2
            rules: Assignment rules (uses defaults if not provided)
        """
        self.user_preferences = user_preferences
        self.rules = rules or VisualStyleAssignmentRules()

        if user_preferences:
            logger.info(
                f"VisualStyleAssigner initialized with user preferences: "
                f"style={user_preferences.visual_style}, "
                f"sections={user_preferences.use_images_for_sections}, "
                f"closing={user_preferences.use_images_for_closing}"
            )
        else:
            logger.info("VisualStyleAssigner initialized with AI defaults")

    def assign_visual_style(
        self,
        slide: Slide,
        strawman: PresentationStrawman
    ) -> VisualStyleAssignment:
        """
        Assign visual style configuration to a hero slide.

        Args:
            slide: Slide to configure (must be hero slide with layout_id="L29")
            strawman: Presentation context (for deck size, theme, audience)

        Returns:
            VisualStyleAssignment with:
            - visual_style: "professional", "illustrated", "kids", or None
            - use_image_background: True/False
            - assignment_reason: Explanation for debugging
        """
        # Only applies to hero slides (L29)
        if slide.layout_id != "L29":
            return VisualStyleAssignment(
                visual_style=None,
                use_image_background=False,
                assignment_reason="Not a hero slide (only L29 hero slides support visual styles)"
            )

        classification = slide.slide_type_classification

        # Determine use_image_background based on slide type and context
        use_image, reason_image = self._should_use_image_background(
            classification,
            strawman
        )

        # Determine visual_style (only relevant if using images)
        if use_image:
            style, reason_style = self._determine_visual_style(strawman)
            final_reason = f"{reason_image}; {reason_style}"
        else:
            style = None
            final_reason = reason_image

        logger.info(
            f"Slide #{slide.slide_number} ({classification}): "
            f"use_image={use_image}, style={style} | {final_reason}"
        )

        return VisualStyleAssignment(
            visual_style=style,
            use_image_background=use_image,
            assignment_reason=final_reason
        )

    def _should_use_image_background(
        self,
        classification: str,
        strawman: PresentationStrawman
    ) -> tuple[bool, str]:
        """
        Determine if slide should use image background.

        Args:
            classification: Slide type classification (title_slide, section_divider, closing_slide)
            strawman: Presentation context

        Returns:
            Tuple of (use_image: bool, reason: str)
        """
        deck_size = strawman.total_slides

        # Title slides: ALWAYS use images (user requirement)
        if classification == "title_slide":
            return True, "Title slide always uses image (user requirement)"

        # Section dividers: Complex logic based on deck size and preferences
        if classification == "section_divider":
            # Small decks (≤10 slides): No section images by default
            if deck_size <= self.rules.small_deck_threshold:
                # User explicitly requested section images
                if self.user_preferences and self.user_preferences.use_images_for_sections:
                    return True, f"Small deck ({deck_size}≤{self.rules.small_deck_threshold}), but user requested section images"
                else:
                    return False, f"Small deck ({deck_size}≤{self.rules.small_deck_threshold}), section images not needed"

            # Large decks (>10 slides): Use images based on preferences or theme
            else:
                # User preference takes precedence
                if self.user_preferences and self.user_preferences.use_images_for_sections:
                    return True, f"Large deck ({deck_size}>{self.rules.small_deck_threshold}), user requested section images"

                # Check if using images from strawman-level setting
                if strawman.use_images_for_sections:
                    return True, f"Large deck ({deck_size}>{self.rules.small_deck_threshold}), strawman enabled section images"

                # AI recommendation: Use images for creative themes
                theme = strawman.overall_theme.lower()
                creative_keywords = self.rules.creative_theme_keywords
                is_creative = any(keyword in theme for keyword in creative_keywords)

                if is_creative:
                    return True, f"Large deck ({deck_size}>{self.rules.small_deck_threshold}), creative theme detected: '{strawman.overall_theme}'"
                else:
                    return False, f"Large deck ({deck_size}>{self.rules.small_deck_threshold}), professional theme, section images not needed"

        # Closing slides: User preference or default (True for memorable impact)
        if classification == "closing_slide":
            # User preference takes precedence
            if self.user_preferences and self.user_preferences.use_images_for_closing is not None:
                if self.user_preferences.use_images_for_closing:
                    return True, "User requested closing image"
                else:
                    return False, "User disabled closing image"

            # Check strawman-level setting
            if strawman.use_images_for_closing:
                return True, "Strawman default: closing images enabled for memorable impact"
            else:
                return False, "Strawman disabled closing images"

        # Unknown classification: No images
        return False, f"Unknown classification: {classification}"

    def _determine_visual_style(
        self,
        strawman: PresentationStrawman
    ) -> tuple[str, str]:
        """
        Determine visual style based on preferences or AI defaults.

        Args:
            strawman: Presentation context (for theme, audience)

        Returns:
            Tuple of (style: str, reason: str)
        """
        # User preference takes precedence
        if self.user_preferences and self.user_preferences.visual_style:
            return (
                self.user_preferences.visual_style,
                f"User selected '{self.user_preferences.visual_style}' style"
            )

        # Check strawman-level preference
        if strawman.visual_style_preference:
            return (
                strawman.visual_style_preference,
                f"Strawman preference: '{strawman.visual_style_preference}' style"
            )

        # AI default based on audience and theme
        audience = strawman.target_audience.lower()
        theme = strawman.overall_theme.lower()

        # Kids audience → kids style
        kids_keywords = self.rules.kids_audience_keywords
        if any(keyword in audience for keyword in kids_keywords):
            return (
                "kids",
                f"Kids audience detected ('{strawman.target_audience}') → kids style"
            )

        # Creative theme → illustrated style
        creative_keywords = self.rules.creative_theme_keywords
        if any(keyword in theme for keyword in creative_keywords):
            return (
                "illustrated",
                f"Creative theme detected ('{strawman.overall_theme}') → illustrated style"
            )

        # Default: professional style
        return (
            "professional",
            f"Default professional style (audience: '{strawman.target_audience}', theme: '{strawman.overall_theme}')"
        )
