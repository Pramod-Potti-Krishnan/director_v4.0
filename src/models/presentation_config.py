"""
Presentation Configuration Models - v4.2
=========================================

Models for per-presentation configuration:
- FooterConfig: Footer text, slide numbers, date display
- LogoConfig: Logo URL, position, size
- PresentationBranding: Combined footer + logo configuration

v4.2: Stage 6 - Director only adds footer/logo to generated slides.
Services handle title/subtitle generation.
"""

from typing import Optional
from pydantic import BaseModel, Field
from enum import Enum


class LogoPosition(str, Enum):
    """Allowed logo positions on slides."""
    TOP_LEFT = "top-left"
    TOP_RIGHT = "top-right"
    BOTTOM_LEFT = "bottom-left"
    BOTTOM_RIGHT = "bottom-right"


class FooterAlignment(str, Enum):
    """Footer text alignment options."""
    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"


class FooterConfig(BaseModel):
    """
    Footer configuration for slides.

    Controls footer text, slide numbers, and date display.
    Applied consistently across all slides in the presentation.
    """
    text: Optional[str] = Field(
        None,
        description="Custom footer text (company name, copyright, etc.)"
    )
    show_slide_number: bool = Field(
        True,
        description="Whether to display slide numbers"
    )
    show_date: bool = Field(
        False,
        description="Whether to display the current date"
    )
    alignment: FooterAlignment = Field(
        FooterAlignment.CENTER,
        description="Footer text alignment"
    )
    font_size: str = Field(
        "12px",
        description="Footer font size"
    )
    color: str = Field(
        "#666666",
        description="Footer text color (hex)"
    )

    def to_css(self) -> str:
        """Generate CSS for footer styling."""
        return f"""
            .slide-footer {{
                font-size: {self.font_size};
                color: {self.color};
                text-align: {self.alignment.value};
            }}
        """.strip()


class LogoConfig(BaseModel):
    """
    Logo configuration for slides.

    Controls logo display position and sizing.
    Applied consistently across all slides in the presentation.
    """
    url: Optional[str] = Field(
        None,
        description="URL to the logo image"
    )
    position: LogoPosition = Field(
        LogoPosition.TOP_RIGHT,
        description="Position of the logo on slides"
    )
    width: int = Field(
        120,
        ge=20,
        le=300,
        description="Logo width in pixels"
    )
    height: Optional[int] = Field(
        None,
        description="Logo height in pixels (auto if not specified)"
    )
    margin: int = Field(
        16,
        description="Margin from slide edges in pixels"
    )

    def to_css(self) -> str:
        """Generate CSS for logo positioning."""
        position_css = {
            LogoPosition.TOP_LEFT: f"top: {self.margin}px; left: {self.margin}px;",
            LogoPosition.TOP_RIGHT: f"top: {self.margin}px; right: {self.margin}px;",
            LogoPosition.BOTTOM_LEFT: f"bottom: {self.margin}px; left: {self.margin}px;",
            LogoPosition.BOTTOM_RIGHT: f"bottom: {self.margin}px; right: {self.margin}px;",
        }

        height_css = f"height: {self.height}px;" if self.height else "height: auto;"

        return f"""
            .slide-logo {{
                position: absolute;
                {position_css.get(self.position, position_css[LogoPosition.TOP_RIGHT])}
                width: {self.width}px;
                {height_css}
            }}
        """.strip()


class PresentationBranding(BaseModel):
    """
    Combined branding configuration for a presentation.

    v4.2: Stage 6 - Director's only slide modification is adding branding.
    Services handle all title/subtitle/content generation.
    """
    footer: FooterConfig = Field(
        default_factory=FooterConfig,
        description="Footer configuration"
    )
    logo: LogoConfig = Field(
        default_factory=LogoConfig,
        description="Logo configuration"
    )
    apply_to_hero_slides: bool = Field(
        False,
        description="Whether to apply branding to hero/title slides"
    )
    apply_to_closing_slides: bool = Field(
        True,
        description="Whether to apply branding to closing slides"
    )

    @property
    def has_footer(self) -> bool:
        """Check if footer has content to display."""
        return bool(
            self.footer.text or
            self.footer.show_slide_number or
            self.footer.show_date
        )

    @property
    def has_logo(self) -> bool:
        """Check if logo is configured."""
        return bool(self.logo.url)

    def to_css(self) -> str:
        """Generate combined CSS for branding elements."""
        css_parts = []
        if self.has_footer:
            css_parts.append(self.footer.to_css())
        if self.has_logo:
            css_parts.append(self.logo.to_css())
        return "\n".join(css_parts)


class ThemeConfig(BaseModel):
    """
    Theme configuration for presentation styling.

    Future enhancement: Theme selection and customization.
    """
    name: str = Field("professional", description="Theme name")
    primary_color: str = Field("#1a1a2e", description="Primary color (hex)")
    accent_color: str = Field("#4361ee", description="Accent color (hex)")
    background_color: str = Field("#ffffff", description="Background color (hex)")
    text_color: str = Field("#333333", description="Text color (hex)")
    font_family: str = Field("Inter, sans-serif", description="Font family")
