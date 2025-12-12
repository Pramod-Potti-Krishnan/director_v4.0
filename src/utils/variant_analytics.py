"""
Variant Analytics for Director v3.4
=====================================

Provides comprehensive analytics for variant usage, diversity metrics,
and classification accuracy across presentations.

Features:
- Track variant usage patterns
- Analyze diversity scores
- Identify underused variants
- Generate usage reports
- Monitor classification accuracy
- Export analytics data

Author: Director v3.4 Variant Diversity Enhancement
Date: 2025-01-11
"""

from typing import Dict, List, Optional, Any, Tuple
from collections import Counter, defaultdict
from datetime import datetime
import json
from pathlib import Path

from src.models.agents import PresentationStrawman, Slide
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class VariantAnalytics:
    """
    Comprehensive analytics for variant usage and diversity.

    Usage:
        analytics = VariantAnalytics()

        # Record a presentation
        analytics.record_presentation(
            session_id="sess_123",
            strawman=presentation_strawman,
            diversity_metrics=diversity_tracker.get_diversity_metrics()
        )

        # Get analytics report
        report = analytics.generate_report()
        print(report)

        # Identify underused variants
        underused = analytics.get_underused_variants(threshold=5)
    """

    def __init__(self, analytics_dir: Optional[Path] = None):
        """
        Initialize variant analytics tracker.

        Args:
            analytics_dir: Directory to store analytics data (optional)
        """
        self.analytics_dir = analytics_dir or Path("analytics")
        self.analytics_dir.mkdir(exist_ok=True)

        # In-memory analytics data
        self.presentations: List[Dict[str, Any]] = []
        self.variant_usage: Counter = Counter()
        self.classification_usage: Counter = Counter()
        self.diversity_scores: List[int] = []

        # Load existing analytics if available
        self._load_analytics()

        logger.info(f"VariantAnalytics initialized (dir: {self.analytics_dir})")

    def record_presentation(
        self,
        session_id: str,
        strawman: PresentationStrawman,
        diversity_metrics: Dict[str, Any],
        stage: str = "GENERATE_STRAWMAN"
    ):
        """
        Record a presentation for analytics.

        Args:
            session_id: Session identifier
            strawman: Presentation strawman object
            diversity_metrics: Diversity metrics from DiversityTracker
            stage: Which stage generated this (GENERATE_STRAWMAN or REFINE_STRAWMAN)
        """
        timestamp = datetime.utcnow().isoformat()

        # Extract variant and classification data
        variants_used = []
        classifications_used = []

        for slide in strawman.slides:
            if hasattr(slide, 'variant_id') and slide.variant_id:
                variants_used.append(slide.variant_id)
                self.variant_usage[slide.variant_id] += 1

            if hasattr(slide, 'slide_type_classification') and slide.slide_type_classification:
                classifications_used.append(slide.slide_type_classification)
                self.classification_usage[slide.slide_type_classification] += 1

        # Record diversity score
        diversity_score = diversity_metrics.get('diversity_score', 0)
        self.diversity_scores.append(diversity_score)

        # Create presentation record
        presentation_record = {
            "session_id": session_id,
            "timestamp": timestamp,
            "stage": stage,
            "metadata": {
                "title": strawman.main_title,
                "slide_count": len(strawman.slides),
                "target_audience": strawman.target_audience,
                "duration": strawman.presentation_duration
            },
            "variants": {
                "used": variants_used,
                "unique_count": len(set(variants_used)),
                "distribution": dict(Counter(variants_used))
            },
            "classifications": {
                "used": classifications_used,
                "unique_count": len(set(classifications_used)),
                "distribution": dict(Counter(classifications_used))
            },
            "diversity": diversity_metrics,
            "semantic_groups": diversity_metrics.get('semantic_groups', {})
        }

        self.presentations.append(presentation_record)

        logger.info(
            f"📊 Recorded presentation: {session_id} "
            f"({len(variants_used)} slides, diversity: {diversity_score}/100)"
        )

        # Auto-save analytics
        self._save_analytics()

    def generate_report(self, last_n: Optional[int] = None) -> str:
        """
        Generate comprehensive analytics report.

        Args:
            last_n: Only include last N presentations (None = all)

        Returns:
            Formatted analytics report
        """
        presentations_to_analyze = self.presentations[-last_n:] if last_n else self.presentations

        if not presentations_to_analyze:
            return "No presentation data available for analytics."

        total_presentations = len(presentations_to_analyze)
        total_slides = sum(p['metadata']['slide_count'] for p in presentations_to_analyze)

        # Diversity statistics
        diversity_scores = [p['diversity']['diversity_score'] for p in presentations_to_analyze]
        avg_diversity = sum(diversity_scores) / len(diversity_scores) if diversity_scores else 0
        min_diversity = min(diversity_scores) if diversity_scores else 0
        max_diversity = max(diversity_scores) if diversity_scores else 0

        # Variant usage statistics
        all_variants = []
        for p in presentations_to_analyze:
            all_variants.extend(p['variants']['used'])

        variant_counts = Counter(all_variants)
        total_unique_variants = len(variant_counts)

        # Classification usage statistics
        all_classifications = []
        for p in presentations_to_analyze:
            all_classifications.extend(p['classifications']['used'])

        classification_counts = Counter(all_classifications)
        total_unique_classifications = len(classification_counts)

        # Build report
        report = f"""
{'='*80}
VARIANT DIVERSITY ANALYTICS REPORT
{'='*80}

OVERVIEW:
  Total Presentations Analyzed: {total_presentations}
  Total Slides Generated: {total_slides}
  Analysis Period: {presentations_to_analyze[0]['timestamp'][:10]} to {presentations_to_analyze[-1]['timestamp'][:10]}

DIVERSITY METRICS:
  Average Diversity Score: {avg_diversity:.1f}/100
  Minimum Diversity Score: {min_diversity}/100
  Maximum Diversity Score: {max_diversity}/100

  Score Interpretation:
    • 80-100: Excellent diversity (varied layouts)
    • 60-79:  Good diversity (some variety)
    • 40-59:  Fair diversity (limited variety)
    • 0-39:   Poor diversity (repetitive layouts)

VARIANT USAGE:
  Total Unique Variants Used: {total_unique_variants} of 34 available
  Variant Coverage: {(total_unique_variants/34)*100:.1f}%

  Top 10 Most Used Variants:
{self._format_top_items(variant_counts, 10)}

  Underused Variants (< 5% of slides):
{self._format_underused_variants(variant_counts, total_slides)}

CLASSIFICATION USAGE:
  Total Unique Classifications: {total_unique_classifications} of 13 available
  Classification Coverage: {(total_unique_classifications/13)*100:.1f}%

  Classification Distribution:
{self._format_distribution(classification_counts)}

RECOMMENDATIONS:
{self._generate_recommendations(variant_counts, classification_counts, avg_diversity, total_slides)}

{'='*80}
""".strip()

        return report

    def get_underused_variants(self, threshold: int = 5) -> List[str]:
        """
        Get list of variants used fewer than threshold times.

        Args:
            threshold: Minimum usage count

        Returns:
            List of underused variant IDs
        """
        underused = [
            variant for variant, count in self.variant_usage.items()
            if count < threshold
        ]
        return sorted(underused)

    def get_overused_variants(self, threshold: float = 0.15) -> List[Tuple[str, int, float]]:
        """
        Get variants used more than threshold percentage of total slides.

        Args:
            threshold: Maximum usage percentage (0.0 to 1.0)

        Returns:
            List of (variant_id, count, percentage) tuples
        """
        total_slides = sum(self.variant_usage.values())
        if total_slides == 0:
            return []

        overused = []
        for variant, count in self.variant_usage.most_common():
            percentage = count / total_slides
            if percentage > threshold:
                overused.append((variant, count, percentage))

        return overused

    def get_classification_accuracy(self) -> Dict[str, Any]:
        """
        Analyze classification accuracy and distribution.

        Returns:
            Dict with classification metrics
        """
        total_classifications = sum(self.classification_usage.values())

        if total_classifications == 0:
            return {
                "total": 0,
                "unique": 0,
                "distribution": {},
                "single_column_percentage": 0,
                "accuracy_score": 0
            }

        # Calculate single_column dominance (indicator of classification issues)
        single_column_count = self.classification_usage.get('single_column', 0)
        single_column_pct = (single_column_count / total_classifications) * 100

        # Accuracy score: Lower single_column % = better classification
        # Target: < 40% single_column (good), < 20% (excellent)
        accuracy_score = max(0, 100 - (single_column_pct * 1.5))

        return {
            "total": total_classifications,
            "unique": len(self.classification_usage),
            "distribution": dict(self.classification_usage),
            "single_column_percentage": single_column_pct,
            "accuracy_score": int(accuracy_score),
            "interpretation": self._interpret_classification_accuracy(single_column_pct)
        }

    def export_analytics(self, filename: Optional[str] = None) -> Path:
        """
        Export analytics data to JSON file.

        Args:
            filename: Custom filename (optional, auto-generated if None)

        Returns:
            Path to exported file
        """
        if filename is None:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"variant_analytics_{timestamp}.json"

        export_path = self.analytics_dir / filename

        export_data = {
            "export_timestamp": datetime.utcnow().isoformat(),
            "summary": {
                "total_presentations": len(self.presentations),
                "total_slides": sum(p['metadata']['slide_count'] for p in self.presentations),
                "avg_diversity_score": sum(self.diversity_scores) / len(self.diversity_scores) if self.diversity_scores else 0,
                "unique_variants_used": len(self.variant_usage),
                "unique_classifications_used": len(self.classification_usage)
            },
            "variant_usage": dict(self.variant_usage),
            "classification_usage": dict(self.classification_usage),
            "presentations": self.presentations
        }

        with open(export_path, 'w') as f:
            json.dump(export_data, f, indent=2)

        logger.info(f"📁 Analytics exported to: {export_path}")
        return export_path

    def _save_analytics(self):
        """Save analytics data to persistent storage."""
        analytics_file = self.analytics_dir / "variant_analytics.json"

        data = {
            "last_updated": datetime.utcnow().isoformat(),
            "variant_usage": dict(self.variant_usage),
            "classification_usage": dict(self.classification_usage),
            "diversity_scores": self.diversity_scores,
            "presentations": self.presentations
        }

        with open(analytics_file, 'w') as f:
            json.dump(data, f, indent=2)

    def _load_analytics(self):
        """Load analytics data from persistent storage."""
        analytics_file = self.analytics_dir / "variant_analytics.json"

        if not analytics_file.exists():
            logger.debug("No existing analytics data found")
            return

        try:
            with open(analytics_file, 'r') as f:
                data = json.load(f)

            self.variant_usage = Counter(data.get('variant_usage', {}))
            self.classification_usage = Counter(data.get('classification_usage', {}))
            self.diversity_scores = data.get('diversity_scores', [])
            self.presentations = data.get('presentations', [])

            logger.info(
                f"📂 Loaded analytics: {len(self.presentations)} presentations, "
                f"{len(self.variant_usage)} unique variants tracked"
            )
        except Exception as e:
            logger.warning(f"Failed to load analytics data: {e}")

    def _format_top_items(self, counter: Counter, limit: int) -> str:
        """Format top items from counter."""
        if not counter:
            return "    (no data)"

        lines = []
        for i, (item, count) in enumerate(counter.most_common(limit), 1):
            lines.append(f"    {i:2d}. {item}: {count} uses")

        return "\n".join(lines)

    def _format_distribution(self, counter: Counter) -> str:
        """Format distribution from counter."""
        if not counter:
            return "    (no data)"

        total = sum(counter.values())
        lines = []

        for item, count in sorted(counter.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total) * 100
            bar = "█" * int(percentage / 5)  # Visual bar
            lines.append(f"    • {item:25s}: {count:3d} ({percentage:5.1f}%) {bar}")

        return "\n".join(lines)

    def _format_underused_variants(self, variant_counts: Counter, total_slides: int) -> str:
        """Format underused variants section."""
        if total_slides == 0:
            return "    (no data)"

        threshold_pct = 0.05  # 5%
        threshold_count = int(total_slides * threshold_pct)

        underused = [
            (variant, count)
            for variant, count in variant_counts.items()
            if count < threshold_count
        ]

        if not underused:
            return "    ✅ No underused variants (all variants used appropriately)"

        lines = []
        for variant, count in sorted(underused, key=lambda x: x[1]):
            percentage = (count / total_slides) * 100
            lines.append(f"    • {variant}: {count} uses ({percentage:.1f}%)")

        return "\n".join(lines)

    def _generate_recommendations(
        self,
        variant_counts: Counter,
        classification_counts: Counter,
        avg_diversity: float,
        total_slides: int
    ) -> str:
        """Generate actionable recommendations."""
        recommendations = []

        # Diversity recommendations
        if avg_diversity < 40:
            recommendations.append(
                "⚠️  LOW DIVERSITY: Presentations show repetitive layouts. Review Stage 4 prompt "
                "to ensure LLM uses classification keywords in structure_preference."
            )
        elif avg_diversity < 60:
            recommendations.append(
                "📊 FAIR DIVERSITY: Some variety present but room for improvement. Consider "
                "enhancing keyword sets in slide_type_classifier.py."
            )
        else:
            recommendations.append(
                "✅ GOOD DIVERSITY: Presentations show healthy variety in slide layouts."
            )

        # Variant usage recommendations
        variant_coverage = len(variant_counts) / 34 * 100
        if variant_coverage < 40:
            recommendations.append(
                f"📉 LOW VARIANT COVERAGE: Only {variant_coverage:.0f}% of available variants used. "
                "This suggests classification is defaulting to few types. Review keyword matching."
            )
        elif variant_coverage < 60:
            recommendations.append(
                f"📈 MODERATE VARIANT COVERAGE: {variant_coverage:.0f}% of variants used. "
                "Consider expanding classification keyword sets for better coverage."
            )

        # Single column dominance check
        single_column_pct = (classification_counts.get('single_column', 0) / total_slides) * 100
        if single_column_pct > 50:
            recommendations.append(
                f"⚠️  SINGLE-COLUMN DOMINANCE: {single_column_pct:.0f}% of slides use single_column. "
                "This indicates classification keyword matching needs improvement."
            )

        # Overused variants check
        overused = self.get_overused_variants(threshold=0.20)
        if overused:
            top_overused = overused[0]
            recommendations.append(
                f"🔁 OVERUSED VARIANT: '{top_overused[0]}' used for {top_overused[2]*100:.0f}% of slides. "
                "Consider if diversity rules are being bypassed by semantic groups."
            )

        if not recommendations:
            recommendations.append("✅ All metrics look healthy. No specific recommendations.")

        return "\n".join(f"  {i+1}. {rec}" for i, rec in enumerate(recommendations))

    def _interpret_classification_accuracy(self, single_column_pct: float) -> str:
        """Interpret classification accuracy based on single_column percentage."""
        if single_column_pct < 20:
            return "Excellent - Classification working well"
        elif single_column_pct < 40:
            return "Good - Acceptable classification accuracy"
        elif single_column_pct < 60:
            return "Fair - Classification needs improvement"
        else:
            return "Poor - Classification defaulting to single_column too often"


# Convenience functions

def create_analytics(analytics_dir: Optional[Path] = None) -> VariantAnalytics:
    """
    Create a VariantAnalytics instance.

    Args:
        analytics_dir: Directory for analytics storage

    Returns:
        VariantAnalytics instance
    """
    return VariantAnalytics(analytics_dir=analytics_dir)


# Example usage
if __name__ == "__main__":
    print("Variant Analytics - Test Example")
    print("=" * 80)

    analytics = VariantAnalytics()

    # Simulate some presentation data
    from collections import Counter

    # Mock data
    analytics.variant_usage = Counter({
        'single_column_3section': 45,
        'single_column_4section': 38,
        'single_column_5section': 32,
        'grid_3x2': 15,
        'matrix_2x2': 12,
        'comparison_2col': 10,
        'sequential_3col': 8,
        'metrics_grid_3card': 6,
        'asymmetric_8_4': 4,
        'hybrid_1_2x2': 3
    })

    analytics.classification_usage = Counter({
        'single_column': 115,
        'grid_3x3': 15,
        'matrix_2x2': 12,
        'comparison_2col': 10,
        'sequential_3col': 8,
        'metrics_grid': 6,
        'asymmetric_8_4': 4,
        'hybrid_1_2x2': 3
    })

    analytics.diversity_scores = [45, 52, 38, 61, 55, 48, 43, 59, 47, 51]

    # Generate report
    print("\n" + "=" * 80)
    print(analytics.generate_report())

    # Get classification accuracy
    print("\n" + "=" * 80)
    print("CLASSIFICATION ACCURACY:")
    accuracy = analytics.get_classification_accuracy()
    print(f"  Accuracy Score: {accuracy['accuracy_score']}/100")
    print(f"  Interpretation: {accuracy['interpretation']}")
    print(f"  Single Column %: {accuracy['single_column_percentage']:.1f}%")
