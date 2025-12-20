"""
Playbook Merger for Director Agent v4.1

Handles merging playbook slides with AI-generated custom slides
for partial match scenarios (60-89% confidence).

Author: Director v4.1 Playbook System
Date: December 2024
"""

from typing import Dict, Any, List, Optional
import uuid

from src.models.playbook import Playbook, MergeInstruction
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class PlaybookMerger:
    """
    Merges playbook templates with AI-generated custom slides.

    Used for partial match scenarios (60-89% confidence).
    When a playbook is a good base but needs customization, this class
    identifies gaps and merges playbook slides with custom content.
    """

    # Purpose mappings for different presentation types
    PURPOSE_SLIDES = {
        "investor_pitch": ["traction", "team", "ask", "market_size"],
        "qbr": ["metrics", "achievements", "blockers", "risks", "roadmap"],
        "training": ["examples", "practice", "quiz", "key_takeaways"],
        "product_demo": ["features", "benefits", "use_cases", "pricing"],
        "sales": ["benefits", "pricing", "testimonials", "next_steps"],
        "informational": ["overview", "details", "examples", "summary"]
    }

    def __init__(self):
        """Initialize PlaybookMerger."""
        self.merge_strategies = {
            "duration_expand": self._merge_duration_expand,
            "purpose_adapt": self._merge_purpose_adapt,
            "topic_specific": self._merge_topic_specific
        }

    def merge(
        self,
        playbook_slides: List[Dict[str, Any]],
        custom_slides: List[Dict[str, Any]],
        match_details: Dict[str, Any],
        adaptation_notes: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Merge playbook slides with custom generated slides.

        Args:
            playbook_slides: Slides from playbook template
            custom_slides: AI-generated slides for gaps
            match_details: What matched/didn't match
            adaptation_notes: Suggested adaptations

        Returns:
            Merged list of slides
        """
        logger.info(
            f"Merging {len(playbook_slides)} playbook slides with "
            f"{len(custom_slides)} custom slides"
        )

        # Determine merge strategy based on match details
        if match_details.get("duration_match") in ["adaptable", "close"]:
            merged = self._merge_duration_expand(playbook_slides, custom_slides)
        elif match_details.get("purpose_match") == "compatible":
            merged = self._merge_purpose_adapt(playbook_slides, custom_slides)
        else:
            merged = self._merge_interleave(playbook_slides, custom_slides)

        # Renumber and add slide IDs
        for i, slide in enumerate(merged):
            slide["slide_number"] = i + 1
            if "slide_id" not in slide:
                slide["slide_id"] = str(uuid.uuid4())

        logger.info(f"Merge complete: {len(merged)} total slides")
        return merged

    def _merge_duration_expand(
        self,
        playbook_slides: List[Dict[str, Any]],
        custom_slides: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Expand playbook with custom slides for longer duration.

        Strategy: Insert custom slides after content sections,
        maintaining playbook's narrative flow.
        """
        merged = []
        custom_idx = 0

        # Expandable purposes - where we can insert custom slides
        expandable_purposes = {
            "problem_statement", "solution_overview", "traction",
            "detailed_content", "examples", "features"
        }

        for slide in playbook_slides:
            merged.append(slide)

            # After content sections (not heroes), insert custom slides
            if not slide.get("is_hero") and custom_idx < len(custom_slides):
                slide_purpose = slide.get("purpose", "")

                # Insert custom slide after expandable sections
                if slide_purpose in expandable_purposes:
                    merged.append(custom_slides[custom_idx])
                    custom_idx += 1

        # Append remaining custom slides before closing
        while custom_idx < len(custom_slides):
            # Insert before closing slide
            if merged and merged[-1].get("hero_type") == "closing_slide":
                merged.insert(-1, custom_slides[custom_idx])
            else:
                merged.append(custom_slides[custom_idx])
            custom_idx += 1

        return merged

    def _merge_purpose_adapt(
        self,
        playbook_slides: List[Dict[str, Any]],
        custom_slides: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Adapt playbook structure for different purpose.

        Strategy: Keep hero slides from playbook, augment content
        slides with purpose-specific custom slides.
        """
        merged = []

        # First pass: add all playbook slides
        for slide in playbook_slides:
            merged.append(slide)

        # Second pass: insert custom slides that cover gaps
        playbook_purposes = {s.get("purpose") for s in playbook_slides}

        for custom in custom_slides:
            custom_purpose = custom.get("purpose")

            # Only add if not already covered
            if custom_purpose not in playbook_purposes:
                # Insert before closing
                if merged and merged[-1].get("hero_type") == "closing_slide":
                    merged.insert(-1, custom)
                else:
                    merged.append(custom)

        return merged

    def _merge_topic_specific(
        self,
        playbook_slides: List[Dict[str, Any]],
        custom_slides: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Merge for topic-specific customization.

        Strategy: Use playbook as skeleton, inject topic-specific
        slides at relevant positions.
        """
        merged = []

        # Keep title and closing from playbook
        title_slide = None
        closing_slide = None
        content_slides = []

        for slide in playbook_slides:
            if slide.get("hero_type") == "title_slide":
                title_slide = slide
            elif slide.get("hero_type") == "closing_slide":
                closing_slide = slide
            else:
                content_slides.append(slide)

        # Build merged list
        if title_slide:
            merged.append(title_slide)

        # Interleave content and custom slides
        custom_idx = 0
        for content in content_slides:
            merged.append(content)
            if custom_idx < len(custom_slides):
                merged.append(custom_slides[custom_idx])
                custom_idx += 1

        # Add remaining custom slides
        while custom_idx < len(custom_slides):
            merged.append(custom_slides[custom_idx])
            custom_idx += 1

        if closing_slide:
            merged.append(closing_slide)

        return merged

    def _merge_interleave(
        self,
        playbook_slides: List[Dict[str, Any]],
        custom_slides: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Interleave playbook and custom slides.

        Strategy: Alternate between playbook and custom content,
        preserving title and closing structure.
        """
        merged = []
        pb_idx = 0
        custom_idx = 0

        # Title slide from playbook
        if playbook_slides and playbook_slides[0].get("hero_type") == "title_slide":
            merged.append(playbook_slides[0])
            pb_idx = 1

        # Alternate between playbook content and custom
        while pb_idx < len(playbook_slides) or custom_idx < len(custom_slides):
            # Add playbook slide (skip closing for now)
            if pb_idx < len(playbook_slides):
                slide = playbook_slides[pb_idx]
                if slide.get("hero_type") != "closing_slide":
                    merged.append(slide)
                pb_idx += 1

            # Add custom slide
            if custom_idx < len(custom_slides):
                merged.append(custom_slides[custom_idx])
                custom_idx += 1

        # Closing slide from playbook
        for slide in playbook_slides:
            if slide.get("hero_type") == "closing_slide":
                merged.append(slide)
                break

        return merged

    def identify_gaps(
        self,
        playbook: Playbook,
        topic: str,
        purpose: str,
        duration: int
    ) -> List[MergeInstruction]:
        """
        Identify what custom slides are needed to fill gaps.

        Args:
            playbook: The matched playbook
            topic: Presentation topic
            purpose: Target purpose
            duration: Target duration

        Returns:
            List of instructions for generating custom slides
        """
        instructions = []
        pb_duration = playbook.metadata.duration
        pb_purpose = playbook.metadata.purpose

        # Duration gap - need more slides
        if duration > pb_duration:
            extra_minutes = duration - pb_duration
            extra_slides = max(1, extra_minutes // 3)  # ~3 min per slide

            instructions.append(MergeInstruction(
                position="expand",
                reference_slot="content_section",
                purpose=f"Additional details about {topic}",
                count=extra_slides
            ))

            logger.debug(
                f"Duration gap: need {extra_slides} extra slides "
                f"({pb_duration}min -> {duration}min)"
            )

        # Purpose gap - need purpose-specific slides
        if pb_purpose != purpose:
            needed_purposes = self.PURPOSE_SLIDES.get(purpose, [])
            existing_purposes = {s.purpose for s in playbook.slides}

            for p in needed_purposes:
                if p not in existing_purposes:
                    instructions.append(MergeInstruction(
                        position="before",
                        reference_slot="closing",
                        purpose=p,
                        count=1
                    ))

            logger.debug(
                f"Purpose gap: playbook is {pb_purpose}, target is {purpose}. "
                f"Need slides for: {[i.purpose for i in instructions if i.position == 'before']}"
            )

        logger.info(
            f"Identified {len(instructions)} gaps to fill for "
            f"topic='{topic}', purpose='{purpose}', duration={duration}min"
        )
        return instructions

    def adapt_slide_for_audience(
        self,
        slide: Dict[str, Any],
        target_audience: str,
        source_audience: str
    ) -> Dict[str, Any]:
        """
        Adapt slide content for a different audience.

        Args:
            slide: The slide to adapt
            target_audience: The target audience
            source_audience: The original audience

        Returns:
            Adapted slide
        """
        # Tone adaptations
        tone_map = {
            "professionals": "formal",
            "college_students": "engaging",
            "high_school_students": "accessible",
            "children": "simple",
            "seniors": "clear"
        }

        adapted = slide.copy()

        # Add adaptation note
        if target_audience != source_audience:
            adapted["adaptation_note"] = (
                f"Adapted from {source_audience} to {target_audience} audience. "
                f"Use {tone_map.get(target_audience, 'neutral')} tone."
            )

        return adapted
