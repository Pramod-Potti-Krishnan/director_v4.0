"""
Slide Type Classifier for Director v3.4
========================================

Classifies slides into 13 taxonomy types for routing to specialized generators.

Classification Strategy:
1. L29 Hero Classification (position-based)
2. L25 Content Classification (10-priority heuristics)
"""

import re
from typing import Optional, Dict, Any, List
from src.models.agents import Slide
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class SlideTypeClassifier:
    """
    Classifies slides into 14 taxonomy types.

    L29 Hero Types (3):
    - title_slide: First slide
    - section_divider: Middle divider slides
    - closing_slide: Last slide

    L25 Content Types (10):
    - impact_quote: Quote-focused slides
    - metrics_grid: Metric/statistic cards
    - matrix_2x2: 4-quadrant matrix
    - grid_3x3: 9-cell grid
    - styled_table: Tabular data
    - bilateral_comparison: Two-column comparison
    - sequential_3col: 3-step process
    - hybrid_1_2x2: Overview + 2x2 grid
    - asymmetric_8_4: Main + sidebar
    - single_column: Dense single-column (default)

    Visualization Types (1):
    - pyramid: Hierarchical pyramid visualization (Illustrator Service)
    """

    # Keywords for classification (v3.4-diversity: Expanded keyword sets)
    # Aligned with generate_strawman.md taxonomy

    QUOTE_KEYWORDS = {
        "quote", "quotation", "testimonial", "said", "stated",
        "said by", "according to", "states that", "believes that",
        "mission statement", "vision statement", "powerful statement"
    }

    METRICS_KEYWORDS = {
        "metric", "kpi", "statistic", "number", "figure", "data point",
        "performance indicator", "key metric", "dashboard", "scorecard",
        "trend arrow", "growth", "improvement", "quarterly metric"
    }

    # v3.4-pyramid: Pyramid visualization keywords (Illustrator Service)
    PYRAMID_KEYWORDS = {
        "pyramid", "hierarchical", "hierarchy", "organizational structure",
        "levels", "tier", "tiers", "tiered", "layered", "layers",
        "foundation to top", "base to peak", "top to bottom",
        "organizational chart", "org chart", "reporting structure",
        "escalation", "progression", "maslow", "food pyramid",
        "pyramid structure", "pyramid model", "pyramid framework",
        "from foundation", "building blocks", "level 1", "level 2",
        "3 levels", "4 levels", "5 levels", "6 levels",
        "three tiers", "four tiers", "five tiers", "six tiers"
    }

    # v3.4-analytics: Analytics/Chart visualization keywords (Analytics Service v3.7.0)
    # Supports 18 chart types: 14 Chart.js + 4 D3.js
    # These keywords help Director AI identify slides that benefit from data visualization
    ANALYTICS_KEYWORDS = {
        # Core analytics terms
        "chart", "graph", "analytics", "data visualization", "visualization",
        "revenue", "sales", "growth", "performance", "metrics",
        "quarterly", "monthly", "annual", "year-over-year", "yoy",
        "kpi", "key performance indicator", "metric dashboard", "scorecard",
        "financial data", "business metrics", "operational metrics",
        "show data", "visualize data", "plot data", "display metrics",
        "Q1", "Q2", "Q3", "Q4", "fiscal year", "fy",
        "percentage", "percent", "%", "increase", "decrease",

        # Chart type specific keywords
        "pie chart", "donut chart", "doughnut chart", "bar chart", "line chart",
        "scatter plot", "histogram", "trend", "trending", "time series",
        "comparison chart", "benchmark", "benchmarking",
        "revenue over time", "quarterly comparison", "growth chart",
        "target vs actual", "forecast vs actual", "budget vs actual",

        # Multi-series and composition keywords (area, stacked, grouped)
        "cumulative", "stacked breakdown", "grouped comparison", "side by side",
        "composition over time", "revenue breakdown", "cost structure",
        "segment contribution", "layered data", "multiple series",
        "area chart", "filled area", "cumulative growth",

        # Mixed chart keywords
        "mixed chart", "combined visualization", "revenue vs cost",
        "actual vs target", "multiple metrics", "dual axis",

        # D3 Treemap keywords
        "treemap", "hierarchical breakdown", "budget allocation",
        "resource distribution", "nested rectangles", "proportional sizing",
        "department spending", "portfolio composition", "market share breakdown",

        # D3 Sunburst keywords
        "sunburst", "radial hierarchy", "circular breakdown", "concentric circles",
        "multi-level structure", "organizational breakdown", "nested hierarchy",
        "radial diagram", "circular layout",

        # D3 Choropleth USA keywords
        "map", "geographic", "by state", "state-level", "regional distribution",
        "USA map", "state-by-state", "choropleth", "color-coded map",
        "geographic distribution", "regional performance", "state performance",
        "california", "texas", "new york", "florida", "illinois",
        "regional sales", "market penetration", "geographic breakdown",

        # D3 Sankey keywords
        "flow", "sankey", "flow diagram", "allocation flow", "process flow",
        "from to", "→", "->", "energy flow", "budget flow", "resource flow",
        "customer journey", "workflow", "allocation breakdown", "transfer",
        "revenue allocation", "department allocation", "source to destination"
    }

    MATRIX_KEYWORDS = {
        "matrix", "quadrant", "2x2", "2 x 2", "four quadrants",
        "pros vs cons", "pros and cons", "benefits vs drawbacks",
        "trade-offs", "trade offs", "strengths weaknesses",
        "swot", "swot analysis", "strategic framework",
        "comparing", "comparison matrix"
    }

    GRID_KEYWORDS = {
        "grid", "3x3", "2x3", "3x2", "2x2 grid", "nine",
        "catalog", "gallery", "showcase", "collection",
        "6 items", "9 elements", "6 features", "9 features",
        "portfolio", "feature set", "capabilities", "offerings"
    }

    TABLE_KEYWORDS = {
        "table", "rows", "columns", "data grid", "comparison table",
        "feature matrix", "pricing table", "specification",
        "structured comparison", "decision matrix", "summary table"
    }

    COMPARISON_KEYWORDS = {
        "compare", "comparison", "versus", "vs", "vs.", "v.s.",
        "option a", "option b", "option c", "alternative",
        "choose between", "differences between", "which option",
        "side by side", "side-by-side", "compare and contrast",
        "tier 1", "tier 2", "tier 3", "plan comparison"
    }

    SEQUENTIAL_KEYWORDS = {
        "step", "stage", "phase", "sequential", "process",
        "workflow", "roadmap", "timeline steps",
        "3 steps", "4 steps", "5 steps", "three steps", "four steps",
        "4 phases", "5 phases", "implementation", "onboarding",
        "journey", "pathway", "progression"
    }

    HYBRID_KEYWORDS = {
        "hybrid", "overview + details", "overview plus details",
        "summary + breakdown", "summary plus breakdown",
        "header with grid", "top summary", "overview with"
    }

    ASYMMETRIC_KEYWORDS = {
        "asymmetric", "sidebar", "main + supporting",
        "main content plus supporting", "primary plus secondary",
        "8:4 split", "main and sidebar", "case study with stats"
    }

    # v3.4-diversity: Single column keywords (for explicit detection)
    SINGLE_COLUMN_KEYWORDS = {
        "single column", "list", "sections", "bullet points",
        "3 sections", "4 sections", "5 sections",
        "detailed breakdown", "comprehensive list"
    }

    @classmethod
    def classify(cls, slide: Slide, position: int, total_slides: int) -> str:
        """
        Classify a slide into one of 13 taxonomy types.

        Args:
            slide: Slide object to classify
            position: Slide position (1-indexed)
            total_slides: Total number of slides

        Returns:
            slide_type: One of 13 taxonomy types
        """
        logger.info(f"Classifying slide {position}/{total_slides}: {slide.title}")

        # Step 1: Check for L29 Hero types (position-based)
        hero_type = cls._classify_hero(slide, position, total_slides)
        if hero_type:
            logger.info(f"  → Classified as hero: {hero_type}")
            return hero_type

        # Step 2: Classify as L25 Content type (heuristic-based)
        content_type = cls._classify_content(slide)
        logger.info(f"  → Classified as content: {content_type}")
        return content_type

    @classmethod
    def _classify_hero(cls, slide: Slide, position: int, total_slides: int) -> Optional[str]:
        """
        Classify as L29 hero slide based on position and indicators.

        Args:
            slide: Slide object
            position: Slide position (1-indexed)
            total_slides: Total slides in presentation

        Returns:
            Hero type or None if not hero
        """
        # First slide → title_slide
        if position == 1:
            return "title_slide"

        # Last slide → closing_slide
        if position == total_slides:
            return "closing_slide"

        # Middle slides: check for section divider indicators
        title_lower = slide.title.lower()
        narrative_lower = slide.narrative.lower()

        divider_indicators = {
            "section", "part", "chapter", "agenda", "overview",
            "introduction to", "moving to", "next:"
        }

        # Check if title or narrative contains divider indicators
        combined_text = f"{title_lower} {narrative_lower}"
        for indicator in divider_indicators:
            if indicator in combined_text:
                # Additional check: slide should be relatively simple (few key points)
                if len(slide.key_points) <= 3:
                    return "section_divider"

        # Not a hero slide
        return None

    @classmethod
    def _classify_content(cls, slide: Slide) -> str:
        """
        Classify as L25 content type using 12-priority heuristics.

        Priority Order:
        1. Quote → impact_quote
        2. Analytics → analytics (v3.4-analytics: Analytics Service - charts/graphs)
        3. Metrics → metrics_grid (static KPI cards, not charts)
        4. Pyramid → pyramid (v3.4-pyramid: Illustrator Service)
        5. Matrix → matrix_2x2
        6. Grid → grid_3x3
        7. Table → styled_table
        8. Comparison → bilateral_comparison
        9. Sequential → sequential_3col
        10. Hybrid → hybrid_1_2x2
        11. Asymmetric → asymmetric_8_4
        12. Default → single_column

        Args:
            slide: Slide object

        Returns:
            Slide type (one of 13 types: 10 L25 + 2 visualizations + 1 default)
        """
        # Combine all text for analysis
        text_corpus = cls._build_text_corpus(slide)

        # Priority 1: Quote detection
        if cls._contains_keywords(text_corpus, cls.QUOTE_KEYWORDS):
            return "impact_quote"

        # Priority 2: Analytics/Chart detection (v3.4-analytics: Analytics Service)
        # Detect data visualizations, charts, and analytics slides BEFORE metrics
        # This prevents confusion between static metrics cards and dynamic charts
        # CRITICAL v3.4.2: Only classify as analytics if slide has L02 layout
        # Analytics Service currently only works with L02 (L01/L03 planned for future)
        if cls._contains_keywords(text_corpus, cls.ANALYTICS_KEYWORDS):
            # Check if slide has L02 layout (the only analytics-compatible layout currently)
            if hasattr(slide, 'layout_id') and slide.layout_id == 'L02':
                return "analytics"
            # Non-L02 slides with analytics keywords → fall through to text content types
            logger.debug(
                f"Slide has analytics keywords but layout '{getattr(slide, 'layout_id', 'unknown')}' "
                f"is not L02 (analytics layout). Falling through to text content types."
            )

        # Priority 3: Metrics detection (static KPI cards, not charts)
        if cls._contains_keywords(text_corpus, cls.METRICS_KEYWORDS):
            # Check for 3-card pattern (common for metrics)
            if "3" in text_corpus or "three" in text_corpus:
                return "metrics_grid"

        # Priority 4: Pyramid detection (v3.4-pyramid: Illustrator Service)
        # Detect hierarchical/pyramid structures early (very specific pattern)
        if cls._contains_keywords(text_corpus, cls.PYRAMID_KEYWORDS):
            return "pyramid"

        # Priority 5: Matrix detection
        if cls._contains_keywords(text_corpus, cls.MATRIX_KEYWORDS):
            return "matrix_2x2"

        # Priority 6: Grid detection
        if cls._contains_keywords(text_corpus, cls.GRID_KEYWORDS):
            return "grid_3x3"

        # Priority 7: Table detection
        if slide.tables_needed or cls._contains_keywords(text_corpus, cls.TABLE_KEYWORDS):
            return "styled_table"

        # Priority 8: Comparison detection
        if cls._contains_keywords(text_corpus, cls.COMPARISON_KEYWORDS):
            return "bilateral_comparison"

        # Priority 9: Sequential detection
        if cls._contains_keywords(text_corpus, cls.SEQUENTIAL_KEYWORDS):
            return "sequential_3col"

        # Priority 10: Hybrid detection
        if cls._contains_keywords(text_corpus, cls.HYBRID_KEYWORDS):
            return "hybrid_1_2x2"

        # Priority 11: Asymmetric detection
        if cls._contains_keywords(text_corpus, cls.ASYMMETRIC_KEYWORDS):
            return "asymmetric_8_4"

        # Priority 12: Default to single_column
        # Used for dense, detailed content that doesn't fit other patterns
        return "single_column"

    @classmethod
    def _build_text_corpus(cls, slide: Slide) -> str:
        """
        Build combined text corpus from slide for analysis.

        Args:
            slide: Slide object

        Returns:
            Lowercase combined text
        """
        parts = [
            slide.title,
            slide.narrative,
            " ".join(slide.key_points),
            slide.structure_preference or "",
            slide.analytics_needed or "",
            slide.diagrams_needed or "",
            slide.tables_needed or ""
        ]

        return " ".join(parts).lower()

    @classmethod
    def _contains_keywords(cls, text: str, keywords: set) -> bool:
        """
        Check if text contains any of the keywords.

        Args:
            text: Text to search (already lowercase)
            keywords: Set of keywords to match

        Returns:
            True if any keyword found
        """
        for keyword in keywords:
            if keyword in text:
                return True
        return False

    @classmethod
    def detect_semantic_group(cls, slide: Slide) -> Optional[str]:
        """
        Detect if slide is part of a semantic group (v3.4-diversity feature).

        Looks for markers like **[GROUP: use_cases]** in the narrative field.

        Args:
            slide: Slide object

        Returns:
            Group identifier (e.g., "use_cases") or None if not in a group
        """
        narrative = slide.narrative or ""

        # Pattern: **[GROUP: group_name]**
        import re
        pattern = r'\*\*\[GROUP:\s*([a-z_]+)\]\*\*'
        match = re.search(pattern, narrative, re.IGNORECASE)

        if match:
            group_name = match.group(1).lower()
            logger.debug(f"Detected semantic group: '{group_name}' in slide '{slide.title}'")
            return group_name

        return None

    @classmethod
    def classify_batch(cls, slides: List[Slide]) -> List[str]:
        """
        Classify multiple slides in batch.

        Args:
            slides: List of Slide objects

        Returns:
            List of slide types (same order as input)
        """
        total_slides = len(slides)
        slide_types = []

        for position, slide in enumerate(slides, start=1):
            slide_type = cls.classify(slide, position, total_slides)
            slide_types.append(slide_type)

        return slide_types

    @classmethod
    def get_classification_reasoning(cls, slide: Slide, position: int, total_slides: int) -> Dict[str, Any]:
        """
        Get detailed classification reasoning for debugging.

        Args:
            slide: Slide object
            position: Slide position
            total_slides: Total slides

        Returns:
            Dict with classification details and reasoning
        """
        slide_type = cls.classify(slide, position, total_slides)
        text_corpus = cls._build_text_corpus(slide)

        reasoning = {
            "slide_type": slide_type,
            "position": position,
            "total_slides": total_slides,
            "is_first": position == 1,
            "is_last": position == total_slides,
            "matched_keywords": [],
            "classification_path": []
        }

        # Determine classification path
        if position == 1:
            reasoning["classification_path"].append("Position-based: First slide → title_slide")
        elif position == total_slides:
            reasoning["classification_path"].append("Position-based: Last slide → closing_slide")
        else:
            # Check content-based classification
            if cls._contains_keywords(text_corpus, cls.QUOTE_KEYWORDS):
                reasoning["matched_keywords"].extend(list(cls.QUOTE_KEYWORDS & set(text_corpus.split())))
                reasoning["classification_path"].append("Priority 1: Quote keywords → impact_quote")

            elif cls._contains_keywords(text_corpus, cls.METRICS_KEYWORDS):
                reasoning["matched_keywords"].extend(list(cls.METRICS_KEYWORDS & set(text_corpus.split())))
                reasoning["classification_path"].append("Priority 2: Metrics keywords → metrics_grid")

            # ... similar for other priorities

            if not reasoning["matched_keywords"]:
                reasoning["classification_path"].append("Priority 10: Default → single_column")

        return reasoning


# Convenience function

def classify_slide(slide: Slide, position: int, total_slides: int) -> str:
    """
    Classify a slide (convenience function).

    Args:
        slide: Slide object
        position: Slide position (1-indexed)
        total_slides: Total slides in presentation

    Returns:
        Classified slide type
    """
    return SlideTypeClassifier.classify(slide, position, total_slides)


# Example usage
if __name__ == "__main__":
    print("Slide Type Classifier (v3.4-pyramid)")
    print("=" * 70)
    print("\nClassification Strategy:")
    print("  L29 Hero Types (3):")
    print("    • title_slide: First slide (position-based)")
    print("    • section_divider: Middle divider slides (keyword-based)")
    print("    • closing_slide: Last slide (position-based)")
    print("\n  L25 Content Types (10):")
    print("    Priority 1: impact_quote (quote keywords)")
    print("    Priority 2: metrics_grid (metric keywords)")
    print("    Priority 3: pyramid (pyramid keywords) [v3.4-pyramid: Illustrator Service]")
    print("    Priority 4: matrix_2x2 (matrix keywords)")
    print("    Priority 5: grid_3x3 (grid keywords)")
    print("    Priority 6: styled_table (table keywords)")
    print("    Priority 7: bilateral_comparison (comparison keywords)")
    print("    Priority 8: sequential_3col (sequential keywords)")
    print("    Priority 9: hybrid_1_2x2 (hybrid keywords)")
    print("    Priority 10: asymmetric_8_4 (asymmetric keywords)")
    print("    Priority 11: single_column (default)")
    print("\n  Visualization Types (1):")
    print("    • pyramid: Hierarchical pyramid (Illustrator Service v1.0)")
    print("\n" + "=" * 70)
    print(f"Total Slide Types: 14 (3 hero + 10 content + 1 visualization)")
