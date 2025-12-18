"""
Layout Models for Director Agent v4.0

Defines the data structures for Layout Service coordination,
enabling intelligent layout/variant selection via the Layout Service API.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class LayoutSlot(BaseModel):
    """A content slot within a layout template."""
    id: str = Field(..., description="Unique slot identifier (e.g., 'slot1', 'slot2')")
    type: str = Field(..., description="Slot type: text, image, chart, table, icon")
    x: int = Field(..., description="X position in pixels from left edge")
    y: int = Field(..., description="Y position in pixels from top edge")
    width: int = Field(..., description="Slot width in pixels")
    height: int = Field(..., description="Slot height in pixels")
    constraints: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional constraints (max_chars, min_font_size, etc.)"
    )


class LayoutTemplate(BaseModel):
    """A layout template from Layout Service."""
    id: str = Field(..., description="Layout ID (e.g., 'L25', 'L29', 'C01')")
    name: str = Field(..., description="Human-readable layout name")
    series: str = Field(..., description="Layout series: H, C, V, I, S, B, L")
    category: str = Field(..., description="Category: hero, content, visual, infographic")
    slots: List[LayoutSlot] = Field(default_factory=list, description="Content slots in the layout")
    content_zone_width: int = Field(..., description="Content zone width in pixels")
    content_zone_height: int = Field(..., description="Content zone height in pixels")
    supported_variants: List[str] = Field(
        default_factory=list,
        description="List of variant IDs this layout supports"
    )
    recommended_for: List[str] = Field(
        default_factory=list,
        description="Slide types this layout is recommended for"
    )


class LayoutRecommendation(BaseModel):
    """A layout recommendation from the Layout Service."""
    layout_id: str = Field(..., description="Recommended layout ID")
    score: float = Field(..., ge=0.0, le=1.0, description="Recommendation score (0-1)")
    reason: str = Field(..., description="Explanation of why this layout was recommended")
    variant_suggestions: List[str] = Field(
        default_factory=list,
        description="Suggested variants for this layout"
    )


class CanFitResponse(BaseModel):
    """Response from the /can-fit endpoint."""
    fits: bool = Field(..., description="Whether the content fits in the layout")
    layout_id: str = Field(..., description="The layout ID that was checked")
    details: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional details about fit (overflow, warnings, etc.)"
    )


class LayoutCapabilities(BaseModel):
    """Capabilities returned by the Layout Service."""
    service_name: str = Field(default="layout-service")
    version: str = Field(..., description="Service version")
    total_layouts: int = Field(..., description="Total number of available layouts")
    series_available: List[str] = Field(default_factory=list, description="Available layout series")
    endpoints: List[str] = Field(default_factory=list, description="Available API endpoints")
