"""
Stage 5: Refinement Models for Strawman Feedback Loop

Pydantic models for:
- RefinementResult: Result of AI-driven strawman refinement
- SlideChange: Individual slide modification record
- StrawmanDiff: Difference between Director's strawman and Deck-Builder state
- SlideMatch: Matched slide pair for diff computation
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


class ChangeType(str, Enum):
    """Type of change detected in a slide."""
    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"
    REORDERED = "reordered"
    UNCHANGED = "unchanged"


class SlideChange(BaseModel):
    """Record of a single slide change."""
    slide_id: str = Field(..., description="Unique identifier for the slide")
    slide_number: int = Field(..., description="Position in the presentation (1-indexed)")
    change_type: ChangeType = Field(..., description="Type of change detected")

    # What changed
    field_changes: Dict[str, Any] = Field(
        default_factory=dict,
        description="Map of field name to {old: value, new: value}"
    )

    # AI reasoning for the change
    ai_reasoning: Optional[str] = Field(
        None,
        description="AI's explanation for making this change"
    )

    # Layout/variant updates
    layout_changed: bool = Field(False, description="Whether layout was updated")
    new_layout: Optional[str] = Field(None, description="New layout if changed")
    variant_changed: bool = Field(False, description="Whether variant was updated")
    new_variant_id: Optional[str] = Field(None, description="New variant if changed")


class SlideModification(BaseModel):
    """Detailed modification record for a single slide."""
    slide_id: str
    slide_number: int

    # Content changes
    title_changed: bool = False
    content_changed: bool = False
    topics_changed: bool = False
    notes_changed: bool = False
    layout_changed: bool = False

    # Old and new values
    old_values: Dict[str, Any] = Field(default_factory=dict)
    new_values: Dict[str, Any] = Field(default_factory=dict)

    @property
    def has_significant_changes(self) -> bool:
        """Check if slide has changes that require re-analysis."""
        return self.content_changed or self.topics_changed or self.layout_changed


class SlideMatch(BaseModel):
    """Matched slide pair for diff computation."""
    director_slide: Optional[Dict[str, Any]] = Field(None, description="Slide from Director's strawman")
    deckbuilder_slide: Optional[Dict[str, Any]] = Field(None, description="Slide from Deck-Builder")

    director_index: Optional[int] = Field(None, description="Index in Director's slide list")
    deckbuilder_index: Optional[int] = Field(None, description="Index in Deck-Builder's slide list")

    match_type: str = Field("matched", description="matched, added, removed")
    match_confidence: float = Field(1.0, description="Confidence of the match (0-1)")

    @property
    def is_added(self) -> bool:
        """Slide exists in Deck-Builder but not Director."""
        return self.director_slide is None and self.deckbuilder_slide is not None

    @property
    def is_removed(self) -> bool:
        """Slide exists in Director but not Deck-Builder."""
        return self.director_slide is not None and self.deckbuilder_slide is None

    @property
    def is_matched(self) -> bool:
        """Slide exists in both."""
        return self.director_slide is not None and self.deckbuilder_slide is not None


class StrawmanDiff(BaseModel):
    """
    Difference between Director's strawman and Deck-Builder's current state.

    Used by the "Diff on Generate" approach to detect changes made by the user
    in the Deck-Builder preview before content generation.
    """
    has_changes: bool = Field(False, description="Whether any changes were detected")

    # Structural changes
    added_slides: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Slides added in Deck-Builder (not in Director)"
    )
    removed_slide_ids: List[str] = Field(
        default_factory=list,
        description="Slide IDs removed from Deck-Builder"
    )
    modified_slides: List[SlideModification] = Field(
        default_factory=list,
        description="Slides with content changes"
    )

    # Order changes
    reordered: bool = Field(False, description="Whether slide order changed")
    new_order: List[str] = Field(
        default_factory=list,
        description="New slide order (list of slide IDs) if reordered"
    )

    # Presentation-level changes
    title_changed: bool = Field(False, description="Whether presentation title changed")
    new_title: Optional[str] = Field(None, description="New title if changed")

    # Matched slides for reference
    slide_matches: List[SlideMatch] = Field(
        default_factory=list,
        description="Full list of slide matches for analysis"
    )

    @property
    def change_count(self) -> int:
        """Total number of changes detected."""
        return (
            len(self.added_slides) +
            len(self.removed_slide_ids) +
            len(self.modified_slides) +
            (1 if self.reordered else 0) +
            (1 if self.title_changed else 0)
        )

    @property
    def slides_needing_reanalysis(self) -> List[SlideModification]:
        """Slides that need layout/variant re-analysis due to content changes."""
        return [s for s in self.modified_slides if s.has_significant_changes]


class RefinementResult(BaseModel):
    """
    Result of AI-driven strawman refinement from user feedback.

    Returned by StrawmanRefiner.refine_from_chat() after processing
    user feedback like "change slide 3 to focus on benefits".
    """
    success: bool = Field(..., description="Whether refinement was successful")

    # Updated strawman
    updated_strawman: Optional[Dict[str, Any]] = Field(
        None,
        description="Updated strawman with changes applied"
    )

    # Changes made
    changes: List[SlideChange] = Field(
        default_factory=list,
        description="List of changes made to the strawman"
    )

    # AI reasoning
    reasoning: str = Field("", description="AI's explanation of the changes made")

    # Re-approval needed
    needs_reapproval: bool = Field(
        True,
        description="Whether user should re-approve the modified strawman"
    )

    # Error handling
    error: Optional[str] = Field(None, description="Error message if success=False")
    affected_slide_numbers: List[int] = Field(
        default_factory=list,
        description="List of slide numbers that were modified"
    )

    @property
    def change_count(self) -> int:
        """Number of slides changed."""
        return len(self.changes)

    @property
    def change_summary(self) -> str:
        """Human-readable summary of changes."""
        if not self.changes:
            return "No changes made."

        summaries = []
        for change in self.changes:
            if change.change_type == ChangeType.MODIFIED:
                fields = list(change.field_changes.keys())
                summaries.append(f"Slide {change.slide_number}: Updated {', '.join(fields)}")
            elif change.change_type == ChangeType.ADDED:
                summaries.append(f"Slide {change.slide_number}: Added new slide")
            elif change.change_type == ChangeType.REMOVED:
                summaries.append(f"Slide {change.slide_number}: Removed")
            elif change.change_type == ChangeType.REORDERED:
                summaries.append(f"Slide {change.slide_number}: Reordered")

        return "\n".join(summaries)


class RefineRequest(BaseModel):
    """Request model for strawman refinement."""
    feedback: str = Field(..., description="User's feedback for refinement")
    slide_numbers: Optional[List[int]] = Field(
        None,
        description="Specific slides to modify (if None, AI determines from feedback)"
    )
    context: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Additional context for refinement"
    )


class MergeStrategy(str, Enum):
    """Strategy for merging Deck-Builder changes into Director's strawman."""
    DECKBUILDER_WINS = "deckbuilder_wins"  # Deck-Builder changes take precedence
    DIRECTOR_WINS = "director_wins"  # Director's version takes precedence
    MERGE_FIELDS = "merge_fields"  # Merge individual fields intelligently
    ASK_USER = "ask_user"  # Ask user to resolve conflicts


class MergeResult(BaseModel):
    """Result of merging Deck-Builder changes into Director's strawman."""
    success: bool
    merged_strawman: Optional[Dict[str, Any]] = None
    conflicts: List[Dict[str, Any]] = Field(default_factory=list)
    merge_strategy_used: MergeStrategy = MergeStrategy.DECKBUILDER_WINS
    slides_updated: List[int] = Field(default_factory=list)
