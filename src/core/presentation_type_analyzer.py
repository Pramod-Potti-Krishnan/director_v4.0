"""
Presentation Type Analyzer for Director Agent v4.0

Classifies presentations into visual types based on audience and purpose,
determining I-series allocation strategy.

v4.9: Audience-aware I-series implementation
- VISUAL_HEAVY (kids): 50-60% images, prefer I1/I2 (wide)
- BALANCED (students): 40-50% images, I1/I2/I3
- PROFESSIONAL (default): 25-35% images, prefer I3/I4 (narrow)
- TEXT_FOCUSED (executive): 20-30% images, I3/I4 only
"""

from enum import Enum
from typing import Optional, Tuple, List
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class PresentationType(str, Enum):
    """
    Presentation visual type classification.

    Determines I-series allocation and image position preferences.
    """
    VISUAL_HEAVY = "visual_heavy"   # 50-60% images, I1/I2 (wide)
    BALANCED = "balanced"           # 40-50% images, I1/I2/I3
    PROFESSIONAL = "professional"   # 25-35% images (DEFAULT), I3/I4 (narrow)
    TEXT_FOCUSED = "text_focused"   # 20-30% images, I3/I4 (narrow)


# Mapping from audience presets to presentation types
AUDIENCE_TYPE_MAPPING = {
    # Kids/young audiences → VISUAL_HEAVY (more images, wider format)
    "kids_young": PresentationType.VISUAL_HEAVY,
    "kids_older": PresentationType.VISUAL_HEAVY,

    # Students → BALANCED
    "middle_school": PresentationType.BALANCED,
    "high_school": PresentationType.BALANCED,

    # Professional → PROFESSIONAL (default)
    "college": PresentationType.PROFESSIONAL,
    "professional": PresentationType.PROFESSIONAL,
    "general": PresentationType.PROFESSIONAL,

    # Executive → TEXT_FOCUSED (fewer images, narrower format)
    "executive": PresentationType.TEXT_FOCUSED,
}

# Purpose modifiers (can shift type up/down)
PURPOSE_VISUAL_BOOST = {
    # Purposes that benefit from more visuals
    "entertain": 1,      # Shift toward more visual
    "inspire": 1,        # Shift toward more visual
    "educate": 0,        # No shift
    "inform": 0,         # No shift
    "persuade": 0,       # No shift
    "qbr": -1,           # Shift toward less visual (data-focused)
}


def get_target_range(presentation_type: PresentationType) -> Tuple[float, float]:
    """
    Get the target I-series percentage range for a presentation type.

    Args:
        presentation_type: The classified presentation type

    Returns:
        Tuple of (min_percentage, max_percentage)
    """
    ranges = {
        PresentationType.VISUAL_HEAVY: (0.50, 0.60),
        PresentationType.BALANCED: (0.40, 0.50),
        PresentationType.PROFESSIONAL: (0.25, 0.35),
        PresentationType.TEXT_FOCUSED: (0.20, 0.30),
    }
    return ranges.get(presentation_type, (0.25, 0.35))


def get_preferred_image_positions(presentation_type: PresentationType) -> List[str]:
    """
    Get preferred I-series image positions for a presentation type.

    Args:
        presentation_type: The classified presentation type

    Returns:
        List of preferred image positions (e.g., ["i1", "i2"])
    """
    if presentation_type == PresentationType.VISUAL_HEAVY:
        return ["i1", "i2"]  # Wide images for engagement
    elif presentation_type == PresentationType.BALANCED:
        return ["i1", "i2", "i3"]  # Mix of wide and narrow
    else:
        # PROFESSIONAL and TEXT_FOCUSED prefer narrow images
        return ["i3", "i4"]


def classify_presentation(
    audience_preset: Optional[str] = None,
    purpose_preset: Optional[str] = None
) -> PresentationType:
    """
    Classify a presentation into a visual type based on audience and purpose.

    Args:
        audience_preset: Audience preset (e.g., "kids_young", "professional")
        purpose_preset: Purpose preset (e.g., "educate", "persuade")

    Returns:
        PresentationType classification

    Examples:
        >>> classify_presentation("kids_young", "educate")
        PresentationType.VISUAL_HEAVY

        >>> classify_presentation("executive", "qbr")
        PresentationType.TEXT_FOCUSED

        >>> classify_presentation(None, None)  # Default
        PresentationType.PROFESSIONAL
    """
    # Start with base classification from audience
    if audience_preset and audience_preset in AUDIENCE_TYPE_MAPPING:
        base_type = AUDIENCE_TYPE_MAPPING[audience_preset]
    else:
        # Default to PROFESSIONAL when no audience specified
        base_type = PresentationType.PROFESSIONAL

    # Apply purpose modifier if applicable
    if purpose_preset and purpose_preset in PURPOSE_VISUAL_BOOST:
        boost = PURPOSE_VISUAL_BOOST[purpose_preset]
        if boost != 0:
            base_type = _apply_visual_boost(base_type, boost)

    logger.debug(
        f"PresentationType: audience={audience_preset}, purpose={purpose_preset} "
        f"-> {base_type.value}"
    )

    return base_type


def _apply_visual_boost(
    base_type: PresentationType,
    boost: int
) -> PresentationType:
    """
    Apply a visual boost to shift presentation type.

    Args:
        base_type: Starting presentation type
        boost: +1 for more visual, -1 for less visual

    Returns:
        Adjusted presentation type
    """
    # Order from most visual to least visual
    order = [
        PresentationType.VISUAL_HEAVY,
        PresentationType.BALANCED,
        PresentationType.PROFESSIONAL,
        PresentationType.TEXT_FOCUSED,
    ]

    try:
        current_idx = order.index(base_type)
        # Negative boost = more visual (lower index)
        # Positive boost = less visual (higher index)
        new_idx = max(0, min(len(order) - 1, current_idx - boost))
        return order[new_idx]
    except ValueError:
        return base_type


# Convenience function for external use
def get_iseries_strategy(
    audience_preset: Optional[str] = None,
    purpose_preset: Optional[str] = None
) -> dict:
    """
    Get complete I-series strategy for a presentation.

    Args:
        audience_preset: Audience preset
        purpose_preset: Purpose preset

    Returns:
        Dict with presentation_type, target_range, preferred_positions
    """
    presentation_type = classify_presentation(audience_preset, purpose_preset)
    target_range = get_target_range(presentation_type)
    preferred_positions = get_preferred_image_positions(presentation_type)

    return {
        "presentation_type": presentation_type,
        "target_min": target_range[0],
        "target_max": target_range[1],
        "preferred_positions": preferred_positions,
    }
