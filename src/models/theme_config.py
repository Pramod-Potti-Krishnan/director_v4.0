"""
Theme Configuration Models for Director Agent v4.5

Defines the theme system structures for cross-service theming.
Director expands theme_id → full ThemeConfig before calling Text Service.

Reference: THEME_SYSTEM_DESIGN.md v2.3
"""

from typing import Dict, Optional
from pydantic import BaseModel, Field


class TypographyLevel(BaseModel):
    """Typography specification for a single level (t1, t2, t3, t4, etc.)."""

    size: int = Field(..., description="Font size in pixels")
    weight: int = Field(default=400, description="Font weight (400=normal, 600=semibold, 700=bold)")
    color: str = Field(..., description="Text color as hex string (e.g., '#111827')")
    family: str = Field(default="Inter", description="Font family name")
    line_height: float = Field(default=1.4, description="Line height multiplier")

    class Config:
        extra = "allow"


class ThemeTypography(BaseModel):
    """Complete typography hierarchy for a theme.

    Three groups per THEME_SYSTEM_DESIGN.md:
    - Hero: hero_title, hero_subtitle, hero_accent (for H1, H2, H3)
    - Slide-level: slide_title, slide_subtitle (for title bars)
    - Content: t1, t2, t3, t4 (for main content area)
    """

    # Group 1: Hero slides (72-96px range)
    hero_title: TypographyLevel = Field(
        default_factory=lambda: TypographyLevel(size=84, weight=700, color="#ffffff", line_height=1.1)
    )
    hero_subtitle: TypographyLevel = Field(
        default_factory=lambda: TypographyLevel(size=36, weight=400, color="#ffffff", line_height=1.3)
    )
    hero_accent: TypographyLevel = Field(
        default_factory=lambda: TypographyLevel(size=24, weight=500, color="#ffffff", line_height=1.3)
    )

    # Group 2: Slide-level (42-48px range)
    slide_title: TypographyLevel = Field(
        default_factory=lambda: TypographyLevel(size=48, weight=700, color="#111827", line_height=1.2)
    )
    slide_subtitle: TypographyLevel = Field(
        default_factory=lambda: TypographyLevel(size=32, weight=400, color="#374151", line_height=1.3)
    )

    # Group 3: Content hierarchy (t1 > t2 > t3 > t4)
    t1: TypographyLevel = Field(
        default_factory=lambda: TypographyLevel(size=32, weight=600, color="#111827", line_height=1.2)
    )
    t2: TypographyLevel = Field(
        default_factory=lambda: TypographyLevel(size=26, weight=600, color="#374151", line_height=1.3)
    )
    t3: TypographyLevel = Field(
        default_factory=lambda: TypographyLevel(size=22, weight=500, color="#4b5563", line_height=1.4)
    )
    t4: TypographyLevel = Field(
        default_factory=lambda: TypographyLevel(size=20, weight=400, color="#4b5563", line_height=1.5)
    )

    class Config:
        extra = "allow"


class ThemeColors(BaseModel):
    """Complete color palette for a theme.

    Per THEME_SYSTEM_DESIGN.md Section 1.4:
    - Primary colors (brand identity)
    - Accent colors (highlights, CTAs)
    - Tertiary colors (variety, charts)
    - Neutral colors (backgrounds, borders)
    - Chart colors (data visualization)
    """

    # Primary colors
    primary: str = Field(default="#1e3a5f", description="Primary brand color")
    primary_dark: str = Field(default="#0f172a", description="Darker variant")
    primary_light: str = Field(default="#f1f5f9", description="Lighter variant")

    # Accent colors
    accent: str = Field(default="#3b82f6", description="Accent/highlight color")
    accent_dark: str = Field(default="#1d4ed8", description="Darker accent")
    accent_light: str = Field(default="#dbeafe", description="Lighter accent")

    # Tertiary colors (for variety)
    tertiary_1: str = Field(default="#10b981", description="Green variant")
    tertiary_2: str = Field(default="#f59e0b", description="Yellow/orange variant")
    tertiary_3: str = Field(default="#8b5cf6", description="Purple variant")

    # Neutral colors
    background: str = Field(default="#ffffff", description="Page background")
    surface: str = Field(default="#f8fafc", description="Card/box background")
    border: str = Field(default="#e2e8f0", description="Border color")

    # Text colors
    text_primary: str = Field(default="#1e3a5f", description="Primary text")
    text_secondary: str = Field(default="#4b5563", description="Secondary text")
    text_muted: str = Field(default="#9ca3af", description="Muted/disabled text")

    # Chart colors (for data visualization)
    chart_1: str = Field(default="#3b82f6", description="Chart color 1")
    chart_2: str = Field(default="#10b981", description="Chart color 2")
    chart_3: str = Field(default="#f59e0b", description="Chart color 3")
    chart_4: str = Field(default="#8b5cf6", description="Chart color 4")
    chart_5: str = Field(default="#ef4444", description="Chart color 5")
    chart_6: str = Field(default="#06b6d4", description="Chart color 6")

    class Config:
        extra = "allow"


class ThemeConfig(BaseModel):
    """Complete theme configuration.

    Director expands theme_id → ThemeConfig using THEME_REGISTRY,
    then passes full config to Text Service.
    """

    theme_id: str = Field(..., description="Theme identifier (professional, executive, etc.)")
    typography: ThemeTypography = Field(default_factory=ThemeTypography)
    colors: ThemeColors = Field(default_factory=ThemeColors)

    # Optional metadata
    name: Optional[str] = Field(default=None, description="Human-readable theme name")
    description: Optional[str] = Field(default=None, description="Theme description")

    class Config:
        extra = "allow"

    def to_text_service_format(self) -> Dict:
        """Convert to format expected by Text Service.

        Returns flattened structure per THEME_SYSTEM_DESIGN.md Section 4.3.1.
        """
        return {
            "theme_id": self.theme_id,
            "typography": {
                "hero_title": self.typography.hero_title.model_dump(),
                "hero_subtitle": self.typography.hero_subtitle.model_dump(),
                "hero_accent": self.typography.hero_accent.model_dump(),
                "slide_title": self.typography.slide_title.model_dump(),
                "slide_subtitle": self.typography.slide_subtitle.model_dump(),
                "t1": self.typography.t1.model_dump(),
                "t2": self.typography.t2.model_dump(),
                "t3": self.typography.t3.model_dump(),
                "t4": self.typography.t4.model_dump(),
            },
            "colors": self.colors.model_dump()
        }


# ============================================================================
# THEME REGISTRY
# ============================================================================
# Embedded presets until Layout Service provides sync endpoint.
# Per THEME_SYSTEM_DESIGN.md Section 4.8, Director maintains local registry.

THEME_REGISTRY: Dict[str, ThemeConfig] = {
    "professional": ThemeConfig(
        theme_id="professional",
        name="Professional",
        description="Clean, corporate styling for business presentations",
        typography=ThemeTypography(
            hero_title=TypographyLevel(size=84, weight=700, color="#ffffff", line_height=1.1),
            hero_subtitle=TypographyLevel(size=36, weight=400, color="rgba(255,255,255,0.9)", line_height=1.3),
            slide_title=TypographyLevel(size=48, weight=700, color="#1e3a5f", line_height=1.2),
            slide_subtitle=TypographyLevel(size=32, weight=400, color="#4b5563", line_height=1.3),
            t1=TypographyLevel(size=28, weight=600, color="#1e3a5f", line_height=1.2),
            t2=TypographyLevel(size=24, weight=600, color="#374151", line_height=1.3),
            t3=TypographyLevel(size=20, weight=500, color="#4b5563", line_height=1.4),
            t4=TypographyLevel(size=18, weight=400, color="#4b5563", line_height=1.5),
        ),
        colors=ThemeColors(
            primary="#1e3a5f",
            primary_dark="#0f172a",
            primary_light="#f1f5f9",
            accent="#3b82f6",
            accent_dark="#1d4ed8",
            accent_light="#dbeafe",
            tertiary_1="#10b981",
            tertiary_2="#f59e0b",
            tertiary_3="#8b5cf6",
            background="#ffffff",
            surface="#f8fafc",
            border="#e2e8f0",
            text_primary="#1e3a5f",
            text_secondary="#4b5563",
            text_muted="#9ca3af",
        )
    ),

    "executive": ThemeConfig(
        theme_id="executive",
        name="Executive",
        description="Bold, high-contrast styling for C-suite presentations",
        typography=ThemeTypography(
            hero_title=TypographyLevel(size=84, weight=800, color="#ffffff", line_height=1.1),
            hero_subtitle=TypographyLevel(size=36, weight=400, color="rgba(255,255,255,0.9)", line_height=1.3),
            slide_title=TypographyLevel(size=48, weight=700, color="#111827", line_height=1.2),
            slide_subtitle=TypographyLevel(size=32, weight=400, color="#374151", line_height=1.3),
            t1=TypographyLevel(size=32, weight=600, color="#111827", line_height=1.2),
            t2=TypographyLevel(size=26, weight=600, color="#374151", line_height=1.3),
            t3=TypographyLevel(size=22, weight=500, color="#4b5563", line_height=1.4),
            t4=TypographyLevel(size=20, weight=400, color="#4b5563", line_height=1.5),
        ),
        colors=ThemeColors(
            primary="#111827",
            primary_dark="#030712",
            primary_light="#f3f4f6",
            accent="#dc2626",
            accent_dark="#b91c1c",
            accent_light="#fee2e2",
            tertiary_1="#059669",
            tertiary_2="#d97706",
            tertiary_3="#7c3aed",
            background="#ffffff",
            surface="#f9fafb",
            border="#e5e7eb",
            text_primary="#111827",
            text_secondary="#374151",
            text_muted="#9ca3af",
        )
    ),

    "educational": ThemeConfig(
        theme_id="educational",
        name="Educational",
        description="Clear, accessible styling for teaching and training",
        typography=ThemeTypography(
            hero_title=TypographyLevel(size=72, weight=700, color="#ffffff", line_height=1.2),
            hero_subtitle=TypographyLevel(size=32, weight=400, color="rgba(255,255,255,0.9)", line_height=1.4),
            slide_title=TypographyLevel(size=42, weight=600, color="#1e40af", line_height=1.3),
            slide_subtitle=TypographyLevel(size=28, weight=400, color="#4b5563", line_height=1.4),
            t1=TypographyLevel(size=26, weight=600, color="#1e40af", line_height=1.3),
            t2=TypographyLevel(size=22, weight=600, color="#374151", line_height=1.4),
            t3=TypographyLevel(size=20, weight=500, color="#4b5563", line_height=1.5),
            t4=TypographyLevel(size=18, weight=400, color="#1f2937", line_height=1.6),
        ),
        colors=ThemeColors(
            primary="#1e40af",
            primary_dark="#1e3a8a",
            primary_light="#dbeafe",
            accent="#059669",
            accent_dark="#047857",
            accent_light="#d1fae5",
            tertiary_1="#7c3aed",
            tertiary_2="#f59e0b",
            tertiary_3="#ec4899",
            background="#ffffff",
            surface="#f0f9ff",
            border="#bfdbfe",
            text_primary="#1e3a8a",
            text_secondary="#4b5563",
            text_muted="#9ca3af",
        )
    ),

    "children": ThemeConfig(
        theme_id="children",
        name="Children",
        description="Fun, colorful styling for young audiences",
        typography=ThemeTypography(
            hero_title=TypographyLevel(size=72, weight=800, color="#ffffff", family="Comic Sans MS", line_height=1.2),
            hero_subtitle=TypographyLevel(size=32, weight=600, color="rgba(255,255,255,0.95)", family="Comic Sans MS", line_height=1.4),
            slide_title=TypographyLevel(size=42, weight=700, color="#7c3aed", family="Comic Sans MS", line_height=1.3),
            slide_subtitle=TypographyLevel(size=28, weight=500, color="#4b5563", family="Comic Sans MS", line_height=1.4),
            t1=TypographyLevel(size=28, weight=700, color="#7c3aed", family="Comic Sans MS", line_height=1.4),
            t2=TypographyLevel(size=24, weight=600, color="#059669", family="Comic Sans MS", line_height=1.5),
            t3=TypographyLevel(size=22, weight=500, color="#f59e0b", family="Comic Sans MS", line_height=1.5),
            t4=TypographyLevel(size=20, weight=400, color="#374151", family="Comic Sans MS", line_height=1.6),
        ),
        colors=ThemeColors(
            primary="#7c3aed",
            primary_dark="#6d28d9",
            primary_light="#ede9fe",
            accent="#f59e0b",
            accent_dark="#d97706",
            accent_light="#fef3c7",
            tertiary_1="#10b981",
            tertiary_2="#ec4899",
            tertiary_3="#06b6d4",
            background="#fffbeb",
            surface="#fef3c7",
            border="#fcd34d",
            text_primary="#7c3aed",
            text_secondary="#374151",
            text_muted="#9ca3af",
        )
    ),
}

# Default theme when not specified
DEFAULT_THEME_ID = "professional"

# ============================================================================
# v4.5 Phase 3: Dynamic Theme Loading from Layout Service
# ============================================================================
# Cache for themes synced from Layout Service (canonical source)
_SYNCED_THEMES: Optional[Dict[str, ThemeConfig]] = None
_SYNC_VERSION: Optional[str] = None
_SYNC_TIMESTAMP: Optional[str] = None


def _parse_theme_from_layout_service(theme_id: str, data: Dict) -> ThemeConfig:
    """Parse theme data from Layout Service response into ThemeConfig.

    Args:
        theme_id: Theme identifier
        data: Theme data from Layout Service

    Returns:
        ThemeConfig object
    """
    typography_data = data.get("typography", {})
    colors_data = data.get("colors", {})

    # Parse typography levels
    def parse_typography_level(level_data: Dict) -> TypographyLevel:
        return TypographyLevel(
            size=level_data.get("size", 18),
            weight=level_data.get("weight", 400),
            color=level_data.get("color", "#111827"),
            family=level_data.get("family", "Inter"),
            line_height=level_data.get("line_height", 1.4)
        )

    typography = ThemeTypography(
        hero_title=parse_typography_level(typography_data.get("hero_title", {})),
        hero_subtitle=parse_typography_level(typography_data.get("hero_subtitle", {})),
        hero_accent=parse_typography_level(typography_data.get("hero_accent", {})),
        slide_title=parse_typography_level(typography_data.get("slide_title", {})),
        slide_subtitle=parse_typography_level(typography_data.get("slide_subtitle", {})),
        t1=parse_typography_level(typography_data.get("t1", {})),
        t2=parse_typography_level(typography_data.get("t2", {})),
        t3=parse_typography_level(typography_data.get("t3", {})),
        t4=parse_typography_level(typography_data.get("t4", {})),
    )

    colors = ThemeColors(**colors_data) if colors_data else ThemeColors()

    return ThemeConfig(
        theme_id=theme_id,
        name=data.get("name"),
        description=data.get("description"),
        typography=typography,
        colors=colors
    )


async def sync_themes_from_layout_service() -> bool:
    """Sync themes from Layout Service (canonical source).

    v4.5 Phase 3: Director fetches themes from Layout Service at startup
    and caches them. Falls back to embedded THEME_REGISTRY if unavailable.

    Returns:
        True if sync succeeded, False if using fallback

    Usage:
        # Call at startup
        await sync_themes_from_layout_service()

        # Then use get_theme_config() as normal
        theme = get_theme_config("professional")
    """
    global _SYNCED_THEMES, _SYNC_VERSION, _SYNC_TIMESTAMP

    try:
        from src.clients.layout_service_client import LayoutServiceClient

        client = LayoutServiceClient()
        data = await client.get_themes_sync()

        if data and "themes" in data:
            _SYNCED_THEMES = {}
            for theme_id, theme_data in data["themes"].items():
                _SYNCED_THEMES[theme_id] = _parse_theme_from_layout_service(theme_id, theme_data)

            _SYNC_VERSION = data.get("version")
            _SYNC_TIMESTAMP = data.get("last_updated")

            print(f"[THEME-SYNC] Synced {len(_SYNCED_THEMES)} themes from Layout Service (v{_SYNC_VERSION})")
            return True
        else:
            print("[THEME-SYNC] Layout Service returned no themes, using embedded registry")
            return False

    except Exception as e:
        print(f"[THEME-SYNC] Failed to sync from Layout Service: {str(e)[:100]}")
        print("[THEME-SYNC] Using embedded THEME_REGISTRY as fallback")
        return False


def get_theme_config(theme_id: str) -> ThemeConfig:
    """Get theme configuration by ID.

    v4.5 Phase 3: Checks synced themes from Layout Service first,
    falls back to embedded THEME_REGISTRY.

    Args:
        theme_id: Theme identifier

    Returns:
        ThemeConfig for the theme, or professional theme if not found
    """
    # First check synced themes from Layout Service (canonical source)
    if _SYNCED_THEMES and theme_id in _SYNCED_THEMES:
        return _SYNCED_THEMES[theme_id]

    # Fall back to embedded registry
    return THEME_REGISTRY.get(theme_id, THEME_REGISTRY[DEFAULT_THEME_ID])


def get_available_themes() -> list:
    """Get list of available theme IDs.

    Returns themes from synced cache if available, otherwise embedded registry.
    """
    if _SYNCED_THEMES:
        return list(_SYNCED_THEMES.keys())
    return list(THEME_REGISTRY.keys())


def get_theme_sync_status() -> Dict[str, any]:
    """Get status of theme sync from Layout Service.

    Returns:
        Dict with sync status, version, timestamp, and theme count
    """
    return {
        "synced": _SYNCED_THEMES is not None,
        "version": _SYNC_VERSION,
        "last_updated": _SYNC_TIMESTAMP,
        "theme_count": len(_SYNCED_THEMES) if _SYNCED_THEMES else len(THEME_REGISTRY),
        "source": "layout_service" if _SYNCED_THEMES else "embedded"
    }
