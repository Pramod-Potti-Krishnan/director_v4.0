"""
Variant Catalog Loader for Director v3.4
==========================================

Loads and caches the 34 platinum variants from Text Service v1.2.

The catalog maps slide types to their available variants:
- matrix: 2 variants (matrix_2x2, matrix_2x3)
- grid: 9 variants (grid_2x3, grid_3x2, grid_2x2_centered, grid_2x3_left, grid_3x2_left,
                    grid_2x2_left, grid_2x3_numbered, grid_3x2_numbered, grid_2x2_numbered)
- comparison: 3 variants (comparison_2col, comparison_3col, comparison_4col)
- sequential: 3 variants (sequential_3col, sequential_4col, sequential_5col)
- asymmetric: 3 variants (asymmetric_8_4_3section, asymmetric_8_4_4section, asymmetric_8_4_5section)
- hybrid: 2 variants (hybrid_top_2x2, hybrid_left_2x2)
- metrics: 4 variants (metrics_3col, metrics_4col, metrics_3x2_grid, metrics_2x2_grid)
- impact_quote: 1 variant (impact_quote)
- table: 4 variants (table_2col, table_3col, table_4col, table_5col)
- single_column: 3 variants (single_column_3section, single_column_4section, single_column_5section)

UPDATED 2025-12-01: Corrected variant names to match Text Service v1.2 backend
"""

import httpx
from typing import Dict, List, Optional, Any
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


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
