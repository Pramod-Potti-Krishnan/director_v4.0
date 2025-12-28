"""
Content Analyzer for Director Agent v4.0.25

Simplified content analyzer for variant selection hints.

v4.0.25: This analyzer no longer handles service routing. Service routing is now
story-driven via the LayoutAnalyzer. This analyzer only provides hints for
variant selection (comparison, sequential, topic_count, etc.).

v4.9: Added presentation_type-aware I-series layout suggestions.
- VISUAL_HEAVY/BALANCED: Prefer I1/I2 (wide images)
- PROFESSIONAL/TEXT_FOCUSED: Prefer I3/I4 (narrow images)

The analyzer examines:
- Slide title and topics
- Content structure (comparison, sequence) for variant selection
- Topic count for variant capacity matching

Usage:
    analyzer = ContentAnalyzer()
    hints = analyzer.analyze(slide)  # Returns ContentHints with variant hints
"""

import re
from typing import Optional, List, Set, TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.presentation_type_analyzer import PresentationType
from src.models.content_hints import (
    ContentHints,
    PatternType,
    SuggestedService
)
from src.models.decision import StrawmanSlide
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class ContentAnalyzer:
    """
    Simplified content analyzer for variant selection hints.

    v4.0.25: Service routing is now story-driven (handled by LayoutAnalyzer).
    This analyzer focuses on:
    - Detecting comparison patterns (for comparison_* variants)
    - Detecting sequential patterns (for sequential_* variants)
    - Topic count (for variant capacity matching)
    - Basic content structure hints
    """

    # Comparison patterns - for selecting comparison_* variants
    COMPARISON_PATTERNS = [
        r'\bvs\.?\b',
        r'\bversus\b',
        r'\bcompare[ds]?\b',
        r'\boption\s+[a-c]\b',
        r'\btier\s+\d\b',
        r'\bplan\s+(a|b|c|basic|pro|enterprise)\b',
        r'\bpros?\s+(and|&)\s+cons?\b'
    ]

    # Sequential/process patterns - for selecting sequential_* variants
    SEQUENTIAL_PATTERNS = [
        r'\bstep\s+\d\b',
        r'\bphase\s+\d\b',
        r'\bstage\s+\d\b',
        r'\b\d+\s+steps?\b',
        r'\b(first|second|third|finally|next|then)\b'
    ]

    # Numeric patterns - for detecting metrics content
    NUMERIC_PATTERNS = [
        r'\d+%',           # Percentages
        r'\$[\d,.]+',      # Currency
        r'[\d,.]+[KMB]',   # Shorthand numbers (5K, 10M, 2B)
        r'\d+\.\d+',       # Decimals
    ]

    # =========================================================================
    # MAIN ANALYSIS METHOD
    # =========================================================================

    def analyze(self, slide: StrawmanSlide) -> ContentHints:
        """
        Analyze slide content and generate variant selection hints.

        v4.0.25: Simplified to focus on variant selection only.
        Service routing is now story-driven (handled by LayoutAnalyzer).

        Args:
            slide: StrawmanSlide with title, topics, etc.

        Returns:
            ContentHints with variant selection hints
        """
        # Build text corpus from slide content
        text_corpus = self._build_text_corpus(slide)
        text_lower = text_corpus.lower()

        # Count topics (critical for variant capacity matching)
        topic_count = len(slide.topics) if slide.topics else 0

        # Detect patterns for variant selection
        is_comparison = self._detect_comparison(text_lower)
        is_sequential = self._detect_sequential(text_lower)
        has_numbers = self._detect_numbers(text_lower)

        # Determine pattern type for variant selection
        pattern_type = self._detect_pattern_type(is_comparison, is_sequential, has_numbers)

        # Calculate numeric density (for metrics variants)
        numeric_density = self._calculate_numeric_density(text_corpus)

        # Check if slide would benefit from I-series layout
        # v4.8: Pass pattern_type for Gold Standard variant selection
        needs_image = self._detect_image_need(text_lower, topic_count)
        suggested_iseries = self._suggest_iseries_layout(needs_image, topic_count, pattern_type)

        hints = ContentHints(
            has_numbers=has_numbers,
            is_comparison=is_comparison,
            is_time_based=False,  # Simplified - not used for variant selection
            is_hierarchical=False,  # Simplified - not used for variant selection
            is_process_flow=is_sequential,  # Map to sequential for variant selection
            is_sequential=is_sequential,
            detected_keywords=[],  # Simplified - keywords not used for variant selection
            pattern_type=pattern_type,
            numeric_density=numeric_density,
            topic_count=topic_count,
            needs_image=needs_image,
            suggested_iseries=suggested_iseries,
            suggested_service=None,  # v4.0.25: No longer used - service from LayoutAnalyzer
            service_confidence=0.0  # v4.0.25: No longer used - service from LayoutAnalyzer
        )

        logger.debug(
            f"ContentAnalyzer: slide='{slide.title[:30]}...' "
            f"pattern={pattern_type} topics={topic_count} "
            f"comparison={is_comparison} sequential={is_sequential}"
        )

        return hints

    # =========================================================================
    # DETECTION METHODS (Simplified for variant selection)
    # =========================================================================

    def _build_text_corpus(self, slide: StrawmanSlide) -> str:
        """Build combined text corpus from slide content."""
        parts = [
            slide.title or "",
            " ".join(slide.topics) if slide.topics else "",
            slide.notes or ""
        ]
        return " ".join(parts)

    def _detect_numbers(self, text: str) -> bool:
        """Detect if text contains numeric content (for metrics variants)."""
        for pattern in self.NUMERIC_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

    def _detect_comparison(self, text: str) -> bool:
        """Detect comparison patterns (for comparison_* variants)."""
        for pattern in self.COMPARISON_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        # Also check keywords
        return self._contains_any(text, {"compare", "versus", "vs", "pros", "cons", "alternative"})

    def _detect_sequential(self, text: str) -> bool:
        """Detect sequential patterns (for sequential_* variants)."""
        for pattern in self.SEQUENTIAL_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return self._contains_any(text, {"step", "phase", "stage", "sequence", "order", "workflow", "process"})

    def _calculate_numeric_density(self, text: str) -> float:
        """Calculate ratio of numeric content (0-1) for metrics variant selection."""
        if not text:
            return 0.0

        words = text.split()
        if not words:
            return 0.0

        numeric_count = 0
        for word in words:
            if re.search(r'\d', word):
                numeric_count += 1

        return min(1.0, numeric_count / len(words))

    def _detect_pattern_type(
        self,
        is_comparison: bool,
        is_sequential: bool,
        has_numbers: bool
    ) -> Optional[PatternType]:
        """
        Determine the primary content pattern for variant selection.

        v4.0.25: Simplified to focus on patterns that affect variant choice.
        """
        if is_comparison:
            return PatternType.COMPARISON
        if is_sequential:
            return PatternType.FLOW
        if has_numbers:
            return PatternType.METRICS
        # Default to narrative for standard text content
        return PatternType.NARRATIVE

    # =========================================================================
    # I-SERIES RECOMMENDATIONS
    # =========================================================================

    def _detect_image_need(self, text: str, topic_count: int) -> bool:
        """Determine if content would benefit from an image."""
        # Image-benefiting keywords
        image_keywords = {
            "visual", "show", "demonstrate", "illustrate", "example",
            "product", "feature", "solution", "team", "office",
            "environment", "concept", "idea", "innovation", "technology"
        }

        # Check for image-related keywords
        if self._contains_any(text, image_keywords):
            return True

        # Slides with 3-5 topics often benefit from image+text layout
        if 3 <= topic_count <= 5:
            # Check for narrative content that pairs well with images
            if self._contains_any(text, {"benefit", "advantage", "feature", "highlight", "key"}):
                return True

        return False

    def _suggest_iseries_layout(
        self,
        needs_image: bool,
        topic_count: int,
        pattern_type: Optional[PatternType] = None,
        presentation_type: Optional["PresentationType"] = None
    ) -> Optional[str]:
        """
        Suggest I-series Gold Standard variant if image would enhance content.

        v4.8: Unified Variant System - returns full Gold Standard variant_id
        instead of just I1/I2/I3/I4. The variant_id encodes both the content
        template and image position.

        v4.9: Presentation type awareness
        - VISUAL_HEAVY/BALANCED: Prefer I1/I2 (wide images) for engagement
        - PROFESSIONAL/TEXT_FOCUSED: Prefer I3/I4 (narrow images) for text

        I-series layouts:
        - I1: Wide image left (660×1080), content right (1200×840) - balanced
        - I2: Wide image right (660×1080), content left (1140×840) - balanced
        - I3: Narrow image left (360×1080), content right (1500×840) - text-heavy
        - I4: Narrow image right (360×1080), content left (1440×840) - text-heavy

        Gold Standard I-series variants (26 total):
        - single_column_3section_i1/i2/i3/i4 (12)
        - comparison_2col_i1/i2/i3/i4, comparison_3col_i1/i2/i3/i4 (8)
        - sequential_3col_i1/i2/i3/i4, sequential_4col_i3/i4 (6)

        Args:
            needs_image: Whether the content needs an image
            topic_count: Number of topics in the slide
            pattern_type: Detected content pattern
            presentation_type: Presentation type for image position preference

        Returns:
            Gold Standard variant_id (e.g., "sequential_3col_i1") or None
        """
        if not needs_image:
            return None

        # Determine content variant base based on pattern and topic count
        if pattern_type == PatternType.COMPARISON:
            if topic_count >= 3:
                content_base = "comparison_3col"
            else:
                content_base = "comparison_2col"
        elif pattern_type == PatternType.FLOW:
            if topic_count >= 4:
                # sequential_4col only available for I3/I4 (narrow)
                content_base = "sequential_4col"
                # Force narrow layout for 4col
                if topic_count >= 5:
                    return "sequential_4col_i3"  # Narrow left
                else:
                    return "sequential_4col_i4"  # Narrow right
            else:
                content_base = "sequential_3col"
        else:
            # Default to single_column (most versatile)
            if topic_count >= 5:
                content_base = "single_column_5section"
            elif topic_count >= 4:
                content_base = "single_column_4section"
            else:
                content_base = "single_column_3section"

        # v4.9: Determine image position based on presentation type
        image_position = self._get_image_position(topic_count, presentation_type)

        variant_id = f"{content_base}_{image_position}"

        logger.debug(
            f"I-series suggestion: topic_count={topic_count}, pattern={pattern_type}, "
            f"presentation_type={presentation_type} -> {variant_id}"
        )

        return variant_id

    def _get_image_position(
        self,
        topic_count: int,
        presentation_type: Optional["PresentationType"] = None
    ) -> str:
        """
        Determine I-series image position based on presentation type and topic count.

        v4.9: Audience-aware image position selection
        - VISUAL_HEAVY/BALANCED: Prefer I1/I2 (wide images) for engagement
        - PROFESSIONAL/TEXT_FOCUSED: Prefer I3/I4 (narrow images) for text

        Args:
            topic_count: Number of topics in the slide
            presentation_type: Presentation type classification

        Returns:
            Image position string (i1, i2, i3, or i4)
        """
        # Import here to avoid circular imports
        try:
            from src.core.presentation_type_analyzer import PresentationType
        except ImportError:
            # Fallback to topic-count-based logic
            if topic_count >= 5:
                return "i3"
            elif topic_count >= 3:
                return "i1"
            else:
                return "i2"

        # Default to PROFESSIONAL if not specified
        if presentation_type is None:
            presentation_type = PresentationType.PROFESSIONAL

        # Visual-heavy and balanced presentations prefer wide images (I1/I2)
        if presentation_type in [PresentationType.VISUAL_HEAVY, PresentationType.BALANCED]:
            # Wide images for engagement
            # I1 = wide left, I2 = wide right
            if topic_count >= 3:
                return "i1"  # Wide left for more topics
            else:
                return "i2"  # Wide right for fewer topics (visual focus)

        # Professional and text-focused prefer narrow images (I3/I4)
        else:
            # Narrow images for text-heavy content
            # I3 = narrow left, I4 = narrow right
            if topic_count >= 4:
                return "i3"  # Narrow left for more topics
            else:
                return "i4"  # Narrow right for fewer topics

    def suggest_iseries(self, hints: ContentHints) -> Optional[str]:
        """
        Public method to suggest I-series layout from content hints.

        Args:
            hints: ContentHints from analyze()

        Returns:
            Layout ID (I1, I2, I3, I4) or None
        """
        return hints.suggested_iseries

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    def _contains_any(self, text: str, keywords: Set[str]) -> bool:
        """Check if text contains any of the keywords."""
        for keyword in keywords:
            if keyword in text:
                return True
        return False


# Convenience function
def analyze_slide_content(slide: StrawmanSlide) -> ContentHints:
    """
    Analyze slide content and return hints (convenience function).

    Args:
        slide: StrawmanSlide to analyze

    Returns:
        ContentHints with analysis results
    """
    analyzer = ContentAnalyzer()
    return analyzer.analyze(slide)
