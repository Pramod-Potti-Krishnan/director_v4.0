"""
Layout Analyzer for Director Agent v4.0.25

Maps slide_type_hint from storyline to exact layout, service, and variant requirements.
This is the Step 2 of the two-step process: Storyline → Layout Analysis.

The service-layout mapping is hardcoded knowledge:
- Analytics: L02, C2, V2 (charts and data visualization)
- Diagram: C4, V3 (flow diagrams, architecture, Mermaid)
- Illustrator: C3, V4, L25* (pyramids, funnels, infographics)
- Text Service: L25*, L29, C1, V1, I1-I4, H1-H3 (text content)

* L25 is dual-purpose: Text Service for standard content, Illustrator for infographics

Author: Director v4.0.25 Story-Driven Coordination
Date: December 2024
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class LayoutSeriesMode(str, Enum):
    """Which layout series to use."""
    L_ONLY = "L_ONLY"       # Legacy only (L25, L29, L02)
    L_AND_C = "L_AND_C"     # Legacy + Content (adds C1-C4)
    C_AND_H = "C_AND_H"     # Content + Hero (C1-C4, H1-H3)
    ALL = "ALL"             # All series including V and I


@dataclass
class LayoutAnalysisResult:
    """Result of layout analysis for a slide."""
    layout: str                          # Exact layout ID (H1, L25, C2, etc.)
    service: str                         # Service to handle: text, analytics, diagram, illustrator
    variant_id: Optional[str]            # Pre-selected variant if known
    needs_variant_lookup: bool           # Whether to call Text Service /recommend-variant
    generation_instructions: Optional[str]  # Instructions for non-variant slides


class LayoutAnalyzer:
    """
    Analyzes slide_type_hint from storyline and determines exact layout/service.

    The two-step process:
    1. Storyline Generation: AI determines slide_type_hint and purpose
    2. Layout Analysis: This class maps to exact layout, service, variant strategy

    Service-Layout Mapping (hardcoded knowledge):
    ┌───────────────────┬─────────────────────────────────────────────────────┐
    │  SERVICE          │  LAYOUTS                                            │
    ├───────────────────┼─────────────────────────────────────────────────────┤
    │  Analytics        │  L02, C2, V2                                        │
    │  Diagram          │  C4, V3                                             │
    │  Illustrator      │  L25*, C3, V4                                       │
    │  Text Service     │  L25*, L29, C1, V1, I1-I4, H1-H3                   │
    └───────────────────┴─────────────────────────────────────────────────────┘
    """

    # Service-Layout mapping
    SERVICE_LAYOUTS = {
        "analytics": ["L02", "C2", "V2"],
        "diagram": ["C4", "V3"],
        "illustrator": ["C3", "V4", "L25"],  # L25 for pyramid/funnel only
        "text": ["L25", "L29", "C1", "V1", "I1", "I2", "I3", "I4", "H1", "H2", "H3"]
    }

    # Hero type to layout mapping
    HERO_LAYOUTS = {
        "title_slide": {"H": "H1", "L": "L29"},
        "section_divider": {"H": "H2", "L": "L29"},
        "closing_slide": {"H": "H3", "L": "L29"}
    }

    # Layouts that support variants (need Text Service /recommend-variant)
    VARIANT_LAYOUTS = {"L25", "C1"}

    # Default layout preferences by series mode
    LAYOUT_PREFERENCES = {
        LayoutSeriesMode.L_ONLY: {
            "text": "L25",
            "hero": "L29",
            "chart": "L02",
            "diagram": "L25",      # Fallback to L25 since no C4 in L_ONLY
            "infographic": "L25"  # Fallback to L25 since no C3 in L_ONLY
        },
        LayoutSeriesMode.L_AND_C: {
            "text": "C1",
            "hero": "L29",
            "chart": "C2",
            "diagram": "C4",
            "infographic": "C3"
        },
        LayoutSeriesMode.C_AND_H: {
            "text": "C1",
            "hero": "H1",  # Will be adjusted based on hero_type
            "chart": "C2",
            "diagram": "C4",
            "infographic": "C3"
        },
        LayoutSeriesMode.ALL: {
            "text": "C1",
            "hero": "H1",  # Will be adjusted based on hero_type
            "chart": "V2",  # V-series for visual layouts
            "diagram": "V3",
            "infographic": "V4"
        }
    }

    def __init__(self, series_mode: LayoutSeriesMode = LayoutSeriesMode.L_ONLY):
        """
        Initialize LayoutAnalyzer.

        Args:
            series_mode: Which layout series to use
        """
        self.series_mode = series_mode
        logger.info(f"LayoutAnalyzer initialized with series_mode={series_mode.value}")

    def analyze(
        self,
        slide_type_hint: str,
        hero_type: Optional[str] = None,
        topic_count: int = 3,
        purpose: Optional[str] = None,
        title: Optional[str] = None,
        topics: Optional[List[str]] = None
    ) -> LayoutAnalysisResult:
        """
        Analyze slide and determine layout, service, and variant strategy.

        Args:
            slide_type_hint: Story-driven type from AI (hero, text, chart, diagram, infographic)
            hero_type: For hero slides: title_slide, section_divider, closing_slide
            topic_count: Number of topics/bullets
            purpose: Slide purpose from storyline
            title: Slide title (for generation instructions)
            topics: Slide topics (for generation instructions)

        Returns:
            LayoutAnalysisResult with layout, service, variant_id, needs_variant_lookup
        """
        slide_type = slide_type_hint.lower() if slide_type_hint else "text"

        # Handle hero slides
        if slide_type == "hero":
            return self._analyze_hero(hero_type, purpose)

        # Handle chart slides (Analytics Service)
        if slide_type == "chart":
            return self._analyze_chart(purpose, title, topics)

        # Handle diagram slides (Diagram Service)
        if slide_type == "diagram":
            return self._analyze_diagram(purpose, title, topics)

        # Handle infographic slides (Illustrator Service)
        if slide_type == "infographic":
            return self._analyze_infographic(purpose, title, topics)

        # Default: text slides (Text Service)
        return self._analyze_text(topic_count, purpose)

    def _analyze_hero(
        self,
        hero_type: Optional[str],
        purpose: Optional[str]
    ) -> LayoutAnalysisResult:
        """Analyze hero slide."""
        # Determine hero subtype
        if not hero_type:
            # Infer from purpose
            if purpose in ["title_slide", "opening"]:
                hero_type = "title_slide"
            elif purpose in ["closing", "closing_slide", "thank_you"]:
                hero_type = "closing_slide"
            else:
                hero_type = "section_divider"

        # Get layout based on series mode
        if self.series_mode in [LayoutSeriesMode.C_AND_H, LayoutSeriesMode.ALL]:
            layout_map = self.HERO_LAYOUTS.get(hero_type, {"H": "H2", "L": "L29"})
            layout = layout_map["H"]
        else:
            layout = "L29"

        logger.debug(f"Hero slide analysis: hero_type={hero_type}, layout={layout}")

        return LayoutAnalysisResult(
            layout=layout,
            service="text",
            variant_id=None,  # Hero slides use hero_type for variant selection
            needs_variant_lookup=False,  # L29 variants are pre-determined by hero_type
            generation_instructions=None
        )

    def _analyze_chart(
        self,
        purpose: Optional[str],
        title: Optional[str],
        topics: Optional[List[str]]
    ) -> LayoutAnalysisResult:
        """Analyze chart slide (Analytics Service)."""
        # Get layout based on series mode
        prefs = self.LAYOUT_PREFERENCES.get(self.series_mode, {})
        layout = prefs.get("chart", "L02")

        # Generate chart instructions from purpose and topics
        instructions = self._generate_chart_instructions(purpose, title, topics)

        logger.debug(f"Chart slide analysis: layout={layout}, instructions={instructions[:50]}...")

        return LayoutAnalysisResult(
            layout=layout,
            service="analytics",
            variant_id=None,
            needs_variant_lookup=False,
            generation_instructions=instructions
        )

    def _analyze_diagram(
        self,
        purpose: Optional[str],
        title: Optional[str],
        topics: Optional[List[str]]
    ) -> LayoutAnalysisResult:
        """Analyze diagram slide (Diagram Service)."""
        prefs = self.LAYOUT_PREFERENCES.get(self.series_mode, {})
        layout = prefs.get("diagram", "C4")

        # If L_ONLY mode, fall back to L25 with Illustrator
        if self.series_mode == LayoutSeriesMode.L_ONLY:
            layout = "L25"
            service = "illustrator"  # Illustrator can handle some diagram-like visuals
        else:
            service = "diagram"

        instructions = self._generate_diagram_instructions(purpose, title, topics)

        logger.debug(f"Diagram slide analysis: layout={layout}, service={service}")

        return LayoutAnalysisResult(
            layout=layout,
            service=service,
            variant_id=None,
            needs_variant_lookup=False,
            generation_instructions=instructions
        )

    def _analyze_infographic(
        self,
        purpose: Optional[str],
        title: Optional[str],
        topics: Optional[List[str]]
    ) -> LayoutAnalysisResult:
        """Analyze infographic slide (Illustrator Service)."""
        prefs = self.LAYOUT_PREFERENCES.get(self.series_mode, {})
        layout = prefs.get("infographic", "L25")

        instructions = self._generate_infographic_instructions(purpose, title, topics)

        logger.debug(f"Infographic slide analysis: layout={layout}")

        return LayoutAnalysisResult(
            layout=layout,
            service="illustrator",
            variant_id=None,
            needs_variant_lookup=False,
            generation_instructions=instructions
        )

    def _analyze_text(
        self,
        topic_count: int,
        purpose: Optional[str]
    ) -> LayoutAnalysisResult:
        """Analyze text slide (Text Service)."""
        prefs = self.LAYOUT_PREFERENCES.get(self.series_mode, {})
        layout = prefs.get("text", "L25")

        # Text slides need variant lookup from Text Service
        needs_variant = layout in self.VARIANT_LAYOUTS

        logger.debug(f"Text slide analysis: layout={layout}, needs_variant={needs_variant}")

        return LayoutAnalysisResult(
            layout=layout,
            service="text",
            variant_id=None,  # Will be determined by Text Service /recommend-variant
            needs_variant_lookup=needs_variant,
            generation_instructions=None
        )

    def _generate_chart_instructions(
        self,
        purpose: Optional[str],
        title: Optional[str],
        topics: Optional[List[str]]
    ) -> str:
        """Generate chart generation instructions from slide context."""
        parts = []

        # Infer chart type from purpose
        chart_type = "Line chart"
        if purpose:
            purpose_lower = purpose.lower()
            if "market" in purpose_lower or "share" in purpose_lower:
                chart_type = "Pie chart"
            elif "comparison" in purpose_lower or "compare" in purpose_lower:
                chart_type = "Bar chart"
            elif "trend" in purpose_lower or "growth" in purpose_lower or "traction" in purpose_lower:
                chart_type = "Line chart"
            elif "distribution" in purpose_lower:
                chart_type = "Histogram"

        parts.append(f"{chart_type} showing")

        if title:
            parts.append(title.lower())

        if topics:
            data_points = ", ".join(topics[:4])
            parts.append(f"with data points: {data_points}")

        return " ".join(parts)

    def _generate_diagram_instructions(
        self,
        purpose: Optional[str],
        title: Optional[str],
        topics: Optional[List[str]]
    ) -> str:
        """Generate diagram generation instructions from slide context."""
        parts = []

        # Infer diagram type from purpose
        diagram_type = "Flow diagram"
        if purpose:
            purpose_lower = purpose.lower()
            if "architecture" in purpose_lower or "system" in purpose_lower:
                diagram_type = "Architecture diagram"
            elif "process" in purpose_lower or "workflow" in purpose_lower:
                diagram_type = "Flow diagram"
            elif "sequence" in purpose_lower:
                diagram_type = "Sequence diagram"
            elif "org" in purpose_lower or "structure" in purpose_lower:
                diagram_type = "Organization diagram"

        parts.append(f"{diagram_type} showing")

        if title:
            parts.append(title.lower())

        if topics:
            steps = " → ".join(topics[:5])
            parts.append(f"with steps: {steps}")

        return " ".join(parts)

    def _generate_infographic_instructions(
        self,
        purpose: Optional[str],
        title: Optional[str],
        topics: Optional[List[str]]
    ) -> str:
        """Generate infographic generation instructions from slide context."""
        parts = []

        # Infer infographic type from purpose
        infographic_type = "Visual hierarchy"
        if purpose:
            purpose_lower = purpose.lower()
            if "pyramid" in purpose_lower or "hierarchy" in purpose_lower:
                infographic_type = "Pyramid"
            elif "funnel" in purpose_lower or "conversion" in purpose_lower:
                infographic_type = "Funnel"
            elif "value" in purpose_lower or "proposition" in purpose_lower:
                infographic_type = "Value pyramid"
            elif "cycle" in purpose_lower:
                infographic_type = "Cycle diagram"

        parts.append(f"{infographic_type} showing")

        if title:
            parts.append(title.lower())

        if topics:
            topic_count = len(topics)
            parts.append(f"with {topic_count} levels: {', '.join(topics)}")

        return " ".join(parts)

    def get_service_for_layout(self, layout: str) -> str:
        """Get the service responsible for a given layout."""
        for service, layouts in self.SERVICE_LAYOUTS.items():
            if layout in layouts:
                return service
        return "text"  # Default to text service


# Convenience function
def analyze_slide_layout(
    slide_type_hint: str,
    hero_type: Optional[str] = None,
    topic_count: int = 3,
    purpose: Optional[str] = None,
    series_mode: str = "L_ONLY"
) -> LayoutAnalysisResult:
    """
    Convenience function to analyze a slide's layout requirements.

    Args:
        slide_type_hint: Story-driven type (hero, text, chart, diagram, infographic)
        hero_type: For hero slides (title_slide, section_divider, closing_slide)
        topic_count: Number of topics
        purpose: Slide purpose
        series_mode: Layout series mode (L_ONLY, L_AND_C, C_AND_H, ALL)

    Returns:
        LayoutAnalysisResult with layout, service, variant strategy
    """
    mode = LayoutSeriesMode(series_mode)
    analyzer = LayoutAnalyzer(series_mode=mode)
    return analyzer.analyze(slide_type_hint, hero_type, topic_count, purpose)
