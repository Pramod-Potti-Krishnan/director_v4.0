"""
Stage 5: Strawman Refiner

AI-driven refinement of strawman from user chat feedback.
Parses user feedback like "change slide 3 to focus on benefits" and modifies the outline.

Key responsibilities:
- Parse user feedback to identify which slides to modify
- Use AI to determine the best modifications
- Re-run LayoutAnalyzer on modified slides for proper service routing
- Return RefinementResult with changes and updated strawman

Author: Director v4.2 Stage 5
Date: December 2024
"""

import json
import logging
import re
import uuid
from copy import deepcopy
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

from src.core.layout_analyzer import LayoutAnalyzer, LayoutSeriesMode
from src.models.refinement import (
    ChangeType,
    RefinementResult,
    SlideChange,
)
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class SlideModification(BaseModel):
    """AI-generated modification for a single slide."""
    slide_number: int = Field(..., description="1-indexed slide number")
    new_title: Optional[str] = Field(None, description="New title if changed")
    new_topics: Optional[List[str]] = Field(None, description="New topics if changed")
    new_notes: Optional[str] = Field(None, description="New notes if changed")
    new_slide_type_hint: Optional[str] = Field(None, description="New type hint if changed")
    new_purpose: Optional[str] = Field(None, description="New purpose if changed")
    reasoning: str = Field("", description="Why this change was made")


class RefinementPlan(BaseModel):
    """AI-generated plan for strawman refinement."""
    understood_feedback: str = Field(..., description="What the AI understood from the feedback")
    modifications: List[SlideModification] = Field(default_factory=list)
    add_slides: List[Dict[str, Any]] = Field(default_factory=list, description="New slides to add")
    remove_slide_numbers: List[int] = Field(default_factory=list, description="Slide numbers to remove")
    reasoning: str = Field("", description="Overall reasoning for the changes")


class StrawmanRefiner:
    """
    AI-driven strawman refinement from user feedback.

    Does NOT use playbook - AI determines best layout/variant based on feedback.
    Uses LayoutAnalyzer to map slide_type_hint to proper service routing.
    """

    # Regex patterns for parsing slide references
    SLIDE_NUMBER_PATTERNS = [
        r"slide\s*(\d+)",
        r"slide\s+(\d+)",
        r"the\s+(\d+)(?:st|nd|rd|th)\s+slide",
        r"(?:first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth)\s+slide",
    ]

    # Word to number mapping
    WORD_TO_NUMBER = {
        "first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5,
        "sixth": 6, "seventh": 7, "eighth": 8, "ninth": 9, "tenth": 10
    }

    def __init__(
        self,
        model_name: str = "gemini-2.5-flash",
        project_id: str = "deckster-xyz",
        location: str = "us-central1",
        series_mode: LayoutSeriesMode = LayoutSeriesMode.L_ONLY
    ):
        """
        Initialize StrawmanRefiner.

        Args:
            model_name: Gemini model for refinement
            project_id: GCP project ID
            location: GCP location
            series_mode: Layout series mode for LayoutAnalyzer
        """
        self.model_name = model_name
        self.project_id = project_id
        self.location = location
        self.layout_analyzer = LayoutAnalyzer(series_mode=series_mode)

        # Initialize pydantic-ai agent
        self._agent = None

        logger.info(f"StrawmanRefiner initialized with model={model_name}")

    @property
    def agent(self):
        """Lazy-load the pydantic-ai agent."""
        if self._agent is None:
            try:
                from pydantic_ai import Agent

                self._agent = Agent(
                    model=f"google-vertex:{self.model_name}",
                    result_type=RefinementPlan,
                    system_prompt=self._get_system_prompt()
                )
            except Exception as e:
                logger.error(f"Failed to initialize pydantic-ai agent: {e}")
                raise
        return self._agent

    def _get_system_prompt(self) -> str:
        """Get the system prompt for the refinement agent."""
        return """You are a presentation refinement assistant. Your job is to modify presentation outlines based on user feedback.

When given a strawman (presentation outline) and user feedback:
1. Identify which slides the user wants to modify
2. Understand what changes they want
3. Generate specific modifications

Slide types you can use:
- "hero": Title slides, section dividers, closing slides
- "text": Standard content slides with bullet points
- "chart": Data visualization slides (when data/metrics need to be shown)
- "diagram": Process flows, architecture, workflows
- "infographic": Visual hierarchies like pyramids, funnels

When modifying slides:
- Keep titles concise and descriptive
- Topics should be bullet-point style (3-5 per slide)
- Match the tone to the existing presentation
- Only change what the user requested

Return a RefinementPlan with:
- understood_feedback: What you understood from the user
- modifications: List of slide changes
- add_slides: New slides if the user wants to add
- remove_slide_numbers: Slides to remove if requested
- reasoning: Why you made these changes
"""

    async def refine_from_chat(
        self,
        current_strawman: Dict[str, Any],
        user_feedback: str,
        context: Optional[Dict[str, Any]] = None
    ) -> RefinementResult:
        """
        Refine strawman based on user chat feedback.

        Args:
            current_strawman: Current strawman dictionary
            user_feedback: User's feedback message
            context: Additional context (audience, tone, etc.)

        Returns:
            RefinementResult with updated strawman and changes
        """
        logger.info(f"Refining strawman from feedback: '{user_feedback[:100]}...'")

        if not user_feedback or not user_feedback.strip():
            return RefinementResult(
                success=False,
                error="No feedback provided",
                reasoning="Cannot refine without user feedback"
            )

        try:
            # Step 1: Parse any explicit slide references from feedback
            referenced_slides = self._parse_slide_references(user_feedback)
            logger.debug(f"Parsed slide references: {referenced_slides}")

            # Step 2: Generate refinement plan via AI
            plan = await self._generate_refinement_plan(
                current_strawman, user_feedback, referenced_slides, context
            )

            if not plan:
                return RefinementResult(
                    success=False,
                    error="Failed to generate refinement plan",
                    reasoning="AI could not understand the feedback"
                )

            logger.info(f"Refinement plan: {plan.understood_feedback}")

            # Step 3: Apply modifications to strawman
            updated_strawman, changes = await self._apply_modifications(
                current_strawman, plan
            )

            # Step 4: Re-analyze layout for modified slides
            updated_strawman = await self._reanalyze_modified_slides(
                updated_strawman, [c.slide_number for c in changes if c.change_type == ChangeType.MODIFIED]
            )

            return RefinementResult(
                success=True,
                updated_strawman=updated_strawman,
                changes=changes,
                reasoning=plan.reasoning,
                needs_reapproval=True,
                affected_slide_numbers=[c.slide_number for c in changes]
            )

        except Exception as e:
            logger.error(f"Refinement failed: {e}", exc_info=True)
            return RefinementResult(
                success=False,
                error=str(e),
                reasoning="An error occurred during refinement"
            )

    def _parse_slide_references(self, feedback: str) -> List[int]:
        """
        Extract slide numbers from user feedback.

        Handles patterns like:
        - "slide 3"
        - "the third slide"
        - "slides 2 and 5"
        """
        slide_numbers = []
        feedback_lower = feedback.lower()

        # Pattern 1: "slide 3" or "slide 3, 5, 7"
        for match in re.finditer(r"slides?\s*(\d+(?:\s*[,and]+\s*\d+)*)", feedback_lower):
            numbers = re.findall(r"\d+", match.group(1))
            slide_numbers.extend([int(n) for n in numbers])

        # Pattern 2: "the third slide"
        for word, num in self.WORD_TO_NUMBER.items():
            if f"{word} slide" in feedback_lower:
                slide_numbers.append(num)

        # Pattern 3: "first and last slide"
        if "last slide" in feedback_lower or "final slide" in feedback_lower:
            slide_numbers.append(-1)  # -1 indicates last slide

        if "first slide" in feedback_lower:
            slide_numbers.append(1)

        return list(set(slide_numbers))

    async def _generate_refinement_plan(
        self,
        strawman: Dict[str, Any],
        feedback: str,
        referenced_slides: List[int],
        context: Optional[Dict[str, Any]]
    ) -> Optional[RefinementPlan]:
        """Generate refinement plan using AI."""

        # Format current strawman for the prompt
        slides_summary = self._format_slides_for_prompt(strawman)

        prompt = f"""Current presentation outline:
{slides_summary}

User feedback: "{feedback}"

{f"User referenced slides: {referenced_slides}" if referenced_slides else ""}

{f"Context - Audience: {context.get('audience', 'general')}, Tone: {context.get('tone', 'professional')}" if context else ""}

Based on this feedback, determine what modifications are needed to the presentation outline.
If the user mentions specific slides, focus on those. If they give general feedback, apply it appropriately.
"""

        try:
            from src.utils.vertex_retry import call_with_retry

            result = await call_with_retry(
                lambda: self.agent.run(prompt),
                operation_name="Strawman Refiner"
            )

            return result.output

        except Exception as e:
            logger.error(f"AI refinement failed: {e}")
            # Try to create a basic plan from parsed references
            return self._create_fallback_plan(feedback, referenced_slides)

    def _format_slides_for_prompt(self, strawman: Dict[str, Any]) -> str:
        """Format slides for the AI prompt."""
        lines = []
        slides = strawman.get("slides", [])

        for i, slide in enumerate(slides, 1):
            slide_type = slide.get("slide_type_hint", "text")
            title = slide.get("title", "Untitled")
            topics = slide.get("topics", [])

            lines.append(f"Slide {i} ({slide_type}): {title}")
            if topics:
                for topic in topics[:3]:  # Limit to first 3 for brevity
                    lines.append(f"  - {topic}")

        return "\n".join(lines)

    def _create_fallback_plan(
        self,
        feedback: str,
        referenced_slides: List[int]
    ) -> Optional[RefinementPlan]:
        """Create a basic plan when AI fails."""
        if not referenced_slides:
            return None

        # Try to extract intent from feedback
        intent = "modify"
        if any(word in feedback.lower() for word in ["remove", "delete", "drop"]):
            intent = "remove"
        elif any(word in feedback.lower() for word in ["add", "insert", "new"]):
            intent = "add"

        if intent == "remove":
            return RefinementPlan(
                understood_feedback=f"Remove slides: {referenced_slides}",
                remove_slide_numbers=referenced_slides,
                reasoning="User requested to remove specific slides"
            )

        return RefinementPlan(
            understood_feedback=feedback,
            modifications=[
                SlideModification(
                    slide_number=slide_num,
                    reasoning="User requested modification"
                )
                for slide_num in referenced_slides if slide_num > 0
            ],
            reasoning="Created fallback plan from parsed slide references"
        )

    async def _apply_modifications(
        self,
        strawman: Dict[str, Any],
        plan: RefinementPlan
    ) -> Tuple[Dict[str, Any], List[SlideChange]]:
        """Apply the refinement plan to the strawman."""
        updated = deepcopy(strawman)
        slides = updated.get("slides", [])
        changes: List[SlideChange] = []

        # Handle removals first (reverse order to preserve indices)
        for slide_num in sorted(plan.remove_slide_numbers, reverse=True):
            idx = slide_num - 1
            if 0 <= idx < len(slides):
                removed_slide = slides.pop(idx)
                changes.append(SlideChange(
                    slide_id=removed_slide.get("slide_id", f"slide_{slide_num}"),
                    slide_number=slide_num,
                    change_type=ChangeType.REMOVED,
                    ai_reasoning=f"Removed as requested"
                ))
                logger.info(f"Removed slide {slide_num}")

        # Handle modifications
        for mod in plan.modifications:
            idx = mod.slide_number - 1
            if idx == -2:  # -1 becomes -2 after -1 (last slide handling)
                idx = len(slides) - 1

            if 0 <= idx < len(slides):
                slide = slides[idx]
                field_changes = {}

                if mod.new_title and mod.new_title != slide.get("title"):
                    field_changes["title"] = {"old": slide.get("title"), "new": mod.new_title}
                    slide["title"] = mod.new_title

                if mod.new_topics and mod.new_topics != slide.get("topics"):
                    field_changes["topics"] = {"old": slide.get("topics"), "new": mod.new_topics}
                    slide["topics"] = mod.new_topics

                if mod.new_notes and mod.new_notes != slide.get("notes"):
                    field_changes["notes"] = {"old": slide.get("notes"), "new": mod.new_notes}
                    slide["notes"] = mod.new_notes

                if mod.new_slide_type_hint and mod.new_slide_type_hint != slide.get("slide_type_hint"):
                    field_changes["slide_type_hint"] = {
                        "old": slide.get("slide_type_hint"),
                        "new": mod.new_slide_type_hint
                    }
                    slide["slide_type_hint"] = mod.new_slide_type_hint

                if mod.new_purpose and mod.new_purpose != slide.get("purpose"):
                    field_changes["purpose"] = {"old": slide.get("purpose"), "new": mod.new_purpose}
                    slide["purpose"] = mod.new_purpose

                if field_changes:
                    changes.append(SlideChange(
                        slide_id=slide.get("slide_id", f"slide_{mod.slide_number}"),
                        slide_number=mod.slide_number,
                        change_type=ChangeType.MODIFIED,
                        field_changes=field_changes,
                        ai_reasoning=mod.reasoning,
                        layout_changed="slide_type_hint" in field_changes
                    ))
                    logger.info(f"Modified slide {mod.slide_number}: {list(field_changes.keys())}")

        # Handle additions
        for new_slide_data in plan.add_slides:
            slide_id = str(uuid.uuid4())
            new_slide = {
                "slide_id": slide_id,
                "slide_number": len(slides) + 1,
                "title": new_slide_data.get("title", "New Slide"),
                "topics": new_slide_data.get("topics", []),
                "notes": new_slide_data.get("notes", ""),
                "slide_type_hint": new_slide_data.get("slide_type_hint", "text"),
                "purpose": new_slide_data.get("purpose", ""),
                "layout": "L25",  # Will be updated by layout analyzer
                "is_hero": new_slide_data.get("is_hero", False),
            }

            # Insert at specified position or append
            position = new_slide_data.get("position", len(slides) + 1)
            if position <= len(slides):
                slides.insert(position - 1, new_slide)
            else:
                slides.append(new_slide)

            changes.append(SlideChange(
                slide_id=slide_id,
                slide_number=position,
                change_type=ChangeType.ADDED,
                ai_reasoning=f"Added new slide: {new_slide['title']}"
            ))
            logger.info(f"Added new slide at position {position}")

        # Renumber slides after modifications
        for i, slide in enumerate(slides):
            slide["slide_number"] = i + 1

        updated["slides"] = slides

        return updated, changes

    async def _reanalyze_modified_slides(
        self,
        strawman: Dict[str, Any],
        modified_slide_numbers: List[int]
    ) -> Dict[str, Any]:
        """Re-run layout analysis on modified slides."""
        if not modified_slide_numbers:
            return strawman

        slides = strawman.get("slides", [])

        for slide_num in modified_slide_numbers:
            idx = slide_num - 1
            if 0 <= idx < len(slides):
                slide = slides[idx]

                # Run layout analysis
                result = self.layout_analyzer.analyze(
                    slide_type_hint=slide.get("slide_type_hint", "text"),
                    hero_type=slide.get("hero_type"),
                    topic_count=len(slide.get("topics", [])),
                    purpose=slide.get("purpose"),
                    title=slide.get("title"),
                    topics=slide.get("topics")
                )

                # Update slide with analysis results
                slide["layout"] = result.layout
                slide["service"] = result.service
                slide["needs_variant_lookup"] = result.needs_variant_lookup
                if result.generation_instructions:
                    slide["generation_instructions"] = result.generation_instructions

                logger.debug(
                    f"Re-analyzed slide {slide_num}: layout={result.layout}, "
                    f"service={result.service}"
                )

        return strawman

    def summarize_changes(self, changes: List[SlideChange]) -> str:
        """Generate a human-readable summary of changes."""
        if not changes:
            return "No changes were made."

        summaries = []
        for change in changes:
            if change.change_type == ChangeType.MODIFIED:
                fields = list(change.field_changes.keys())
                summaries.append(f"Updated slide {change.slide_number} ({', '.join(fields)})")
            elif change.change_type == ChangeType.ADDED:
                summaries.append(f"Added new slide at position {change.slide_number}")
            elif change.change_type == ChangeType.REMOVED:
                summaries.append(f"Removed slide {change.slide_number}")

        return "; ".join(summaries)
