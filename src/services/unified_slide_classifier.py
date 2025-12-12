"""
Unified Slide Classifier

Registry-driven slide classification using keyword matching and priority ordering.
Replaces hardcoded keyword sets with configuration from unified variant registry.

Version: 2.0.0
Created: 2025-11-29
"""

from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass
from src.models.variant_registry import UnifiedVariantRegistry
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


@dataclass
class ClassificationMatch:
    """
    Single classification match result.

    Attributes:
        variant_id: Variant identifier
        service_name: Service providing this variant
        display_name: Human-readable variant name
        priority: Classification priority (lower = higher priority)
        match_score: Number of keywords matched
        matched_keywords: List of keywords that matched
        confidence: Match confidence (0.0 to 1.0)
    """
    variant_id: str
    service_name: str
    display_name: str
    priority: int
    match_score: int
    matched_keywords: List[str]
    confidence: float


class UnifiedSlideClassifier:
    """
    Registry-driven slide classifier.

    Uses keywords from unified variant registry to classify slides by matching
    slide content (title, key points, description) against variant keywords.
    Returns ranked list of matching variants by priority.

    Features:
    - Zero hardcoded keywords (all from registry)
    - Priority-based ranking
    - Match score calculation
    - Confidence scoring
    - Multi-service support
    - Case-insensitive matching

    Architecture:
        Registry → Classifier → Ranked Matches
        ↓
        Keywords by Variant

    Usage:
        registry = load_registry_from_file("config/unified_variant_registry.json")
        classifier = UnifiedSlideClassifier(registry)

        matches = classifier.classify_slide(
            title="Market Share Analysis",
            key_points=["Product A: 45%", "Product B: 30%", "Product C: 25%"],
            context="Q4 revenue breakdown"
        )

        # Get best match
        if matches:
            best = matches[0]
            print(f"Best variant: {best.variant_id} ({best.confidence:.2%} confidence)")
    """

    def __init__(self, registry: UnifiedVariantRegistry):
        """
        Initialize unified slide classifier.

        Args:
            registry: UnifiedVariantRegistry instance with all variants
        """
        self.registry = registry
        self.variant_keywords: Dict[str, Dict[str, Any]] = {}

        # Build keyword index
        self._build_keyword_index()

        logger.info(
            f"UnifiedSlideClassifier initialized",
            extra={
                "total_variants": len(self.variant_keywords),
                "total_services": len(registry.services)
            }
        )

    def _build_keyword_index(self):
        """
        Build keyword index from registry.

        Creates mapping of variant_id to:
        - keywords (normalized, lowercase)
        - priority
        - service_name
        - display_name
        """
        for service_name, service_config in self.registry.services.items():
            if not service_config.enabled:
                continue

            for variant_id, variant_config in service_config.variants.items():
                # Normalize keywords to lowercase for case-insensitive matching
                keywords = [kw.lower() for kw in variant_config.classification.keywords]

                self.variant_keywords[variant_id] = {
                    "keywords": set(keywords),
                    "priority": variant_config.classification.priority,
                    "service_name": service_name,
                    "display_name": variant_config.display_name,
                    "status": variant_config.status
                }

        logger.debug(
            f"Built keyword index",
            extra={
                "variant_count": len(self.variant_keywords),
                "avg_keywords": sum(len(v["keywords"]) for v in self.variant_keywords.values()) // max(1, len(self.variant_keywords))
            }
        )

    def classify_slide(
        self,
        title: Optional[str] = None,
        key_points: Optional[List[str]] = None,
        context: Optional[str] = None,
        min_confidence: float = 0.1,
        max_results: int = 5
    ) -> List[ClassificationMatch]:
        """
        Classify slide content against all variants.

        Matches slide content (title, key points, context) against variant
        keywords from registry. Returns ranked list of matches by priority
        and match score.

        Args:
            title: Slide title
            key_points: List of key points or bullet points
            context: Additional context or description
            min_confidence: Minimum confidence threshold (0.0 to 1.0)
            max_results: Maximum number of results to return

        Returns:
            List of ClassificationMatch objects, sorted by priority then match score

        Example:
            matches = classifier.classify_slide(
                title="Sales Conversion Funnel",
                key_points=[
                    "Website Visitors: 10,000",
                    "Qualified Leads: 1,000",
                    "Opportunities: 100",
                    "Closed Deals: 25"
                ],
                context="Q4 sales pipeline analysis"
            )

            # matches[0] might be:
            # ClassificationMatch(
            #     variant_id="funnel",
            #     service_name="illustrator_service_v1.0",
            #     display_name="Funnel (Conversion)",
            #     priority=5,
            #     match_score=8,
            #     matched_keywords=["funnel", "conversion", "sales", "pipeline", ...],
            #     confidence=0.85
            # )
        """
        # Combine all text for matching
        text_parts = []
        if title:
            text_parts.append(title)
        if key_points:
            text_parts.extend(key_points)
        if context:
            text_parts.append(context)

        if not text_parts:
            logger.warning("No content provided for classification")
            return []

        # Normalize text to lowercase
        combined_text = " ".join(text_parts).lower()

        # Match against all variants
        matches = []
        for variant_id, variant_info in self.variant_keywords.items():
            # Skip disabled variants
            if variant_info["status"] == "disabled":
                continue

            # Count keyword matches
            keywords = variant_info["keywords"]
            matched = [kw for kw in keywords if kw in combined_text]

            if not matched:
                continue

            # Calculate match score and confidence
            match_score = len(matched)

            # Confidence based on:
            # - Percentage of variant's keywords matched
            # - Match score (more matches = higher confidence)
            keyword_coverage = len(matched) / max(1, len(keywords))
            match_strength = min(1.0, match_score / 10.0)  # Cap at 10 matches
            confidence = (keyword_coverage * 0.6) + (match_strength * 0.4)

            if confidence < min_confidence:
                continue

            matches.append(
                ClassificationMatch(
                    variant_id=variant_id,
                    service_name=variant_info["service_name"],
                    display_name=variant_info["display_name"],
                    priority=variant_info["priority"],
                    match_score=match_score,
                    matched_keywords=matched,
                    confidence=confidence
                )
            )

        # Sort by priority (lower = higher priority) then by match score
        matches.sort(key=lambda m: (m.priority, -m.match_score, -m.confidence))

        # Limit results
        matches = matches[:max_results]

        logger.info(
            f"Classified slide",
            extra={
                "matches_found": len(matches),
                "best_match": matches[0].variant_id if matches else None,
                "best_confidence": f"{matches[0].confidence:.2%}" if matches else None
            }
        )

        return matches

    def get_variant_keywords(self, variant_id: str) -> Optional[Set[str]]:
        """
        Get keywords for specific variant.

        Args:
            variant_id: Variant identifier

        Returns:
            Set of keywords or None if variant not found
        """
        variant_info = self.variant_keywords.get(variant_id)
        if not variant_info:
            return None
        return variant_info["keywords"]

    def get_all_keywords(self) -> Set[str]:
        """
        Get all keywords across all variants.

        Returns:
            Set of all unique keywords
        """
        all_keywords = set()
        for variant_info in self.variant_keywords.values():
            all_keywords.update(variant_info["keywords"])
        return all_keywords

    def find_variants_by_keyword(self, keyword: str) -> List[str]:
        """
        Find all variants containing a specific keyword.

        Args:
            keyword: Keyword to search for (case-insensitive)

        Returns:
            List of variant IDs containing the keyword
        """
        keyword = keyword.lower()
        matching_variants = []

        for variant_id, variant_info in self.variant_keywords.items():
            if keyword in variant_info["keywords"]:
                matching_variants.append(variant_id)

        # Sort by priority
        matching_variants.sort(
            key=lambda v: self.variant_keywords[v]["priority"]
        )

        return matching_variants

    def get_classification_stats(self) -> Dict[str, Any]:
        """
        Get statistics about classification system.

        Returns:
            Dict with classification statistics
        """
        total_keywords = sum(
            len(v["keywords"]) for v in self.variant_keywords.values()
        )

        service_breakdown = {}
        for variant_id, variant_info in self.variant_keywords.items():
            service_name = variant_info["service_name"]
            if service_name not in service_breakdown:
                service_breakdown[service_name] = {
                    "variant_count": 0,
                    "keyword_count": 0
                }
            service_breakdown[service_name]["variant_count"] += 1
            service_breakdown[service_name]["keyword_count"] += len(variant_info["keywords"])

        return {
            "total_variants": len(self.variant_keywords),
            "total_keywords": total_keywords,
            "avg_keywords_per_variant": total_keywords // max(1, len(self.variant_keywords)),
            "unique_keywords": len(self.get_all_keywords()),
            "services": service_breakdown,
            "priority_range": {
                "min": min(v["priority"] for v in self.variant_keywords.values()),
                "max": max(v["priority"] for v in self.variant_keywords.values())
            }
        }
