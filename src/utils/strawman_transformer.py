"""
Strawman Transformer for v4.0.5

Transforms strawman data to deck-builder API format for preview generation.

This is a simplified version of v3.4's ContentTransformer, focused only on
generating preview presentations during the strawman phase.

Layouts:
- L29: Hero slides (title, section dividers, closing)
- L25: Content slides (rich content area)
"""
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class StrawmanTransformer:
    """
    Transform strawman data to deck-builder API format.

    v4.0.5: Simplified transformer for preview generation only.
    """

    def transform(self, strawman_dict: Dict[str, Any], topic: str) -> Dict[str, Any]:
        """
        Transform strawman to deck-builder API format.

        Args:
            strawman_dict: Strawman data from StrawmanGenerator
            topic: Presentation topic (fallback for title)

        Returns:
            Dict with 'title' and 'slides' for deck-builder API:
            {
                "title": "Presentation Title",
                "slides": [
                    {"layout": "L29", "content": {"hero_content": "..."}},
                    {"layout": "L25", "content": {"slide_title": "...", "rich_content": "..."}},
                    ...
                ]
            }
        """
        transformed_slides = []

        for slide in strawman_dict.get('slides', []):
            # Determine if this is a hero slide or content slide
            is_hero = slide.get('is_hero', False)
            hero_type = slide.get('hero_type')

            if is_hero or hero_type:
                # Hero slide -> L29
                transformed_slides.append({
                    'layout': 'L29',
                    'content': {
                        'hero_content': self._create_hero_html(slide, hero_type)
                    }
                })
            else:
                # Content slide -> L25
                transformed_slides.append({
                    'layout': 'L25',
                    'content': {
                        'slide_title': slide.get('title', 'Slide'),
                        'rich_content': self._create_content_html(slide)
                    }
                })

        presentation_title = strawman_dict.get('title', topic) or 'Untitled Presentation'

        logger.info(f"Transformed {len(transformed_slides)} slides for preview")

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

        # Use first topic as subtitle, or notes
        subtitle = topics[0] if topics else notes

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
            # Title slide (default)
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
