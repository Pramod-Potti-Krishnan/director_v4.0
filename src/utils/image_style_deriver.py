"""
Image Style Deriver for Director Agent v4.6

Derives ImageStyleAgreement from session context (audience, purpose, domain).
Called once at strawman generation to establish consistent image styling
for all slides in the presentation.

Derivation Logic:
- Executives → photorealistic, minimal, no anime
- Kids → vibrant, playful, colorful
- Technical → minimalist, clean diagrams
- General/Students → illustrated, warm

Version: 1.0.0
"""

import logging
from typing import Optional, Dict, Any

from src.models.session import SessionV4
from src.models.presentation_config import (
    ImageStyleAgreement,
    ImageArchetype,
    ImageQualityTier
)

logger = logging.getLogger(__name__)


# =============================================================================
# Audience → Archetype Mapping
# =============================================================================

AUDIENCE_ARCHETYPE_MAP: Dict[str, ImageArchetype] = {
    # Professional/Executive audiences
    "executives": ImageArchetype.PHOTOREALISTIC,
    "executive": ImageArchetype.PHOTOREALISTIC,
    "professional": ImageArchetype.PHOTOREALISTIC,
    "business": ImageArchetype.PHOTOREALISTIC,

    # Technical audiences
    "technical": ImageArchetype.MINIMALIST,
    "developers": ImageArchetype.MINIMALIST,
    "engineers": ImageArchetype.MINIMALIST,

    # Kids/Youth audiences
    "kids_young": ImageArchetype.VIBRANT,
    "kids_tween": ImageArchetype.VIBRANT,
    "kids_teen": ImageArchetype.ILLUSTRATED,
    "children": ImageArchetype.VIBRANT,
    "middle_school": ImageArchetype.VIBRANT,
    "high_school": ImageArchetype.ILLUSTRATED,

    # Educational audiences
    "students": ImageArchetype.ILLUSTRATED,
    "college": ImageArchetype.ILLUSTRATED,
    "academic": ImageArchetype.ILLUSTRATED,

    # General audience
    "general": ImageArchetype.ILLUSTRATED,
}

# =============================================================================
# Audience → Style Parameters Mapping
# =============================================================================

AUDIENCE_STYLE_PARAMS: Dict[str, Dict[str, Any]] = {
    "executives": {
        "mood": "professional",
        "color_scheme": "neutral",
        "lighting": "professional",
        "avoid_elements": ["anime", "cartoon", "playful", "childish", "bright colors"]
    },
    "professional": {
        "mood": "professional",
        "color_scheme": "neutral",
        "lighting": "professional",
        "avoid_elements": ["anime", "cartoon", "childish"]
    },
    "technical": {
        "mood": "informative",
        "color_scheme": "cool",
        "lighting": "clean",
        "avoid_elements": ["people", "faces", "cartoon characters", "decorative"]
    },
    "developers": {
        "mood": "informative",
        "color_scheme": "cool",
        "lighting": "clean",
        "avoid_elements": ["people", "faces", "cartoon characters"]
    },
    "kids_young": {
        "mood": "playful",
        "color_scheme": "vibrant",
        "lighting": "playful",
        "avoid_elements": ["realistic faces", "corporate", "adult themes", "scary"]
    },
    "kids_tween": {
        "mood": "accessible",
        "color_scheme": "vibrant",
        "lighting": "playful",
        "avoid_elements": ["corporate", "adult themes", "complex diagrams"]
    },
    "kids_teen": {
        "mood": "engaging",
        "color_scheme": "warm",
        "lighting": "bright",
        "avoid_elements": ["childish cartoons", "corporate settings"]
    },
    "students": {
        "mood": "educational",
        "color_scheme": "vibrant",
        "lighting": "bright",
        "avoid_elements": ["corporate stock photos", "boring office"]
    },
    "general": {
        "mood": "accessible",
        "color_scheme": "warm",
        "lighting": "soft",
        "avoid_elements": ["complex technical diagrams", "jargon-heavy imagery"]
    },
}

# =============================================================================
# Purpose → Mood Adjustment
# =============================================================================

PURPOSE_MOOD_ADJUSTMENTS: Dict[str, str] = {
    "inform": "informative",
    "educate": "educational",
    "persuade": "compelling",
    "inspire": "aspirational",
    "entertain": "engaging",
    "qbr": "professional",  # Quarterly Business Review
}


# =============================================================================
# v4.7: Global Brand Variables Mappings (for simplified prompting)
# =============================================================================

# Audience → Target Demographic Keywords (for prompt aesthetic)
AUDIENCE_DEMOGRAPHIC_MAP: Dict[str, str] = {
    "executives": "enterprise executives, corporate leadership",
    "executive": "enterprise executives, corporate leadership",
    "professional": "modern professionals, business audience",
    "business": "business professionals, corporate setting",
    "technical": "tech professionals, developers",
    "developers": "software developers, engineering teams",
    "engineers": "technical engineers, analytical minds",
    "kids_young": "young children, playful learning",
    "kids_tween": "tweens, energetic youth",
    "kids_teen": "teenagers, dynamic youth culture",
    "children": "young children, imaginative play",
    "middle_school": "middle schoolers, curious learners",
    "high_school": "high school students, young adults",
    "students": "college students, academic learners",
    "college": "university students, higher education",
    "academic": "academic researchers, scholarly community",
    "general": "general audience, broad appeal",
}

# Audience → Visual Style Descriptor (style phrase for prompt)
AUDIENCE_STYLE_DESCRIPTOR_MAP: Dict[str, str] = {
    "executives": "sleek modern photorealistic",
    "executive": "sleek modern photorealistic",
    "professional": "polished professional photorealistic",
    "business": "clean corporate photorealistic",
    "technical": "clean minimalist technical",
    "developers": "modern minimalist technical",
    "engineers": "precise technical minimalist",
    "kids_young": "bright playful illustrated cartoon",
    "kids_tween": "vibrant energetic illustrated",
    "kids_teen": "cool modern illustrated",
    "children": "warm friendly illustrated cartoon",
    "middle_school": "colorful engaging illustrated",
    "high_school": "dynamic contemporary illustrated",
    "students": "fresh modern illustrated",
    "college": "contemporary illustrated",
    "academic": "sophisticated illustrated",
    "general": "warm approachable illustrated",
}

# Color Scheme → Color Palette Descriptor (for prompt)
COLOR_PALETTE_MAP: Dict[str, str] = {
    "neutral": "cool grays and subtle blues",
    "warm": "warm earth tones and amber accents",
    "cool": "cool blues and metallic silvers",
    "vibrant": "bright vibrant colors and bold accents",
}

# Mood + Lighting → Lighting/Mood Phrase (for prompt)
def build_lighting_mood_phrase(mood: str, lighting: str) -> str:
    """Build lighting/mood phrase for prompt."""
    lighting_descriptors = {
        "professional": "professional studio lighting",
        "soft": "soft natural lighting",
        "bright": "bright ambient lighting",
        "playful": "cheerful vibrant lighting",
        "clean": "clean even lighting",
    }
    mood_descriptors = {
        "professional": "sophisticated atmosphere",
        "informative": "clear focused atmosphere",
        "educational": "engaging learning atmosphere",
        "compelling": "impactful dynamic atmosphere",
        "aspirational": "inspiring uplifting atmosphere",
        "engaging": "captivating energetic atmosphere",
        "playful": "fun cheerful atmosphere",
        "accessible": "welcoming friendly atmosphere",
    }
    light_phrase = lighting_descriptors.get(lighting, "professional lighting")
    mood_phrase = mood_descriptors.get(mood, "professional atmosphere")
    return f"{light_phrase}, {mood_phrase}"


def derive_image_style(
    session: SessionV4,
    quality_override: Optional[ImageQualityTier] = None
) -> ImageStyleAgreement:
    """
    Derive ImageStyleAgreement from session context.

    Called once at strawman generation to establish consistent
    image styling for all slides in the presentation.

    v4.7: Now also derives global brand variables for simplified prompting:
    - target_demographic: Audience keywords for prompt aesthetic
    - visual_style_descriptor: Style phrase for prompt
    - color_palette_descriptor: Color phrase for prompt
    - lighting_mood_phrase: Lighting/mood phrase for prompt

    Args:
        session: SessionV4 with audience/purpose information
        quality_override: Optional quality tier override from frontend

    Returns:
        ImageStyleAgreement for the presentation
    """
    # Extract audience and purpose from session
    audience = session.audience_preset or session.audience or "general"
    purpose = session.purpose_preset or session.purpose or "inform"

    # Normalize to lowercase for mapping
    audience_key = audience.lower().replace(" ", "_")
    purpose_key = purpose.lower().replace(" ", "_")

    # Get archetype from audience
    archetype = AUDIENCE_ARCHETYPE_MAP.get(audience_key, ImageArchetype.ILLUSTRATED)

    # Get style parameters from audience
    style_params = AUDIENCE_STYLE_PARAMS.get(audience_key, AUDIENCE_STYLE_PARAMS["general"])

    # Adjust mood based on purpose
    mood = PURPOSE_MOOD_ADJUSTMENTS.get(purpose_key, style_params.get("mood", "professional"))

    # Determine quality tier
    quality_tier = quality_override or ImageQualityTier.SMART  # Default to smart selection

    # Build derivation source string
    derived_from = f"audience:{audience_key}+purpose:{purpose_key}"

    # v4.7: Derive global brand variables for simplified prompting
    color_scheme = style_params.get("color_scheme", "neutral")
    lighting = style_params.get("lighting", "professional")

    target_demographic = AUDIENCE_DEMOGRAPHIC_MAP.get(audience_key, "general audience, broad appeal")
    visual_style_descriptor = AUDIENCE_STYLE_DESCRIPTOR_MAP.get(audience_key, "warm approachable illustrated")
    color_palette_descriptor = COLOR_PALETTE_MAP.get(color_scheme, "cool grays and subtle blues")
    lighting_mood_phrase = build_lighting_mood_phrase(mood, lighting)

    # Create ImageStyleAgreement
    agreement = ImageStyleAgreement(
        archetype=archetype,
        mood=mood,
        color_scheme=color_scheme,
        lighting=lighting,
        avoid_elements=style_params.get("avoid_elements", []),
        derived_from=derived_from,
        quality_tier=quality_tier,
        # v4.7: Global brand variables
        target_demographic=target_demographic,
        visual_style_descriptor=visual_style_descriptor,
        color_palette_descriptor=color_palette_descriptor,
        lighting_mood_phrase=lighting_mood_phrase
    )

    logger.info(
        f"Derived image style: archetype={archetype.value}, mood={mood}, "
        f"quality={quality_tier.value}, from={derived_from}"
    )
    logger.debug(
        f"Global brand vars: demographic='{target_demographic}', "
        f"style='{visual_style_descriptor}', palette='{color_palette_descriptor}'"
    )

    return agreement


def derive_image_style_from_dict(
    audience: Optional[str] = None,
    purpose: Optional[str] = None,
    quality_tier: Optional[str] = None
) -> ImageStyleAgreement:
    """
    Derive ImageStyleAgreement from direct parameters.

    Useful when session is not available (e.g., API calls).

    v4.7: Now also derives global brand variables for simplified prompting.

    Args:
        audience: Audience type string
        purpose: Purpose type string
        quality_tier: Quality tier string ('fast', 'standard', 'high', 'smart')

    Returns:
        ImageStyleAgreement with global brand variables
    """
    # Normalize inputs
    audience_key = (audience or "general").lower().replace(" ", "_")
    purpose_key = (purpose or "inform").lower().replace(" ", "_")

    # Get archetype from audience
    archetype = AUDIENCE_ARCHETYPE_MAP.get(audience_key, ImageArchetype.ILLUSTRATED)

    # Get style parameters from audience
    style_params = AUDIENCE_STYLE_PARAMS.get(audience_key, AUDIENCE_STYLE_PARAMS["general"])

    # Adjust mood based on purpose
    mood = PURPOSE_MOOD_ADJUSTMENTS.get(purpose_key, style_params.get("mood", "professional"))

    # Parse quality tier
    quality = ImageQualityTier.SMART  # Default
    if quality_tier:
        try:
            quality = ImageQualityTier(quality_tier.lower())
        except ValueError:
            logger.warning(f"Invalid quality_tier '{quality_tier}', using SMART")

    # Build derivation source string
    derived_from = f"audience:{audience_key}+purpose:{purpose_key}"

    # v4.7: Derive global brand variables for simplified prompting
    color_scheme = style_params.get("color_scheme", "neutral")
    lighting = style_params.get("lighting", "professional")

    target_demographic = AUDIENCE_DEMOGRAPHIC_MAP.get(audience_key, "general audience, broad appeal")
    visual_style_descriptor = AUDIENCE_STYLE_DESCRIPTOR_MAP.get(audience_key, "warm approachable illustrated")
    color_palette_descriptor = COLOR_PALETTE_MAP.get(color_scheme, "cool grays and subtle blues")
    lighting_mood_phrase = build_lighting_mood_phrase(mood, lighting)

    return ImageStyleAgreement(
        archetype=archetype,
        mood=mood,
        color_scheme=color_scheme,
        lighting=lighting,
        avoid_elements=style_params.get("avoid_elements", []),
        derived_from=derived_from,
        quality_tier=quality,
        # v4.7: Global brand variables
        target_demographic=target_demographic,
        visual_style_descriptor=visual_style_descriptor,
        color_palette_descriptor=color_palette_descriptor,
        lighting_mood_phrase=lighting_mood_phrase
    )


def get_visual_style_for_text_service(agreement: ImageStyleAgreement) -> str:
    """
    Get visual_style parameter for Text Service from ImageStyleAgreement.

    Maps archetype to Text Service visual_style:
    - PHOTOREALISTIC → 'professional'
    - ILLUSTRATED → 'illustrated'
    - MINIMALIST → 'professional'
    - VIBRANT → 'kids'

    Args:
        agreement: ImageStyleAgreement

    Returns:
        Visual style string for Text Service
    """
    return agreement.to_visual_style()


def get_image_model_for_slide(
    agreement: ImageStyleAgreement,
    is_hero: bool = False
) -> str:
    """
    Get Imagen model for a specific slide based on agreement and slide type.

    Args:
        agreement: ImageStyleAgreement with quality_tier
        is_hero: Whether this is a hero/title slide (gets higher priority)

    Returns:
        Imagen model identifier string
    """
    return agreement.get_model_for_slide(is_hero=is_hero)
