"""
Chart Type Mapper for Analytics Refinement
===========================================

Maps user-friendly chart type keywords to Analytics Service chart_ids
during refinement operations.

Author: Director v3.4 Integration Team
Date: November 16, 2025
"""

import re
from typing import Optional, Dict
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class ChartTypeMapper:
    """
    Maps natural language chart type requests to Analytics Service chart_ids.

    Used during refinement when users request chart type changes like:
    - "change slide 3 from line chart to bar chart"
    - "make the revenue slide a doughnut chart"
    - "convert to scatter plot"
    """

    # Mapping from keywords to chart_ids
    CHART_TYPE_MAPPINGS: Dict[str, str] = {
        # Line chart variations
        "line": "line",
        "line chart": "line",
        "trend": "line",
        "trend line": "line",

        # Bar chart variations (vertical)
        "bar": "bar_vertical",
        "bar chart": "bar_vertical",
        "vertical bar": "bar_vertical",
        "column": "bar_vertical",
        "column chart": "bar_vertical",

        # Horizontal bar variations
        "horizontal bar": "bar_horizontal",
        "horizontal": "bar_horizontal",
        "bar horizontal": "bar_horizontal",

        # Pie chart variations
        "pie": "pie",
        "pie chart": "pie",

        # Doughnut variations
        "doughnut": "doughnut",
        "doughnut chart": "doughnut",
        "donut": "doughnut",
        "donut chart": "doughnut",

        # Scatter plot variations
        "scatter": "scatter",
        "scatter plot": "scatter",
        "scatterplot": "scatter",
        "scatter chart": "scatter",

        # Bubble chart variations
        "bubble": "bubble",
        "bubble chart": "bubble",
        "bubble plot": "bubble",

        # Radar chart variations
        "radar": "radar",
        "radar chart": "radar",
        "spider": "radar",
        "spider chart": "radar",

        # Polar area variations
        "polar": "polar_area",
        "polar area": "polar_area",
        "polar chart": "polar_area",
        "polar area chart": "polar_area",
    }

    @classmethod
    def extract_chart_type_from_request(
        cls,
        user_request: str
    ) -> Optional[str]:
        """
        Extract chart type from user refinement request.

        Args:
            user_request: User's refinement request

        Returns:
            chart_id (e.g., "line", "bar_vertical", "pie") or None if not detected

        Example:
            >>> ChartTypeMapper.extract_chart_type_from_request(
            ...     "change slide 3 from line chart to bar chart"
            ... )
            "bar_vertical"
        """
        request_lower = user_request.lower()

        # Try each mapping
        for keyword, chart_id in cls.CHART_TYPE_MAPPINGS.items():
            # Look for patterns like:
            # - "to [chart type]"
            # - "make it a [chart type]"
            # - "use [chart type]"
            # - "change to [chart type]"
            patterns = [
                rf'\bto (?:a |an )?{re.escape(keyword)}\b',
                rf'\bmake (?:it |.*? )?(?:a |an )?{re.escape(keyword)}\b',
                rf'\buse (?:a |an )?{re.escape(keyword)}\b',
                rf'\bchange (?:to |.*? to )?(?:a |an )?{re.escape(keyword)}\b',
                rf'\bconvert (?:to |.*? to )?(?:a |an )?{re.escape(keyword)}\b',
                rf'\b{re.escape(keyword)} instead\b',
                rf'\bas (?:a |an )?{re.escape(keyword)}\b',
            ]

            for pattern in patterns:
                if re.search(pattern, request_lower):
                    logger.debug(
                        f"Detected chart type '{chart_id}' from keyword '{keyword}' "
                        f"in request: '{user_request[:100]}...'"
                    )
                    return chart_id

        logger.debug(f"No chart type detected in request: '{user_request[:100]}...'")
        return None

    @classmethod
    def is_valid_chart_type(cls, chart_id: str) -> bool:
        """
        Validate if chart_id is a valid Analytics chart type.

        Args:
            chart_id: Chart type identifier

        Returns:
            True if valid, False otherwise
        """
        valid_types = {
            "line", "bar_vertical", "bar_horizontal",
            "pie", "doughnut", "scatter", "bubble",
            "radar", "polar_area"
        }

        return chart_id in valid_types

    @classmethod
    def get_chart_type_display_name(cls, chart_id: str) -> str:
        """
        Get display name for chart_id.

        Args:
            chart_id: Chart type identifier

        Returns:
            Human-readable chart type name
        """
        display_names = {
            "line": "Line Chart",
            "bar_vertical": "Vertical Bar Chart",
            "bar_horizontal": "Horizontal Bar Chart",
            "pie": "Pie Chart",
            "doughnut": "Doughnut Chart",
            "scatter": "Scatter Plot",
            "bubble": "Bubble Chart",
            "radar": "Radar Chart",
            "polar_area": "Polar Area Chart",
        }

        return display_names.get(chart_id, chart_id)

    @classmethod
    def suggest_structure_preference_for_chart(
        cls,
        chart_id: str,
        narrative: Optional[str] = None
    ) -> str:
        """
        Generate structure_preference text for a chart type.

        Args:
            chart_id: Chart type identifier
            narrative: Optional slide narrative for context

        Returns:
            structure_preference text with chart type keyword
        """
        display_name = cls.get_chart_type_display_name(chart_id)

        # Extract subject from narrative if available
        if narrative:
            # Simple extraction - use first few words as subject
            words = narrative.split()
            subject = " ".join(words[:5]) if len(words) >= 5 else narrative
            subject = subject.rstrip(".")
        else:
            subject = "data"

        # Generate structure_preference
        templates = {
            "line": f"{display_name} showing {subject} trends over time",
            "bar_vertical": f"{display_name} comparing {subject} across categories",
            "bar_horizontal": f"{display_name} ranking {subject} from highest to lowest",
            "pie": f"{display_name} showing {subject} distribution",
            "doughnut": f"{display_name} visualizing {subject} composition",
            "scatter": f"{display_name} analyzing correlation in {subject}",
            "bubble": f"{display_name} showing multi-dimensional {subject} analysis",
            "radar": f"{display_name} comparing {subject} across multiple dimensions",
            "polar_area": f"{display_name} displaying {subject} by category",
        }

        return templates.get(chart_id, f"{display_name} visualizing {subject}")


# Convenience functions
def extract_chart_type_from_refinement(user_request: str) -> Optional[str]:
    """
    Extract chart type from user refinement request (convenience function).

    Args:
        user_request: User's refinement request

    Returns:
        chart_id or None

    Example:
        >>> extract_chart_type_from_refinement("change to bar chart")
        "bar_vertical"
    """
    return ChartTypeMapper.extract_chart_type_from_request(user_request)


def is_valid_chart_type(chart_id: str) -> bool:
    """
    Validate chart_id (convenience function).

    Args:
        chart_id: Chart type identifier

    Returns:
        True if valid
    """
    return ChartTypeMapper.is_valid_chart_type(chart_id)


# Example usage
if __name__ == "__main__":
    print("Chart Type Mapper - Analytics Refinement Support")
    print("=" * 70)
    print()

    # Test extraction
    test_requests = [
        "change slide 3 from line chart to bar chart",
        "make the revenue slide a doughnut chart",
        "convert to scatter plot",
        "use radar chart for the skills slide",
        "slide 5 should be a bubble chart instead",
        "change to horizontal bar",
    ]

    print("Chart Type Extraction Tests:")
    for request in test_requests:
        chart_id = ChartTypeMapper.extract_chart_type_from_request(request)
        if chart_id:
            display_name = ChartTypeMapper.get_chart_type_display_name(chart_id)
            print(f"✅ '{request}'")
            print(f"   → chart_id: '{chart_id}' ({display_name})")
        else:
            print(f"❌ '{request}'")
            print(f"   → No chart type detected")
        print()

    # Test structure_preference generation
    print("Structure Preference Generation:")
    test_narratives = [
        ("line", "Quarterly revenue has grown steadily"),
        ("pie", "Market share is distributed across competitors"),
        ("radar", "Product features compared across dimensions"),
    ]

    for chart_id, narrative in test_narratives:
        structure_pref = ChartTypeMapper.suggest_structure_preference_for_chart(
            chart_id=chart_id,
            narrative=narrative
        )
        print(f"{chart_id}: '{structure_pref}'")

    print()
    print("=" * 70)
