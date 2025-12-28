"""
I-Series Budget Tracker for Director Agent v4.0

Tracks I-series (image+text) slide allocation during strawman generation,
enforcing percentage limits with soft guidelines.

v4.9: Audience-aware I-series budget tracking
- Hero slides (title, closing) count toward the budget
- Soft enforcement: can exceed budget for highly visual content
- Balances I-series allocation across the presentation
"""

from typing import List, Optional
from src.core.presentation_type_analyzer import (
    PresentationType,
    get_target_range,
    get_preferred_image_positions
)
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class ISeriesBudgetTracker:
    """
    Tracks I-series allocation during strawman content analysis.

    Implements soft enforcement of I-series percentage targets:
    - Under target: allow I-series
    - At target but content strongly suggests: allow (soft guideline)
    - Well over target: deny

    Hero slides (title + closing) are pre-counted since they have images.
    """

    # Hero slides that always have images
    HERO_SLIDE_COUNT = 2  # Title + Closing

    # Soft cap multiplier (allow up to this % over target for strong suggestions)
    SOFT_CAP_MULTIPLIER = 1.2  # 20% over target allowed

    def __init__(
        self,
        total_slides: int,
        presentation_type: PresentationType
    ):
        """
        Initialize the budget tracker.

        Args:
            total_slides: Total number of slides in the presentation
            presentation_type: Classified presentation type
        """
        self.presentation_type = presentation_type
        self.total_slides = total_slides

        # Calculate content slides (exclude hero slides)
        self.hero_slides = min(self.HERO_SLIDE_COUNT, total_slides)
        self.content_slides = max(0, total_slides - self.hero_slides)

        # Get target range for this presentation type
        self.target_min, self.target_max = get_target_range(presentation_type)

        # Calculate target I-series count
        # Target is based on total slides (hero slides count toward percentage)
        target_percentage = (self.target_min + self.target_max) / 2
        self.target_count = max(
            self.hero_slides,  # At minimum, hero slides have images
            round(total_slides * target_percentage)
        )

        # Calculate hard cap (absolute maximum with soft enforcement)
        self.hard_cap = round(total_slides * self.target_max * self.SOFT_CAP_MULTIPLIER)

        # Current I-series count (hero slides pre-counted)
        self.current_count = self.hero_slides

        # Get preferred image positions for this type
        self.preferred_positions = get_preferred_image_positions(presentation_type)

        # Track which slide indices got I-series
        self.iseries_indices: List[int] = []

        logger.info(
            f"ISeriesBudgetTracker: total={total_slides}, type={presentation_type.value}, "
            f"target={self.target_count} ({self.target_min*100:.0f}-{self.target_max*100:.0f}%), "
            f"hero={self.hero_slides}, hard_cap={self.hard_cap}"
        )

    def should_use_iseries(
        self,
        slide_idx: int,
        content_strongly_suggests: bool = False
    ) -> bool:
        """
        Determine if a slide should use I-series layout.

        Implements soft enforcement:
        - Under target: allow I-series
        - At target but content strongly suggests: allow (soft guideline)
        - Over hard cap: deny

        Args:
            slide_idx: Current slide index (0-based)
            content_strongly_suggests: True if content analysis strongly
                                       suggests an image (e.g., comparison,
                                       flow patterns)

        Returns:
            True if I-series should be used, False otherwise
        """
        # Skip hero slides (they're already counted)
        if self._is_hero_slide(slide_idx):
            logger.debug(f"Slide {slide_idx}: Hero slide, already counted")
            return False

        # Calculate remaining budget
        remaining_target = self.target_count - self.current_count
        remaining_slides = self._remaining_content_slides(slide_idx)

        # Hard cap check - never exceed this
        if self.current_count >= self.hard_cap:
            logger.debug(
                f"Slide {slide_idx}: Denied (hard cap {self.hard_cap} reached)"
            )
            return False

        # Under target - allow
        if self.current_count < self.target_count:
            # Balance allocation: don't front-load all images
            # If we have lots of budget remaining vs remaining slides, be more selective
            if remaining_slides > 0:
                target_ratio = remaining_target / remaining_slides
                if target_ratio < 0.3 and not content_strongly_suggests:
                    # Running low on budget, be selective
                    logger.debug(
                        f"Slide {slide_idx}: Denied (conserving budget, "
                        f"ratio={target_ratio:.2f})"
                    )
                    return False

            logger.debug(
                f"Slide {slide_idx}: Allowed (under target, "
                f"current={self.current_count}/{self.target_count})"
            )
            return True

        # At or over target - only allow with strong suggestion (soft enforcement)
        if content_strongly_suggests:
            logger.debug(
                f"Slide {slide_idx}: Allowed (soft enforcement, "
                f"content strongly suggests)"
            )
            return True

        logger.debug(
            f"Slide {slide_idx}: Denied (at target {self.target_count}, "
            f"content doesn't strongly suggest)"
        )
        return False

    def record_iseries_used(self, slide_idx: int) -> None:
        """
        Record that I-series was used for a slide.

        Args:
            slide_idx: Slide index that used I-series
        """
        if slide_idx not in self.iseries_indices:
            self.iseries_indices.append(slide_idx)
            self.current_count += 1
            logger.debug(
                f"I-series used for slide {slide_idx}, "
                f"total now: {self.current_count}/{self.target_count}"
            )

    def get_preferred_position(self, topic_count: int) -> str:
        """
        Get the preferred image position based on presentation type and topic count.

        Args:
            topic_count: Number of topics in the slide

        Returns:
            Image position (e.g., "i1", "i2", "i3", "i4")
        """
        if self.presentation_type in [
            PresentationType.VISUAL_HEAVY,
            PresentationType.BALANCED
        ]:
            # Prefer wide images for engagement
            # i1 = wide left, i2 = wide right
            return "i1" if topic_count >= 3 else "i2"
        else:
            # PROFESSIONAL and TEXT_FOCUSED prefer narrow images
            # i3 = narrow left, i4 = narrow right
            return "i3" if topic_count >= 4 else "i4"

    def get_budget_status(self) -> dict:
        """
        Get current budget status for logging/debugging.

        Returns:
            Dict with budget information
        """
        return {
            "presentation_type": self.presentation_type.value,
            "total_slides": self.total_slides,
            "target_count": self.target_count,
            "current_count": self.current_count,
            "remaining": max(0, self.target_count - self.current_count),
            "hard_cap": self.hard_cap,
            "percentage": (
                self.current_count / self.total_slides * 100
                if self.total_slides > 0 else 0
            ),
            "iseries_indices": self.iseries_indices.copy(),
        }

    def _is_hero_slide(self, slide_idx: int) -> bool:
        """Check if slide is a hero slide (title or closing)."""
        # First slide (title) and last slide (closing) are hero slides
        return slide_idx == 0 or slide_idx == self.total_slides - 1

    def _remaining_content_slides(self, current_idx: int) -> int:
        """Calculate remaining content slides after current index."""
        # Exclude hero slides from count
        remaining = 0
        for i in range(current_idx + 1, self.total_slides):
            if not self._is_hero_slide(i):
                remaining += 1
        return remaining
