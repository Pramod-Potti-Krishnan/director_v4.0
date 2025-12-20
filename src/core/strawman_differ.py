"""
Stage 5: Strawman Differ

Compares Director's strawman with Deck-Builder's current state to detect
changes made by the user in the preview. Used by the "Diff on Generate" approach.

Key responsibilities:
- Match slides between Director and Deck-Builder by ID or content hash
- Detect added, removed, modified, and reordered slides
- Identify which fields changed in modified slides
- Flag slides that need layout/variant re-analysis
"""

import hashlib
import logging
from typing import Any, Dict, List, Optional, Tuple

from src.models.refinement import (
    ChangeType,
    MergeResult,
    MergeStrategy,
    SlideMatch,
    SlideModification,
    StrawmanDiff,
)

logger = logging.getLogger(__name__)


class StrawmanDiffer:
    """
    Compare Director's strawman with Deck-Builder's current state.

    The Deck-Builder is the source of truth during editing. This class
    detects what changes the user made so Director can incorporate them.
    """

    # Fields to compare for content changes
    CONTENT_FIELDS = ["title", "topics", "notes", "layout", "variant_id"]

    # Fields that trigger layout re-analysis when changed
    REANALYSIS_FIELDS = ["topics", "title"]

    def __init__(self):
        pass

    def compute_diff(
        self,
        director_strawman: Dict[str, Any],
        deckbuilder_state: Dict[str, Any]
    ) -> StrawmanDiff:
        """
        Compare Director's strawman with Deck-Builder's current state.

        Args:
            director_strawman: Strawman from Director's session (has_strawman=True)
            deckbuilder_state: Current state fetched from Deck-Builder API

        Returns:
            StrawmanDiff with all detected changes
        """
        diff = StrawmanDiff()

        # Get slide lists
        director_slides = director_strawman.get("slides", [])
        db_slides = deckbuilder_state.get("slides", [])

        logger.info(
            f"Computing diff: Director has {len(director_slides)} slides, "
            f"Deck-Builder has {len(db_slides)} slides"
        )

        # Match slides between the two sources
        matches = self._match_slides(director_slides, db_slides)
        diff.slide_matches = matches

        # Process matches to find changes
        for match in matches:
            if match.is_added:
                # Slide added in Deck-Builder
                diff.added_slides.append(match.deckbuilder_slide)
                diff.has_changes = True
                logger.debug(f"Detected added slide at index {match.deckbuilder_index}")

            elif match.is_removed:
                # Slide removed from Deck-Builder
                slide_id = match.director_slide.get("slide_id", f"slide_{match.director_index}")
                diff.removed_slide_ids.append(slide_id)
                diff.has_changes = True
                logger.debug(f"Detected removed slide: {slide_id}")

            elif match.is_matched:
                # Check for modifications
                modification = self._detect_slide_changes(
                    match.director_slide,
                    match.deckbuilder_slide,
                    match.director_index + 1  # 1-indexed slide number
                )
                if modification:
                    diff.modified_slides.append(modification)
                    diff.has_changes = True

        # Check for reordering
        diff.reordered = self._detect_reorder(matches)
        if diff.reordered:
            diff.new_order = [
                m.deckbuilder_slide.get("slide_id", f"slide_{m.deckbuilder_index}")
                for m in matches
                if m.deckbuilder_slide is not None
            ]
            diff.has_changes = True

        # Check presentation title
        director_title = director_strawman.get("title", "")
        db_title = deckbuilder_state.get("title", "")
        if director_title != db_title and db_title:
            diff.title_changed = True
            diff.new_title = db_title
            diff.has_changes = True

        logger.info(
            f"Diff complete: {diff.change_count} change(s) detected - "
            f"{len(diff.added_slides)} added, {len(diff.removed_slide_ids)} removed, "
            f"{len(diff.modified_slides)} modified, reordered={diff.reordered}"
        )

        return diff

    def _match_slides(
        self,
        director_slides: List[Dict[str, Any]],
        db_slides: List[Dict[str, Any]]
    ) -> List[SlideMatch]:
        """
        Match slides between Director and Deck-Builder.

        Matching strategy:
        1. First, try to match by slide_id (exact match)
        2. Then, match by position + title hash (fuzzy match)
        3. Remaining slides are marked as added or removed
        """
        matches: List[SlideMatch] = []
        used_director_indices = set()
        used_db_indices = set()

        # Phase 1: Match by slide_id
        for db_idx, db_slide in enumerate(db_slides):
            db_slide_id = db_slide.get("slide_id")
            if not db_slide_id:
                continue

            for dir_idx, dir_slide in enumerate(director_slides):
                if dir_idx in used_director_indices:
                    continue

                dir_slide_id = dir_slide.get("slide_id")
                if dir_slide_id == db_slide_id:
                    matches.append(SlideMatch(
                        director_slide=dir_slide,
                        deckbuilder_slide=db_slide,
                        director_index=dir_idx,
                        deckbuilder_index=db_idx,
                        match_type="matched",
                        match_confidence=1.0
                    ))
                    used_director_indices.add(dir_idx)
                    used_db_indices.add(db_idx)
                    break

        # Phase 2: Match remaining by content hash (title + position proximity)
        for db_idx, db_slide in enumerate(db_slides):
            if db_idx in used_db_indices:
                continue

            db_hash = self._slide_content_hash(db_slide)
            best_match = None
            best_score = 0.0

            for dir_idx, dir_slide in enumerate(director_slides):
                if dir_idx in used_director_indices:
                    continue

                dir_hash = self._slide_content_hash(dir_slide)

                # Calculate match score based on content similarity and position
                content_match = 1.0 if db_hash == dir_hash else 0.0
                title_match = self._title_similarity(
                    db_slide.get("title", ""),
                    dir_slide.get("title", "")
                )
                position_score = 1.0 - min(abs(db_idx - dir_idx) / max(len(db_slides), 1), 1.0)

                # Weighted score
                score = (content_match * 0.5) + (title_match * 0.3) + (position_score * 0.2)

                if score > best_score and score >= 0.5:
                    best_score = score
                    best_match = (dir_idx, dir_slide)

            if best_match:
                dir_idx, dir_slide = best_match
                matches.append(SlideMatch(
                    director_slide=dir_slide,
                    deckbuilder_slide=db_slide,
                    director_index=dir_idx,
                    deckbuilder_index=db_idx,
                    match_type="matched",
                    match_confidence=best_score
                ))
                used_director_indices.add(dir_idx)
                used_db_indices.add(db_idx)
            else:
                # No match found - this is an added slide
                matches.append(SlideMatch(
                    director_slide=None,
                    deckbuilder_slide=db_slide,
                    director_index=None,
                    deckbuilder_index=db_idx,
                    match_type="added",
                    match_confidence=0.0
                ))

        # Phase 3: Mark remaining Director slides as removed
        for dir_idx, dir_slide in enumerate(director_slides):
            if dir_idx not in used_director_indices:
                matches.append(SlideMatch(
                    director_slide=dir_slide,
                    deckbuilder_slide=None,
                    director_index=dir_idx,
                    deckbuilder_index=None,
                    match_type="removed",
                    match_confidence=0.0
                ))

        # Sort matches by Deck-Builder index for proper ordering
        matches.sort(key=lambda m: m.deckbuilder_index if m.deckbuilder_index is not None else float('inf'))

        return matches

    def _slide_content_hash(self, slide: Dict[str, Any]) -> str:
        """Generate a content hash for a slide."""
        content = f"{slide.get('title', '')}|{','.join(slide.get('topics', []))}"
        return hashlib.md5(content.encode()).hexdigest()[:8]

    def _title_similarity(self, title1: str, title2: str) -> float:
        """Calculate similarity between two titles (0-1)."""
        if not title1 or not title2:
            return 0.0

        title1_lower = title1.lower().strip()
        title2_lower = title2.lower().strip()

        if title1_lower == title2_lower:
            return 1.0

        # Check for substring match
        if title1_lower in title2_lower or title2_lower in title1_lower:
            return 0.8

        # Word overlap
        words1 = set(title1_lower.split())
        words2 = set(title2_lower.split())
        if not words1 or not words2:
            return 0.0

        overlap = len(words1 & words2)
        return overlap / max(len(words1), len(words2))

    def _detect_slide_changes(
        self,
        director_slide: Dict[str, Any],
        db_slide: Dict[str, Any],
        slide_number: int
    ) -> Optional[SlideModification]:
        """
        Detect changes between Director's slide and Deck-Builder's slide.

        Returns SlideModification if changes found, None otherwise.
        """
        modification = SlideModification(
            slide_id=director_slide.get("slide_id", f"slide_{slide_number}"),
            slide_number=slide_number
        )

        # Compare each content field
        for field in self.CONTENT_FIELDS:
            dir_value = director_slide.get(field)
            db_value = db_slide.get(field)

            # Normalize for comparison
            if isinstance(dir_value, list) and isinstance(db_value, list):
                changed = set(dir_value) != set(db_value) or dir_value != db_value
            else:
                changed = dir_value != db_value

            if changed:
                modification.old_values[field] = dir_value
                modification.new_values[field] = db_value

                if field == "title":
                    modification.title_changed = True
                elif field == "topics":
                    modification.topics_changed = True
                elif field == "notes":
                    modification.notes_changed = True
                elif field == "layout":
                    modification.layout_changed = True

        # Check if content changed (topics or notes)
        modification.content_changed = modification.topics_changed or modification.notes_changed

        # Return modification only if there are actual changes
        if modification.old_values:
            logger.debug(
                f"Slide {slide_number} modified: "
                f"fields={list(modification.old_values.keys())}"
            )
            return modification

        return None

    def _detect_reorder(self, matches: List[SlideMatch]) -> bool:
        """
        Detect if slides were reordered.

        Compares the relative order of matched slides.
        """
        # Get matched slides only (not added/removed)
        matched = [m for m in matches if m.is_matched]

        if len(matched) < 2:
            return False

        # Check if Director indices are in increasing order
        director_indices = [m.director_index for m in matched]
        for i in range(1, len(director_indices)):
            if director_indices[i] < director_indices[i - 1]:
                return True

        return False

    def merge_changes(
        self,
        director_strawman: Dict[str, Any],
        diff: StrawmanDiff,
        strategy: MergeStrategy = MergeStrategy.DECKBUILDER_WINS
    ) -> MergeResult:
        """
        Merge Deck-Builder changes into Director's strawman.

        Args:
            director_strawman: Original strawman from Director
            diff: Computed diff from compute_diff()
            strategy: How to handle conflicts

        Returns:
            MergeResult with merged strawman
        """
        if not diff.has_changes:
            return MergeResult(
                success=True,
                merged_strawman=director_strawman,
                merge_strategy_used=strategy
            )

        # Create a copy to modify
        merged = {**director_strawman}
        merged["slides"] = list(director_strawman.get("slides", []))
        slides_updated = []

        try:
            # Handle modified slides
            for modification in diff.modified_slides:
                slide_idx = modification.slide_number - 1
                if 0 <= slide_idx < len(merged["slides"]):
                    slide = merged["slides"][slide_idx]

                    # Apply changes based on strategy
                    if strategy == MergeStrategy.DECKBUILDER_WINS:
                        for field, new_value in modification.new_values.items():
                            slide[field] = new_value
                            slides_updated.append(modification.slide_number)

            # Handle added slides
            for added_slide in diff.added_slides:
                # Add at the end or at the specified position
                merged["slides"].append(added_slide)
                slides_updated.append(len(merged["slides"]))

            # Handle removed slides
            if diff.removed_slide_ids:
                merged["slides"] = [
                    s for s in merged["slides"]
                    if s.get("slide_id") not in diff.removed_slide_ids
                ]

            # Handle reordering
            if diff.reordered and diff.new_order:
                # Create a map of slide_id to slide
                slide_map = {s.get("slide_id"): s for s in merged["slides"]}

                # Reorder based on new_order
                reordered_slides = []
                for slide_id in diff.new_order:
                    if slide_id in slide_map:
                        reordered_slides.append(slide_map[slide_id])
                        del slide_map[slide_id]

                # Append any remaining slides (shouldn't happen normally)
                reordered_slides.extend(slide_map.values())
                merged["slides"] = reordered_slides

            # Handle title change
            if diff.title_changed and diff.new_title:
                merged["title"] = diff.new_title

            return MergeResult(
                success=True,
                merged_strawman=merged,
                merge_strategy_used=strategy,
                slides_updated=list(set(slides_updated))
            )

        except Exception as e:
            logger.error(f"Merge failed: {e}")
            return MergeResult(
                success=False,
                merged_strawman=None,
                conflicts=[{"error": str(e)}],
                merge_strategy_used=strategy
            )
