"""
Branding Injector - v4.2
========================

Utility for injecting footer and logo into slide HTML.

v4.2: Stage 6 - Director's ONLY content modification.
Services generate title/subtitle/content; Director only adds branding.

Key responsibilities:
- Generate footer HTML with slide number, date, custom text
- Generate logo HTML with proper positioning
- Inject branding elements into slide containers
"""

import logging
from datetime import datetime
from typing import Optional

from src.models.presentation_config import (
    PresentationBranding,
    FooterConfig,
    LogoConfig,
    LogoPosition,
    FooterAlignment
)
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class BrandingInjector:
    """
    Injects footer and logo into slide HTML.

    Director's ONLY content modification responsibility.
    All other content (title, subtitle, main content) comes from services.
    """

    # CSS classes used for branding elements
    FOOTER_CLASS = "slide-footer"
    LOGO_CLASS = "slide-logo"
    FOOTER_CONTAINER_CLASS = "footer-container"

    # Default slide container markers
    SLIDE_CONTAINER_OPEN = '<div class="slide-container'
    SLIDE_CONTAINER_CLOSE = '</div>'

    def inject(
        self,
        slide_html: str,
        branding: PresentationBranding,
        slide_number: int,
        total_slides: int,
        is_hero: bool = False,
        hero_type: Optional[str] = None
    ) -> str:
        """
        Inject branding elements into slide HTML.

        Args:
            slide_html: Original slide HTML content
            branding: Branding configuration
            slide_number: Current slide number (1-indexed)
            total_slides: Total number of slides
            is_hero: Whether this is a hero slide
            hero_type: Type of hero slide (title_slide, section_divider, closing_slide)

        Returns:
            Slide HTML with branding injected
        """
        # Check if branding should be applied to this slide
        if is_hero:
            if hero_type == "title_slide" and not branding.apply_to_hero_slides:
                return slide_html
            if hero_type == "closing_slide" and not branding.apply_to_closing_slides:
                return slide_html
            if hero_type == "section_divider":
                # Section dividers typically don't have branding
                return slide_html

        # Generate branding elements
        footer_html = ""
        logo_html = ""

        if branding.has_footer:
            footer_html = self._generate_footer_html(
                branding.footer, slide_number, total_slides
            )

        if branding.has_logo:
            logo_html = self._generate_logo_html(branding.logo)

        # Inject into slide HTML
        result = slide_html

        if footer_html:
            result = self._insert_before_close(result, footer_html)

        if logo_html:
            result = self._insert_after_open(result, logo_html)

        return result

    def _generate_footer_html(
        self,
        footer: FooterConfig,
        slide_number: int,
        total_slides: int
    ) -> str:
        """
        Generate footer HTML with configured content.

        Args:
            footer: Footer configuration
            slide_number: Current slide number
            total_slides: Total slides

        Returns:
            Footer HTML string
        """
        parts = []

        # Slide number
        if footer.show_slide_number:
            parts.append(f'<span class="slide-number">{slide_number} / {total_slides}</span>')

        # Custom text
        if footer.text:
            parts.append(f'<span class="footer-text">{footer.text}</span>')

        # Date
        if footer.show_date:
            date_str = datetime.now().strftime("%B %d, %Y")
            parts.append(f'<span class="footer-date">{date_str}</span>')

        if not parts:
            return ""

        # Build footer container
        content = " | ".join(parts)
        style = f'text-align: {footer.alignment.value}; font-size: {footer.font_size}; color: {footer.color};'

        return f'''
<div class="{self.FOOTER_CLASS}" style="{style}">
    {content}
</div>
'''.strip()

    def _generate_logo_html(self, logo: LogoConfig) -> str:
        """
        Generate logo HTML with positioning.

        Args:
            logo: Logo configuration

        Returns:
            Logo HTML string
        """
        if not logo.url:
            return ""

        # Build position styles
        position_styles = {
            LogoPosition.TOP_LEFT: f"top: {logo.margin}px; left: {logo.margin}px;",
            LogoPosition.TOP_RIGHT: f"top: {logo.margin}px; right: {logo.margin}px;",
            LogoPosition.BOTTOM_LEFT: f"bottom: {logo.margin}px; left: {logo.margin}px;",
            LogoPosition.BOTTOM_RIGHT: f"bottom: {logo.margin}px; right: {logo.margin}px;",
        }

        position_css = position_styles.get(logo.position, position_styles[LogoPosition.TOP_RIGHT])
        height_css = f"height: {logo.height}px;" if logo.height else "height: auto;"

        style = f"position: absolute; {position_css} width: {logo.width}px; {height_css}"

        return f'''
<img class="{self.LOGO_CLASS}" src="{logo.url}" alt="Logo" style="{style}" />
'''.strip()

    def _insert_before_close(self, html: str, element: str) -> str:
        """
        Insert element before the closing tag of the slide container.

        Args:
            html: Original HTML
            element: Element to insert

        Returns:
            Modified HTML
        """
        # Find the last closing div (slide container close)
        last_close = html.rfind(self.SLIDE_CONTAINER_CLOSE)

        if last_close == -1:
            # No container found, append to end
            return html + "\n" + element

        # Insert before the last closing tag
        return html[:last_close] + "\n" + element + "\n" + html[last_close:]

    def _insert_after_open(self, html: str, element: str) -> str:
        """
        Insert element after the opening tag of the slide container.

        Args:
            html: Original HTML
            element: Element to insert

        Returns:
            Modified HTML
        """
        # Find the first slide container opening
        container_start = html.find(self.SLIDE_CONTAINER_OPEN)

        if container_start == -1:
            # No container found, prepend
            return element + "\n" + html

        # Find the end of the opening tag (the >)
        tag_end = html.find(">", container_start)

        if tag_end == -1:
            return element + "\n" + html

        # Insert after the opening tag
        insert_pos = tag_end + 1
        return html[:insert_pos] + "\n" + element + "\n" + html[insert_pos:]

    def generate_branding_css(self, branding: PresentationBranding) -> str:
        """
        Generate CSS for branding elements.

        Can be included in slide <style> blocks or presentation-level CSS.

        Args:
            branding: Branding configuration

        Returns:
            CSS string
        """
        css_parts = []

        # Footer styles
        if branding.has_footer:
            css_parts.append(f"""
.{self.FOOTER_CLASS} {{
    position: absolute;
    bottom: 16px;
    left: 0;
    right: 0;
    padding: 0 24px;
    font-family: inherit;
    z-index: 10;
}}
.{self.FOOTER_CLASS} .slide-number {{
    font-weight: 500;
}}
.{self.FOOTER_CLASS} .footer-text {{
    opacity: 0.8;
}}
.{self.FOOTER_CLASS} .footer-date {{
    opacity: 0.6;
}}
""")

        # Logo styles
        if branding.has_logo:
            css_parts.append(f"""
.{self.LOGO_CLASS} {{
    z-index: 10;
    pointer-events: none;
}}
""")

        return "\n".join(css_parts)


# Convenience function
def inject_branding(
    slide_html: str,
    branding: PresentationBranding,
    slide_number: int,
    total_slides: int,
    is_hero: bool = False,
    hero_type: Optional[str] = None
) -> str:
    """
    Convenience function to inject branding into slide HTML.

    Args:
        slide_html: Original slide HTML
        branding: Branding configuration
        slide_number: Current slide number (1-indexed)
        total_slides: Total slides
        is_hero: Whether this is a hero slide
        hero_type: Hero slide type

    Returns:
        Slide HTML with branding injected
    """
    injector = BrandingInjector()
    return injector.inject(
        slide_html, branding, slide_number, total_slides, is_hero, hero_type
    )
