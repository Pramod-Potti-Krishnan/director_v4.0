"""
Diversity Tracker for Director v3.4
====================================

Tracks variant usage and enforces diversity rules to prevent repetitive slide formats.

Features:
- Track recent slide classifications
- Detect consecutive repetition
- Suggest alternative classifications
- Support semantic grouping exceptions
- Provide diversity metrics

Author: Director v3.4 Variant Diversity Enhancement
Date: 2025-01-11
"""

from typing import List, Optional, Tuple, Dict, Any
from collections import Counter, deque
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class DiversityTracker:
    """
    Tracks variant usage and enforces diversity rules.

    Diversity Rules:
    1. No more than 2 consecutive slides of same variant_id (unless semantic_group)
    2. No more than 3 consecutive slides of same slide_type_classification
    3. Suggest underused variants after 5+ slides
    4. Semantic groups exempt from all diversity rules

    Usage:
        tracker = DiversityTracker()

        # Check if classification violates diversity
        should_override, suggestion = tracker.should_override_for_diversity(
            classification="single_column",
            semantic_group=None  # or "use_cases"
        )

        if should_override:
            # Use suggested classification instead
            classification = suggestion

        # Track the slide
        tracker.add_slide(classification, variant_id="single_column_3section")
    """

    def __init__(self, max_consecutive_variant: int = 2, max_consecutive_type: int = 3):
        """
        Initialize diversity tracker.

        Args:
            max_consecutive_variant: Max consecutive slides with same variant_id
            max_consecutive_type: Max consecutive slides with same classification
        """
        self.max_consecutive_variant = max_consecutive_variant
        self.max_consecutive_type = max_consecutive_type

        # Track recent slides (last 5)
        self.recent_slides: deque = deque(maxlen=5)

        # Track all usage for analytics
        self.all_classifications: List[str] = []
        self.all_variants: List[str] = []

        # Track semantic groups
        self.semantic_groups: Dict[str, List[int]] = {}  # group_name -> [slide_numbers]

        logger.info(
            f"DiversityTracker initialized "
            f"(max_consecutive_variant={max_consecutive_variant}, "
            f"max_consecutive_type={max_consecutive_type})"
        )

    def add_slide(
        self,
        classification: str,
        variant_id: Optional[str] = None,
        semantic_group: Optional[str] = None,
        slide_number: Optional[int] = None
    ):
        """
        Add a slide to tracking history.

        Args:
            classification: Slide type classification
            variant_id: Variant ID (if available)
            semantic_group: Semantic group identifier (if any)
            slide_number: Slide position in presentation
        """
        slide_record = {
            "classification": classification,
            "variant_id": variant_id,
            "semantic_group": semantic_group,
            "slide_number": slide_number
        }

        self.recent_slides.append(slide_record)
        self.all_classifications.append(classification)

        if variant_id:
            self.all_variants.append(variant_id)

        if semantic_group:
            if semantic_group not in self.semantic_groups:
                self.semantic_groups[semantic_group] = []
            if slide_number:
                self.semantic_groups[semantic_group].append(slide_number)

        logger.debug(
            f"Tracked slide {slide_number}: {classification} "
            f"(variant: {variant_id}, group: {semantic_group})"
        )

    def should_override_for_diversity(
        self,
        classification: str,
        variant_id: Optional[str] = None,
        semantic_group: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Determine if classification should be overridden for diversity.

        Args:
            classification: Proposed classification
            variant_id: Proposed variant_id (if known)
            semantic_group: Semantic group (if any)

        Returns:
            Tuple of (should_override, suggested_classification)
            - should_override: True if diversity rules violated
            - suggested_classification: Alternative classification (or None)
        """
        # Rule 0: Semantic groups are exempt from diversity rules
        if semantic_group:
            logger.debug(
                f"Slide in semantic group '{semantic_group}' - exempt from diversity rules"
            )
            return False, None

        if len(self.recent_slides) < 2:
            # Not enough history yet
            return False, None

        # Rule 1: Check consecutive variant_id repetition
        if variant_id:
            recent_variants = [
                s["variant_id"] for s in self.recent_slides
                if s["variant_id"] is not None and s["semantic_group"] is None
            ]

            consecutive_count = self._count_consecutive(recent_variants, variant_id)

            if consecutive_count >= self.max_consecutive_variant:
                logger.warning(
                    f"Diversity violation: variant '{variant_id}' used "
                    f"{consecutive_count} consecutive times (max: {self.max_consecutive_variant})"
                )
                suggestion = self._suggest_alternative_classification(classification)
                return True, suggestion

        # Rule 2: Check consecutive classification repetition
        recent_classifications = [
            s["classification"] for s in self.recent_slides
            if s["semantic_group"] is None
        ]

        consecutive_count = self._count_consecutive(recent_classifications, classification)

        if consecutive_count >= self.max_consecutive_type:
            logger.warning(
                f"Diversity violation: classification '{classification}' used "
                f"{consecutive_count} consecutive times (max: {self.max_consecutive_type})"
            )
            suggestion = self._suggest_alternative_classification(classification)
            return True, suggestion

        # No violation
        return False, None

    def _count_consecutive(self, items: List[str], target: str) -> int:
        """
        Count how many times target appears consecutively at the end of items list.

        Args:
            items: List of items (most recent at end)
            target: Target item to count

        Returns:
            Number of consecutive occurrences at end
        """
        if not items:
            return 0

        count = 0
        for item in reversed(items):
            if item == target:
                count += 1
            else:
                break

        return count

    def _suggest_alternative_classification(self, current: str) -> Optional[str]:
        """
        Suggest an alternative classification to avoid repetition.

        Args:
            current: Current classification that's violating diversity

        Returns:
            Suggested alternative classification (or None if none found)
        """
        # Define alternative classifications for each type
        # UPDATED 2025-12-01: Using correct Text Service v1.2 classification names
        # Note: grid_3x3 does not exist in Text Service, use grid_2x2_centered instead
        alternatives = {
            "single_column": ["grid_2x2_centered", "sequential_3col", "asymmetric_8_4"],
            "grid_2x2_centered": ["matrix_2x2", "comparison_2col", "sequential_3col"],
            "matrix_2x2": ["grid_2x2_centered", "comparison_2col", "styled_table"],
            "comparison_2col": ["matrix_2x2", "styled_table", "grid_2x2_centered"],
            "sequential_3col": ["grid_2x2_centered", "asymmetric_8_4", "hybrid_1_2x2"],
            "metrics_grid": ["grid_2x2_centered", "single_column", "styled_table"],
            "styled_table": ["comparison_2col", "matrix_2x2", "grid_2x2_centered"],
            "hybrid_1_2x2": ["grid_2x2_centered", "sequential_3col", "asymmetric_8_4"],
            "asymmetric_8_4": ["single_column", "hybrid_1_2x2", "grid_2x2_centered"],
            "impact_quote": ["single_column", "asymmetric_8_4"]
        }

        if current not in alternatives:
            return None

        # Get alternatives that haven't been used recently
        recent_classifications = [s["classification"] for s in self.recent_slides]
        underused = [
            alt for alt in alternatives[current]
            if alt not in recent_classifications[-2:]  # Not in last 2 slides
        ]

        if underused:
            suggestion = underused[0]
            logger.info(f"Suggesting alternative: {current} → {suggestion}")
            return suggestion

        # If all alternatives were used recently, just return first alternative
        return alternatives[current][0]

    def get_diversity_metrics(self) -> Dict[str, Any]:
        """
        Calculate diversity metrics for the tracked presentation.

        Returns:
            Dict with diversity metrics:
            - total_slides: Number of slides tracked
            - unique_classifications: Number of unique classification types
            - unique_variants: Number of unique variants
            - diversity_score: 0-100 score (higher = more diverse)
            - classification_distribution: Count of each classification
            - variant_distribution: Count of each variant
            - semantic_groups: Detected semantic groups
        """
        total_slides = len(self.all_classifications)

        if total_slides == 0:
            return {
                "total_slides": 0,
                "unique_classifications": 0,
                "unique_variants": 0,
                "diversity_score": 0,
                "classification_distribution": {},
                "variant_distribution": {},
                "semantic_groups": {}
            }

        unique_classifications = len(set(self.all_classifications))
        unique_variants = len(set(self.all_variants))

        # Calculate diversity score (0-100)
        # Based on: unique_types / total_slides ratio
        # Perfect diversity: 10 unique types in 10 slides = 100%
        # Low diversity: 3 unique types in 10 slides = 30%
        diversity_score = min(100, int((unique_classifications / total_slides) * 100))

        # Bonus points for using underrepresented classifications
        classification_counts = Counter(self.all_classifications)
        even_distribution_bonus = 0
        if len(classification_counts) > 1:
            # Calculate standard deviation - lower is more even
            counts = list(classification_counts.values())
            mean = sum(counts) / len(counts)
            variance = sum((x - mean) ** 2 for x in counts) / len(counts)
            std_dev = variance ** 0.5

            # Low std_dev = even distribution = bonus points
            if std_dev < 1.5:
                even_distribution_bonus = 20
            elif std_dev < 2.5:
                even_distribution_bonus = 10

        diversity_score = min(100, diversity_score + even_distribution_bonus)

        return {
            "total_slides": total_slides,
            "unique_classifications": unique_classifications,
            "unique_variants": unique_variants,
            "diversity_score": diversity_score,
            "classification_distribution": dict(classification_counts),
            "variant_distribution": dict(Counter(self.all_variants)),
            "semantic_groups": {
                group: len(slides)
                for group, slides in self.semantic_groups.items()
            }
        }

    def get_summary(self) -> str:
        """
        Get human-readable diversity summary.

        Returns:
            Formatted summary string
        """
        metrics = self.get_diversity_metrics()

        summary = f"""
Diversity Metrics Summary:
==========================
Total Slides: {metrics['total_slides']}
Unique Classifications: {metrics['unique_classifications']}
Unique Variants: {metrics['unique_variants']}
Diversity Score: {metrics['diversity_score']}/100

Classification Distribution:
{self._format_distribution(metrics['classification_distribution'])}

Variant Distribution:
{self._format_distribution(metrics['variant_distribution'])}

Semantic Groups: {len(metrics['semantic_groups'])}
{self._format_semantic_groups(metrics['semantic_groups'])}
""".strip()

        return summary

    def _format_distribution(self, distribution: Dict[str, int]) -> str:
        """Format distribution dict as readable string."""
        if not distribution:
            return "  (none)"

        lines = []
        for item, count in sorted(
            distribution.items(),
            key=lambda x: x[1],
            reverse=True
        ):
            lines.append(f"  • {item}: {count}")

        return "\n".join(lines)

    def _format_semantic_groups(self, groups: Dict[str, int]) -> str:
        """Format semantic groups dict as readable string."""
        if not groups:
            return "  (none detected)"

        lines = []
        for group, count in groups.items():
            lines.append(f"  • {group}: {count} slides")

        return "\n".join(lines)


# Convenience functions

def create_diversity_tracker(
    max_consecutive_variant: int = 2,
    max_consecutive_type: int = 3
) -> DiversityTracker:
    """
    Create a diversity tracker with custom settings.

    Args:
        max_consecutive_variant: Max consecutive slides with same variant_id
        max_consecutive_type: Max consecutive slides with same classification

    Returns:
        DiversityTracker instance
    """
    return DiversityTracker(max_consecutive_variant, max_consecutive_type)


# Example usage
if __name__ == "__main__":
    print("Diversity Tracker - Test Example")
    print("=" * 70)

    tracker = DiversityTracker()

    # Simulate slide sequence
    slides = [
        ("single_column", "single_column_3section", None),
        ("single_column", "single_column_4section", None),
        ("grid_3x3", "grid_3x2", None),  # Good - diversity
        ("use_case_1", "matrix_2x2", "use_cases"),  # Semantic group
        ("use_case_2", "matrix_2x2", "use_cases"),  # Same group - allowed
        ("use_case_3", "matrix_2x2", "use_cases"),  # Same group - allowed
        ("single_column", "single_column_3section", None),  # OK - not consecutive
    ]

    for i, (classification, variant, group) in enumerate(slides, start=1):
        print(f"\nSlide {i}: {classification} (variant: {variant}, group: {group})")

        # Check diversity before adding
        should_override, suggestion = tracker.should_override_for_diversity(
            classification, variant, group
        )

        if should_override:
            print(f"  ⚠️ Diversity violation! Suggested: {suggestion}")
        else:
            print(f"  ✅ Diversity OK")

        # Add to tracker
        tracker.add_slide(classification, variant, group, i)

    # Print final metrics
    print("\n" + "=" * 70)
    print(tracker.get_summary())
