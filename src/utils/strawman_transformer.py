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
                # Analytics slide - placeholder for chart
                content = {
                    'slide_title': slide.get('title', 'Analytics'),
                    'rich_content': self._create_analytics_placeholder_html(slide)
                }

            elif layout in self.DIAGRAM_LAYOUTS:
                # Diagram slide - placeholder for diagram
                content = {
                    'slide_title': slide.get('title', 'Diagram'),
                    'rich_content': self._create_diagram_placeholder_html(slide)
                }

            elif layout in self.INFOGRAPHIC_LAYOUTS:
                # Infographic slide - placeholder for visual
                content = {
                    'slide_title': slide.get('title', 'Infographic'),
                    'rich_content': self._create_infographic_placeholder_html(slide)
                }

            elif layout in self.ISERIES_LAYOUTS:
                # I-series slide - placeholder for image+text
                content = {
                    'slide_title': slide.get('title', 'Visual'),
                    'rich_content': self._create_iseries_placeholder_html(slide, layout)
                }

            else:
                # Default content slide (L25, C1, V1)
                content = {
                    'slide_title': slide.get('title', 'Slide'),
                    'rich_content': self._create_content_html(slide)
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

    def _create_hero_html(self, slide: Dict[str, Any], hero_type: str = None) -> str:
        """
        Create HTML for hero slide (L29).

        Args:
            slide: Slide data
            hero_type: Type of hero (title_slide, section_divider, closing_slide)

        Returns:
            HTML string for hero_content field
        """
        title = slide.get('title', '')
        topics = slide.get('topics', [])
        notes = slide.get('notes', '')

        # Use first topic as subtitle, or notes (v4.0.24: null-safe to avoid "None" display)
        subtitle = (topics[0] if topics else notes) or ""

        # Style based on hero type
        if hero_type == 'closing_slide':
            return f'''
<div style="display:flex;flex-direction:column;justify-content:center;align-items:center;
            text-align:center;height:100%;padding:60px;background:linear-gradient(135deg,#1f2937 0%,#374151 100%);">
    <h1 style="font-size:64px;font-weight:bold;color:#ffffff;margin:0 0 24px 0;line-height:1.2;">
        {title}
    </h1>
    <p style="font-size:28px;color:#9ca3af;margin:0;max-width:80%;line-height:1.5;">
        {subtitle}
    </p>
</div>
'''
        elif hero_type == 'section_divider':
            return f'''
<div style="display:flex;flex-direction:column;justify-content:center;align-items:center;
            text-align:center;height:100%;padding:60px;background:#f3f4f6;">
    <h1 style="font-size:56px;font-weight:bold;color:#1f2937;margin:0 0 16px 0;line-height:1.2;">
        {title}
    </h1>
    <p style="font-size:24px;color:#6b7280;margin:0;max-width:70%;line-height:1.5;">
        {subtitle}
    </p>
</div>
'''
        else:
            # Generic hero slide (default) - for unspecified hero types
            return f'''
<div style="display:flex;flex-direction:column;justify-content:center;align-items:center;
            text-align:center;height:100%;padding:60px;">
    <h1 style="font-size:72px;font-weight:bold;color:#1f2937;margin:0 0 24px 0;line-height:1.2;">
        {title}
    </h1>
    <p style="font-size:32px;color:#6b7280;margin:0;max-width:80%;line-height:1.5;">
        {subtitle}
    </p>
</div>
'''

    def _create_title_slide_html(self, presentation_title: str, slide: Dict[str, Any]) -> str:
        """
        Create HTML specifically for title slide (first slide).

        v4.0.6: Dedicated handler for title slides with prominent presentation title
        and gradient background for visual impact.

        Args:
            presentation_title: The main presentation title (from strawman.title or topic)
            slide: Slide data with optional subtitle from topics/notes

        Returns:
            HTML string for hero_content field
        """
        topics = slide.get('topics', [])
        notes = slide.get('notes', '')

        # Use first topic as subtitle, or notes (v4.0.24: null-safe to avoid "None" display)
        subtitle = (topics[0] if topics else notes) or ""

        return f'''
<div style="display:flex;flex-direction:column;justify-content:center;align-items:center;
            text-align:center;height:100%;padding:60px;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);">
    <h1 style="font-size:72px;font-weight:bold;color:#ffffff;margin:0 0 24px 0;line-height:1.2;
               text-shadow:2px 2px 4px rgba(0,0,0,0.3);">
        {presentation_title}
    </h1>
    <p style="font-size:28px;color:#f0f0f0;margin:0;max-width:80%;line-height:1.5;">
        {subtitle}
    </p>
</div>
'''

    def _create_content_html(self, slide: Dict[str, Any]) -> str:
        """
        Create HTML for content slide (L25).

        Args:
            slide: Slide data with topics/key_points

        Returns:
            HTML string for rich_content field
        """
        topics = slide.get('topics', [])
        notes = slide.get('notes', '')

        parts = []

        # Add notes/narrative if present
        if notes:
            parts.append(f'<p style="font-size:20px;color:#4b5563;line-height:1.6;margin-bottom:24px;">{notes}</p>')

        # Add bullet points from topics
        if topics:
            items = ''.join([
                f'<li style="margin-bottom:12px;color:#374151;">{topic}</li>'
                for topic in topics
            ])
            parts.append(f'''
<ul style="font-size:22px;line-height:1.8;padding-left:24px;margin:0;">
{items}
</ul>
''')

        if not parts:
            # Fallback if no content
            return '<p style="font-size:20px;color:#6b7280;">Content placeholder</p>'

        return '\n'.join(parts)

    def _create_analytics_placeholder_html(self, slide: Dict[str, Any]) -> str:
        """
        Create placeholder HTML for analytics/chart slides (L02, C2, V2).

        v4.0.25: Placeholder for chart generation. Will be replaced by Analytics Service.

        Args:
            slide: Slide data with topics/generation_instructions

        Returns:
            HTML string for rich_content field (chart placeholder)
        """
        title = slide.get('title', 'Analytics')
        topics = slide.get('topics', [])
        instructions = slide.get('generation_instructions', '')

        # Format data points from topics
        data_points = ''
        if topics:
            items = ''.join([
                f'<li style="margin-bottom:8px;color:#374151;">{topic}</li>'
                for topic in topics[:6]  # Max 6 data points
            ])
            data_points = f'''
<div style="margin-top:16px;">
    <p style="font-size:16px;color:#6b7280;margin-bottom:8px;">Data points:</p>
    <ul style="font-size:18px;line-height:1.6;padding-left:20px;margin:0;">{items}</ul>
</div>
'''

        return f'''
<div style="display:flex;flex-direction:column;align-items:center;justify-content:center;
            height:100%;padding:40px;background:#f9fafb;border:2px dashed #d1d5db;border-radius:12px;">
    <div style="font-size:48px;margin-bottom:16px;">📊</div>
    <h3 style="font-size:24px;color:#1f2937;margin:0 0 8px 0;text-align:center;">
        Chart: {title}
    </h3>
    <p style="font-size:16px;color:#6b7280;margin:0;text-align:center;max-width:80%;">
        {instructions or 'Chart will be generated by Analytics Service'}
    </p>
    {data_points}
</div>
'''

    def _create_diagram_placeholder_html(self, slide: Dict[str, Any]) -> str:
        """
        Create placeholder HTML for diagram slides (C4, V3).

        v4.0.25: Placeholder for diagram generation. Will be replaced by Diagram Service.

        Args:
            slide: Slide data with topics/generation_instructions

        Returns:
            HTML string for rich_content field (diagram placeholder)
        """
        title = slide.get('title', 'Diagram')
        topics = slide.get('topics', [])
        instructions = slide.get('generation_instructions', '')

        # Format steps/nodes from topics
        steps = ''
        if topics:
            step_boxes = ' → '.join([
                f'<span style="background:#e0e7ff;padding:8px 16px;border-radius:6px;white-space:nowrap;">{topic}</span>'
                for topic in topics[:5]  # Max 5 steps
            ])
            steps = f'''
<div style="margin-top:20px;display:flex;flex-wrap:wrap;gap:8px;align-items:center;justify-content:center;">
    {step_boxes}
</div>
'''

        return f'''
<div style="display:flex;flex-direction:column;align-items:center;justify-content:center;
            height:100%;padding:40px;background:#f0f9ff;border:2px dashed #7dd3fc;border-radius:12px;">
    <div style="font-size:48px;margin-bottom:16px;">🔀</div>
    <h3 style="font-size:24px;color:#0c4a6e;margin:0 0 8px 0;text-align:center;">
        Diagram: {title}
    </h3>
    <p style="font-size:16px;color:#64748b;margin:0;text-align:center;max-width:80%;">
        {instructions or 'Diagram will be generated by Diagram Service'}
    </p>
    {steps}
</div>
'''

    def _create_infographic_placeholder_html(self, slide: Dict[str, Any]) -> str:
        """
        Create placeholder HTML for infographic slides (C3, V4).

        v4.0.25: Placeholder for infographic generation. Will be replaced by Illustrator Service.

        Args:
            slide: Slide data with topics/generation_instructions

        Returns:
            HTML string for rich_content field (infographic placeholder)
        """
        title = slide.get('title', 'Infographic')
        topics = slide.get('topics', [])
        instructions = slide.get('generation_instructions', '')

        # Format levels from topics (for pyramid/funnel)
        levels = ''
        if topics:
            level_items = ''.join([
                f'<div style="background:linear-gradient(135deg,#fef3c7,#fde68a);padding:12px 24px;'
                f'border-radius:6px;margin:4px 0;width:{90 - i*10}%;text-align:center;color:#92400e;">'
                f'{topic}</div>'
                for i, topic in enumerate(topics[:5])  # Max 5 levels
            ])
            levels = f'''
<div style="display:flex;flex-direction:column;align-items:center;margin-top:20px;width:100%;">
    {level_items}
</div>
'''

        return f'''
<div style="display:flex;flex-direction:column;align-items:center;justify-content:center;
            height:100%;padding:40px;background:#fffbeb;border:2px dashed #fbbf24;border-radius:12px;">
    <div style="font-size:48px;margin-bottom:16px;">🎨</div>
    <h3 style="font-size:24px;color:#92400e;margin:0 0 8px 0;text-align:center;">
        Infographic: {title}
    </h3>
    <p style="font-size:16px;color:#a16207;margin:0;text-align:center;max-width:80%;">
        {instructions or 'Infographic will be generated by Illustrator Service'}
    </p>
    {levels}
</div>
'''

    def _create_iseries_placeholder_html(self, slide: Dict[str, Any], layout: str) -> str:
        """
        Create placeholder HTML for I-series slides (I1-I4: Image + Text layouts).

        v4.0.25: Placeholder for image+text generation.

        I-series layouts:
        - I1: Wide image left (660×1080), content right (1200×840)
        - I2: Wide image right (660×1080), content left (1140×840)
        - I3: Narrow image left (360×1080), content right (1500×840)
        - I4: Narrow image right (360×1080), content left (1440×840)

        Args:
            slide: Slide data with topics
            layout: Layout ID (I1, I2, I3, I4)

        Returns:
            HTML string for rich_content field
        """
        topics = slide.get('topics', [])
        notes = slide.get('notes', '')

        # Determine image position and size from layout
        image_left = layout in ['I1', 'I3']
        wide_image = layout in ['I1', 'I2']

        image_width = '45%' if wide_image else '30%'
        content_width = '50%' if wide_image else '65%'

        # Image placeholder
        image_placeholder = f'''
<div style="width:{image_width};height:300px;background:linear-gradient(135deg,#e0e7ff,#c7d2fe);
            border-radius:12px;display:flex;flex-direction:column;align-items:center;justify-content:center;">
    <div style="font-size:48px;margin-bottom:8px;">🖼️</div>
    <p style="font-size:14px;color:#4338ca;margin:0;">Image placeholder</p>
    <p style="font-size:12px;color:#6366f1;margin:4px 0 0 0;">{layout}: {'Wide' if wide_image else 'Narrow'} {'Left' if image_left else 'Right'}</p>
</div>
'''

        # Content
        content_parts = []
        if notes:
            content_parts.append(f'<p style="font-size:18px;color:#4b5563;line-height:1.6;margin-bottom:16px;">{notes}</p>')
        if topics:
            items = ''.join([
                f'<li style="margin-bottom:8px;color:#374151;">{topic}</li>'
                for topic in topics
            ])
            content_parts.append(f'<ul style="font-size:18px;line-height:1.6;padding-left:20px;margin:0;">{items}</ul>')

        content_html = ''.join(content_parts) if content_parts else '<p style="color:#6b7280;">Content placeholder</p>'

        content_block = f'''
<div style="width:{content_width};padding:20px;">
    {content_html}
</div>
'''

        # Arrange based on image position
        if image_left:
            return f'''
<div style="display:flex;align-items:center;gap:24px;height:100%;padding:20px;">
    {image_placeholder}
    {content_block}
</div>
'''
        else:
            return f'''
<div style="display:flex;align-items:center;gap:24px;height:100%;padding:20px;">
    {content_block}
    {image_placeholder}
</div>
'''
