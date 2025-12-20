"""
Playbook Models for Director Agent v4.1

Pydantic models defining the structure of presentation playbooks.
Playbooks are pre-defined presentation templates indexed by:
- Audience (who you're presenting to)
- Purpose (why you're presenting)
- Duration (how long)

Author: Director v4.1 Playbook System
Date: December 2024
"""

from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from enum import Enum


class AudienceType(str, Enum):
    """Target audience for the presentation."""
    PROFESSIONALS = "professionals"
    COLLEGE_STUDENTS = "college_students"
    HIGH_SCHOOL_STUDENTS = "high_school_students"
    CHILDREN = "children"
    SENIORS = "seniors"


class PurposeType(str, Enum):
    """Purpose/goal of the presentation."""
    INVESTOR_PITCH = "investor_pitch"
    QBR = "qbr"
    TRAINING = "training"
    PRODUCT_DEMO = "product_demo"
    SALES = "sales"
    INFORMATIONAL = "informational"


class MatchConfidence(str, Enum):
    """Playbook match confidence levels."""
    FULL_MATCH = "full_match"       # >= 0.90: Use playbook directly
    PARTIAL_MATCH = "partial_match"  # 0.60-0.89: Merge with custom slides
    NO_MATCH = "no_match"            # < 0.60: Generate from scratch


class PlaybookSection(BaseModel):
    """A logical section within a playbook."""
    section_id: str = Field(..., description="Unique identifier for the section")
    section_name: str = Field(..., description="Display name of the section")
    purpose_in_narrative: Optional[str] = Field(
        None,
        description="What role this section plays in the presentation narrative"
    )
    is_required: bool = Field(True, description="Whether this section must be included")
    can_expand: bool = Field(False, description="Whether extra slides can be added to this section")
    max_expansion_slides: int = Field(0, description="Maximum slides that can be added")


class PlaybookSlide(BaseModel):
    """A slide template within a playbook."""
    slot_id: str = Field(..., description="Unique identifier for this slide slot")
    slide_number: int = Field(..., description="Position in the playbook sequence")
    section_id: Optional[str] = Field(None, description="Which section this slide belongs to")

    # Title template with {topic} placeholder
    title_template: str = Field(
        ...,
        description="Title template with {topic} placeholder, e.g., 'Introduction to {topic}'"
    )

    # Slide type for story-driven routing
    slide_type_hint: str = Field(
        "text",
        description="Type hint: hero, text, chart, diagram, infographic"
    )
    purpose: str = Field(
        ...,
        description="Narrative purpose: title_slide, problem_statement, traction, etc."
    )

    # Layout and variant suggestions
    layout: str = Field("L25", description="Suggested layout: L29, L25, C1, etc.")
    suggested_variant: Optional[str] = Field(None, description="Suggested variant_id for L25/C1")

    # Hero slide properties
    is_hero: bool = Field(False, description="Whether this is a hero slide")
    hero_type: Optional[str] = Field(
        None,
        description="Hero type: title_slide, section_divider, closing_slide"
    )

    # Content templates with {topic} placeholders
    topic_templates: List[str] = Field(
        default_factory=list,
        description="Templates for bullet points with {topic} placeholders"
    )
    narrative_template: Optional[str] = Field(
        None,
        description="Template for notes/narrative with {topic} placeholder"
    )

    # Optional slide properties
    is_optional: bool = Field(False, description="Can be removed for shorter durations")
    depends_on_context: List[str] = Field(
        default_factory=list,
        description="Context keys that must exist for this slide to be included"
    )


class AdaptationRules(BaseModel):
    """Rules for adapting playbook to different durations or contexts."""
    shorter_duration_removes: List[str] = Field(
        default_factory=list,
        description="slot_ids to remove for shorter durations"
    )
    longer_duration_adds: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Slides to add for longer durations"
    )
    audience_tone_map: Dict[str, str] = Field(
        default_factory=dict,
        description="Mapping of audience to tone adjustments"
    )


class PlaybookMetadata(BaseModel):
    """Metadata for a playbook."""
    audience: str = Field(..., description="Target audience")
    purpose: str = Field(..., description="Presentation purpose")
    duration: int = Field(..., description="Optimal duration in minutes")
    description: Optional[str] = Field(None, description="Human-readable description")
    created_at: Optional[str] = Field(None, description="Creation timestamp")
    updated_at: Optional[str] = Field(None, description="Last update timestamp")


class PlaybookStructure(BaseModel):
    """High-level structure of a playbook."""
    total_slides: int = Field(..., description="Total number of slides")
    sections: List[PlaybookSection] = Field(
        default_factory=list,
        description="Logical sections in the playbook"
    )


class Playbook(BaseModel):
    """
    Complete playbook definition.

    A playbook provides a pre-defined presentation structure
    that can be applied to any topic. The key dimensions are:
    - audience: WHO you're presenting to
    - purpose: WHY you're presenting
    - duration: HOW LONG
    """
    playbook_id: str = Field(..., description="Unique ID: audience-purpose-duration")
    version: str = Field("1.0.0", description="Playbook version")

    metadata: PlaybookMetadata = Field(..., description="Playbook metadata")
    structure: PlaybookStructure = Field(..., description="High-level structure")
    slides: List[PlaybookSlide] = Field(..., description="Slide templates")

    adaptation_rules: Optional[AdaptationRules] = Field(
        None,
        description="Rules for adapting to different contexts"
    )

    def get_slide_count_for_duration(self, target_duration: int) -> int:
        """Calculate expected slide count for a given duration."""
        base_duration = self.metadata.duration
        base_slides = self.structure.total_slides

        if target_duration == base_duration:
            return base_slides

        # Adjust based on duration difference
        slides_per_minute = base_slides / base_duration
        adjusted = int(target_duration * slides_per_minute)

        # Clamp to reasonable range
        return max(5, min(30, adjusted))


class PlaybookMatch(BaseModel):
    """Result of playbook matching."""
    playbook_id: Optional[str] = Field(None, description="Matched playbook ID")
    playbook: Optional[Playbook] = Field(None, description="The matched playbook")
    confidence: float = Field(0.0, description="Match confidence score (0-1)")
    match_type: MatchConfidence = Field(
        MatchConfidence.NO_MATCH,
        description="Type of match: full, partial, or none"
    )
    match_details: Dict[str, Any] = Field(
        default_factory=dict,
        description="Details about what matched/didn't match"
    )
    adaptation_notes: List[str] = Field(
        default_factory=list,
        description="Suggested adaptations for partial matches"
    )


class MergeInstruction(BaseModel):
    """Instruction for merging playbook with custom content."""
    position: str = Field(
        ...,
        description="Where to insert: before, after, replace, expand"
    )
    reference_slot: str = Field(..., description="slot_id to reference for positioning")
    purpose: str = Field(..., description="Purpose of the custom slide to generate")
    count: int = Field(1, description="Number of slides to generate")


class PlaybookRegistry(BaseModel):
    """Registry of all available playbooks."""
    version: str = Field("1.0.0", description="Registry version")
    playbooks: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Map of playbook_id to metadata (path, description)"
    )
