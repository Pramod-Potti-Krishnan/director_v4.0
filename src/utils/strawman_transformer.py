"""
Strawman Transformer for v4.0.25

Transforms strawman data to deck-builder API format for preview generation.

v4.0.25: Story-driven multi-service coordination.
- Uses exact layout from slide (not hardcoded L29/L25)
- Includes all precise fields: slide_type_hint, purpose, service, generation_instructions
- Supports all layout series (L, C, H, V, I)

Layouts:
- L29, H1-H3: Hero slides (title, section dividers, closing)
- L25, C1, V1: Content slides (rich content area)
- C2, V2, L02: Analytics slides (charts)
- C4, V3: Diagram slides
- C3, V4: Infographic slides
- I1-I4: Image+Text slides

v4.0.6: Enhanced title slide handling with dedicated method.
v4.5.6: Metadata-only strawman preview (no template generation).
v4.5.7: Fixed subtitle/logo fields missing from content dict.
v4.5.8: Redesigned full-width card-based preview (replaces narrow table).
- Topics displayed as colorful gradient cards (hero content)
- Metadata shown as compact chips at top
- Each slide type has unique visual treatment
- Uses full content area instead of narrow left-aligned table
v4.5.12: Proper footer and logo placement per SLIDE_GENERATION_INPUT_SPEC.md.
- STRAWMAN logo in footer logo area via logo field
- Footer with template/variant/service via presentation_name (L25) or footer_text (C1)
- Better subtitle generation from purpose + topics
v4.5.13: Clean four-section structure for strawman content.
- Purpose: Why this slide exists in the story
- Topics: What content to cover (bullet points)
- Generation Instructions: How the service should build it
- Notes: Additional context or speaker notes
"""
from typing import Dict, Any, List
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class StrawmanTransformer:
    """
    Transform strawman data to deck-builder API format.

    v4.0.5: Simplified transformer for preview generation only.
    v4.0.6: Enhanced title slide with dedicated handler.
    v4.0.25: Story-driven with precise fields and exact layouts.
    v4.5.6: Metadata display - shows AI decisions without template generation.
    """

    # Hero layouts
    HERO_LAYOUTS = {"L29", "H1", "H2", "H3"}

    # Content layouts (Text Service)
    CONTENT_LAYOUTS = {"L25", "C1", "V1"}

    # I-series layouts (Image+Text)
    ISERIES_LAYOUTS = {"I1", "I2", "I3", "I4"}

    # Analytics layouts
    ANALYTICS_LAYOUTS = {"L02", "C2", "V2"}

    # Diagram layouts
    DIAGRAM_LAYOUTS = {"C4", "V3"}

    # Infographic layouts
    INFOGRAPHIC_LAYOUTS = {"C3", "V4"}

    # v4.5.9: Layout ID mapping - short-form to Layout Service full-form
    # This fixes 422 errors from Layout Service validation
    LAYOUT_MAP = {
        # Hero layouts
        # v4.5.15: Changed H1 to H1-structured for reliable full-width background
        "H1": "H1-structured",  # Structured title (slide_title, subtitle, author_info + background_color)
        "H2": "H2-section",     # Section divider
        "H3": "H3-closing",     # Closing slide

        # Content layouts
        "C1": "C1-text",        # Standard text content (uses body field)
        "V1": "V1-image-text",

        # Image+Content layouts
        "I1": "I1-image-left",
        "I2": "I2-image-right",
        "I3": "I3-image-left-narrow",
        "I4": "I4-image-right-narrow",

        # Visual layouts
        "V2": "V2-chart-text",
        "V3": "V3-diagram-text",
        "V4": "V4-infographic-text",

        # Analytics/Chart layouts
        "C2": "C3-chart",

        # Diagram layouts
        "C4": "C5-diagram",

        # Infographic layouts
        "C3": "C4-infographic",

        # Backend layouts (already full names - pass through)
        "L25": "L25",
        "L29": "L29",
        "L02": "L02",
    }

    # v4.5.11: STRAWMAN logo as HTML for footer logo area
    # Layout Service accepts URL or HTML for logo field (v7.5.5 standardized)
    STRAWMAN_LOGO_HTML = '''<div style="display: inline-flex; align-items: center; gap: 6px;
        background: linear-gradient(135deg, #fef3c7, #fde68a); border: 2px solid #f59e0b;
        border-radius: 8px; padding: 4px 12px;">
        <span style="font-size: 12px;">📋</span>
        <span style="font-size: 11px; font-weight: 700; color: #92400e;
            text-transform: uppercase; letter-spacing: 1px;">STRAWMAN</span>
    </div>'''

    def _map_layout_id(self, layout: str) -> str:
        """
        Map short-form layout ID to Layout Service full-form.

        v4.5.9: Fixes 422 errors by converting Director's short layout IDs
        (e.g., H1, C1, I1) to Layout Service's expected full names
        (e.g., H1-generated, L25, I1-image-left).

        Args:
            layout: Short-form layout ID from strawman

        Returns:
            Layout Service full-form layout ID
        """
        return self.LAYOUT_MAP.get(layout, layout)

    def _generate_subtitle(self, slide: Dict[str, Any]) -> str:
        """
        Generate single-line summary of slide content.

        v4.5.11: Generates meaningful subtitle instead of empty placeholder.
        v4.5.12: Creates descriptive single-line summary from purpose + topics.

        Args:
            slide: Slide data with optional subtitle, purpose, topics

        Returns:
            Subtitle string (from slide data or generated)
        """
        subtitle = slide.get('subtitle', '')
        if subtitle:
            return subtitle

        # Try to generate from context
        purpose = slide.get('purpose', '')
        topics = slide.get('topics', [])
        slide_type_hint = slide.get('slide_type_hint', '')

        # v4.5.12: Build descriptive subtitle
        if purpose and purpose != '-':
            # Convert purpose to readable format
            purpose_text = purpose.replace('_', ' ').title()
            if topics:
                # Truncate first topic if too long
                first_topic = topics[0][:60] + '...' if len(topics[0]) > 60 else topics[0]
                return f"{purpose_text}: {first_topic}"
            return purpose_text
        elif topics:
            if len(topics) == 1:
                return topics[0][:100]
            return f"Key points: {', '.join(topics[:2])}..."
        else:
            return f"Strawman {slide_type_hint or 'content'} slide"

    def _generate_footer(self, slide: Dict[str, Any], layout: str) -> str:
        """
        Generate footer with template, variant, and service info.

        v4.5.12: Creates footer showing slide metadata for user review.

        Args:
            slide: Slide data with variant_id and service
            layout: Layout ID (C1, L25, etc.)

        Returns:
            Footer string with template/variant/service info
        """
        variant_id = slide.get('variant_id') or 'auto'
        service = slide.get('service') or 'text'
        return f"🎨 {layout} | 📐 {variant_id} | ⚙️ {service}"

    def transform(self, strawman_dict: Dict[str, Any], topic: str) -> Dict[str, Any]:
        """
        Transform strawman to deck-builder API format with precise fields.

        v4.0.25: Includes all story-driven fields for each slide.

        Args:
            strawman_dict: Strawman data from StrawmanGenerator
            topic: Presentation topic (fallback for title)

        Returns:
            Dict with 'title' and 'slides' for deck-builder API:
            {
                "title": "Presentation Title",
                "slides": [
                    {
                        "layout": "H1",
                        "content": {...},
                        "metadata": {
                            "slide_type_hint": "hero",
                            "purpose": "title_slide",
                            "service": "text",
                            "variant_id": null,
                            "generation_instructions": null
                        }
                    },
                    ...
                ]
            }
        """
        transformed_slides = []

        # v4.0.6: Get presentation title early for title slide
        presentation_title = strawman_dict.get('title', topic) or 'Untitled Presentation'

        for slide in strawman_dict.get('slides', []):
            # v4.0.25: Get exact layout from slide (story-driven)
            layout = slide.get('layout', 'L25')
            is_hero = slide.get('is_hero', False)
            hero_type = slide.get('hero_type')

            # v4.0.25: Get story-driven fields
            slide_type_hint = slide.get('slide_type_hint')
            purpose = slide.get('purpose')
            service = slide.get('service')
            variant_id = slide.get('variant_id')
            generation_instructions = slide.get('generation_instructions')

            # Build slide content based on layout type
            # v4.5.15: Default background color for hero slides (set at slide level)
            background_color = None

            if is_hero or layout in self.HERO_LAYOUTS:
                # Hero slide - v4.5.15: Use H1-structured for title slides
                if hero_type == 'title_slide':
                    # H1-structured: use slide_title, subtitle, author_info (not hero_content)
                    subtitle = slide.get('subtitle', '')
                    topics = slide.get('topics', [])
                    notes = slide.get('notes', '')

                    # Use subtitle if set, otherwise first topic or notes
                    if not subtitle:
                        subtitle = (topics[0] if topics else notes) or ""

                    content = {
                        'slide_title': f"📋 {presentation_title}",  # STRAWMAN prefix
                        'subtitle': subtitle,
                        'author_info': '📋 STRAWMAN PREVIEW'
                    }
                    # Set background at slide level for full coverage
                    background_color = '#1e3a5f'
                else:
                    html_content = self._create_hero_html(slide, hero_type)
                    content = {'hero_content': html_content}

            elif layout in self.ANALYTICS_LAYOUTS:
                # Analytics slide - metadata display
                # v4.5.7: Added subtitle and logo for Layout Service
                # v4.5.12: Added presentation_name for footer
                content = {
                    'slide_title': slide.get('title', 'Analytics'),
                    'subtitle': self._generate_subtitle(slide),
                    'rich_content': self._create_analytics_metadata_html(slide, layout),
                    'presentation_name': self._generate_footer(slide, layout),
                    'logo': self.STRAWMAN_LOGO_HTML
                }

            elif layout in self.DIAGRAM_LAYOUTS:
                # Diagram slide - metadata display
                # v4.5.7: Added subtitle and logo for Layout Service
                # v4.5.12: Added presentation_name for footer
                content = {
                    'slide_title': slide.get('title', 'Diagram'),
                    'subtitle': self._generate_subtitle(slide),
                    'rich_content': self._create_diagram_metadata_html(slide, layout),
                    'presentation_name': self._generate_footer(slide, layout),
                    'logo': self.STRAWMAN_LOGO_HTML
                }

            elif layout in self.INFOGRAPHIC_LAYOUTS:
                # Infographic slide - metadata display
                # v4.5.7: Added subtitle and logo for Layout Service
                # v4.5.12: Added presentation_name for footer
                content = {
                    'slide_title': slide.get('title', 'Infographic'),
                    'subtitle': self._generate_subtitle(slide),
                    'rich_content': self._create_infographic_metadata_html(slide, layout),
                    'presentation_name': self._generate_footer(slide, layout),
                    'logo': self.STRAWMAN_LOGO_HTML
                }

            elif layout in self.ISERIES_LAYOUTS:
                # I-series slide - metadata display with image placeholder
                # v4.5.7: Added subtitle and logo for Layout Service
                # v4.5.12: Added presentation_name for footer
                content = {
                    'slide_title': slide.get('title', 'Visual'),
                    'subtitle': self._generate_subtitle(slide),
                    'rich_content': self._create_iseries_metadata_html(slide, layout),
                    'presentation_name': self._generate_footer(slide, layout),
                    'logo': self.STRAWMAN_LOGO_HTML
                }

            elif layout == 'C1':
                # v4.5.9: C1-text expects 'body' field, not 'rich_content'
                # v4.5.12: Added footer_text (C1 uses footer_text, not presentation_name)
                content = {
                    'slide_title': slide.get('title', 'Slide'),
                    'subtitle': self._generate_subtitle(slide),
                    'body': self._create_content_metadata_html(slide, layout),
                    'footer_text': self._generate_footer(slide, layout),
                    'logo': self.STRAWMAN_LOGO_HTML
                }

            else:
                # Default content slide (L25, V1) - uses rich_content
                # v4.5.7: Added subtitle and logo for Layout Service
                # v4.5.12: Added presentation_name for footer
                content = {
                    'slide_title': slide.get('title', 'Slide'),
                    'subtitle': self._generate_subtitle(slide),
                    'rich_content': self._create_content_metadata_html(slide, layout),
                    'presentation_name': self._generate_footer(slide, layout),
                    'logo': self.STRAWMAN_LOGO_HTML
                }

            # Build transformed slide with metadata
            # v4.5.9: Map layout to Layout Service full-form to fix 422 errors
            transformed_slide = {
                'layout': self._map_layout_id(layout),
                'content': content,
                # v4.0.25: Include precise metadata for content generation
                'metadata': {
                    'slide_number': slide.get('slide_number'),
                    'slide_type_hint': slide_type_hint,
                    'purpose': purpose,
                    'service': service,
                    'variant_id': variant_id,
                    'generation_instructions': generation_instructions,
                    'is_hero': is_hero,
                    'hero_type': hero_type,
                    'topics': slide.get('topics', [])
                }
            }

            # v4.5.15: Add background_color at slide level for H1-structured
            if background_color:
                transformed_slide['background_color'] = background_color

            transformed_slides.append(transformed_slide)

        logger.info(f"Transformed {len(transformed_slides)} slides for preview (title: {presentation_title})")

        return {
            'title': presentation_title,
            'slides': transformed_slides
        }

    def _create_strawman_badge(self) -> str:
        """Create the STRAWMAN PREVIEW badge HTML."""
        return '''
<div style="background: #fef3c7; border: 2px solid #f59e0b; border-radius: 12px;
            padding: 16px 24px; margin-bottom: 24px; text-align: center;">
    <span style="font-size: 18px; font-weight: 700; color: #92400e;
                 text-transform: uppercase; letter-spacing: 2px;">
        📋 STRAWMAN PREVIEW
    </span>
</div>
'''

    def _create_metadata_table(self, rows: List[tuple]) -> str:
        """
        Create a formatted metadata table.

        Args:
            rows: List of (label, value) tuples

        Returns:
            HTML table string
        """
        table_rows = []
        for i, (label, value) in enumerate(rows):
            if value is None or value == '':
                continue
            bg = 'background: #f9fafb;' if i % 2 == 1 else ''
            table_rows.append(f'''
    <tr style="{bg}">
        <td style="padding: 12px; font-weight: 600; color: #6b7280; width: 35%; vertical-align: top;">{label}</td>
        <td style="padding: 12px; color: #1f2937;">{value}</td>
    </tr>''')

        return f'''
<table style="width: 100%; font-size: 18px; border-collapse: collapse; border: 1px solid #e5e7eb; border-radius: 8px;">
    {''.join(table_rows)}
</table>
'''

    def _format_topics(self, topics: List[str]) -> str:
        """Format topics as HTML bullet list."""
        if not topics:
            return '<span style="color: #9ca3af;">None specified</span>'
        return '<br>'.join([f'• {topic}' for topic in topics])

    # ==================== v4.5.8 Helper Methods ====================

    def _get_topic_card_gradient(self, index: int) -> str:
        """
        Get gradient color for topic card based on index.

        v4.5.8: Colorful gradients for topic cards.

        Args:
            index: Topic index (0-based)

        Returns:
            CSS gradient string
        """
        gradients = [
            "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",  # Purple
            "linear-gradient(135deg, #f093fb 0%, #f5576c 100%)",  # Pink
            "linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)",  # Blue
            "linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)",  # Green
            "linear-gradient(135deg, #fa709a 0%, #fee140 100%)",  # Orange
            "linear-gradient(135deg, #a8edea 0%, #fed6e3 100%)",  # Pastel
        ]
        return gradients[index % len(gradients)]

    def _create_topic_cards(self, topics: List[str]) -> str:
        """
        Create grid of colorful topic cards.

        v4.5.8: Topics as hero content with gradient backgrounds.

        Args:
            topics: List of topic strings

        Returns:
            HTML string with topic cards
        """
        if not topics:
            return '''
            <div style="background: #f8fafc; border-radius: 16px; padding: 24px;
                        color: #9ca3af; font-style: italic; text-align: center;">
                No topics specified
            </div>
            '''

        cards = []
        for i, topic in enumerate(topics):
            gradient = self._get_topic_card_gradient(i)
            cards.append(f'''
            <div style="background: {gradient}; border-radius: 16px; padding: 24px;
                        color: white; box-shadow: 0 4px 12px rgba(0,0,0,0.15);">
                <div style="font-size: 13px; opacity: 0.85; margin-bottom: 8px;">Topic {i+1}</div>
                <div style="font-size: 17px; font-weight: 600; line-height: 1.4;">{topic}</div>
            </div>
            ''')
        return '\n'.join(cards)

    def _create_metadata_chips(self, layout: str, variant_id: str, service: str) -> str:
        """
        Create row of compact metadata chips.

        v4.5.8: Compact badges for layout/variant/service info.

        Args:
            layout: Layout ID (C1, H1, I1, etc.)
            variant_id: Variant identifier
            service: Service name (text, analytics, diagram, etc.)

        Returns:
            HTML string with metadata chips
        """
        return f'''
        <div style="display: flex; gap: 12px; flex-wrap: wrap;">
            <span style="background: #e0e7ff; color: #3730a3; padding: 6px 16px;
                         border-radius: 16px; font-size: 14px; font-weight: 600;">
                🎨 {layout}
            </span>
            <span style="background: #d1fae5; color: #065f46; padding: 6px 16px;
                         border-radius: 16px; font-size: 14px; font-weight: 600;">
                📐 {variant_id}
            </span>
            <span style="background: #fce7f3; color: #9d174d; padding: 6px 16px;
                         border-radius: 16px; font-size: 14px; font-weight: 600;">
                ⚙️ {service}
            </span>
        </div>
        '''

    def _create_compact_badge(self) -> str:
        """
        Create compact STRAWMAN badge for v4.5.8.

        Returns:
            HTML string with compact badge
        """
        return '''
        <div style="background: linear-gradient(135deg, #fef3c7, #fde68a);
                    border: 2px solid #f59e0b; border-radius: 24px;
                    padding: 8px 20px; display: inline-flex; align-items: center; gap: 8px;">
            <span style="font-size: 16px;">📋</span>
            <span style="font-size: 14px; font-weight: 700; color: #92400e;
                         text-transform: uppercase; letter-spacing: 1px;">STRAWMAN</span>
        </div>
        '''

    # ==================== End v4.5.8 Helper Methods ====================

    def _create_content_metadata_html(self, slide: Dict[str, Any], layout: str) -> str:
        """
        Create strawman metadata display HTML for content slides (C1, L25, V1).

        v4.5.13: Clean four-section structure for strawman content:
        1. Purpose - Why this slide exists in the story
        2. Topics - What content to cover (bullet points)
        3. Generation Instructions - How the service should build it
        4. Notes - Additional context or speaker notes

        Args:
            slide: Slide data with all strawman fields
            layout: Layout ID (C1, L25, V1)

        Returns:
            HTML string for rich_content field
        """
        variant_id = slide.get('variant_id') or 'auto-select'
        service = slide.get('service') or 'text'
        purpose = slide.get('purpose') or ''
        topics = slide.get('topics', [])
        generation_instructions = slide.get('generation_instructions', '')
        notes = slide.get('notes', '')

        # v4.5.13: Build four consistent sections

        # Section 1: Purpose (v4.5.14: font sizes increased 20%)
        purpose_section = ''
        if purpose and purpose != '-':
            purpose_display = purpose.replace('_', ' ').title()
            purpose_section = f'''
            <div style="margin-bottom: 24px;">
                <div style="font-size: 22px; font-weight: 700; color: #6366f1; margin-bottom: 8px;
                            text-transform: uppercase; letter-spacing: 1px;">
                    Purpose
                </div>
                <div style="font-size: 24px; color: #1f2937; line-height: 1.5;">
                    {purpose_display}
                </div>
            </div>
            '''

        # Section 2: Topics (v4.5.14: font sizes increased 20%)
        topics_section = ''
        if topics:
            bullet_items = ''.join([f'<li style="margin-bottom: 8px;">{t}</li>' for t in topics])
            topics_section = f'''
            <div style="margin-bottom: 24px;">
                <div style="font-size: 22px; font-weight: 700; color: #6366f1; margin-bottom: 8px;
                            text-transform: uppercase; letter-spacing: 1px;">
                    Topics
                </div>
                <ul style="list-style: disc; margin-left: 24px; font-size: 24px; color: #1f2937; line-height: 1.6;">
                    {bullet_items}
                </ul>
            </div>
            '''

        # Section 3: Generation Instructions (v4.5.14: font sizes increased 20%)
        gen_instructions_section = ''
        if generation_instructions:
            gen_instructions_section = f'''
            <div style="margin-bottom: 24px;">
                <div style="font-size: 22px; font-weight: 700; color: #6366f1; margin-bottom: 8px;
                            text-transform: uppercase; letter-spacing: 1px;">
                    Generation Instructions
                </div>
                <div style="font-size: 24px; color: #1f2937; line-height: 1.5;">
                    {generation_instructions}
                </div>
            </div>
            '''

        # Section 4: Notes (v4.5.14: font sizes increased 20%)
        notes_section = ''
        if notes:
            notes_section = f'''
            <div style="margin-bottom: 24px;">
                <div style="font-size: 22px; font-weight: 700; color: #6366f1; margin-bottom: 8px;
                            text-transform: uppercase; letter-spacing: 1px;">
                    Notes
                </div>
                <div style="font-size: 24px; color: #1f2937; line-height: 1.5;">
                    {notes}
                </div>
            </div>
            '''

        # v4.5.14: Removed redundant STRAWMAN badge and metadata chips from content area
        # (already shown in slide header and footer)
        return f'''
<div style="height: 100%; padding: 40px; font-family: system-ui, -apple-system, sans-serif;
            display: flex; flex-direction: column; gap: 16px;">

    <!-- Four Sections: Purpose, Topics, Generation Instructions, Notes -->
    {purpose_section}
    {topics_section}
    {gen_instructions_section}
    {notes_section}
</div>
'''

    def _create_hero_html(self, slide: Dict[str, Any], hero_type: str = None) -> str:
        """
        Create HTML for hero slide with STRAWMAN indicator.

        v4.5.6: Shows metadata in hero format with clear strawman badge.

        Args:
            slide: Slide data
            hero_type: Type of hero (title_slide, section_divider, closing_slide)

        Returns:
            HTML string for hero_content field
        """
        title = slide.get('title', '')
        subtitle = slide.get('subtitle', '')
        topics = slide.get('topics', [])
        notes = slide.get('notes', '')
        slide_number = slide.get('slide_number', 0)
        layout = slide.get('layout', 'H1')

        # Use subtitle if set, otherwise first topic or notes
        if not subtitle:
            subtitle = (topics[0] if topics else notes) or ""

        # Style based on hero type
        if hero_type == 'closing_slide':
            layout_label = 'H3 · Closing Slide'
            bg_gradient = 'linear-gradient(135deg, #1e3a5f 0%, #2d5a87 100%)'
        elif hero_type == 'section_divider':
            layout_label = 'H2 · Section Divider'
            bg_gradient = 'linear-gradient(135deg, #374151 0%, #4b5563 100%)'
        else:
            layout_label = f'{layout} · Hero Slide'
            bg_gradient = 'linear-gradient(135deg, #1e3a5f 0%, #374151 100%)'

        return f'''
<div style="display: flex; flex-direction: column; justify-content: center; align-items: center;
            text-align: center; height: 100%; padding: 60px 80px;
            background: {bg_gradient};">

    <!-- STRAWMAN Badge -->
    <div style="background: rgba(245, 158, 11, 0.9); padding: 8px 24px;
                border-radius: 20px; margin-bottom: 24px;">
        <span style="font-size: 14px; font-weight: 700; color: #92400e;
                     text-transform: uppercase; letter-spacing: 2px;">
            📋 STRAWMAN
        </span>
    </div>

    <!-- Layout indicator -->
    <div style="margin-bottom: 32px;">
        <span style="background: rgba(255,255,255,0.1); color: #9ca3af; padding: 8px 20px;
                    border-radius: 16px; font-size: 14px; font-weight: 500;
                    border: 1px solid rgba(255,255,255,0.2);">
            {layout_label}
        </span>
    </div>

    <h1 style="font-size: 64px; font-weight: 700; color: #ffffff; margin: 0 0 24px 0; line-height: 1.2;
               text-shadow: 0 2px 4px rgba(0,0,0,0.2); max-width: 90%;">
        {title}
    </h1>

    <p style="font-size: 28px; color: #94a3b8; margin: 0; max-width: 70%; line-height: 1.5;">
        {subtitle}
    </p>
</div>
'''

    def _create_title_slide_html(self, presentation_title: str, slide: Dict[str, Any]) -> str:
        """
        Create HTML specifically for title slide with STRAWMAN indicator.

        v4.5.6: Shows title slide with clear strawman badge and layout info.

        Args:
            presentation_title: The main presentation title
            slide: Slide data with optional subtitle

        Returns:
            HTML string for hero_content field
        """
        subtitle = slide.get('subtitle', '')
        topics = slide.get('topics', [])
        notes = slide.get('notes', '')
        layout = slide.get('layout', 'H1')

        # Use subtitle if set, otherwise first topic or notes
        if not subtitle:
            subtitle = (topics[0] if topics else notes) or ""

        return f'''
<div style="display: flex; flex-direction: column; justify-content: center; align-items: center;
            text-align: center; height: 100%; padding: 60px 80px;
            background: linear-gradient(135deg, #1e3a5f 0%, #2d5a87 100%);">

    <!-- STRAWMAN Badge -->
    <div style="background: rgba(245, 158, 11, 0.9); padding: 8px 24px;
                border-radius: 20px; margin-bottom: 24px;">
        <span style="font-size: 14px; font-weight: 700; color: #92400e;
                     text-transform: uppercase; letter-spacing: 2px;">
            📋 STRAWMAN
        </span>
    </div>

    <!-- Layout indicator -->
    <div style="margin-bottom: 40px;">
        <span style="background: rgba(255,255,255,0.1); color: #9ca3af; padding: 8px 20px;
                    border-radius: 16px; font-size: 14px; font-weight: 500;
                    border: 1px solid rgba(255,255,255,0.2);">
            {layout} · Title Slide
        </span>
    </div>

    <h1 style="font-size: 72px; font-weight: 700; color: #ffffff; margin: 0 0 24px 0; line-height: 1.2;
               text-shadow: 0 4px 8px rgba(0,0,0,0.3); max-width: 90%;">
        {presentation_title}
    </h1>

    <p style="font-size: 28px; color: #94a3b8; margin: 0 0 60px 0; max-width: 70%; line-height: 1.5;">
        {subtitle}
    </p>

    <div style="color: #64748b; font-size: 16px;">
        Footer · Logo area
    </div>
</div>
'''

    def _create_analytics_metadata_html(self, slide: Dict[str, Any], layout: str) -> str:
        """
        Create strawman metadata display for analytics/chart slides.

        v4.5.8: Full-width with large chart placeholder.

        Args:
            slide: Slide data
            layout: Layout ID (L02, C2, V2)

        Returns:
            HTML string for rich_content field
        """
        variant_id = slide.get('variant_id') or 'auto-select'
        service = slide.get('service') or 'analytics'
        topics = slide.get('topics', [])

        # Create data point chips
        data_chips = ''
        if topics:
            chips = []
            for topic in topics[:6]:  # Max 6 data points shown
                chips.append(f'''
                <span style="background: #dbeafe; color: #1e40af; padding: 8px 16px;
                             border-radius: 12px; font-size: 13px; font-weight: 500;">
                    📈 {topic}
                </span>
                ''')
            data_chips = '\n'.join(chips)

        # v4.5.10: return with bigger chips and STRAWMAN watermark
        return f'''
<div style="height: 100%; padding: 40px; font-family: system-ui, -apple-system, sans-serif;
            display: flex; flex-direction: column; gap: 24px; position: relative;">

    <!-- Top: Badge + Service Info - v4.5.10: 2x bigger chips -->
    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 20px;">
        <div style="display: flex; align-items: center; gap: 16px; flex-wrap: wrap;">
            {self._create_compact_badge()}
            <span style="background: #dbeafe; color: #1e40af; padding: 12px 28px;
                         border-radius: 20px; font-size: 24px; font-weight: 600;">
                📊 Analytics Service
            </span>
        </div>
        <div style="display: flex; gap: 20px; flex-wrap: wrap;">
            <span style="background: #e0e7ff; color: #3730a3; padding: 12px 28px;
                         border-radius: 20px; font-size: 24px; font-weight: 600;">
                🎨 {layout}
            </span>
            <span style="background: #d1fae5; color: #065f46; padding: 12px 28px;
                         border-radius: 20px; font-size: 24px; font-weight: 600;">
                📐 {variant_id}
            </span>
        </div>
    </div>

    <!-- Chart Placeholder - Large Visual -->
    <div style="flex: 1; background: linear-gradient(135deg, #1e3a5f 0%, #2d5a87 100%);
                border-radius: 20px; display: flex; flex-direction: column;
                justify-content: center; align-items: center; gap: 24px;
                border: 3px dashed rgba(255,255,255,0.3); min-height: 200px;">
        <span style="font-size: 80px;">📊</span>
        <div style="text-align: center;">
            <div style="font-size: 24px; font-weight: 700; color: white; margin-bottom: 8px;">
                {variant_id} Chart
            </div>
            <div style="font-size: 16px; color: rgba(255,255,255,0.7);">
                Generated by Analytics Service
            </div>
        </div>
    </div>

    <!-- Data Points -->
    <div style="display: flex; gap: 12px; flex-wrap: wrap;">
        {data_chips}
    </div>

    <!-- v4.5.10: STRAWMAN watermark bottom-right -->
    <div style="position: absolute; bottom: 16px; right: 24px;
                font-size: 14px; font-weight: 600; color: #9ca3af;
                letter-spacing: 2px; opacity: 0.7;">
        STRAWMAN
    </div>
</div>
'''

    def _create_diagram_metadata_html(self, slide: Dict[str, Any], layout: str) -> str:
        """
        Create strawman metadata display for diagram slides.

        v4.5.8: Full-width with diagram flow placeholder.

        Args:
            slide: Slide data
            layout: Layout ID (C4, V3)

        Returns:
            HTML string for rich_content field
        """
        variant_id = slide.get('variant_id') or 'auto-select'
        service = slide.get('service') or 'diagram'
        topics = slide.get('topics', [])

        # Create flow step chips
        flow_chips = ''
        if topics:
            chips = []
            for i, topic in enumerate(topics[:5]):  # Max 5 steps shown
                arrow = ' → ' if i < len(topics) - 1 and i < 4 else ''
                chips.append(f'''
                <span style="background: linear-gradient(135deg, #a855f7 0%, #6366f1 100%);
                             color: white; padding: 10px 18px;
                             border-radius: 12px; font-size: 13px; font-weight: 600;
                             box-shadow: 0 2px 8px rgba(139, 92, 246, 0.3);">
                    {topic}
                </span>
                ''')
                if arrow:
                    chips.append(f'''
                    <span style="color: #9ca3af; font-size: 20px; font-weight: bold;">→</span>
                    ''')
            flow_chips = '\n'.join(chips)

        # v4.5.10: return with bigger chips and STRAWMAN watermark
        return f'''
<div style="height: 100%; padding: 40px; font-family: system-ui, -apple-system, sans-serif;
            display: flex; flex-direction: column; gap: 24px; position: relative;">

    <!-- Top: Badge + Service Info - v4.5.10: 2x bigger chips -->
    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 20px;">
        <div style="display: flex; align-items: center; gap: 16px; flex-wrap: wrap;">
            {self._create_compact_badge()}
            <span style="background: #ede9fe; color: #6d28d9; padding: 12px 28px;
                         border-radius: 20px; font-size: 24px; font-weight: 600;">
                🔀 Diagram Service
            </span>
        </div>
        <div style="display: flex; gap: 20px; flex-wrap: wrap;">
            <span style="background: #e0e7ff; color: #3730a3; padding: 12px 28px;
                         border-radius: 20px; font-size: 24px; font-weight: 600;">
                🎨 {layout}
            </span>
            <span style="background: #d1fae5; color: #065f46; padding: 12px 28px;
                         border-radius: 20px; font-size: 24px; font-weight: 600;">
                📐 {variant_id}
            </span>
        </div>
    </div>

    <!-- Diagram Placeholder - Large Visual -->
    <div style="flex: 1; background: linear-gradient(135deg, #4c1d95 0%, #6d28d9 100%);
                border-radius: 20px; display: flex; flex-direction: column;
                justify-content: center; align-items: center; gap: 24px;
                border: 3px dashed rgba(255,255,255,0.3); min-height: 200px;">
        <span style="font-size: 80px;">🔀</span>
        <div style="text-align: center;">
            <div style="font-size: 24px; font-weight: 700; color: white; margin-bottom: 8px;">
                {variant_id} Diagram
            </div>
            <div style="font-size: 16px; color: rgba(255,255,255,0.7);">
                Generated by Diagram Service
            </div>
        </div>
    </div>

    <!-- Flow Steps -->
    <div style="display: flex; gap: 12px; flex-wrap: wrap; align-items: center; justify-content: center;">
        {flow_chips}
    </div>

    <!-- v4.5.10: STRAWMAN watermark bottom-right -->
    <div style="position: absolute; bottom: 16px; right: 24px;
                font-size: 14px; font-weight: 600; color: #9ca3af;
                letter-spacing: 2px; opacity: 0.7;">
        STRAWMAN
    </div>
</div>
'''

    def _create_infographic_metadata_html(self, slide: Dict[str, Any], layout: str) -> str:
        """
        Create strawman metadata display for infographic slides.

        v4.5.8: Full-width with visual hierarchy placeholder.

        Args:
            slide: Slide data
            layout: Layout ID (C3, V4)

        Returns:
            HTML string for rich_content field
        """
        variant_id = slide.get('variant_id') or 'auto-select'
        service = slide.get('service') or 'illustrator'
        topics = slide.get('topics', [])

        # Create element chips
        element_chips = ''
        if topics:
            chips = []
            for topic in topics[:6]:  # Max 6 elements shown
                chips.append(f'''
                <span style="background: linear-gradient(135deg, #ec4899 0%, #f43f5e 100%);
                             color: white; padding: 8px 16px;
                             border-radius: 12px; font-size: 13px; font-weight: 500;
                             box-shadow: 0 2px 8px rgba(236, 72, 153, 0.3);">
                    🎯 {topic}
                </span>
                ''')
            element_chips = '\n'.join(chips)

        # v4.5.10: return with bigger chips and STRAWMAN watermark
        return f'''
<div style="height: 100%; padding: 40px; font-family: system-ui, -apple-system, sans-serif;
            display: flex; flex-direction: column; gap: 24px; position: relative;">

    <!-- Top: Badge + Service Info - v4.5.10: 2x bigger chips -->
    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 20px;">
        <div style="display: flex; align-items: center; gap: 16px; flex-wrap: wrap;">
            {self._create_compact_badge()}
            <span style="background: #fce7f3; color: #9d174d; padding: 12px 28px;
                         border-radius: 20px; font-size: 24px; font-weight: 600;">
                🎨 Illustrator Service
            </span>
        </div>
        <div style="display: flex; gap: 20px; flex-wrap: wrap;">
            <span style="background: #e0e7ff; color: #3730a3; padding: 12px 28px;
                         border-radius: 20px; font-size: 24px; font-weight: 600;">
                🎨 {layout}
            </span>
            <span style="background: #d1fae5; color: #065f46; padding: 12px 28px;
                         border-radius: 20px; font-size: 24px; font-weight: 600;">
                📐 {variant_id}
            </span>
        </div>
    </div>

    <!-- Infographic Placeholder - Large Visual -->
    <div style="flex: 1; background: linear-gradient(135deg, #be185d 0%, #ec4899 100%);
                border-radius: 20px; display: flex; flex-direction: column;
                justify-content: center; align-items: center; gap: 24px;
                border: 3px dashed rgba(255,255,255,0.3); min-height: 200px;">
        <span style="font-size: 80px;">🎨</span>
        <div style="text-align: center;">
            <div style="font-size: 24px; font-weight: 700; color: white; margin-bottom: 8px;">
                {variant_id} Infographic
            </div>
            <div style="font-size: 16px; color: rgba(255,255,255,0.7);">
                Generated by Illustrator Service
            </div>
        </div>
    </div>

    <!-- Content Elements -->
    <div style="display: flex; gap: 12px; flex-wrap: wrap;">
        {element_chips}
    </div>

    <!-- v4.5.10: STRAWMAN watermark bottom-right -->
    <div style="position: absolute; bottom: 16px; right: 24px;
                font-size: 14px; font-weight: 600; color: #9ca3af;
                letter-spacing: 2px; opacity: 0.7;">
        STRAWMAN
    </div>
</div>
'''

    def _create_iseries_metadata_html(self, slide: Dict[str, Any], layout: str) -> str:
        """
        Create strawman metadata display for I-series slides with split layout preview.

        v4.5.8: True split layout showing actual image zone proportions.

        I-series layouts:
        - I1: Wide image left (660×1080), content right
        - I2: Wide image right (660×1080), content left
        - I3: Narrow image left (360×1080), content right
        - I4: Narrow image right (360×1080), content left

        Args:
            slide: Slide data
            layout: Layout ID (I1, I2, I3, I4)

        Returns:
            HTML string for rich_content field
        """
        variant_id = slide.get('variant_id') or 'auto-select'
        service = slide.get('service') or 'text'
        topics = slide.get('topics', [])
        semantic_group = slide.get('semantic_group')

        # Determine image position and size
        image_left = layout in ['I1', 'I3']
        wide_image = layout in ['I1', 'I2']

        image_dims = '660×1080' if wide_image else '360×1080'
        image_width = '40%' if wide_image else '25%'

        # Create topic rows for content zone
        topic_rows = ''
        if topics:
            for i, topic in enumerate(topics[:4]):  # Max 4 topics shown
                gradient = self._get_topic_card_gradient(i)
                topic_rows += f'''
                <div style="background: {gradient}; border-radius: 12px; padding: 16px;
                            color: white; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                    <div style="font-size: 11px; opacity: 0.85; margin-bottom: 4px;">Topic {i+1}</div>
                    <div style="font-size: 14px; font-weight: 600; line-height: 1.3;">{topic}</div>
                </div>
                '''
        else:
            topic_rows = '''
            <div style="background: #f8fafc; border-radius: 12px; padding: 16px;
                        color: #9ca3af; font-style: italic; text-align: center;">
                No topics specified
            </div>
            '''

        # Image zone placeholder
        image_zone = f'''
        <div style="width: {image_width}; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    display: flex; flex-direction: column; justify-content: center; align-items: center;
                    padding: 32px; min-height: 100%;">
            <span style="font-size: 64px; margin-bottom: 16px;">🖼️</span>
            <div style="background: rgba(255,255,255,0.2); padding: 12px 24px; border-radius: 12px; text-align: center;">
                <div style="font-size: 16px; color: white; font-weight: 600;">Image Zone</div>
                <div style="font-size: 14px; color: rgba(255,255,255,0.8);">{image_dims}</div>
            </div>
        </div>
        '''

        # Content zone
        semantic_chip = ''
        if semantic_group:
            semantic_chip = f'''
            <span style="background: #fef3c7; color: #92400e; padding: 4px 12px;
                         border-radius: 12px; font-size: 12px; font-weight: 600;">
                🏷️ {semantic_group}
            </span>
            '''

        # v4.5.10: Update content zone with bigger chips
        content_zone = f'''
        <div style="flex: 1; padding: 32px; display: flex; flex-direction: column; gap: 20px;">

            <!-- Badge Row - v4.5.10: bigger chips -->
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
                <div style="background: linear-gradient(135deg, #fef3c7, #fde68a);
                            border: 2px solid #f59e0b; border-radius: 20px;
                            padding: 10px 20px; display: inline-flex; align-items: center; gap: 8px;">
                    <span style="font-size: 18px;">📋</span>
                    <span style="font-size: 16px; font-weight: 700; color: #92400e;
                                 text-transform: uppercase; letter-spacing: 1px;">STRAWMAN</span>
                </div>
                <span style="background: #c7d2fe; color: #3730a3; padding: 12px 28px;
                             border-radius: 20px; font-size: 24px; font-weight: 600;">🎨 {layout}</span>
            </div>

            <!-- Topics Grid -->
            <div style="flex: 1; display: flex; flex-direction: column; gap: 12px;">
                {topic_rows}
            </div>

            <!-- Footer Info - v4.5.10: bigger chips -->
            <div style="display: flex; gap: 16px; flex-wrap: wrap;">
                <span style="background: #d1fae5; color: #065f46; padding: 12px 28px;
                             border-radius: 20px; font-size: 24px; font-weight: 600;">
                    📐 {variant_id}
                </span>
                <span style="background: #fce7f3; color: #9d174d; padding: 12px 28px;
                             border-radius: 20px; font-size: 24px; font-weight: 600;">
                    ⚙️ {service}
                </span>
                {semantic_chip}
            </div>
        </div>
        '''

        # v4.5.10: STRAWMAN watermark element
        strawman_watermark = '''
        <div style="position: absolute; bottom: 16px; right: 24px;
                    font-size: 14px; font-weight: 600; color: #9ca3af;
                    letter-spacing: 2px; opacity: 0.7;">
            STRAWMAN
        </div>
        '''

        # Arrange based on image position - v4.5.10: add position relative and watermark
        if image_left:
            return f'''
<div style="height: 100%; display: flex; gap: 0; font-family: system-ui, -apple-system, sans-serif; position: relative;">
    {image_zone}
    {content_zone}
    {strawman_watermark}
</div>
'''
        else:
            return f'''
<div style="height: 100%; display: flex; gap: 0; font-family: system-ui, -apple-system, sans-serif; position: relative;">
    {content_zone}
    {image_zone}
    {strawman_watermark}
</div>
'''
