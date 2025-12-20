"""
Layout Payload Assembler - v4.4
================================

Assembles layout-specific payloads matching SLIDE_GENERATION_INPUT_SPEC.md exactly.

This is the bridge between service responses and Layout Service expectations.
Each layout has specific field requirements that MUST be met.

Key Responsibility:
- Map service response fields to Layout Service field names
- Assemble complete payload structure for each layout type
- Inject branding (footer/logo) where applicable

Field Mapping (Service → Layout Service):
- Text v1.2.2: Returns spec-compliant fields directly! (slide_title, body, background_color)
- Analytics v3.0: Returns spec-compliant fields directly! (chart_html, body, element_4)
- Illustrator v1.0.2: Returns spec-compliant fields directly! (infographic_html)
- Diagram v3.0: Returns spec-compliant fields directly! (diagram_html, mermaid_code)

ALL FOUR services now return spec-compliant field names - no Director mapping needed!

v4.2: Stage 6 - Layout-aligned content generation
v4.3: Text Service v1.2.2 integration
      - Text Service /v1.2/slides/* endpoints now return spec-compliant fields
      - slide_title, subtitle, body, background_color returned directly
      - I-series includes aliases (slide_title, body, not title_html, content_html)
      - C1-text uses combined generation (1 LLM call instead of 3)
v4.4: All services alignment complete!
      - Text v1.2.2: slide_title, body, background_color aliases
      - Analytics v3.0: chart_html, element_4, body aliases
      - Illustrator v1.0.2: infographic_html alias
      - Diagram v3.0: diagram_html + mermaid_code (for debugging)
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class AssemblyContext:
    """Context for payload assembly."""
    slide_number: int
    total_slides: int
    presentation_title: Optional[str] = None
    theme_id: Optional[str] = None


class LayoutPayloadAssembler:
    """
    Assembles layout-specific payloads matching SLIDE_GENERATION_INPUT_SPEC.

    Each layout has a specific content structure that the Layout/Deck-Builder
    service expects. This class ensures the correct fields are assembled
    with proper names.

    Usage:
        assembler = LayoutPayloadAssembler()
        payload = assembler.assemble(
            layout="C3-chart",
            slide_title="<h2>Revenue Growth</h2>",
            subtitle="<p>FY 2024 Results</p>",
            content={"chart_html": "<canvas>...</canvas>"},
            branding=branding_config
        )
    """

    # Layouts that should not receive footer/logo branding
    HERO_LAYOUTS = {"H1-generated", "H1-structured", "H2-section", "L29"}

    # Layouts that get full-bleed hero content
    FULL_BLEED_LAYOUTS = {"H1-generated", "L29"}

    def assemble(
        self,
        layout: str,
        slide_title: Optional[str],
        subtitle: Optional[str],
        content: Dict[str, Any],
        branding: Optional[Any] = None,
        context: Optional[AssemblyContext] = None,
        background_color: Optional[str] = None,
        background_image: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Assemble a layout-specific payload.

        Args:
            layout: Layout ID (L25, C3-chart, C5-diagram, etc.)
            slide_title: HTML string for title (e.g., "<h2>Title</h2>")
            subtitle: HTML string for subtitle (e.g., "<p>Subtitle</p>")
            content: Service response content (varies by service)
            branding: PresentationBranding config (optional)
            context: AssemblyContext with slide/presentation info
            background_color: Hex color for slide background
            background_image: URL for background image

        Returns:
            Dict with layout, content, and optional background fields
        """
        context = context or AssemblyContext(slide_number=1, total_slides=1)

        # Dispatch to layout-specific assembler
        if layout in self.FULL_BLEED_LAYOUTS:
            payload = self._assemble_hero_generated(content)
        elif layout == "H1-structured":
            payload = self._assemble_hero_structured(slide_title, subtitle, content)
        elif layout == "H2-section":
            payload = self._assemble_section_divider(slide_title, content, context)
        elif layout == "H3-closing":
            payload = self._assemble_closing(slide_title, subtitle, content, branding)
        elif layout == "L25":
            payload = self._assemble_l25(slide_title, subtitle, content, branding, context)
        elif layout == "C1-text":
            payload = self._assemble_c1_text(slide_title, subtitle, content, branding)
        elif layout.startswith("I") and layout[1].isdigit():
            payload = self._assemble_iseries(layout, slide_title, subtitle, content)
        elif layout == "V1-image-text":
            payload = self._assemble_v1_image_text(slide_title, subtitle, content)
        elif layout in ["C3-chart", "C3"]:
            payload = self._assemble_c3_chart(slide_title, subtitle, content)
        elif layout in ["V2-chart-text", "V2"]:
            payload = self._assemble_v2_chart_text(slide_title, subtitle, content)
        elif layout == "L02":
            payload = self._assemble_l02(slide_title, content)
        elif layout in ["C5-diagram", "C5"]:
            payload = self._assemble_c5_diagram(slide_title, subtitle, content)
        elif layout in ["V3-diagram-text", "V3"]:
            payload = self._assemble_v3_diagram_text(slide_title, subtitle, content)
        elif layout in ["C4-infographic", "C4"]:
            payload = self._assemble_c4_infographic(slide_title, subtitle, content)
        elif layout in ["V4-infographic-text", "V4"]:
            payload = self._assemble_v4_infographic_text(slide_title, subtitle, content)
        elif layout == "S3-two-visuals":
            payload = self._assemble_s3_two_visuals(slide_title, subtitle, content)
        elif layout == "S4-comparison":
            payload = self._assemble_s4_comparison(slide_title, subtitle, content)
        elif layout.startswith("X"):
            payload = self._assemble_x_series(layout, slide_title, subtitle, content)
        else:
            # Fallback to L25 for unknown layouts
            logger.warning(f"Unknown layout '{layout}', falling back to L25 structure")
            payload = self._assemble_l25(slide_title, subtitle, content, branding, context)

        # Add layout to payload
        payload["layout"] = layout

        # Add background fields if provided (slide-level, outside content)
        if background_color:
            payload["background_color"] = background_color
        if background_image:
            payload["background_image"] = background_image

        return payload

    # ==================== Hero Layouts ====================

    def _assemble_hero_generated(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """
        H1-generated, L29: Full-bleed hero with complete HTML.

        Expected content fields:
        - hero_content OR hero_html OR content: Complete HTML for 1920x1080
        """
        hero_html = (
            content.get("hero_content") or
            content.get("hero_html") or
            content.get("content") or
            content.get("html") or
            ""
        )

        return {
            "content": {
                "hero_content": hero_html
            }
        }

    def _assemble_hero_structured(
        self,
        slide_title: Optional[str],
        subtitle: Optional[str],
        content: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        H1-structured: Structured title slide with editable fields.

        Expected content fields:
        - author_info: Author name, date, etc.
        """
        return {
            "content": {
                "slide_title": slide_title or "",
                "subtitle": subtitle or "",
                "author_info": content.get("author_info", "")
            }
        }

    def _assemble_section_divider(
        self,
        slide_title: Optional[str],
        content: Dict[str, Any],
        context: AssemblyContext
    ) -> Dict[str, Any]:
        """
        H2-section: Section divider with number and title.

        Expected content fields:
        - section_number: Section number (e.g., "01", "02")
        """
        # Try to get section number from content, or generate from context
        section_number = content.get("section_number", "")
        if not section_number and context.slide_number > 1:
            # Generate section number based on slide position
            section_number = f"{context.slide_number - 1:02d}"

        return {
            "content": {
                "section_number": section_number,
                "slide_title": slide_title or ""
            }
        }

    def _assemble_closing(
        self,
        slide_title: Optional[str],
        subtitle: Optional[str],
        content: Dict[str, Any],
        branding: Optional[Any]
    ) -> Dict[str, Any]:
        """
        H3-closing: Closing/thank you slide.

        Expected content fields:
        - contact_info: Contact details, links, etc.
        """
        contact_info = content.get("contact_info", "")

        # If branding has footer text and no contact_info, use footer as contact
        if not contact_info and branding and hasattr(branding, 'footer'):
            if branding.footer.text:
                contact_info = branding.footer.text

        return {
            "content": {
                "slide_title": slide_title or "Thank You",
                "subtitle": subtitle or "",
                "contact_info": contact_info
            }
        }

    # ==================== Content Layouts ====================

    def _assemble_l25(
        self,
        slide_title: Optional[str],
        subtitle: Optional[str],
        content: Dict[str, Any],
        branding: Optional[Any],
        context: AssemblyContext
    ) -> Dict[str, Any]:
        """
        L25: Main content shell with rich_content.

        Expected content fields:
        - rich_content OR html: HTML content from Text Service
        """
        rich_content = (
            content.get("rich_content") or
            content.get("html") or
            content.get("content_html") or
            ""
        )

        result = {
            "content": {
                "slide_title": slide_title or "",
                "subtitle": subtitle or "",
                "rich_content": rich_content
            }
        }

        # Add branding if available
        if branding:
            if hasattr(branding, 'logo') and branding.logo.url:
                result["content"]["company_logo"] = branding.logo.url
            if context.presentation_title:
                result["content"]["presentation_name"] = context.presentation_title

        return result

    def _assemble_c1_text(
        self,
        slide_title: Optional[str],
        subtitle: Optional[str],
        content: Dict[str, Any],
        branding: Optional[Any]
    ) -> Dict[str, Any]:
        """
        C1-text: Text content with body.

        v4.3: Text Service v1.2.2 /v1.2/slides/C1-text endpoint now returns:
        - slide_title, subtitle, body, rich_content, background_color
        - All in 1 LLM call (67% reduction from previous 3 calls)

        Expected content fields (in priority order):
        - body (v1.2.2 standard) OR html OR content_html: Main text content
        """
        # v4.3: Text Service v1.2.2 returns 'body' directly
        body = (
            content.get("body") or
            content.get("html") or
            content.get("content_html") or
            ""
        )

        result = {
            "content": {
                "slide_title": slide_title or "",
                "subtitle": subtitle or "",
                "body": body
            }
        }

        # Add branding if available
        if branding:
            if hasattr(branding, 'footer') and branding.footer.text:
                result["content"]["footer_text"] = branding.footer.text
            if hasattr(branding, 'logo') and branding.logo.url:
                result["content"]["company_logo"] = branding.logo.url

        return result

    # ==================== I-Series (Image + Content) ====================

    def _assemble_iseries(
        self,
        layout: str,
        slide_title: Optional[str],
        subtitle: Optional[str],
        content: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        I1-I4: Image + text layouts.

        v4.3: Text Service v1.2.2 now returns spec-compliant field names directly:
        - slide_title, subtitle, body, image_url, background_color
        - No more mapping from title_html/content_html needed!

        Expected content fields (in priority order):
        - body (v1.2.2 standard) OR html OR content_html: Text content
        - image_url: URL to image
        """
        # v4.3: Text Service v1.2.2 returns 'body' directly, but we support legacy fallbacks
        body = (
            content.get("body") or
            content.get("html") or
            content.get("content_html") or
            ""
        )

        image_url = content.get("image_url", "")

        return {
            "content": {
                "slide_title": slide_title or "",
                "subtitle": subtitle or "",
                "image_url": image_url,
                "body": body
            }
        }

    def _assemble_v1_image_text(
        self,
        slide_title: Optional[str],
        subtitle: Optional[str],
        content: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        V1-image-text: Image on left, text on right.

        Same structure as I-series.
        """
        return self._assemble_iseries("V1", slide_title, subtitle, content)

    # ==================== Chart Layouts ====================

    def _assemble_c3_chart(
        self,
        slide_title: Optional[str],
        subtitle: Optional[str],
        content: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        C3-chart: Single chart slide.

        v4.4: Analytics v3.0 now returns chart_html directly (alias for element_3).
        No mapping needed - assembler still supports legacy element_3 for compatibility.

        Expected content fields:
        - chart_html (v3.0 standard) OR element_3 (legacy): Chart HTML from Analytics
        """
        # v4.4: Analytics v3.0 returns chart_html directly, element_3 kept for legacy
        chart_html = (
            content.get("chart_html") or
            content.get("element_3") or
            content.get("html") or
            ""
        )

        return {
            "content": {
                "slide_title": slide_title or "",
                "subtitle": subtitle or "",
                "chart_html": chart_html
            }
        }

    def _assemble_v2_chart_text(
        self,
        slide_title: Optional[str],
        subtitle: Optional[str],
        content: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        V2-chart-text: Chart on left, text insights on right.

        v4.4: Analytics v3.0 now returns chart_html and body directly.
        No mapping needed - assembler still supports legacy fields for compatibility.

        Expected content fields:
        - chart_html (v3.0 standard) OR element_3 (legacy): Chart HTML
        - body (v3.0 standard) OR element_2 (legacy): Text insights
        """
        # v4.4: Analytics v3.0 returns chart_html directly
        chart_html = (
            content.get("chart_html") or
            content.get("element_3") or
            ""
        )

        # v4.4: Analytics v3.0 returns body directly (alias for element_2)
        body = (
            content.get("body") or
            content.get("element_2") or
            content.get("insights") or
            ""
        )

        return {
            "content": {
                "slide_title": slide_title or "",
                "subtitle": subtitle or "",
                "chart_html": chart_html,
                "body": body
            }
        }

    def _assemble_l02(
        self,
        slide_title: Optional[str],
        content: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        L02: Analytics-native layout with element slots.

        v4.4: Analytics v3.0 now returns element_4 directly (SPEC-compliant).
        The SPEC requires element_4 for the diagram slot, which Analytics now provides.
        Legacy element_3 still supported for backward compatibility.

        Expected content fields:
        - element_1: Title/label for diagram area (optional)
        - element_2: Text observations
        - element_4 (v3.0 standard) OR element_3 (legacy): Diagram/chart HTML
        """
        return {
            "content": {
                "slide_title": slide_title or "",
                "element_1": content.get("element_1", ""),
                "element_2": content.get("element_2", ""),
                # v4.4: Analytics v3.0 returns element_4 directly (SPEC-compliant)
                "element_4": content.get("element_4") or content.get("element_3", "")
            }
        }

    # ==================== Diagram Layouts ====================

    def _assemble_c5_diagram(
        self,
        slide_title: Optional[str],
        subtitle: Optional[str],
        content: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        C5-diagram: Single diagram slide.

        v4.4 Diagram Service v3.0 returns spec-compliant fields:
        - diagram_html: Inline SVG (PREFERRED - use directly)
        - svg_content: Legacy field (still supported)
        - mermaid_code: Source code for debugging
        - diagram_url: Cloud storage URL fallback
        """
        diagram_html = self._extract_diagram_html(content)

        return {
            "content": {
                "slide_title": slide_title or "",
                "subtitle": subtitle or "",
                "diagram_html": diagram_html
            }
        }

    def _assemble_v3_diagram_text(
        self,
        slide_title: Optional[str],
        subtitle: Optional[str],
        content: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        V3-diagram-text: Diagram on left, text on right.

        v4.4 Diagram Service v3.0 returns spec-compliant fields:
        - diagram_html: Inline SVG (PREFERRED - use directly)
        - svg_content: Legacy field (still supported)
        - body: Text insights (from Text Service)
        """
        diagram_html = self._extract_diagram_html(content)
        body = content.get("body", "")

        return {
            "content": {
                "slide_title": slide_title or "",
                "subtitle": subtitle or "",
                "diagram_html": diagram_html,
                "body": body
            }
        }

    def _extract_diagram_html(self, content: Dict[str, Any]) -> str:
        """
        Extract diagram HTML with v4.4 preference order.

        Diagram Service v3.0 now returns spec-compliant `diagram_html` directly,
        but we maintain fallback chain for backward compatibility:

        Preference order:
        1. diagram_html - Spec-compliant alias (v3.0+, PREFERRED)
        2. svg_content  - Legacy inline SVG field
        3. html         - Generic HTML fallback
        4. diagram_url  - URL wrapped in img tag (last resort)
        """
        # v4.4: Diagram Service v3.0 returns diagram_html directly
        if content.get("diagram_html"):
            return content["diagram_html"]

        # Legacy: SVG content from older Diagram Service
        if content.get("svg_content"):
            return content["svg_content"]

        # Generic html field
        if content.get("html"):
            return content["html"]

        # URL-based fallback - wrap in img tag
        if content.get("diagram_url"):
            url = content["diagram_url"]
            return f'<img src="{url}" class="diagram-image" style="max-width:100%;max-height:100%;" />'

        return ""

    # ==================== Infographic Layouts ====================

    def _assemble_c4_infographic(
        self,
        slide_title: Optional[str],
        subtitle: Optional[str],
        content: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        C4-infographic: Single infographic slide.

        v4.4: Illustrator v1.0.2 now returns infographic_html directly.
        No mapping needed - assembler still supports legacy html for compatibility.

        Expected content fields:
        - infographic_html (v1.0.2 standard) OR html (legacy): Infographic HTML
        """
        infographic_html = self._extract_infographic_html(content)

        return {
            "content": {
                "slide_title": slide_title or "",
                "subtitle": subtitle or "",
                "infographic_html": infographic_html
            }
        }

    def _assemble_v4_infographic_text(
        self,
        slide_title: Optional[str],
        subtitle: Optional[str],
        content: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        V4-infographic-text: Infographic on left, text on right.

        v4.4: Illustrator v1.0.2 now returns infographic_html directly.
        No mapping needed - assembler still supports legacy html for compatibility.

        Expected content fields:
        - infographic_html (v1.0.2 standard) OR html (legacy): Infographic HTML
        - body: Text insights (from Text Service)
        """
        infographic_html = self._extract_infographic_html(content)
        body = content.get("body", "")

        return {
            "content": {
                "slide_title": slide_title or "",
                "subtitle": subtitle or "",
                "infographic_html": infographic_html,
                "body": body
            }
        }

    def _extract_infographic_html(self, content: Dict[str, Any]) -> str:
        """
        Extract infographic HTML from various field names.

        v4.4: Illustrator v1.0.2 returns infographic_html directly (preferred).
        Legacy html field still supported for backward compatibility.
        """
        # v4.4: Illustrator v1.0.2 returns infographic_html directly
        if content.get("infographic_html"):
            return content["infographic_html"]

        # Legacy: Illustrator v1.0.0 returns html
        if content.get("html"):
            return content["html"]

        # SVG content (diagram compatibility)
        if content.get("svg_content"):
            return content["svg_content"]

        return ""

    # ==================== Split Layouts ====================

    def _assemble_s3_two_visuals(
        self,
        slide_title: Optional[str],
        subtitle: Optional[str],
        content: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        S3-two-visuals: Two charts/diagrams side by side.

        Expected content fields:
        - visual_left_html: Left visual HTML
        - visual_right_html: Right visual HTML
        - caption_left: Left caption
        - caption_right: Right caption
        """
        return {
            "content": {
                "slide_title": slide_title or "",
                "subtitle": subtitle or "",
                "visual_left_html": content.get("visual_left_html", ""),
                "visual_right_html": content.get("visual_right_html", ""),
                "caption_left": content.get("caption_left", ""),
                "caption_right": content.get("caption_right", "")
            }
        }

    def _assemble_s4_comparison(
        self,
        slide_title: Optional[str],
        subtitle: Optional[str],
        content: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        S4-comparison: Two columns for comparison.

        Expected content fields:
        - header_left: Left column header
        - header_right: Right column header
        - content_left: Left column content
        - content_right: Right column content
        """
        return {
            "content": {
                "slide_title": slide_title or "",
                "subtitle": subtitle or "",
                "header_left": content.get("header_left", ""),
                "header_right": content.get("header_right", ""),
                "content_left": content.get("content_left", ""),
                "content_right": content.get("content_right", "")
            }
        }

    # ==================== X-Series Dynamic Layouts ====================

    def _assemble_x_series(
        self,
        layout: str,
        slide_title: Optional[str],
        subtitle: Optional[str],
        content: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        X1-X5: Dynamic zone-based layouts.

        Expected content fields:
        - base_layout: The base layout (C1-text, I1, etc.)
        - split_pattern: The split pattern ID
        - zones: List of zone content objects
        """
        base_layout = content.get("base_layout", "C1-text")
        split_pattern = content.get("split_pattern", "")
        zones = content.get("zones", [])

        return {
            "base_layout": base_layout,
            "split_pattern": split_pattern,
            "content": {
                "slide_title": slide_title or "",
                "subtitle": subtitle or ""
            },
            "zones": zones
        }


# Convenience function
def assemble_layout_payload(
    layout: str,
    slide_title: Optional[str],
    subtitle: Optional[str],
    content: Dict[str, Any],
    branding: Optional[Any] = None,
    slide_number: int = 1,
    total_slides: int = 1,
    presentation_title: Optional[str] = None,
    background_color: Optional[str] = None,
    background_image: Optional[str] = None
) -> Dict[str, Any]:
    """
    Convenience function for assembling layout payloads.

    Args:
        layout: Layout ID
        slide_title: HTML title
        subtitle: HTML subtitle
        content: Service response content
        branding: Optional branding config
        slide_number: Position in presentation
        total_slides: Total slide count
        presentation_title: Presentation title for footer
        background_color: Hex color
        background_image: URL

    Returns:
        Layout-specific payload dict
    """
    assembler = LayoutPayloadAssembler()
    context = AssemblyContext(
        slide_number=slide_number,
        total_slides=total_slides,
        presentation_title=presentation_title
    )

    return assembler.assemble(
        layout=layout,
        slide_title=slide_title,
        subtitle=subtitle,
        content=content,
        branding=branding,
        context=context,
        background_color=background_color,
        background_image=background_image
    )
