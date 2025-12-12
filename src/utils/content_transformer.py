"""
Content Transformer for deck-builder API integration.

Transforms v1.0 PresentationStrawman to deck-builder API format.

v3.2: Supports both structured JSON (from Text Service v1.1) and
      HTML/text (from Text Service v1.0) for backward compatibility.
v3.4: L02 Analytics passthrough - preserves HTML from Analytics Service v3.
      Layout Builder v7.5.1 handles HTML rendering with auto-detection.
"""
from typing import Dict, Any, List, Union, Optional
from datetime import datetime
import re
from src.models.agents import PresentationStrawman, Slide
# v3.2: LayoutMapper removed - replaced by LayoutSchemaManager
from src.utils.layout_schema_manager import get_schema_manager
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class ContentTransformer:
    """Transform v1.0 PresentationStrawman to deck-builder API format.

    v3.2: Uses LayoutSchemaManager for schema-driven architecture.
    v1.1: Enhanced with Format Ownership Architecture.

    Format Ownership (v1.1):
    ========================
    The ContentTransformer implements format ownership where:

    1. **Structured Content (Text Service v1.1+)**:
       - Content is dict matching layout schema
       - Pass-through without parsing or truncation
       - Text Service owns HTML formatting for content fields
       - Layout Builder owns formatting for title/subtitle fields

    2. **Legacy Content (Text Service v1.0)**:
       - Content is HTML/text string
       - Requires parsing and transformation
       - Backward compatibility maintained

    3. **Fallback Content** (No generated content):
       - Uses slide.title, slide.narrative, slide.key_points
       - Applies basic truncation without ellipsis

    Key Changes in v1.1:
    - truncate() no longer adds "..." by default (cleaner overflow handling)
    - Structured content gets complete pass-through
    - Format ownership respected per field specifications
    """

    def __init__(self):
        """
        Initialize content transformer.

        v3.2: No longer requires LayoutMapper - uses LayoutSchemaManager instead.
        v1.1: Enhanced for format ownership architecture.
        """
        self.schema_manager = get_schema_manager()  # v3.2: Schema-driven source

    @staticmethod
    def _is_structured_content(content: Any) -> bool:
        """
        Detect if content is structured JSON (v3.2) vs HTML/text (v1.0).

        v3.2: Text Service v1.1 returns structured dict matching layout schema.
        v1.0: Text Service v1.0 returns HTML/text string that needs parsing.

        Args:
            content: Content from enriched_slide.generated_text.content

        Returns:
            True if structured JSON (dict), False if HTML/text (string)
        """
        return isinstance(content, dict)

    @staticmethod
    def _strip_html_tags(html_content: str) -> str:
        """
        Strip HTML tags from content, keeping text only.

        DEPRECATED for Analytics L02: Layout Builder v7.5.1 now supports HTML
        in element_2 with auto-detection. This method is kept for potential
        other uses but is NO LONGER used for Analytics Service content.

        Args:
            html_content: HTML string with tags

        Returns:
            Plain text with HTML tags removed
        """
        if not html_content:
            return ""

        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', html_content)

        # Clean up extra whitespace
        text = ' '.join(text.split())

        return text

    def transform_presentation(self, strawman: PresentationStrawman,
                              enriched_data=None) -> Dict[str, Any]:
        """
        Transform entire presentation to deck-builder format.

        v3.1: Uses pre-assigned slide.layout_id instead of re-selecting layouts.

        Args:
            strawman: PresentationStrawman object from Director
            enriched_data: Optional EnrichedPresentationStrawman with generated content (v3.1)

        Returns:
            {
                "title": "Presentation Title",
                "slides": [
                    {"layout": "L01", "content": {...}},
                    {"layout": "L05", "content": {...}},
                    ...
                ]
            }
        """
        total_slides = len(strawman.slides)
        transformed_slides = []

        for idx, slide in enumerate(strawman.slides):
            # v3.1: Use pre-assigned layout_id
            layout_id = slide.layout_id

            # Fallback if layout_id not assigned (backward compatibility)
            if not layout_id:
                logger.warning(f"Slide {slide.slide_number} has no layout_id (should not happen in v3.4+)")
                # v3.4: Simplified to 2-layout system
                # Determine position-based fallback
                if idx == 0 or idx == total_slides - 1 or slide.slide_type == "section_divider":
                    layout_id = "L29"  # Hero slide
                else:
                    layout_id = "L25"  # Content slide
                logger.info(f"Assigned fallback layout {layout_id} for slide {slide.slide_number}")

            # Get enriched slide data if available (v3.1)
            enriched_slide = None
            if enriched_data and enriched_data.enriched_slides:
                enriched_slide = enriched_data.enriched_slides[idx]

            # Transform slide content (with enriched data if available)
            transformed_slide = self.transform_slide(slide, layout_id, strawman, enriched_slide)
            transformed_slides.append(transformed_slide)

        if enriched_data:
            logger.info(f"Transformed {total_slides} slides with generated content using pre-assigned layouts")
        else:
            logger.info(f"Transformed {total_slides} slides with placeholder content using pre-assigned layouts")

        return {
            "title": strawman.main_title,
            "slides": transformed_slides
        }

    def transform_slide(self, slide: Slide, layout_id: str,
                       presentation: PresentationStrawman, enriched_slide=None) -> Dict[str, Any]:
        """
        Transform single slide to layout-specific content.

        v3.2: Uses LayoutSchemaManager for schema-driven content mapping.

        Args:
            slide: Slide object
            layout_id: Selected layout ID (e.g., "L05")
            presentation: Full presentation for metadata access
            enriched_slide: Optional EnrichedSlide with generated content (v3.1)

        Returns:
            {"layout": "L05", "content": {...}}
        """
        # v3.2: Get schema from LayoutSchemaManager
        schema = self.schema_manager.get_schema(layout_id)
        content_fields = schema['content_schema']  # v3.2: renamed from 'content_fields'

        # Map content based on layout ID (with enriched data if available)
        content = self._map_content_to_layout(slide, layout_id, content_fields,
                                              presentation, enriched_slide)

        return {
            "layout": layout_id,
            "variant_id": slide.variant_id,
            "content": content
        }

    def _map_content_to_layout(self, slide: Slide, layout_id: str,
                               content_fields: Dict[str, Any],
                               presentation: PresentationStrawman,
                               enriched_slide=None) -> Dict[str, Any]:
        """
        Map slide content to L25 or L29 format.

        v3.4: Simplified for 2-layout system (L25 and L29 only).
        v3.1: Supports enriched_slide parameter for injecting generated text.
        """
        if layout_id == "L29":
            return self._map_hero_slide(slide, content_fields, presentation, enriched_slide)
        elif layout_id == "L25":
            return self._map_content_slide(slide, content_fields, presentation, enriched_slide)
        else:
            logger.error(f"Unknown layout_id: {layout_id}, falling back to L25")
            return self._map_content_slide(slide, content_fields, presentation, enriched_slide)

    def _map_hero_slide(self, slide: Slide, fields: Dict,
                       presentation: PresentationStrawman, enriched_slide=None) -> Dict[str, Any]:
        """
        Map to L29 - Full-Bleed Hero (v3.4).

        L29 is used for:
        - Opening slide (maximum impact)
        - Closing slide (memorable finish)
        - Section dividers (dramatic transitions)

        Args:
            slide: The slide to map
            fields: Schema fields for L29 (hero_content)
            presentation: Full presentation context
            enriched_slide: Optional enriched slide with generated content from text service

        Returns:
            Dict with hero_content field (HTML from text_service)
        """
        # Check if we have generated content from text service
        if enriched_slide and enriched_slide.generated_text and not enriched_slide.has_text_failure:
            generated_content = enriched_slide.generated_text.content

            # Structured content (Text Service v1.1+) - should have hero_content field
            if self._is_structured_content(generated_content):
                logger.info(f"Using structured content for L29 hero slide: {slide.slide_id}")
                return {
                    "hero_content": generated_content.get("hero_content", generated_content.get("rich_content", ""))
                }

            # Legacy HTML/text string (Text Service v1.0) - use as-is for hero_content
            logger.info(f"Using legacy HTML for L29 hero slide: {slide.slide_id}")
            return {
                "hero_content": generated_content
            }

        # Fallback: Create simple HTML placeholder from slide content
        logger.info(f"Creating placeholder content for L29 hero slide: {slide.slide_id}")

        # Build hero content HTML with proper styling for centering and visual appeal
        hero_html_parts = []

        # Add title as main heading with styling
        if slide.title:
            hero_html_parts.append(
                f"<h1 style='font-size: 72px; font-weight: bold; color: #1f2937; "
                f"margin: 0 0 24px 0; line-height: 1.2;'>{slide.title}</h1>"
            )

        # Add narrative as subtitle if present with styling
        if slide.narrative:
            hero_html_parts.append(
                f"<p style='font-size: 32px; color: #6b7280; margin: 0; "
                f"max-width: 80%; line-height: 1.5;'>{slide.narrative}</p>"
            )

        # Join all parts and wrap in centered container div
        inner_content = "\n".join(hero_html_parts) if hero_html_parts else "<h1>Hero Slide</h1>"
        hero_content = f"""
<div style="display: flex; flex-direction: column; justify-content: center; align-items: center;
            text-align: center; height: 100%; padding: 60px;">
{inner_content}
</div>
"""

        return {
            "hero_content": hero_content
        }

    def _map_content_slide(self, slide: Slide, fields: Dict,
                          presentation: PresentationStrawman, enriched_slide=None) -> Dict[str, Any]:
        """
        Map to L25 - Main Content Shell (v3.4-v1.2).

        L25 is the workhorse layout for all content slides with:
        - slide_title (plain text, layout_builder) ← FROM DIRECTOR (generated_title)
        - subtitle (optional, plain text, layout_builder) ← FROM DIRECTOR (generated_subtitle)
        - rich_content (HTML, text_service) - 1800×720px area ← FROM TEXT SERVICE v1.2
        - presentation_name (footer) ← FROM DIRECTOR (footer_text)
        - company_logo (footer)

        v3.4-v1.2 Update:
        - Use slide.generated_title for slide_title (Director-generated, max 50 chars)
        - Use slide.generated_subtitle for subtitle (Director-generated, max 90 chars)
        - Use presentation.footer_text for presentation_name (Director-generated, max 20 chars)
        - Use enriched_slide HTML from Text Service v1.2 for rich_content

        Args:
            slide: The slide to map (with generated_title, generated_subtitle)
            fields: Schema fields for L25
            presentation: Full presentation context (with footer_text)
            enriched_slide: Optional enriched slide with v1.2 HTML content

        Returns:
            Dict with all L25 fields
        """
        # v3.4-v1.2: Use Director's generated titles (character limits already enforced)
        slide_title = slide.generated_title or slide.title
        subtitle = slide.generated_subtitle or ""
        footer = presentation.footer_text or presentation.main_title

        # Check if we have generated content from text service v1.2
        if enriched_slide and enriched_slide.generated_text and not enriched_slide.has_text_failure:
            generated_content = enriched_slide.generated_text.content

            # v1.2: HTML string (complete HTML for rich_content area)
            if isinstance(generated_content, str):
                logger.info(f"Using v1.2 HTML for L25 content slide: {slide.slide_id}")
                result = {
                    "slide_title": slide_title,  # Director's generated_title
                    "rich_content": generated_content  # v1.2's complete HTML
                }

                # Add optional fields
                if 'subtitle' in fields:
                    result["subtitle"] = subtitle  # Director's generated_subtitle
                if 'presentation_name' in fields:
                    result["presentation_name"] = footer  # Director's footer_text
                if 'company_logo' in fields:
                    result["company_logo"] = ""  # Empty for now

                return result

            # v3.4-analytics: Handle Analytics Service v3 L02 response (element_3 + element_2)
            # Analytics Service returns L02 layout with chart (element_3) and observations (element_2)
            # Layout Builder v7.5.1 supports HTML in both fields with auto-detection
            if self._is_structured_content(generated_content):
                # Check if this is analytics content with element_3 and element_2
                if "element_3" in generated_content and "element_2" in generated_content:
                    logger.info(f"Using Analytics Service v3 L02 content for slide: {slide.slide_id}")

                    # ✅ Pass through HTML unchanged - Layout Builder v7.5.1 handles rendering
                    chart_html = generated_content.get("element_3", "")
                    observations_html = generated_content.get("element_2", "")

                    logger.info(
                        f"L02 passthrough: element_3={len(chart_html)}chars, "
                        f"element_2={len(observations_html)}chars"
                    )

                    # ✅ Create proper L02 structure (NOT L25 rich_content!)
                    # Layout Builder v7.5.1 will auto-detect HTML and render correctly
                    # Dimensions: element_3 (1260×720px), element_2 (540×720px)
                    result = {
                        "slide_title": slide_title,           # Director provides
                        "element_1": subtitle,                 # Director provides (subtitle)
                        "element_3": chart_html,               # Analytics provides (chart HTML)
                        "element_2": observations_html,        # Analytics provides (observations HTML)
                        "presentation_name": footer,           # Director provides
                        "company_logo": ""                     # Optional
                    }

                    return result

                # Legacy: Structured content (Text Service v1.1) - backward compatibility
                logger.info(f"Using structured content (v1.1) for L25 content slide: {slide.slide_id}")
                result = {
                    "slide_title": slide_title,  # Director's generated_title (override v1.1)
                    "rich_content": generated_content.get("rich_content", "")
                }

                # Optional fields
                if 'subtitle' in fields:
                    result["subtitle"] = subtitle  # Director's generated_subtitle
                if 'presentation_name' in fields:
                    result["presentation_name"] = footer  # Director's footer_text
                if 'company_logo' in fields:
                    result["company_logo"] = ""

                return result

        # Fallback: Create placeholder content from slide data
        logger.info(f"Creating placeholder content for L25 content slide: {slide.slide_id}")

        # Build rich_content HTML from slide narrative and key points
        rich_content_parts = []

        if slide.narrative:
            rich_content_parts.append(f"<p style='font-size: 20px; line-height: 1.5;'>{slide.narrative}</p>")

        if slide.key_points:
            rich_content_parts.append("<ul style='font-size: 20px; line-height: 1.5;'>")
            for point in slide.key_points[:6]:  # Limit to 6 points
                rich_content_parts.append(f"<li>{point}</li>")
            rich_content_parts.append("</ul>")

        rich_content = "\n".join(rich_content_parts) if rich_content_parts else "<p>Content placeholder</p>"

        result = {
            "slide_title": slide_title,  # Director's generated_title or fallback
            "rich_content": rich_content
        }

        # Add optional fields
        if 'subtitle' in fields:
            result["subtitle"] = subtitle  # Director's generated_subtitle or empty
        if 'presentation_name' in fields:
            result["presentation_name"] = footer  # Director's footer_text or fallback
        if 'company_logo' in fields:
            result["company_logo"] = ""  # Empty for now

        return result

    def _map_title_slide(self, slide: Slide, fields: Dict,
                        presentation: PresentationStrawman, enriched_slide=None) -> Dict[str, Any]:
        """Map to L01 - Title Slide."""
        return {
            "main_title": self.truncate(presentation.main_title,
                                       fields['main_title']['max_chars']),
            "subtitle": self.truncate(slide.narrative or presentation.overall_theme,
                                     fields['subtitle']['max_chars']),
            "presenter_name": "AI-Generated Presentation",
            "organization": self.truncate(presentation.target_audience,
                                         fields['organization']['max_chars']),
            "date": datetime.now().strftime("%Y-%m-%d")
        }

    def _map_section_divider(self, slide: Slide, fields: Dict,
                            presentation: PresentationStrawman, enriched_slide=None) -> Dict[str, Any]:
        """Map to L02 - Section Divider."""
        return {
            "section_title": self.truncate(slide.title, fields['section_title']['max_chars'])
        }

    def _map_closing_slide(self, slide: Slide, fields: Dict,
                          presentation: PresentationStrawman, enriched_slide=None) -> Dict[str, Any]:
        """Map to L03 - Closing Slide."""
        return {
            "closing_message": self.truncate(slide.title or "Thank You",
                                           fields['closing_message']['max_chars']),
            "subtitle": self.truncate(slide.narrative or "Questions & Discussion",
                                     fields['subtitle']['max_chars']),
            "contact_email": "contact@example.com",
            "website": "www.example.com",
            "social_media": "@example"
        }

    def _map_text_summary(self, slide: Slide, fields: Dict,
                         presentation: PresentationStrawman, enriched_slide=None) -> Dict[str, Any]:
        """Map to L04 - Text + Summary.

        v3.2: Supports both structured JSON and HTML/text content.
        - Structured (v3.2): Direct pass-through of JSON from Text Service v1.1
        - HTML/text (v1.0): Legacy handling for backward compatibility
        """
        # v3.2: Check if we have generated content
        if enriched_slide and enriched_slide.generated_text and not enriched_slide.has_text_failure:
            generated_content = enriched_slide.generated_text.content

            # v3.2: Structured content (Text Service v1.1+)
            if self._is_structured_content(generated_content):
                logger.info(f"Using structured content for L04 slide: {slide.slide_id}")
                # Direct pass-through - content already matches schema
                result = {
                    "slide_title": generated_content.get("slide_title", slide.title),
                    "main_text_content": generated_content.get("main_text_content", "")
                }
                if 'subtitle' in fields and 'subtitle' in generated_content:
                    result["subtitle"] = generated_content["subtitle"]
                if 'summary' in fields and 'summary' in generated_content:
                    result["summary"] = generated_content["summary"]
                return result

            # v1.0: Legacy text handling (DEPRECATED - for backward compatibility)
            logger.info(f"Using legacy text for L04 slide: {slide.slide_id}")
            main_text = generated_content
        else:
            # Fallback to placeholder logic
            main_text = slide.narrative
            if slide.key_points:
                main_text += "\n\n" + "\n\n".join(slide.key_points)

        # Extract summary from last key point or narrative
        summary = slide.key_points[-1] if slide.key_points else slide.narrative[:200]

        return {
            "slide_title": self.truncate(slide.title, fields['slide_title']['max_chars']),
            "subtitle": self.truncate(slide.narrative[:80],
                                     fields['subtitle']['max_chars']) if 'subtitle' in fields else None,
            "main_text_content": self.truncate(main_text,
                                              fields['main_text_content']['max_chars']),
            "summary": self.truncate(summary, fields['summary']['max_chars']) if 'summary' in fields else None
        }

    def _map_bullet_list(self, slide: Slide, fields: Dict,
                        presentation: PresentationStrawman, enriched_slide=None) -> Dict[str, Any]:
        """Map to L05 - Bullet List.

        v3.2: Supports both structured JSON and HTML/text content.
        - Structured (v3.2): Direct pass-through of JSON from Text Service v1.1
        - HTML/text (v1.0): Legacy parsing for backward compatibility
        """
        max_items = fields['bullets']['max_items']
        max_chars = fields['bullets']['max_chars_per_item']

        # v3.2: Check if we have generated content
        if enriched_slide and enriched_slide.generated_text and not enriched_slide.has_text_failure:
            generated_content = enriched_slide.generated_text.content

            # v3.2: Structured content (Text Service v1.1+)
            if self._is_structured_content(generated_content):
                logger.info(f"Using structured content for L05 slide: {slide.slide_id}")
                # Direct pass-through - content already matches schema
                result = {
                    "slide_title": generated_content.get("slide_title", slide.title),
                    "bullets": generated_content.get("bullets", [])
                }
                if 'subtitle' in fields and 'subtitle' in generated_content:
                    result["subtitle"] = generated_content["subtitle"]
                return result

            # v1.0: Legacy HTML/text parsing (DEPRECATED - for backward compatibility)
            logger.info(f"Using legacy text parsing for L05 slide: {slide.slide_id}")
            bullets = []
            for line in generated_content.split('\n'):
                line = line.strip()
                # Remove bullet markers if present
                for marker in ['•', '-', '*', '–']:
                    if line.startswith(marker):
                        line = line[1:].strip()
                        break
                if line and len(line) > 10:  # Skip empty or very short lines
                    bullets.append(self.truncate(line, max_chars))
                    if len(bullets) >= max_items:
                        break

            # Fallback if parsing didn't produce enough bullets
            if len(bullets) < 2:
                bullets = [self.truncate(point, max_chars) for point in slide.key_points[:max_items]]
        else:
            # Fallback to placeholder logic
            bullets = [self.truncate(point, max_chars) for point in slide.key_points[:max_items]]

        result = {
            "slide_title": self.truncate(slide.title, fields['slide_title']['max_chars']),
            "bullets": bullets
        }

        if 'subtitle' in fields:
            result["subtitle"] = self.truncate(slide.narrative, fields['subtitle']['max_chars'])

        return result

    def _map_numbered_list(self, slide: Slide, fields: Dict,
                          presentation: PresentationStrawman, enriched_slide=None) -> Dict[str, Any]:
        """Map to L06 - Numbered List.

        v3.2: Supports both structured JSON and HTML/text content.
        - Structured (v3.2): Direct pass-through of JSON from Text Service v1.1
        - HTML/text (v1.0): Legacy parsing for backward compatibility
        """
        max_items = fields['numbered_items']['max_items']

        # v3.2: Check if we have generated content
        if enriched_slide and enriched_slide.generated_text and not enriched_slide.has_text_failure:
            generated_content = enriched_slide.generated_text.content

            # v3.2: Structured content (Text Service v1.1+)
            if self._is_structured_content(generated_content):
                logger.info(f"Using structured content for L06 slide: {slide.slide_id}")
                # Direct pass-through - content already matches schema
                result = {
                    "slide_title": generated_content.get("slide_title", slide.title),
                    "numbered_items": generated_content.get("numbered_items", [])
                }
                if 'subtitle' in fields and 'subtitle' in generated_content:
                    result["subtitle"] = generated_content["subtitle"]
                return result

            # v1.0: Legacy text parsing (DEPRECATED - for backward compatibility)
            logger.info(f"Using legacy text parsing for L06 slide: {slide.slide_id}")
            numbered_items = []
            lines = [line.strip() for line in generated_content.split('\n') if line.strip()]
            for idx, line in enumerate(lines[:max_items]):
                # Try to split into title and description
                if ':' in line:
                    title, description = line.split(':', 1)
                elif '.' in line and idx < len(lines):
                    # Handle "1. Title - description" format
                    parts = line.split('.', 1)
                    if len(parts) > 1:
                        title_desc = parts[1].strip()
                        if '-' in title_desc:
                            title, description = title_desc.split('-', 1)
                        else:
                            title = f"Step {idx + 1}"
                            description = title_desc
                    else:
                        title = f"Step {idx + 1}"
                        description = line
                else:
                    title = f"Step {idx + 1}"
                    description = line

                numbered_items.append({
                    "title": self.truncate(title.strip(), 40),
                    "description": self.truncate(description.strip(), 150)
                })

            # Fallback if parsing didn't produce enough items
            if len(numbered_items) < 2:
                numbered_items = []
                for idx, point in enumerate(slide.key_points[:max_items]):
                    if ':' in point:
                        title, description = point.split(':', 1)
                    else:
                        title = f"Step {idx + 1}"
                        description = point
                    numbered_items.append({
                        "title": self.truncate(title, 40),
                        "description": self.truncate(description, 150)
                    })
        else:
            # Fallback to placeholder logic
            numbered_items = []
            for idx, point in enumerate(slide.key_points[:max_items]):
                if ':' in point:
                    title, description = point.split(':', 1)
                else:
                    title = f"Step {idx + 1}"
                    description = point

                numbered_items.append({
                    "title": self.truncate(title, 40),
                    "description": self.truncate(description, 150)
                })

        result = {
            "slide_title": self.truncate(slide.title, fields['slide_title']['max_chars']),
            "numbered_items": numbered_items
        }

        if 'subtitle' in fields:
            result["subtitle"] = self.truncate(slide.narrative, fields['subtitle']['max_chars'])

        return result

    def _map_image_text(self, slide: Slide, fields: Dict,
                       presentation: PresentationStrawman, enriched_slide=None) -> Dict[str, Any]:
        """Map to L10 - Image Left + Text Right.

        v3.2: Supports both structured JSON and HTML/text content.
        - Structured (v3.2): Direct pass-through of JSON from Text Service v1.1
        - HTML/text (v1.0): Legacy handling for backward compatibility
        """
        # Generate placeholder for image (v3.2: still placeholder, image generation not in scope)
        if slide.visuals_needed:
            image_placeholder = self.generate_placeholder(slide.visuals_needed, "IMAGE")
        elif slide.diagrams_needed:
            image_placeholder = self.generate_placeholder(slide.diagrams_needed, "DIAGRAM")
        else:
            image_placeholder = "PLACEHOLDER: Professional image related to slide content"

        # v3.2: Check if we have generated content
        if enriched_slide and enriched_slide.generated_text and not enriched_slide.has_text_failure:
            generated_content = enriched_slide.generated_text.content

            # v3.2: Structured content (Text Service v1.1+)
            if self._is_structured_content(generated_content):
                logger.info(f"Using structured content for L10 slide: {slide.slide_id}")
                # Direct pass-through - content already matches schema
                result = {
                    "slide_title": generated_content.get("slide_title", slide.title),
                    "image": image_placeholder,  # Image still placeholder
                    "text_content": generated_content.get("text_content", "")
                }
                if 'subtitle' in fields and 'subtitle' in generated_content:
                    result["subtitle"] = generated_content["subtitle"]
                return result

            # v1.0: Legacy text handling (DEPRECATED - for backward compatibility)
            logger.info(f"Using legacy text for L10 slide: {slide.slide_id}")
            text_content = generated_content
        else:
            # Fallback to placeholder logic
            text_content = slide.narrative
            if slide.key_points:
                text_content += "\n\n" + "\n\n".join(slide.key_points)

        result = {
            "slide_title": self.truncate(slide.title, fields['slide_title']['max_chars']),
            "image": image_placeholder,
            "text_content": self.truncate(text_content, fields['text_content']['max_chars'])
        }

        if 'subtitle' in fields:
            result["subtitle"] = self.truncate(slide.narrative[:80], fields['subtitle']['max_chars'])

        return result

    def _map_chart_insights(self, slide: Slide, fields: Dict,
                           presentation: PresentationStrawman, enriched_slide=None) -> Dict[str, Any]:
        """Map to L17 - Chart + Insights.

        v3.2: Supports both structured JSON and HTML/text content.
        - Structured (v3.2): Direct pass-through of JSON from Text Service v1.1
        - HTML/text (v1.0): Legacy parsing for backward compatibility
        """
        # Generate placeholder for chart (v3.2: still placeholder, chart generation not in scope)
        if slide.analytics_needed:
            chart_placeholder = self.generate_placeholder(slide.analytics_needed, "CHART")
        else:
            chart_placeholder = "PLACEHOLDER: Data visualization for this slide"

        max_items = fields['key_insights']['max_items']
        max_chars = fields['key_insights']['max_chars_per_item']

        # v3.2: Check if we have generated content
        if enriched_slide and enriched_slide.generated_text and not enriched_slide.has_text_failure:
            generated_content = enriched_slide.generated_text.content

            # v3.2: Structured content (Text Service v1.1+)
            if self._is_structured_content(generated_content):
                logger.info(f"Using structured content for L17 slide: {slide.slide_id}")
                # Direct pass-through - content already matches schema
                result = {
                    "slide_title": generated_content.get("slide_title", slide.title),
                    "chart_url": chart_placeholder,  # Chart still placeholder
                    "key_insights": generated_content.get("key_insights", [])
                }
                if 'subtitle' in fields and 'subtitle' in generated_content:
                    result["subtitle"] = generated_content["subtitle"]
                if 'summary' in fields and 'summary' in generated_content:
                    result["summary"] = generated_content["summary"]
                return result

            # v1.0: Legacy text parsing (DEPRECATED - for backward compatibility)
            logger.info(f"Using legacy text parsing for L17 slide: {slide.slide_id}")
            insights = []
            for line in generated_content.split('\n'):
                line = line.strip()
                # Remove bullet markers if present
                for marker in ['•', '-', '*', '–']:
                    if line.startswith(marker):
                        line = line[1:].strip()
                        break
                if line and len(line) > 10:  # Skip empty or very short lines
                    insights.append(self.truncate(line, max_chars))
                    if len(insights) >= max_items:
                        break

            # Fallback if parsing didn't produce enough insights
            if len(insights) < 2:
                insights = [self.truncate(point, max_chars) for point in slide.key_points[:max_items]]
        else:
            # Fallback to placeholder logic
            insights = [self.truncate(point, max_chars) for point in slide.key_points[:max_items]]

        result = {
            "slide_title": self.truncate(slide.title, fields['slide_title']['max_chars']),
            "chart_url": chart_placeholder,
            "key_insights": insights
        }

        if 'subtitle' in fields:
            result["subtitle"] = self.truncate(slide.narrative, fields['subtitle']['max_chars'])

        if 'summary' in fields:
            summary = slide.key_points[-1] if slide.key_points else slide.narrative[:200]
            result["summary"] = self.truncate(summary, fields['summary']['max_chars'])

        return result

    def _map_generic(self, slide: Slide, fields: Dict, enriched_slide=None) -> Dict[str, Any]:
        """Generic mapping fallback.

        v3.2: Supports both structured JSON and HTML/text content.
        - Structured (v3.2): Direct pass-through of JSON from Text Service v1.1
        - HTML/text (v1.0): Legacy parsing for backward compatibility
        """
        # v3.2: Check if we have structured content
        if enriched_slide and enriched_slide.generated_text and not enriched_slide.has_text_failure:
            generated_content = enriched_slide.generated_text.content

            # v3.2: Structured content (Text Service v1.1+)
            if self._is_structured_content(generated_content):
                logger.info(f"Using structured content for generic mapping: {slide.slide_id}")
                # Direct pass-through - content already matches schema
                return generated_content

        # Legacy fallback logic (v1.0 compatibility or no enriched content)
        content = {}

        # Try to map common fields
        if 'slide_title' in fields:
            content['slide_title'] = self.truncate(slide.title, fields['slide_title']['max_chars'])

        if 'subtitle' in fields:
            content['subtitle'] = self.truncate(slide.narrative, fields['subtitle']['max_chars'])

        # v1.0: Legacy text parsing for bullets
        if 'bullets' in fields:
            max_items = fields['bullets']['max_items']
            max_chars = fields['bullets']['max_chars_per_item']

            if enriched_slide and enriched_slide.generated_text and not enriched_slide.has_text_failure:
                generated_content = enriched_slide.generated_text.content
                logger.info(f"Using legacy text parsing for generic mapping: {slide.slide_id}")
                bullets = []
                for line in generated_content.split('\n'):
                    line = line.strip()
                    for marker in ['•', '-', '*', '–']:
                        if line.startswith(marker):
                            line = line[1:].strip()
                            break
                    if line and len(line) > 10:
                        bullets.append(self.truncate(line, max_chars))
                        if len(bullets) >= max_items:
                            break
                content['bullets'] = bullets if len(bullets) >= 2 else [self.truncate(p, max_chars) for p in slide.key_points[:max_items]]
            else:
                content['bullets'] = [self.truncate(p, max_chars) for p in slide.key_points[:max_items]]

        return content

    @staticmethod
    def truncate(text: str, max_chars: int, add_ellipsis: bool = False) -> str:
        """
        Intelligently truncate text to character limit.

        Preserves whole sentences when possible.

        Args:
            text: Text to truncate
            max_chars: Maximum character limit
            add_ellipsis: Whether to add "..." when truncating (default: False for v1.1+)

        v1.1: Changed default to NOT add ellipsis for cleaner layout handling.
              Layout Builder will handle visual overflow indicators if needed.
        """
        if not text:
            return ""

        if len(text) <= max_chars:
            return text

        # Try to truncate at sentence boundary
        truncated = text[:max_chars]

        # Look for last sentence ending
        for delimiter in ['. ', '! ', '? ']:
            last_delimiter = truncated.rfind(delimiter)
            if last_delimiter > max_chars * 0.7:  # At least 70% of max_chars
                return truncated[:last_delimiter + 1]

        # Fallback: truncate at last space
        last_space = truncated.rfind(' ')
        if last_space > 0:
            return truncated[:last_space] + ("..." if add_ellipsis else "")

        # Hard truncate
        return truncated + ("..." if add_ellipsis else "")

    @staticmethod
    def generate_placeholder(asset_description: str, asset_type: str) -> str:
        """
        Generate placeholder text for images/charts/diagrams.

        Args:
            asset_description: The description from v1.0 asset field
            asset_type: "IMAGE", "CHART", or "DIAGRAM"

        Returns:
            Placeholder string like "PLACEHOLDER_IMAGE: Description here"
        """
        # Clean up the description if it has Goal/Content/Style format
        if "**Goal:**" in asset_description:
            # Extract just the Content section
            parts = asset_description.split("**Content:**")
            if len(parts) > 1:
                content_part = parts[1].split("**Style:**")[0].strip()
                return f"PLACEHOLDER_{asset_type}: {content_part}"

        # Return full description
        return f"PLACEHOLDER_{asset_type}: {asset_description}"
