"""
Content Context Models for Director Agent v4.5

Defines the content context structures for audience-aware, purpose-driven content generation.
Director builds ContentContext at strawman stage from user inputs.

Reference: THEME_SYSTEM_DESIGN.md v2.3 Sections 2.7-2.10
"""

from typing import Dict, Optional, Tuple
from pydantic import BaseModel, Field


class AudienceConfig(BaseModel):
    """Audience configuration affecting content complexity.

    Per THEME_SYSTEM_DESIGN.md Section 2.7 and Q3 response mapping.
    """

    audience_type: str = Field(
        default="professional",
        description="Target audience: kids_young, kids_older, high_school, college, professional, executive"
    )

    # Complexity controls
    complexity_level: str = Field(
        default="moderate",
        description="simple, moderate, advanced - affects vocabulary complexity"
    )
    max_sentence_words: int = Field(
        default=20,
        ge=5,
        le=40,
        description="Max words per sentence (kids=8, professional=20, executive=15)"
    )
    avoid_jargon: bool = Field(
        default=False,
        description="True for kids/general audience - replaces technical terms"
    )

    # Derived properties
    @property
    def max_bullets(self) -> int:
        """Max bullets per slide based on audience."""
        return {
            "kids_young": 3,
            "kids_older": 4,
            "high_school": 5,
            "college": 5,
            "professional": 6,
            "executive": 4,  # Executives want concise
        }.get(self.audience_type, 5)

    class Config:
        extra = "allow"


class PurposeConfig(BaseModel):
    """Purpose configuration affecting content focus and structure.

    Per THEME_SYSTEM_DESIGN.md Section 2.7 and Q3 response mapping.
    """

    purpose_type: str = Field(
        default="inform",
        description="inform, educate, persuade, entertain, inspire, report"
    )

    # Content focus controls
    include_cta: bool = Field(
        default=False,
        description="Include call-to-action (True for persuade/inspire)"
    )
    include_data: bool = Field(
        default=True,
        description="Include statistics/data points"
    )
    include_examples: bool = Field(
        default=True,
        description="Include real-world examples"
    )
    emotional_tone: str = Field(
        default="neutral",
        description="neutral, enthusiastic, urgent, empathetic, authoritative"
    )

    # Structure guidance
    structure_pattern: str = Field(
        default="topic_details",
        description="topic_details, problem_solution, story_arc, comparison"
    )

    class Config:
        extra = "allow"


class TimeConfig(BaseModel):
    """Time configuration affecting content depth and slide count.

    Per THEME_SYSTEM_DESIGN.md Section 2.7.
    """

    duration_minutes: int = Field(
        default=20,
        ge=1,
        le=120,
        description="Presentation duration in minutes"
    )

    @property
    def slide_count_range(self) -> Tuple[int, int]:
        """Recommended slide count based on duration."""
        if self.duration_minutes <= 5:
            return (3, 5)
        elif self.duration_minutes <= 10:
            return (5, 8)
        elif self.duration_minutes <= 20:
            return (8, 12)
        elif self.duration_minutes <= 30:
            return (10, 15)
        elif self.duration_minutes <= 45:
            return (12, 18)
        else:
            return (15, 25)

    @property
    def bullets_per_slide(self) -> int:
        """Recommended bullets based on duration."""
        if self.duration_minutes <= 5:
            return 2  # Headlines only
        elif self.duration_minutes <= 10:
            return 3
        elif self.duration_minutes <= 30:
            return 4
        else:
            return 5

    @property
    def include_deep_content(self) -> bool:
        """Include case studies, detailed examples for longer presentations."""
        return self.duration_minutes >= 30

    class Config:
        extra = "allow"


class ContentContext(BaseModel):
    """Combined context for content generation (excluding Theme).

    Director builds this at strawman stage from:
    - session.audience → AudienceConfig
    - session.purpose → PurposeConfig
    - session.duration → TimeConfig

    Then passes to Text Service for every slide.
    """

    audience: AudienceConfig = Field(default_factory=AudienceConfig)
    purpose: PurposeConfig = Field(default_factory=PurposeConfig)
    time: TimeConfig = Field(default_factory=TimeConfig)

    def get_max_bullets(self) -> int:
        """Get max bullets considering both audience and time constraints."""
        audience_bullets = self.audience.max_bullets
        time_bullets = self.time.bullets_per_slide
        # Take the minimum of audience and time constraints
        return min(audience_bullets, time_bullets)

    def get_content_density(self) -> float:
        """Get content density multiplier (0.4 - 1.0)."""
        # Shorter presentations = less content per slide
        time_factor = min(1.0, self.time.duration_minutes / 20)

        # Kids = less content
        audience_factor = {
            "kids_young": 0.4,
            "kids_older": 0.6,
            "high_school": 0.8,
            "college": 0.9,
            "professional": 1.0,
            "executive": 0.7,  # Concise
        }.get(self.audience.audience_type, 0.8)

        return time_factor * audience_factor

    def to_text_service_format(self) -> Dict:
        """Convert to format expected by Text Service.

        Returns nested structure per THEME_SYSTEM_DESIGN.md Section 4.3.1.
        """
        return {
            "audience": {
                "audience_type": self.audience.audience_type,
                "complexity_level": self.audience.complexity_level,
                "max_sentence_words": self.audience.max_sentence_words,
                "avoid_jargon": self.audience.avoid_jargon,
            },
            "purpose": {
                "purpose_type": self.purpose.purpose_type,
                "include_cta": self.purpose.include_cta,
                "include_data": self.purpose.include_data,
                "include_examples": self.purpose.include_examples,
                "emotional_tone": self.purpose.emotional_tone,
                "structure_pattern": self.purpose.structure_pattern,
            },
            "time": {
                "duration_minutes": self.time.duration_minutes,
            }
        }

    class Config:
        extra = "allow"


# ============================================================================
# PRESETS
# ============================================================================
# Per THEME_SYSTEM_DESIGN.md Sections 2.8-2.10

AUDIENCE_PRESETS: Dict[str, AudienceConfig] = {
    "kids_young": AudienceConfig(
        audience_type="kids_young",
        complexity_level="simple",
        max_sentence_words=8,
        avoid_jargon=True
    ),
    "kids_older": AudienceConfig(
        audience_type="kids_older",
        complexity_level="simple",
        max_sentence_words=12,
        avoid_jargon=True
    ),
    "high_school": AudienceConfig(
        audience_type="high_school",
        complexity_level="moderate",
        max_sentence_words=15,
        avoid_jargon=False
    ),
    "college": AudienceConfig(
        audience_type="college",
        complexity_level="moderate",
        max_sentence_words=20,
        avoid_jargon=False
    ),
    "professional": AudienceConfig(
        audience_type="professional",
        complexity_level="moderate",
        max_sentence_words=20,
        avoid_jargon=False
    ),
    "executive": AudienceConfig(
        audience_type="executive",
        complexity_level="advanced",
        max_sentence_words=15,
        avoid_jargon=False  # Executives know jargon
    ),
    # Aliases
    "executives": AudienceConfig(
        audience_type="executive",
        complexity_level="advanced",
        max_sentence_words=15,
        avoid_jargon=False
    ),
    "children": AudienceConfig(
        audience_type="kids_young",
        complexity_level="simple",
        max_sentence_words=8,
        avoid_jargon=True
    ),
    "students": AudienceConfig(
        audience_type="college",
        complexity_level="moderate",
        max_sentence_words=18,
        avoid_jargon=False
    ),
    "general": AudienceConfig(
        audience_type="professional",
        complexity_level="moderate",
        max_sentence_words=18,
        avoid_jargon=True
    ),
}

PURPOSE_PRESETS: Dict[str, PurposeConfig] = {
    "inform": PurposeConfig(
        purpose_type="inform",
        include_cta=False,
        include_data=True,
        include_examples=True,
        emotional_tone="neutral",
        structure_pattern="topic_details"
    ),
    "informational": PurposeConfig(  # Alias
        purpose_type="inform",
        include_cta=False,
        include_data=True,
        include_examples=True,
        emotional_tone="neutral",
        structure_pattern="topic_details"
    ),
    "educate": PurposeConfig(
        purpose_type="educate",
        include_cta=False,
        include_data=True,
        include_examples=True,
        emotional_tone="neutral",
        structure_pattern="topic_details"
    ),
    "training": PurposeConfig(  # Alias
        purpose_type="educate",
        include_cta=False,
        include_data=True,
        include_examples=True,
        emotional_tone="neutral",
        structure_pattern="topic_details"
    ),
    "persuade": PurposeConfig(
        purpose_type="persuade",
        include_cta=True,
        include_data=True,
        include_examples=True,
        emotional_tone="enthusiastic",
        structure_pattern="problem_solution"
    ),
    "sales": PurposeConfig(  # Alias
        purpose_type="persuade",
        include_cta=True,
        include_data=True,
        include_examples=True,
        emotional_tone="enthusiastic",
        structure_pattern="problem_solution"
    ),
    "investor_pitch": PurposeConfig(
        purpose_type="persuade",
        include_cta=True,
        include_data=True,
        include_examples=True,
        emotional_tone="authoritative",
        structure_pattern="problem_solution"
    ),
    "entertain": PurposeConfig(
        purpose_type="entertain",
        include_cta=False,
        include_data=False,
        include_examples=True,
        emotional_tone="enthusiastic",
        structure_pattern="story_arc"
    ),
    "inspire": PurposeConfig(
        purpose_type="inspire",
        include_cta=True,
        include_data=False,
        include_examples=True,
        emotional_tone="empathetic",
        structure_pattern="story_arc"
    ),
    "report": PurposeConfig(
        purpose_type="report",
        include_cta=False,
        include_data=True,
        include_examples=False,
        emotional_tone="neutral",
        structure_pattern="topic_details"
    ),
    "qbr": PurposeConfig(  # Quarterly Business Review
        purpose_type="report",
        include_cta=False,
        include_data=True,
        include_examples=False,
        emotional_tone="authoritative",
        structure_pattern="topic_details"
    ),
}

TIME_PRESETS: Dict[str, TimeConfig] = {
    "lightning": TimeConfig(duration_minutes=5),    # 3-5 slides
    "quick": TimeConfig(duration_minutes=10),       # 5-8 slides
    "standard": TimeConfig(duration_minutes=20),    # 8-12 slides
    "extended": TimeConfig(duration_minutes=30),    # 10-15 slides
    "deep": TimeConfig(duration_minutes=45),        # 12-18 slides
    "workshop": TimeConfig(duration_minutes=60),    # 15-25 slides
}


def build_content_context(
    audience: Optional[str] = None,
    purpose: Optional[str] = None,
    duration: Optional[int] = None,
    tone: Optional[str] = None
) -> ContentContext:
    """Build ContentContext from session values.

    Maps string values (from session.audience, session.purpose, etc.)
    to structured config objects using presets.

    Args:
        audience: Audience string (e.g., "executives", "students")
        purpose: Purpose string (e.g., "inform", "persuade")
        duration: Duration in minutes
        tone: Tone string (maps to emotional_tone)

    Returns:
        ContentContext ready to pass to Text Service
    """
    # Resolve audience
    audience_config = AUDIENCE_PRESETS.get(
        audience.lower() if audience else "professional",
        AudienceConfig()
    )

    # Resolve purpose
    purpose_config = PURPOSE_PRESETS.get(
        purpose.lower() if purpose else "inform",
        PurposeConfig()
    )

    # Override emotional_tone if tone provided
    if tone:
        tone_mapping = {
            "professional": "neutral",
            "formal": "neutral",
            "casual": "enthusiastic",
            "inspiring": "empathetic",
            "urgent": "urgent",
            "authoritative": "authoritative",
        }
        purpose_config = purpose_config.model_copy(
            update={"emotional_tone": tone_mapping.get(tone.lower(), tone.lower())}
        )

    # Build time config
    time_config = TimeConfig(duration_minutes=duration or 20)

    return ContentContext(
        audience=audience_config,
        purpose=purpose_config,
        time=time_config
    )
