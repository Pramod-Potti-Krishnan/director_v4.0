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
v4.5.5: Real variant templates from Text Service + proper hero templates.
- Loads actual HTML templates based on variant_id
- Uses H1/H2/H3 styled hero slides for preview
"""
import os
import re
from typing import Dict, Any, List, Optional
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

# Base path to Text Service templates (relative to project root)
# When deployed, this resolves to the text_table_builder templates
TEXT_SERVICE_TEMPLATES_PATH = os.path.join(
    os.path.dirname(__file__),  # src/utils
    '..', '..', '..', '..',  # Go up to agents/
    'text_table_builder', 'v1.2', 'app', 'templates'
)


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

    # v4.5.5: Variant ID to template category mapping
    # Maps variant_id prefix to template subdirectory
    VARIANT_CATEGORY_MAP = {
        'grid': 'grid',
        'metrics': 'metrics',
        'asymmetric': 'asymmetric',
        'hybrid': 'hybrid',
        'impact_quote': 'impact_quote',
        'matrix': 'matrix',
        'comparison': 'multilateral_comparison',
        'sequential': 'sequential',
        'single_column': 'single_column',
        'table': 'table'
    }

    # Default icons for placeholder content
    DEFAULT_ICONS = ['🎯', '📊', '💡', '🚀', '⚡', '🔧', '📈', '✨', '🎨', '🔍']

    def __init__(self):
        """Initialize transformer with template cache."""
        self._template_cache: Dict[str, str] = {}

    def _get_template_path(self, variant_id: str) -> Optional[str]:
        """
        Map variant_id to template file path.

        v4.5.5: Resolves variant_id to actual template HTML file.

        Args:
            variant_id: e.g., "grid_2x2_centered", "metrics_3col"

        Returns:
            Full path to template file, or None if not found
        """
        if not variant_id:
            return None

        # Determine category from variant_id prefix
        category = None
        for prefix, cat in self.VARIANT_CATEGORY_MAP.items():
            if variant_id.startswith(prefix):
                category = cat
                break

        if not category:
            logger.debug(f"No category found for variant: {variant_id}")
            return None

        # Try _c1.html first (compact variant), then .html
        base_path = os.path.join(TEXT_SERVICE_TEMPLATES_PATH, category)
        for suffix in ['_c1.html', '.html']:
            template_path = os.path.join(base_path, f"{variant_id}{suffix}")
            if os.path.exists(template_path):
                return template_path

        logger.debug(f"Template file not found for variant: {variant_id}")
        return None

    def _load_template(self, variant_id: str) -> Optional[str]:
        """
        Load template HTML from file with caching.

        v4.5.5: Loads actual variant templates from Text Service.

        Args:
            variant_id: Variant identifier

        Returns:
            HTML template string with placeholders, or None if not found
        """
        # Check cache first
        if variant_id in self._template_cache:
            return self._template_cache[variant_id]

        template_path = self._get_template_path(variant_id)
        if not template_path:
            return None

        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                template_html = f.read()
                self._template_cache[variant_id] = template_html
                logger.info(f"Loaded template: {variant_id} from {template_path}")
                return template_html
        except Exception as e:
            logger.warning(f"Failed to load template {variant_id}: {e}")
            return None

    def _populate_template(self, template_html: str, slide: Dict[str, Any]) -> str:
        """
        Populate template placeholders with slide content.

        v4.5.5: Intelligent placeholder population from topics.

        Placeholder patterns:
        - {box_N_icon}, {box_N_title}, {box_N_description}
        - {metric_N_number}, {metric_N_label}, {metric_N_description}
        - {item_N_title}, {item_N_description}
        - {insight_N}, {insights_heading}
        - etc.

        Args:
            template_html: HTML template with {placeholders}
            slide: Slide data with topics, title, subtitle

        Returns:
            Populated HTML string
        """
        topics = slide.get('topics', [])
        title = slide.get('title', 'Slide')
        subtitle = slide.get('subtitle', '')
        notes = slide.get('notes', '')

        # Find all placeholders in template
        placeholders = re.findall(r'\{([^}]+)\}', template_html)
        populated_html = template_html

        # Count how many content items we have
        num_topics = len(topics)

        # Group placeholders by index to understand structure
        # e.g., box_1_title, box_2_title -> we need to populate boxes 1-N
        for placeholder in set(placeholders):
            value = ''

            # Parse placeholder name
            if '_icon' in placeholder:
                # Icon placeholders: {box_1_icon}, {item_1_icon}, etc.
                idx = self._extract_index(placeholder)
                if idx is not None and idx < len(self.DEFAULT_ICONS):
                    value = self.DEFAULT_ICONS[idx]
                else:
                    value = '📌'

            elif '_title' in placeholder and 'insight' not in placeholder:
                # Title placeholders: {box_1_title}, {metric_1_label}, etc.
                idx = self._extract_index(placeholder)
                if idx is not None and idx < num_topics:
                    # Use topic as title (often topics are short phrases)
                    value = topics[idx]
                else:
                    value = f"Point {idx + 1 if idx else 1}"

            elif '_description' in placeholder:
                # Description placeholders: {box_1_description}, etc.
                idx = self._extract_index(placeholder)
                if idx is not None and idx < num_topics:
                    # For preview, use the topic itself or a summary
                    value = topics[idx] if idx < num_topics else "Description placeholder"
                else:
                    value = "Description placeholder"

            elif '_number' in placeholder or '_value' in placeholder:
                # Metric numbers: {metric_1_number}
                idx = self._extract_index(placeholder)
                # For preview, show placeholder numbers
                default_numbers = ['100+', '50%', '24/7', '99.9%', '10x', '5★']
                if idx is not None and idx < len(default_numbers):
                    value = default_numbers[idx]
                else:
                    value = 'N/A'

            elif '_label' in placeholder:
                # Metric labels: {metric_1_label}
                idx = self._extract_index(placeholder)
                if idx is not None and idx < num_topics:
                    value = topics[idx]
                else:
                    value = f"Metric {idx + 1 if idx else 1}"

            elif 'insight_' in placeholder and placeholder != 'insights_heading':
                # Insight items: {insight_1}, {insight_2}, etc.
                idx = self._extract_index(placeholder)
                if idx is not None and idx < num_topics:
                    value = topics[idx]
                else:
                    value = f"Key insight {idx + 1 if idx else 1}"

            elif placeholder == 'insights_heading':
                value = 'Key Insights'

            elif placeholder == 'heading' or placeholder == 'title':
                value = title

            elif placeholder == 'subheading' or placeholder == 'subtitle':
                value = subtitle or notes or ''

            # Replace placeholder (if value was set)
            if value:
                populated_html = populated_html.replace(f'{{{placeholder}}}', value)

        return populated_html

    def _extract_index(self, placeholder: str) -> Optional[int]:
        """
        Extract numeric index from placeholder name.

        Args:
            placeholder: e.g., "box_1_title", "metric_2_number"

        Returns:
            0-based index, or None if not found
        """
        match = re.search(r'_(\d+)_', placeholder)
        if match:
            return int(match.group(1)) - 1  # Convert to 0-based
        # Try end of string: insight_1
        match = re.search(r'_(\d+)$', placeholder)
        if match:
            return int(match.group(1)) - 1
        return None

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
        Create HTML for hero slide using H1/H2/H3 template styling.

        v4.5.5: Updated to match Layout Builder hero templates.
        - H2-section: Section divider with dark gray background
        - H3-closing: Closing slide with deep blue gradient

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

        # Use subtitle if set, otherwise first topic or notes
        if not subtitle:
            subtitle = (topics[0] if topics else notes) or ""

        # Style based on hero type (matching H1/H2/H3 templates)
        if hero_type == 'closing_slide':
            # H3-closing: Deep blue gradient, centered content
            return f'''
<div style="display:flex;flex-direction:column;justify-content:center;align-items:center;
            text-align:center;height:100%;padding:60px 80px;
            background:linear-gradient(135deg, #1e3a5f 0%, #2d5a87 100%);">
    <div style="margin-bottom:40px;">
        <span style="background:#374151;color:#9ca3af;padding:8px 20px;border-radius:20px;
                    font-size:16px;font-weight:500;text-transform:uppercase;letter-spacing:2px;">
            H3 · Closing Slide
        </span>
    </div>
    <h1 style="font-size:64px;font-weight:700;color:#ffffff;margin:0 0 24px 0;line-height:1.2;
               text-shadow:0 2px 4px rgba(0,0,0,0.2);">
        {title}
    </h1>
    <p style="font-size:28px;color:#94a3b8;margin:0 0 40px 0;max-width:70%;line-height:1.5;">
        {subtitle}
    </p>
    <div style="color:#64748b;font-size:18px;">
        Contact info placeholder · Logo area
    </div>
</div>
'''
        elif hero_type == 'section_divider':
            # H2-section: Dark gray, section number badge (NO subtitle per spec)
            return f'''
<div style="display:flex;flex-direction:column;justify-content:center;align-items:center;
            text-align:center;height:100%;padding:60px 80px;
            background:linear-gradient(135deg, #374151 0%, #4b5563 100%);">
    <div style="margin-bottom:32px;">
        <span style="background:rgba(255,255,255,0.1);color:#9ca3af;padding:12px 28px;border-radius:30px;
                    font-size:18px;font-weight:600;text-transform:uppercase;letter-spacing:3px;
                    border:1px solid rgba(255,255,255,0.2);">
            Section {slide_number}
        </span>
    </div>
    <div style="margin-bottom:24px;">
        <span style="background:#1f2937;color:#6b7280;padding:6px 16px;border-radius:16px;
                    font-size:14px;font-weight:500;">
            H2 · Section Divider
        </span>
    </div>
    <h1 style="font-size:56px;font-weight:700;color:#ffffff;margin:0;line-height:1.3;
               text-shadow:0 2px 4px rgba(0,0,0,0.3);max-width:80%;">
        {title}
    </h1>
</div>
'''
        else:
            # Generic hero slide (default) - for unspecified hero types
            return f'''
<div style="display:flex;flex-direction:column;justify-content:center;align-items:center;
            text-align:center;height:100%;padding:60px 80px;
            background:linear-gradient(135deg, #1e3a5f 0%, #374151 100%);">
    <div style="margin-bottom:24px;">
        <span style="background:#374151;color:#9ca3af;padding:6px 16px;border-radius:16px;
                    font-size:14px;font-weight:500;">
            Hero Slide
        </span>
    </div>
    <h1 style="font-size:72px;font-weight:700;color:#ffffff;margin:0 0 24px 0;line-height:1.2;
               text-shadow:0 2px 4px rgba(0,0,0,0.2);">
        {title}
    </h1>
    <p style="font-size:32px;color:#94a3b8;margin:0;max-width:70%;line-height:1.5;">
        {subtitle}
    </p>
</div>
'''

    def _create_title_slide_html(self, presentation_title: str, slide: Dict[str, Any]) -> str:
        """
        Create HTML specifically for title slide (first slide) using H1-structured styling.

        v4.5.5: Updated to match Layout Builder H1-structured template.
        - Deep blue gradient background (matches theme hero color)
        - Template badge for preview context
        - Subtitle and footer area placeholders

        Args:
            presentation_title: The main presentation title (from strawman.title or topic)
            slide: Slide data with optional subtitle from topics/notes

        Returns:
            HTML string for hero_content field
        """
        subtitle = slide.get('subtitle', '')
        topics = slide.get('topics', [])
        notes = slide.get('notes', '')

        # Use subtitle if set, otherwise first topic or notes
        if not subtitle:
            subtitle = (topics[0] if topics else notes) or ""

        return f'''
<div style="display:flex;flex-direction:column;justify-content:center;align-items:center;
            text-align:center;height:100%;padding:60px 80px;
            background:linear-gradient(135deg, #1e3a5f 0%, #2d5a87 100%);">
    <div style="margin-bottom:40px;">
        <span style="background:#374151;color:#9ca3af;padding:8px 20px;border-radius:20px;
                    font-size:16px;font-weight:500;text-transform:uppercase;letter-spacing:2px;">
            H1 · Title Slide
        </span>
    </div>
    <h1 style="font-size:72px;font-weight:700;color:#ffffff;margin:0 0 24px 0;line-height:1.2;
               text-shadow:0 4px 8px rgba(0,0,0,0.3);max-width:90%;">
        {presentation_title}
    </h1>
    <p style="font-size:28px;color:#94a3b8;margin:0 0 60px 0;max-width:70%;line-height:1.5;">
        {subtitle}
    </p>
    <div style="color:#64748b;font-size:16px;">
        Footer placeholder · Logo area
    </div>
</div>
'''

    def _create_content_html(self, slide: Dict[str, Any]) -> str:
        """
        Create HTML for content slide using real variant templates.

        v4.5.5: Loads actual templates from Text Service based on variant_id.
        Falls back to generic bullets if template not found.

        Args:
            slide: Slide data with topics/key_points and variant_id

        Returns:
            HTML string for rich_content field
        """
        variant_id = slide.get('variant_id')
        topics = slide.get('topics', [])
        notes = slide.get('notes', '')

        # v4.5.5: Try to load and populate real template
        if variant_id:
            template_html = self._load_template(variant_id)
            if template_html:
                populated_html = self._populate_template(template_html, slide)
                logger.debug(f"Using real template for variant: {variant_id}")
                return populated_html
            else:
                logger.debug(f"Template not found for variant: {variant_id}, using fallback")

        # Fallback: Generic bullets (original behavior)
        return self._create_generic_bullets(slide)

    def _create_generic_bullets(self, slide: Dict[str, Any]) -> str:
        """
        Create generic bullet HTML as fallback when template not available.

        Args:
            slide: Slide data with topics/notes

        Returns:
            HTML string with bullet points
        """
        topics = slide.get('topics', [])
        notes = slide.get('notes', '')
        variant_id = slide.get('variant_id', 'unknown')

        parts = []

        # Show variant info for preview context
        parts.append(f'''
<div style="background:#f0f9ff;border:1px solid #bae6fd;border-radius:8px;padding:12px 16px;margin-bottom:20px;">
    <span style="font-size:14px;color:#0369a1;font-weight:600;">📄 Template: {variant_id or "auto-select"}</span>
</div>
''')

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

        if len(parts) <= 1:  # Only variant info
            # Fallback if no content
            return parts[0] + '<p style="font-size:20px;color:#6b7280;">Content placeholder</p>'

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
