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
- Displays all AI decisions as formatted text in content zone
- Clear STRAWMAN indicator on all slides
- Uses Layout Service templates (C1, I1, H1) for structure only
- NO LLM calls - just shows decisions made
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
            if is_hero or layout in self.HERO_LAYOUTS:
                # Hero slide
                if hero_type == 'title_slide':
                    html_content = self._create_title_slide_html(presentation_title, slide)
                else:
                    html_content = self._create_hero_html(slide, hero_type)

                content = {'hero_content': html_content}

            elif layout in self.ANALYTICS_LAYOUTS:
                # Analytics slide - metadata display
                content = {
                    'slide_title': slide.get('title', 'Analytics'),
                    'rich_content': self._create_analytics_metadata_html(slide, layout)
                }

            elif layout in self.DIAGRAM_LAYOUTS:
                # Diagram slide - metadata display
                content = {
                    'slide_title': slide.get('title', 'Diagram'),
                    'rich_content': self._create_diagram_metadata_html(slide, layout)
                }

            elif layout in self.INFOGRAPHIC_LAYOUTS:
                # Infographic slide - metadata display
                content = {
                    'slide_title': slide.get('title', 'Infographic'),
                    'rich_content': self._create_infographic_metadata_html(slide, layout)
                }

            elif layout in self.ISERIES_LAYOUTS:
                # I-series slide - metadata display with image placeholder
                content = {
                    'slide_title': slide.get('title', 'Visual'),
                    'rich_content': self._create_iseries_metadata_html(slide, layout)
                }

            else:
                # Default content slide (L25, C1, V1)
                content = {
                    'slide_title': slide.get('title', 'Slide'),
                    'rich_content': self._create_content_metadata_html(slide, layout)
                }

            # Build transformed slide with metadata
            transformed_slide = {
                'layout': layout,
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

    def _create_content_metadata_html(self, slide: Dict[str, Any], layout: str) -> str:
        """
        Create strawman metadata display HTML for content slides (C1, L25, V1).

        v4.5.6: Shows all AI decisions as formatted text.

        Args:
            slide: Slide data with all strawman fields
            layout: Layout ID (C1, L25, V1)

        Returns:
            HTML string for rich_content field
        """
        variant_id = slide.get('variant_id') or 'auto-select'
        service = slide.get('service') or 'text'
        purpose = slide.get('purpose') or '-'
        topics = slide.get('topics', [])
        semantic_group = slide.get('semantic_group')
        generation_instructions = slide.get('generation_instructions')

        rows = [
            ('Layout', f'{layout} (Content slide)'),
            ('Selected Variant', variant_id),
            ('Service', service),
            ('Purpose', purpose),
        ]

        if semantic_group:
            rows.append(('Semantic Group', semantic_group))

        rows.append(('Topics', self._format_topics(topics)))

        if generation_instructions:
            rows.append(('Generation Notes', generation_instructions))

        return f'''
<div class="strawman-metadata" style="padding: 24px; font-family: system-ui, -apple-system, sans-serif;">
    {self._create_strawman_badge()}
    {self._create_metadata_table(rows)}
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

        v4.5.6: Shows chart type and data decisions.

        Args:
            slide: Slide data
            layout: Layout ID (L02, C2, V2)

        Returns:
            HTML string for rich_content field
        """
        variant_id = slide.get('variant_id') or 'auto-select'
        service = slide.get('service') or 'analytics'
        purpose = slide.get('purpose') or '-'
        topics = slide.get('topics', [])
        generation_instructions = slide.get('generation_instructions')

        rows = [
            ('Layout', f'{layout} (Analytics/Chart)'),
            ('Chart Type', variant_id),
            ('Service', service),
            ('Purpose', purpose),
            ('Data Points', self._format_topics(topics)),
        ]

        if generation_instructions:
            rows.append(('Chart Instructions', generation_instructions))

        return f'''
<div class="strawman-metadata" style="padding: 24px; font-family: system-ui, -apple-system, sans-serif;">
    {self._create_strawman_badge()}

    <!-- Chart icon indicator -->
    <div style="text-align: center; margin-bottom: 20px;">
        <span style="font-size: 48px;">📊</span>
        <p style="color: #6b7280; font-size: 14px; margin: 8px 0 0 0;">
            Chart will be generated by Analytics Service
        </p>
    </div>

    {self._create_metadata_table(rows)}
</div>
'''

    def _create_diagram_metadata_html(self, slide: Dict[str, Any], layout: str) -> str:
        """
        Create strawman metadata display for diagram slides.

        v4.5.6: Shows diagram type and flow decisions.

        Args:
            slide: Slide data
            layout: Layout ID (C4, V3)

        Returns:
            HTML string for rich_content field
        """
        variant_id = slide.get('variant_id') or 'auto-select'
        service = slide.get('service') or 'diagram'
        purpose = slide.get('purpose') or '-'
        topics = slide.get('topics', [])
        generation_instructions = slide.get('generation_instructions')

        rows = [
            ('Layout', f'{layout} (Diagram)'),
            ('Diagram Type', variant_id),
            ('Service', service),
            ('Purpose', purpose),
            ('Flow Steps', self._format_topics(topics)),
        ]

        if generation_instructions:
            rows.append(('Diagram Instructions', generation_instructions))

        return f'''
<div class="strawman-metadata" style="padding: 24px; font-family: system-ui, -apple-system, sans-serif;">
    {self._create_strawman_badge()}

    <!-- Diagram icon indicator -->
    <div style="text-align: center; margin-bottom: 20px;">
        <span style="font-size: 48px;">🔀</span>
        <p style="color: #6b7280; font-size: 14px; margin: 8px 0 0 0;">
            Diagram will be generated by Diagram Service
        </p>
    </div>

    {self._create_metadata_table(rows)}
</div>
'''

    def _create_infographic_metadata_html(self, slide: Dict[str, Any], layout: str) -> str:
        """
        Create strawman metadata display for infographic slides.

        v4.5.6: Shows infographic type and visual decisions.

        Args:
            slide: Slide data
            layout: Layout ID (C3, V4)

        Returns:
            HTML string for rich_content field
        """
        variant_id = slide.get('variant_id') or 'auto-select'
        service = slide.get('service') or 'illustrator'
        purpose = slide.get('purpose') or '-'
        topics = slide.get('topics', [])
        generation_instructions = slide.get('generation_instructions')

        rows = [
            ('Layout', f'{layout} (Infographic)'),
            ('Visual Type', variant_id),
            ('Service', service),
            ('Purpose', purpose),
            ('Content Elements', self._format_topics(topics)),
        ]

        if generation_instructions:
            rows.append(('Visual Instructions', generation_instructions))

        return f'''
<div class="strawman-metadata" style="padding: 24px; font-family: system-ui, -apple-system, sans-serif;">
    {self._create_strawman_badge()}

    <!-- Infographic icon indicator -->
    <div style="text-align: center; margin-bottom: 20px;">
        <span style="font-size: 48px;">🎨</span>
        <p style="color: #6b7280; font-size: 14px; margin: 8px 0 0 0;">
            Infographic will be generated by Illustrator Service
        </p>
    </div>

    {self._create_metadata_table(rows)}
</div>
'''

    def _create_iseries_metadata_html(self, slide: Dict[str, Any], layout: str) -> str:
        """
        Create strawman metadata display for I-series slides with image placeholder.

        v4.5.6: Shows image+text layout with image zone placeholder.

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
        purpose = slide.get('purpose') or '-'
        topics = slide.get('topics', [])
        semantic_group = slide.get('semantic_group')

        # Determine image position and size
        image_left = layout in ['I1', 'I3']
        wide_image = layout in ['I1', 'I2']

        image_dims = '660×1080' if wide_image else '360×1080'
        position = 'Left' if image_left else 'Right'
        size = 'Wide' if wide_image else 'Narrow'

        rows = [
            ('Layout', f'{layout} (Image + Content)'),
            ('Image Position', f'{position} ({size})'),
            ('Image Size', image_dims),
            ('Selected Variant', variant_id),
            ('Service', service),
            ('Purpose', purpose),
        ]

        if semantic_group:
            rows.append(('Semantic Group', semantic_group))

        rows.append(('Topics', self._format_topics(topics)))

        # Image placeholder
        image_placeholder = f'''
<div style="width: 35%; min-height: 200px; background: linear-gradient(135deg, #e0e7ff, #c7d2fe);
            border-radius: 12px; display: flex; flex-direction: column; align-items: center;
            justify-content: center; border: 2px dashed #818cf8;">
    <span style="font-size: 48px;">🖼️</span>
    <p style="font-size: 14px; color: #4338ca; margin: 8px 0 0 0; font-weight: 600;">Image Zone</p>
    <p style="font-size: 12px; color: #6366f1; margin: 4px 0 0 0;">{image_dims}</p>
</div>
'''

        # Metadata content
        metadata_content = f'''
<div style="width: 60%; padding: 0 20px;">
    {self._create_strawman_badge()}
    {self._create_metadata_table(rows)}
</div>
'''

        # Arrange based on image position
        if image_left:
            return f'''
<div style="display: flex; align-items: stretch; gap: 24px; height: 100%; padding: 20px;
            font-family: system-ui, -apple-system, sans-serif;">
    {image_placeholder}
    {metadata_content}
</div>
'''
        else:
            return f'''
<div style="display: flex; align-items: stretch; gap: 24px; height: 100%; padding: 20px;
            font-family: system-ui, -apple-system, sans-serif;">
    {metadata_content}
    {image_placeholder}
</div>
'''
