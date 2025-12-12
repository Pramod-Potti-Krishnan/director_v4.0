"""
Slide Type Mapper for Director v3.4
=====================================

Maps Director's 13-type taxonomy to Text Service v1.2's 10 slide types.

Director's 13 Types (from SlideTypeClassifier):
  Hero (3):
    - title_slide
    - section_divider
    - closing_slide

  Content (10):
    - impact_quote
    - metrics_grid
    - matrix_2x2
    - grid_3x3
    - styled_table
    - bilateral_comparison
    - sequential_3col
    - hybrid_1_2x2
    - asymmetric_8_4
    - single_column

Text Service v1.2's 10 Slide Types (each with multiple variants):
  - hero (3 variants for title/section/closing)
  - impact_quote (1 variant)
  - metrics (4 variants)
  - matrix (2 variants)
  - grid (9 variants)
  - table (4 variants)
  - comparison (3 variants)
  - sequential (3 variants)
  - hybrid (2 variants)
  - asymmetric (3 variants)
  - single_column (3 variants)
"""

from typing import Dict, Optional
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class SlideTypeMapper:
    """
    Maps Director's 13-type classification to v1.2's 10 slide types.

    This mapping allows the VariantSelector to fetch appropriate variants
    for each classified slide.
    """

    # Mapping from Director's classification → v1.2 slide type
    TAXONOMY_TO_SLIDE_TYPE: Dict[str, str] = {
        # Hero types (L29) → "hero" slide type
        "title_slide": "hero",
        "section_divider": "hero",
        "closing_slide": "hero",

        # Content types (L25) → specific slide types
        "impact_quote": "impact_quote",
        "metrics_grid": "metrics",
        "matrix_2x2": "matrix",
        "grid_3x3": "grid",
        "styled_table": "table",
        "bilateral_comparison": "comparison",
        "sequential_3col": "sequential",
        "hybrid_1_2x2": "hybrid",
        "asymmetric_8_4": "asymmetric",
        "single_column": "single_column"
    }

    # Reverse mapping for validation
    SLIDE_TYPE_TO_TAXONOMIES: Dict[str, list] = {
        "hero": ["title_slide", "section_divider", "closing_slide"],
        "impact_quote": ["impact_quote"],
        "metrics": ["metrics_grid"],
        "matrix": ["matrix_2x2"],
        "grid": ["grid_3x3"],
        "table": ["styled_table"],
        "comparison": ["bilateral_comparison"],
        "sequential": ["sequential_3col"],
        "hybrid": ["hybrid_1_2x2"],
        "asymmetric": ["asymmetric_8_4"],
        "single_column": ["single_column"]
    }

    @classmethod
    def map_to_slide_type(cls, director_classification: str) -> Optional[str]:
        """
        Map Director's 13-type classification to v1.2 slide type.

        Args:
            director_classification: Classification from SlideTypeClassifier
                (e.g., "matrix_2x2", "title_slide", "bilateral_comparison")

        Returns:
            v1.2 slide type (e.g., "matrix", "hero", "comparison")
            None if classification not recognized

        Example:
            >>> SlideTypeMapper.map_to_slide_type("matrix_2x2")
            "matrix"
            >>> SlideTypeMapper.map_to_slide_type("title_slide")
            "hero"
        """
        slide_type = cls.TAXONOMY_TO_SLIDE_TYPE.get(director_classification)

        if slide_type:
            logger.debug(
                f"Mapped '{director_classification}' → v1.2 slide_type '{slide_type}'"
            )
        else:
            logger.warning(
                f"Unknown director classification: '{director_classification}'. "
                f"Valid types: {list(cls.TAXONOMY_TO_SLIDE_TYPE.keys())}"
            )

        return slide_type

    @classmethod
    def is_hero_type(cls, director_classification: str) -> bool:
        """
        Check if classification maps to hero slide type.

        Args:
            director_classification: Director's classification

        Returns:
            True if hero type (title_slide, section_divider, closing_slide)
        """
        slide_type = cls.map_to_slide_type(director_classification)
        return slide_type == "hero"

    @classmethod
    def is_content_type(cls, director_classification: str) -> bool:
        """
        Check if classification maps to content slide type.

        Args:
            director_classification: Director's classification

        Returns:
            True if content type (not hero)
        """
        return not cls.is_hero_type(director_classification)

    @classmethod
    def validate_classification(cls, director_classification: str) -> bool:
        """
        Validate if classification is recognized.

        Args:
            director_classification: Classification to validate

        Returns:
            True if valid, False otherwise
        """
        return director_classification in cls.TAXONOMY_TO_SLIDE_TYPE

    @classmethod
    def get_all_director_types(cls) -> list[str]:
        """Get list of all valid Director classifications."""
        return list(cls.TAXONOMY_TO_SLIDE_TYPE.keys())

    @classmethod
    def get_all_slide_types(cls) -> list[str]:
        """Get list of all v1.2 slide types."""
        return list(set(cls.TAXONOMY_TO_SLIDE_TYPE.values()))

    @classmethod
    def get_default_variant(cls, director_classification: str, layout_id: str) -> str:
        """
        Get default fallback variant when variant catalog is unavailable.

        CRITICAL: Respects L25/L29 layout constraint:
        - L25 (content layouts) → ONLY content variants (never hero)
        - L29 (full-bleed layouts) → ONLY hero variants (never content)

        Used when Text Service v1.2 variant catalog fails to load.
        Returns a safe default variant_id for each slide type, ensuring
        the variant is valid for the specified layout.

        Args:
            director_classification: Director's 13-type classification
            layout_id: Layout identifier - MUST be "L25" or "L29"

        Returns:
            Default variant_id appropriate for the layout
            (e.g., "hero_centered" for L29, "matrix_2x2" for L25)

        Example:
            >>> SlideTypeMapper.get_default_variant("title_slide", "L29")
            "hero_centered"  # Hero variant for L29
            >>> SlideTypeMapper.get_default_variant("title_slide", "L25")
            "single_column_2section"  # Content variant for L25 (title_slide invalid for L25)
            >>> SlideTypeMapper.get_default_variant("matrix_2x2", "L25")
            "matrix_2x2"  # Content variant for L25
        """
        # LAYOUT-AWARE fallback logic
        if layout_id == "L29":
            # L29: Must use hero variant (only 1 option currently)
            variant_id = "hero_centered"
            logger.debug(
                f"L29 layout: Using hero variant '{variant_id}' "
                f"for classification '{director_classification}'"
            )
            return variant_id

        elif layout_id == "L25":
            # L25: Must use content variant (never hero)

            # Default content variants for each classification
            # If classification is a hero type, we fall back to single_column
            # UPDATED 2025-12-01: Using correct Text Service v1.2 variant names
            CONTENT_VARIANTS = {
                # Content types → use base variants (correct v1.2 variant_ids)
                "impact_quote": "impact_quote",
                "metrics_grid": "metrics_3col",
                "matrix_2x2": "matrix_2x2",
                "grid_3x3": "grid_2x2_centered",  # grid_3x3 doesn't exist, use grid_2x2_centered
                "styled_table": "table_2col",
                "bilateral_comparison": "comparison_2col",
                "sequential_3col": "sequential_3col",
                "hybrid_1_2x2": "hybrid_top_2x2",  # Use correct v1.2 variant name
                "asymmetric_8_4": "asymmetric_8_4_3section",  # Use correct v1.2 variant name
                "single_column": "single_column_3section",  # Use correct v1.2 variant name

                # Hero types → fallback to single_column (can't use hero on L25!)
                "title_slide": "single_column_3section",
                "section_divider": "single_column_3section",
                "closing_slide": "single_column_3section",
            }

            variant_id = CONTENT_VARIANTS.get(
                director_classification,
                "single_column_3section"  # Ultimate fallback for L25 (correct v1.2 name)
            )

            logger.debug(
                f"L25 layout: Using content variant '{variant_id}' "
                f"for classification '{director_classification}'"
            )
            return variant_id

        else:
            # Invalid layout_id - log error and fallback safely
            logger.error(f"Invalid layout_id '{layout_id}'. Must be 'L25' or 'L29'. Using L25 fallback.")
            return "single_column_3section"  # Safe default for invalid layout_id (correct v1.2 name)

    @classmethod
    def get_mapping_summary(cls) -> Dict[str, Dict[str, any]]:
        """
        Get summary of type mapping for debugging.

        Returns:
            Dict with mapping statistics and details
        """
        return {
            "total_director_types": len(cls.TAXONOMY_TO_SLIDE_TYPE),
            "total_v1_2_types": len(set(cls.TAXONOMY_TO_SLIDE_TYPE.values())),
            "hero_types": [k for k, v in cls.TAXONOMY_TO_SLIDE_TYPE.items() if v == "hero"],
            "content_types": [k for k, v in cls.TAXONOMY_TO_SLIDE_TYPE.items() if v != "hero"],
            "mapping": cls.TAXONOMY_TO_SLIDE_TYPE
        }


# Convenience function
def map_director_to_v1_2_type(director_classification: str) -> Optional[str]:
    """
    Map Director classification to v1.2 slide type (convenience function).

    Args:
        director_classification: Director's 13-type classification

    Returns:
        v1.2 slide type or None
    """
    return SlideTypeMapper.map_to_slide_type(director_classification)


# Example usage
if __name__ == "__main__":
    print("Slide Type Mapper - Director v3.4 → Text Service v1.2")
    print("=" * 70)

    # Get mapping summary
    summary = SlideTypeMapper.get_mapping_summary()
    print(f"\nMapping Summary:")
    print(f"  Director's 13 types → v1.2's {summary['total_v1_2_types']} slide types")
    print(f"  Hero types: {len(summary['hero_types'])}")
    print(f"  Content types: {len(summary['content_types'])}")

    # Show hero mapping
    print("\nHero Type Mapping (L29):")
    for hero_type in summary['hero_types']:
        v1_2_type = SlideTypeMapper.map_to_slide_type(hero_type)
        print(f"  {hero_type:25s} → {v1_2_type}")

    # Show content mapping
    print("\nContent Type Mapping (L25):")
    for content_type in summary['content_types']:
        v1_2_type = SlideTypeMapper.map_to_slide_type(content_type)
        print(f"  {content_type:25s} → {v1_2_type}")

    # Test validation
    print("\nValidation Tests:")
    test_cases = ["matrix_2x2", "title_slide", "invalid_type", "grid_3x3"]
    for test in test_cases:
        is_valid = SlideTypeMapper.validate_classification(test)
        result = "✅ Valid" if is_valid else "❌ Invalid"
        print(f"  {test:25s} → {result}")

    print("\n" + "=" * 70)
