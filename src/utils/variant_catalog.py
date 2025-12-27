"""
Variant Catalog Loader for Director v4.0
==========================================

Loads and caches the Gold Standard variants from Text Service v1.2.

GOLD STANDARD VARIANTS (Tested & Approved):
- C1 Variants (34 total): All content slide variants ending in _c1
- I-Series Variants (26 total): Image+text layouts ending in _i1/_i2/_i3/_i4
- H-Series: Dedicated endpoints for hero slides (H1/H2/H3)

UPDATED 2025-12-27: Added Gold Standard constants and validation methods
UPDATED 2025-12-01: Corrected variant names to match Text Service v1.2 backend
"""

import httpx
from typing import Dict, List, Optional, Any
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

# =============================================================================
# GOLD STANDARD VARIANTS - Tested & Approved for Production
# =============================================================================

# C1 Variants (34 total) - All content slides MUST use one of these
GOLD_STANDARD_C1_VARIANTS = [
    # Grid (9)
    "grid_2x2_centered_c1", "grid_2x2_left_c1", "grid_2x2_numbered_c1",
    "grid_2x3_c1", "grid_2x3_left_c1", "grid_2x3_numbered_c1",
    "grid_3x2_c1", "grid_3x2_left_c1", "grid_3x2_numbered_c1",
    # Table + Quote (5)
    "table_2col_c1", "table_3col_c1", "table_4col_c1", "table_5col_c1", "impact_quote_c1",
    # Layout (12)
    "single_column_3section_c1", "single_column_4section_c1", "single_column_5section_c1",
    "asymmetric_8_4_3section_c1", "asymmetric_8_4_4section_c1", "asymmetric_8_4_5section_c1",
    "sequential_3col_c1", "sequential_4col_c1", "sequential_5col_c1",
    "comparison_2col_c1", "comparison_3col_c1", "comparison_4col_c1",
    # Metrics, Matrix, Hybrid (8)
    "metrics_2x2_grid_c1", "metrics_3col_c1", "metrics_3x2_grid_c1", "metrics_4col_c1",
    "matrix_2x2_c1", "matrix_2x3_c1", "hybrid_left_2x2_c1", "hybrid_top_2x2_c1"
]

# I-Series Variants (26 total) - Image + text layouts
GOLD_STANDARD_I_SERIES_VARIANTS = [
    # Single Column (12)
    "single_column_3section_i1", "single_column_3section_i2", "single_column_3section_i3", "single_column_3section_i4",
    "single_column_4section_i1", "single_column_4section_i2", "single_column_4section_i3", "single_column_4section_i4",
    "single_column_5section_i1", "single_column_5section_i2", "single_column_5section_i3", "single_column_5section_i4",
    # Comparison (8)
    "comparison_2col_i1", "comparison_2col_i2", "comparison_2col_i3", "comparison_2col_i4",
    "comparison_3col_i1", "comparison_3col_i2", "comparison_3col_i3", "comparison_3col_i4",
    # Sequential (6) - Note: 4col only available for I3/I4 (narrow layouts)
    "sequential_3col_i1", "sequential_3col_i2", "sequential_3col_i3", "sequential_3col_i4",
    "sequential_4col_i3", "sequential_4col_i4"
]

# Convenience functions for validation
def is_gold_standard_c1(variant_id: str) -> bool:
    """Check if variant is a Gold Standard C1 variant."""
    return variant_id in GOLD_STANDARD_C1_VARIANTS

def is_gold_standard_iseries(variant_id: str) -> bool:
    """Check if variant is a Gold Standard I-series variant."""
    return variant_id in GOLD_STANDARD_I_SERIES_VARIANTS

def is_gold_standard(variant_id: str) -> bool:
    """Check if variant is any Gold Standard variant (C1 or I-series)."""
    return is_gold_standard_c1(variant_id) or is_gold_standard_iseries(variant_id)


# =============================================================================
# SERIES TYPE DETECTION - Unified variant_id suffix parsing
# =============================================================================
# The variant_id suffix determines which series and endpoint to use:
#   - _c1 = C1 series → /v1.2/generate
#   - _i1/_i2/_i3/_i4 = I-series → /v1.2/iseries/{I1|I2|I3|I4}
#   - _v1 = V-series (future) → (future endpoint)
#   - _s1 = S-series (future) → (future endpoint)

from typing import Tuple

def get_series_type(variant_id: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Extract series type and layout position from variant_id suffix.

    This is the CORE utility for the unified variant system. The variant_id
    suffix determines which API endpoint and parameters to use.

    Args:
        variant_id: Full variant identifier (e.g., "grid_2x2_centered_c1", "sequential_3col_i1")

    Returns:
        Tuple of (series_type, layout_position):
        - ("C1", None) for C1 content variants
        - ("I", "1"|"2"|"3"|"4") for I-series image+text variants
        - ("V", "1") for future V-series
        - ("S", "1") for future S-series
        - (None, None) if suffix not recognized

    Examples:
        >>> get_series_type("grid_2x2_centered_c1")
        ("C1", None)
        >>> get_series_type("sequential_3col_i1")
        ("I", "1")
        >>> get_series_type("comparison_2col_i4")
        ("I", "4")
        >>> get_series_type("unknown_variant")
        (None, None)
    """
    if not variant_id:
        return (None, None)

    # Check I-series suffixes first (i1, i2, i3, i4)
    for i in ['1', '2', '3', '4']:
        if variant_id.endswith(f'_i{i}'):
            return ('I', i)

    # Check C1 suffix
    if variant_id.endswith('_c1'):
        return ('C1', None)

    # Future: V-series, S-series
    if variant_id.endswith('_v1'):
        return ('V', '1')
    if variant_id.endswith('_s1'):
        return ('S', '1')

    return (None, None)


def is_iseries_variant(variant_id: str) -> bool:
    """
    Check if variant is an I-series (image+text) variant.

    I-series variants have suffixes _i1, _i2, _i3, or _i4 and require
    the /v1.2/iseries/{layout_type} endpoint with content_variant parameter.

    Args:
        variant_id: Full variant identifier

    Returns:
        True if variant is I-series, False otherwise

    Example:
        >>> is_iseries_variant("sequential_3col_i1")
        True
        >>> is_iseries_variant("grid_2x2_centered_c1")
        False
    """
    series, _ = get_series_type(variant_id)
    return series == 'I'


def is_c1_variant(variant_id: str) -> bool:
    """
    Check if variant is a C1 (content-only) variant.

    C1 variants have suffix _c1 and use the /v1.2/generate endpoint.

    Args:
        variant_id: Full variant identifier

    Returns:
        True if variant is C1 series, False otherwise

    Example:
        >>> is_c1_variant("grid_2x2_centered_c1")
        True
        >>> is_c1_variant("sequential_3col_i1")
        False
    """
    series, _ = get_series_type(variant_id)
    return series == 'C1'


def get_iseries_layout(variant_id: str) -> Optional[str]:
    """
    Get I-series layout type (I1/I2/I3/I4) from variant_id.

    This extracts the layout position needed for the /v1.2/iseries/{layout_type}
    API endpoint.

    Args:
        variant_id: Full variant identifier (e.g., "sequential_3col_i1")

    Returns:
        Layout type string ("I1", "I2", "I3", or "I4") if I-series,
        None otherwise

    Example:
        >>> get_iseries_layout("sequential_3col_i1")
        "I1"
        >>> get_iseries_layout("comparison_2col_i4")
        "I4"
        >>> get_iseries_layout("grid_2x2_centered_c1")
        None
    """
    series, position = get_series_type(variant_id)
    if series == 'I' and position:
        return f'I{position}'
    return None


def get_content_variant_base(variant_id: str) -> Optional[str]:
    """
    Get the content variant base name (without series suffix) for I-series variants.

    For I-series variants, this returns what would be passed as content_variant
    to the Text Service. The base determines the template layout.

    Args:
        variant_id: Full variant identifier (e.g., "sequential_3col_i1")

    Returns:
        Base variant name without suffix if I-series, the original variant_id otherwise

    Example:
        >>> get_content_variant_base("sequential_3col_i1")
        "sequential_3col"
        >>> get_content_variant_base("single_column_3section_i4")
        "single_column_3section"
    """
    if not variant_id:
        return None

    # For I-series, strip the _iN suffix to get the base
    for i in ['1', '2', '3', '4']:
        if variant_id.endswith(f'_i{i}'):
            return variant_id[:-3]  # Remove "_i1", "_i2", etc.

    # For C1 variants, the full variant_id is used
    return variant_id


class VariantCatalog:
    """
    Loads and caches variant catalog from Text Service v1.2.

    Provides methods to:
    - Load all 34 variants from /v1.2/variants endpoint
    - Query variants by slide type
    - Get variant details
    - Cache for performance
    """

    def __init__(self, text_service_url: str, timeout: int = 30):
        """
        Initialize variant catalog.

        Args:
            text_service_url: Text Service v1.2 base URL
            timeout: HTTP request timeout in seconds
        """
        self.base_url = text_service_url.rstrip("/")
        self.timeout = timeout
        self.catalog: Optional[Dict[str, Any]] = None
        self._loaded = False

        logger.info(f"VariantCatalog initialized for {self.base_url}")

    async def load_catalog(self, force_reload: bool = False) -> Dict[str, Any]:
        """
        Load variant catalog from Text Service v1.2.

        Fetches from GET /v1.2/variants endpoint and caches the result.

        Args:
            force_reload: Force reload even if already cached

        Returns:
            Catalog dict with structure:
            {
                "total_variants": 34,
                "slide_types": {
                    "matrix": [
                        {"variant_id": "matrix_2x2", "slide_type": "matrix", ...},
                        {"variant_id": "matrix_2x3", "slide_type": "matrix", ...}
                    ],
                    "grid": [...],
                    ...
                }
            }

        Raises:
            Exception: If API call fails
        """
        if self._loaded and not force_reload:
            logger.debug("Using cached variant catalog")
            return self.catalog

        endpoint = f"{self.base_url}/v1.2/variants"

        try:
            logger.info(f"Loading variant catalog from {endpoint}")

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(endpoint)
                response.raise_for_status()

                self.catalog = response.json()
                self._loaded = True

                total = self.catalog.get("total_variants", 0)
                types_count = len(self.catalog.get("slide_types", {}))

                logger.info(
                    f"✅ Variant catalog loaded: {total} variants across {types_count} slide types"
                )

                return self.catalog

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP {e.response.status_code} error loading catalog: {e.response.text}")
            raise Exception(f"Failed to load variant catalog: HTTP {e.response.status_code}")

        except httpx.RequestError as e:
            logger.error(f"Request error loading catalog: {str(e)}")
            raise Exception(f"Failed to load variant catalog: {str(e)}")

        except Exception as e:
            logger.error(f"Unexpected error loading catalog: {str(e)}")
            raise

    def get_variants_for_slide_type(self, slide_type: str) -> List[str]:
        """
        Get all variant IDs for a specific slide type.

        Args:
            slide_type: Slide type (e.g., "matrix", "grid", "comparison")

        Returns:
            List of variant_ids (e.g., ["matrix_2x2", "matrix_2x3"])
            Empty list if slide type not found

        Raises:
            RuntimeError: If catalog not loaded

        Example:
            >>> catalog.get_variants_for_slide_type("matrix")
            ["matrix_2x2", "matrix_2x3"]
        """
        if not self._loaded:
            raise RuntimeError(
                "Variant catalog not loaded. Call await load_catalog() first."
            )

        slide_types = self.catalog.get("slide_types", {})
        variants = slide_types.get(slide_type, [])

        variant_ids = [v["variant_id"] for v in variants]

        if variant_ids:
            logger.debug(
                f"Found {len(variant_ids)} variants for slide_type '{slide_type}': {variant_ids}"
            )
        else:
            logger.warning(f"No variants found for slide_type '{slide_type}'")

        return variant_ids

    def get_variant_details(self, variant_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific variant.

        Args:
            variant_id: Variant identifier (e.g., "matrix_2x2")

        Returns:
            Variant details dict or None if not found
            {
                "variant_id": "matrix_2x2",
                "slide_type": "matrix",
                "description": "2x2 matrix layout",
                "layout": "2x2 grid (4 boxes)"
            }

        Raises:
            RuntimeError: If catalog not loaded
        """
        if not self._loaded:
            raise RuntimeError(
                "Variant catalog not loaded. Call await load_catalog() first."
            )

        # Search through all slide types
        for slide_type, variants in self.catalog.get("slide_types", {}).items():
            for variant in variants:
                if variant["variant_id"] == variant_id:
                    logger.debug(f"Found variant details for '{variant_id}'")
                    return variant

        logger.warning(f"Variant '{variant_id}' not found in catalog")
        return None

    def get_all_slide_types(self) -> List[str]:
        """
        Get list of all available slide types.

        Returns:
            List of slide type names (e.g., ["matrix", "grid", "comparison", ...])

        Raises:
            RuntimeError: If catalog not loaded
        """
        if not self._loaded:
            raise RuntimeError(
                "Variant catalog not loaded. Call await load_catalog() first."
            )

        return list(self.catalog.get("slide_types", {}).keys())

    def get_total_variants(self) -> int:
        """
        Get total number of variants in catalog.

        Returns:
            Total variant count (should be 34)

        Raises:
            RuntimeError: If catalog not loaded
        """
        if not self._loaded:
            raise RuntimeError(
                "Variant catalog not loaded. Call await load_catalog() first."
            )

        return self.catalog.get("total_variants", 0)

    def is_loaded(self) -> bool:
        """Check if catalog has been loaded."""
        return self._loaded

    def validate_variant_id(self, variant_id: str) -> bool:
        """
        Validate if a variant_id exists in the catalog.

        Args:
            variant_id: Variant ID to validate

        Returns:
            True if variant exists, False otherwise
        """
        if not self._loaded:
            return False

        return self.get_variant_details(variant_id) is not None

    def is_hero_variant(self, variant_id: str) -> bool:
        """
        Check if a variant is a hero variant (for L29 layouts only).

        Hero variants belong to the "hero" slide_type and should ONLY be used
        with L29 (full-bleed) layouts. They cannot be used with L25 (content) layouts.

        Args:
            variant_id: Variant ID to check (e.g., "hero_centered", "matrix_2x2")

        Returns:
            True if variant is a hero type (L29 only), False if content type (L25 only)

        Raises:
            RuntimeError: If catalog not loaded
        """
        if not self._loaded:
            raise RuntimeError(
                "Variant catalog not loaded. Call await load_catalog() first."
            )

        # Get variant details
        details = self.get_variant_details(variant_id)

        if details is None:
            logger.warning(f"Variant '{variant_id}' not found, assuming non-hero (content) variant")
            return False

        # Check if slide_type is "hero"
        slide_type = details.get("slide_type", "")
        is_hero = slide_type == "hero"

        logger.debug(
            f"Variant '{variant_id}' is {'HERO (L29 only)' if is_hero else 'CONTENT (L25 only)'}"
        )

        return is_hero


# Convenience function for loading catalog
async def load_variant_catalog(text_service_url: str) -> VariantCatalog:
    """
    Load and return variant catalog (convenience function).

    Args:
        text_service_url: Text Service v1.2 base URL

    Returns:
        Loaded VariantCatalog instance

    Example:
        >>> catalog = await load_variant_catalog("https://text-service.railway.app")
        >>> variants = catalog.get_variants_for_slide_type("matrix")
    """
    catalog = VariantCatalog(text_service_url)
    await catalog.load_catalog()
    return catalog


# Example usage
if __name__ == "__main__":
    import asyncio

    async def test_catalog():
        print("Variant Catalog Loader Test")
        print("=" * 70)

        # Initialize catalog
        catalog = VariantCatalog("https://web-production-5daf.up.railway.app")

        # Load from API
        print("\nLoading catalog from Text Service v1.2...")
        await catalog.load_catalog()

        print(f"✅ Total variants: {catalog.get_total_variants()}")
        print(f"✅ Slide types: {', '.join(catalog.get_all_slide_types())}")

        # Test variant queries
        print("\nExample Queries:")
        for slide_type in ["matrix", "grid", "comparison"]:
            variants = catalog.get_variants_for_slide_type(slide_type)
            print(f"  {slide_type}: {len(variants)} variants → {variants}")

        # Test variant details
        print("\nVariant Details:")
        details = catalog.get_variant_details("matrix_2x2")
        if details:
            print(f"  variant_id: {details['variant_id']}")
            print(f"  slide_type: {details['slide_type']}")
            print(f"  description: {details.get('description', 'N/A')}")

        print("\n" + "=" * 70)
        print("Test complete!")

    asyncio.run(test_catalog())
