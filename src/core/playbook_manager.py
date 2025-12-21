"""
Playbook Manager for Director Agent v4.1

Manages loading, indexing, and matching of presentation playbooks.
Provides automatic playbook selection based on audience/purpose/duration.

Three-tier selection:
- 90%+ confidence: Full match - use playbook directly
- 60-89% confidence: Partial match - merge playbook with custom slides
- <60% confidence: No match - generate from scratch

Author: Director v4.1 Playbook System
Date: December 2024
"""

from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
import json
import uuid

from src.models.playbook import (
    Playbook,
    PlaybookMatch,
    PlaybookSlide,
    MatchConfidence,
    PlaybookMetadata,
    PlaybookStructure,
    PlaybookSection
)
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class PlaybookManager:
    """
    Manages playbook loading, indexing, and matching.

    Three-tier selection:
    - 90%+ confidence: Full match - use playbook directly
    - 60-89% confidence: Partial match - merge playbook with custom slides
    - <60% confidence: No match - generate from scratch
    """

    # Dimension values for matching
    AUDIENCES = ["professionals", "college_students", "high_school_students", "children", "seniors"]
    PURPOSES = ["investor_pitch", "qbr", "training", "product_demo", "sales", "informational"]
    DURATIONS = [5, 10, 15, 20, 30]

    # Compatibility matrices for partial matching
    AUDIENCE_COMPATIBILITY = {
        "professionals": ["professionals", "college_students"],
        "college_students": ["college_students", "professionals", "high_school_students"],
        "high_school_students": ["high_school_students", "college_students", "children"],
        "children": ["children", "high_school_students"],
        "seniors": ["seniors", "professionals"]
    }

    # v4.5.2: Strict purpose matching - each purpose only matches itself
    # Prevents QBR/sales/training playbooks from being force-fit to unrelated topics
    PURPOSE_COMPATIBILITY = {
        "investor_pitch": ["investor_pitch"],
        "qbr": ["qbr"],
        "training": ["training"],
        "product_demo": ["product_demo"],
        "sales": ["sales"],
        "informational": ["informational"]
    }

    # Scoring weights
    AUDIENCE_WEIGHT = 0.40
    PURPOSE_WEIGHT = 0.40
    DURATION_WEIGHT = 0.20

    def __init__(self, playbooks_dir: Optional[str] = None):
        """
        Initialize PlaybookManager.

        Args:
            playbooks_dir: Directory containing playbook JSON files.
                          Defaults to config/playbooks/
        """
        base_dir = Path(__file__).parent.parent.parent
        self.playbooks_dir = Path(playbooks_dir) if playbooks_dir else base_dir / "config" / "playbooks"

        self.registry: Dict[str, Dict[str, Any]] = {}  # playbook_id -> metadata
        self.playbooks: Dict[str, Playbook] = {}       # playbook_id -> full playbook
        self.index: Dict[Tuple[str, str, int], str] = {}  # (audience, purpose, duration) -> playbook_id

        self._load_playbooks()
        logger.info(f"PlaybookManager initialized with {len(self.playbooks)} playbooks from {self.playbooks_dir}")

    def _load_playbooks(self) -> None:
        """Load all playbooks from directory."""
        registry_path = self.playbooks_dir / "playbook_registry.json"

        if not registry_path.exists():
            logger.warning(f"Playbook registry not found: {registry_path}")
            return

        try:
            with open(registry_path) as f:
                registry_data = json.load(f)
                self.registry = registry_data.get("playbooks", {})

            # Load each playbook
            for playbook_id, meta in self.registry.items():
                playbook_path = self.playbooks_dir / meta.get("path", f"{playbook_id}.json")

                if playbook_path.exists():
                    try:
                        with open(playbook_path) as f:
                            playbook_data = json.load(f)
                            playbook = Playbook(**playbook_data)
                            self.playbooks[playbook_id] = playbook

                            # Build index
                            m = playbook.metadata
                            key = (m.audience, m.purpose, m.duration)
                            self.index[key] = playbook_id

                            logger.debug(f"Loaded playbook: {playbook_id}")
                    except Exception as e:
                        logger.error(f"Failed to load playbook {playbook_id}: {e}")
                else:
                    logger.warning(f"Playbook file not found: {playbook_path}")

        except Exception as e:
            logger.error(f"Failed to load playbook registry: {e}")

    def find_best_match(
        self,
        audience: str,
        purpose: str,
        duration: int,
        topic: Optional[str] = None
    ) -> PlaybookMatch:
        """
        Find the best matching playbook for given parameters.

        Args:
            audience: Target audience
            purpose: Presentation purpose
            duration: Duration in minutes
            topic: Optional topic for context-aware matching

        Returns:
            PlaybookMatch with confidence score and playbook data
        """
        # Normalize inputs
        audience = self._normalize_audience(audience)
        purpose = self._normalize_purpose(purpose)
        duration = self._normalize_duration(duration)

        logger.info(f"Finding playbook match: audience={audience}, purpose={purpose}, duration={duration}")

        # v4.1.1: If purpose couldn't be normalized (unknown purpose),
        # force NO_MATCH to generate from scratch with AI
        if purpose is None:
            logger.info(f"Purpose couldn't be normalized - forcing NO_MATCH")
            return PlaybookMatch(
                playbook_id=None,
                playbook=None,
                confidence=0.0,
                match_type=MatchConfidence.NO_MATCH,
                match_details={
                    "reason": "unknown_purpose",
                    "original_purpose": purpose,
                    "searched_audience": audience,
                    "searched_duration": duration
                },
                adaptation_notes=["Unknown purpose type - generate custom content with AI"]
            )

        # Try exact match first
        exact_key = (audience, purpose, duration)
        if exact_key in self.index:
            playbook_id = self.index[exact_key]
            playbook = self.playbooks[playbook_id]
            logger.info(f"Exact playbook match found: {playbook_id}")

            return PlaybookMatch(
                playbook_id=playbook_id,
                playbook=playbook,
                confidence=0.95,
                match_type=MatchConfidence.FULL_MATCH,
                match_details={
                    "audience_match": True,
                    "purpose_match": True,
                    "duration_match": True
                },
                adaptation_notes=[]
            )

        # Try partial matches
        best_match = self._find_partial_match(audience, purpose, duration)

        if best_match and best_match.confidence >= 0.60:
            logger.info(
                f"Partial playbook match found: {best_match.playbook_id} "
                f"(confidence: {best_match.confidence:.2f})"
            )
            return best_match

        # No suitable match
        logger.info(f"No suitable playbook match found (searched {len(self.playbooks)} playbooks)")
        return PlaybookMatch(
            playbook_id=None,
            playbook=None,
            confidence=0.0,
            match_type=MatchConfidence.NO_MATCH,
            match_details={
                "searched_audience": audience,
                "searched_purpose": purpose,
                "searched_duration": duration,
                "available_playbooks": len(self.playbooks)
            },
            adaptation_notes=["No suitable playbook found - generate from scratch"]
        )

    def _find_partial_match(
        self,
        audience: str,
        purpose: str,
        duration: int
    ) -> Optional[PlaybookMatch]:
        """Find best partial match using compatibility matrices."""
        candidates = []

        compatible_audiences = self.AUDIENCE_COMPATIBILITY.get(audience, [audience])
        compatible_purposes = self.PURPOSE_COMPATIBILITY.get(purpose, [purpose])

        for (pb_aud, pb_purp, pb_dur), playbook_id in self.index.items():
            score = 0.0
            match_details = {}
            notes = []

            # Audience scoring (40% weight)
            if pb_aud == audience:
                score += self.AUDIENCE_WEIGHT * 1.0
                match_details["audience_match"] = True
            elif pb_aud in compatible_audiences:
                compat_idx = compatible_audiences.index(pb_aud)
                score += self.AUDIENCE_WEIGHT * (1.0 - 0.15 * compat_idx)
                match_details["audience_match"] = "compatible"
                notes.append(f"Adjust tone for {audience} (playbook is for {pb_aud})")
            else:
                continue  # Skip incompatible audiences

            # Purpose scoring (40% weight)
            if pb_purp == purpose:
                score += self.PURPOSE_WEIGHT * 1.0
                match_details["purpose_match"] = True
            elif pb_purp in compatible_purposes:
                compat_idx = compatible_purposes.index(pb_purp)
                score += self.PURPOSE_WEIGHT * (1.0 - 0.20 * compat_idx)
                match_details["purpose_match"] = "compatible"
                notes.append(f"Adapt structure for {purpose} (playbook is {pb_purp})")
            else:
                continue  # Skip incompatible purposes

            # Duration scoring (20% weight)
            duration_diff = abs(pb_dur - duration)
            if duration_diff == 0:
                score += self.DURATION_WEIGHT * 1.0
                match_details["duration_match"] = True
            elif duration_diff <= 5:
                score += self.DURATION_WEIGHT * (1.0 - duration_diff * 0.10)
                match_details["duration_match"] = "close"
                if pb_dur > duration:
                    notes.append(f"Remove {duration_diff} min of content")
                else:
                    notes.append(f"Add {duration_diff} min of content")
            elif duration_diff <= 10:
                score += self.DURATION_WEIGHT * 0.40
                match_details["duration_match"] = "adaptable"
                notes.append(f"Significant duration adaptation needed ({pb_dur}min -> {duration}min)")
            else:
                continue  # Too different

            playbook = self.playbooks[playbook_id]
            candidates.append((score, playbook_id, playbook, match_details, notes))

        if not candidates:
            return None

        # Get best candidate
        candidates.sort(reverse=True, key=lambda x: x[0])
        best_score, best_id, best_playbook, best_details, best_notes = candidates[0]

        # Determine match type
        if best_score >= 0.90:
            match_type = MatchConfidence.FULL_MATCH
        elif best_score >= 0.60:
            match_type = MatchConfidence.PARTIAL_MATCH
        else:
            match_type = MatchConfidence.NO_MATCH

        return PlaybookMatch(
            playbook_id=best_id,
            playbook=best_playbook,
            confidence=best_score,
            match_type=match_type,
            match_details=best_details,
            adaptation_notes=best_notes
        )

    def _normalize_audience(self, audience: str) -> str:
        """Normalize audience string to canonical value."""
        audience = audience.lower().strip()

        mappings = {
            "professional": "professionals",
            "business": "professionals",
            "executive": "professionals",
            "corporate": "professionals",
            "investor": "professionals",
            "college": "college_students",
            "university": "college_students",
            "student": "college_students",
            "high school": "high_school_students",
            "teenager": "high_school_students",
            "teen": "high_school_students",
            "kids": "children",
            "elementary": "children",
            "child": "children",
            "elderly": "seniors",
            "older adults": "seniors",
            "senior": "seniors"
        }

        for pattern, normalized in mappings.items():
            if pattern in audience:
                return normalized

        if audience in self.AUDIENCES:
            return audience

        return "professionals"  # Default

    def _normalize_purpose(self, purpose: str) -> str:
        """Normalize purpose string to canonical value."""
        purpose = purpose.lower().strip()

        mappings = {
            "investor": "investor_pitch",
            "pitch": "investor_pitch",
            "funding": "investor_pitch",
            "vc": "investor_pitch",
            "quarterly": "qbr",
            "business review": "qbr",
            "review": "qbr",
            "train": "training",
            "education": "training",
            "teach": "training",
            "learn": "training",
            "demo": "product_demo",
            "demonstration": "product_demo",
            "showcase": "product_demo",
            "sell": "sales",
            "persuade": "sales",
            "inform": "informational",
            "present": "informational",
            "explain": "informational"
        }

        for pattern, normalized in mappings.items():
            if pattern in purpose:
                return normalized

        if purpose in self.PURPOSES:
            return purpose

        # v4.1.1: Don't default to "informational" for unknown purposes.
        # This was causing QBR templates to be used for unrelated topics
        # (e.g., "actor dileep - films and life" got QBR slides).
        # Return None to force NO_MATCH and generate from scratch with AI.
        logger.warning(f"Unknown purpose '{purpose}' - will generate from scratch")
        return None

    def _normalize_duration(self, duration: int) -> int:
        """Normalize duration to nearest supported value."""
        if duration <= 5:
            return 5
        elif duration <= 10:
            return 10
        elif duration <= 15:
            return 15
        elif duration <= 20:
            return 20
        else:
            return 30

    def apply_playbook(
        self,
        playbook: Playbook,
        topic: str,
        audience: str,
        purpose: str,
        duration: int
    ) -> List[Dict[str, Any]]:
        """
        Apply a playbook template to generate slides.

        Args:
            playbook: The playbook definition
            topic: Presentation topic
            audience: Target audience
            purpose: Presentation purpose
            duration: Target duration

        Returns:
            List of slide definitions ready for strawman
        """
        slides = []
        pb_duration = playbook.metadata.duration

        # Determine which slides to skip for shorter durations
        skip_slots = set()
        if duration < pb_duration and playbook.adaptation_rules:
            skip_slots = set(playbook.adaptation_rules.shorter_duration_removes)

        for slot in playbook.slides:
            # Skip slots marked for removal in shorter durations
            if slot.slot_id in skip_slots:
                continue

            # Skip optional slides for shorter durations
            if slot.is_optional and duration < pb_duration:
                continue

            slide = self._instantiate_slide(slot, topic, audience, purpose)
            slides.append(slide)

        # Renumber slides
        for i, slide in enumerate(slides):
            slide["slide_number"] = i + 1

        logger.info(f"Applied playbook '{playbook.playbook_id}' to topic '{topic}': {len(slides)} slides")
        return slides

    def _instantiate_slide(
        self,
        slot: PlaybookSlide,
        topic: str,
        audience: str,
        purpose: str
    ) -> Dict[str, Any]:
        """Instantiate a slide from a playbook slot template."""
        # Apply template substitutions
        title = slot.title_template.format(topic=topic)
        topics = [t.format(topic=topic) for t in slot.topic_templates]
        narrative = slot.narrative_template.format(topic=topic) if slot.narrative_template else None

        return {
            "slide_id": str(uuid.uuid4()),
            "slide_number": slot.slide_number,
            "title": title,
            "layout": slot.layout,
            "variant_id": slot.suggested_variant,
            "topics": topics,
            "notes": narrative,
            "is_hero": slot.is_hero,
            "hero_type": slot.hero_type,
            "slide_type_hint": slot.slide_type_hint,
            "purpose": slot.purpose,
            # v4.0.25 story-driven fields
            "service": "text",  # Default, will be updated by layout analyzer
            "generation_instructions": None
        }

    def list_playbooks(self) -> List[Dict[str, Any]]:
        """
        List all available playbooks with metadata.

        Returns:
            List of playbook summaries
        """
        return [
            {
                "playbook_id": pid,
                "audience": pb.metadata.audience,
                "purpose": pb.metadata.purpose,
                "duration": pb.metadata.duration,
                "description": pb.metadata.description,
                "slide_count": pb.structure.total_slides
            }
            for pid, pb in self.playbooks.items()
        ]

    def get_playbook(self, playbook_id: str) -> Optional[Playbook]:
        """Get a specific playbook by ID."""
        return self.playbooks.get(playbook_id)
