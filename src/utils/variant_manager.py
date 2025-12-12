"""
Unified Variant Manager for Director v3.4
==========================================

Manages both text variants and analytics variants in a unified interface.

Integration Strategy:
- Text variants: From Text Service v1.2 (34 platinum variants)
- Analytics variants: From Analytics Service v3.1.2 (9 Chart.js chart types)

The manager provides unified variant selection that routes to the appropriate
catalog based on slide type.

Usage:
    manager = VariantManager(
        variant_catalog=text_catalog,
        analytics_catalog=analytics_catalog
    )

    # Select text variant
    variant_id = manager.select_variant("matrix_2x2", "L25")
    # Returns: "matrix_2x3" (random text variant)

    # Select analytics variant
    variant_id = manager.select_variant("analytics", "L02")
    # Returns: "line" or "bar_vertical" (random chart type)

Author: Director v3.4 Integration Team
Date: November 16, 2025
"""

import random
from typing import Optional, List
from src.utils.variant_catalog import VariantCatalog
from src.utils.analytics_variant_catalog import AnalyticsVariantCatalog
from src.utils.slide_type_mapper import SlideTypeMapper
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class VariantManager:
    """
    Unified variant manager for both text and analytics variants.

    Routes variant selection to appropriate catalog based on slide type:
    - Text slides (matrix, grid, etc.) → VariantCatalog (Text Service v1.2)
    - Analytics slides → AnalyticsVariantCatalog (local config + Analytics API)
    """

    def __init__(
        self,
        variant_catalog: Optional[VariantCatalog] = None,
        analytics_catalog: Optional[AnalyticsVariantCatalog] = None,
        random_seed: Optional[int] = None
    ):
        """
        Initialize variant manager with both catalogs.

        Args:
            variant_catalog: Text variant catalog (optional)
            analytics_catalog: Analytics variant catalog (optional)
            random_seed: Optional seed for reproducible randomization (testing)
        """
        self.variant_catalog = variant_catalog
        self.analytics_catalog = analytics_catalog
        self.mapper = SlideTypeMapper()

        # Set random seed if provided (for testing/reproducibility)
        if random_seed is not None:
            random.seed(random_seed)
            logger.info(f"Random seed set to {random_seed} for reproducible selection")

        # Validation warnings
        if not variant_catalog:
            logger.warning("VariantCatalog not provided - text variant selection will fail")
        if not analytics_catalog:
            logger.warning("AnalyticsVariantCatalog not provided - analytics variant selection will fail")

        logger.info(
            f"VariantManager initialized (text: {bool(variant_catalog)}, analytics: {bool(analytics_catalog)})"
        )

    def is_analytics_slide(self, director_classification: str) -> bool:
        """
        Check if classification is for analytics slide.

        Args:
            director_classification: Director's classification

        Returns:
            True if analytics slide, False otherwise
        """
        return director_classification == "analytics"

    def select_variant(
        self,
        director_classification: str,
        layout_id: str,
        context: Optional[str] = None,
        data_point_count: Optional[int] = None,
        use_case_keyword: Optional[str] = None
    ) -> Optional[str]:
        """
        Select variant for a Director classification using appropriate catalog.

        Routes to:
        - AnalyticsVariantCatalog for "analytics" classification
        - VariantCatalog for all other classifications

        Args:
            director_classification: Director's classification (e.g., "analytics", "matrix_2x2")
            layout_id: Layout identifier (L02 for analytics, L25/L29 for text)
            context: Optional context hint
            data_point_count: For analytics - number of data points (helps select chart type)
            use_case_keyword: For analytics - use case keyword (e.g., "revenue", "comparison")

        Returns:
            Selected variant_id:
            - For analytics: chart_id (e.g., "line", "bar_vertical", "pie")
            - For text: variant_id (e.g., "matrix_2x2", "grid_3x3")
            Returns None if no valid variants found

        Example:
            >>> manager.select_variant("analytics", "L02", data_point_count=6, use_case_keyword="revenue")
            "line"  # Analytics chart type

            >>> manager.select_variant("matrix_2x2", "L25")
            "matrix_2x3"  # Text variant
        """
        logger.debug(
            f"Selecting variant for '{director_classification}' with layout_id='{layout_id}'"
        )

        # Route 1: Analytics slide
        if self.is_analytics_slide(director_classification):
            return self._select_analytics_variant(
                layout_id=layout_id,
                data_point_count=data_point_count,
                use_case_keyword=use_case_keyword
            )

        # Route 2: Text slide
        else:
            return self._select_text_variant(
                director_classification=director_classification,
                layout_id=layout_id,
                context=context
            )

    def _select_analytics_variant(
        self,
        layout_id: str,
        data_point_count: Optional[int] = None,
        use_case_keyword: Optional[str] = None
    ) -> Optional[str]:
        """
        Select analytics chart type using AnalyticsVariantCatalog.

        Args:
            layout_id: Layout identifier (should be L02 for analytics)
            data_point_count: Number of data points (helps select suitable chart)
            use_case_keyword: Use case keyword (e.g., "revenue", "comparison")

        Returns:
            chart_id (e.g., "line", "bar_vertical", "pie") or None
        """
        if not self.analytics_catalog:
            logger.error("Analytics catalog not available - cannot select analytics variant")
            return None

        # Validate layout (analytics currently only supports L02)
        if layout_id != "L02":
            logger.warning(
                f"Analytics slides currently only support L02 layout, got '{layout_id}'. "
                f"Proceeding with L02 assumption."
            )

        try:
            # If data_point_count and use_case provided, get recommendations
            if data_point_count and use_case_keyword:
                chart_types = self.analytics_catalog.get_recommended_chart_types(
                    data_point_count=data_point_count,
                    use_case_keyword=use_case_keyword
                )
                logger.debug(
                    f"Found {len(chart_types)} recommended chart types for "
                    f"{data_point_count} points + '{use_case_keyword}' use case"
                )

            # If only data_point_count, filter by data points
            elif data_point_count:
                chart_types = self.analytics_catalog.get_chart_types_by_data_points(
                    data_point_count=data_point_count
                )
                logger.debug(
                    f"Found {len(chart_types)} chart types suitable for {data_point_count} data points"
                )

            # If only use_case_keyword, filter by use case
            elif use_case_keyword:
                chart_types = self.analytics_catalog.get_chart_types_for_use_case(
                    keyword=use_case_keyword
                )
                logger.debug(
                    f"Found {len(chart_types)} chart types for use case '{use_case_keyword}'"
                )

            # No filters - get all chart types
            else:
                chart_types = self.analytics_catalog.get_all_chart_types()
                logger.debug(f"Using all {len(chart_types)} available chart types")

            # Random selection from matching chart types
            if chart_types:
                selected_chart = random.choice(chart_types)
                chart_id = selected_chart["chart_id"]

                logger.info(
                    f"✅ Selected analytics chart '{chart_id}' ({selected_chart['chart_name']}) "
                    f"from {len(chart_types)} options"
                )

                return chart_id
            else:
                logger.error("No analytics chart types found matching criteria")
                return None

        except Exception as e:
            logger.error(f"Error selecting analytics variant: {str(e)}")
            return None

    def _select_text_variant(
        self,
        director_classification: str,
        layout_id: str,
        context: Optional[str] = None
    ) -> Optional[str]:
        """
        Select text variant using VariantCatalog.

        Args:
            director_classification: Director's classification
            layout_id: Layout identifier (L25 or L29)
            context: Optional context hint

        Returns:
            variant_id (e.g., "matrix_2x2", "grid_3x3") or None
        """
        if not self.variant_catalog:
            logger.error("Variant catalog not available - cannot select text variant")
            return None

        # Validate layout
        if layout_id not in ["L25", "L29"]:
            logger.error(f"Invalid layout_id '{layout_id}'. Must be 'L25' or 'L29'")
            return None

        # Map to v1.2 slide type
        slide_type = self.mapper.map_to_slide_type(director_classification)
        if not slide_type:
            logger.error(
                f"Cannot map '{director_classification}' to v1.2 slide type. "
                f"Valid types: {self.mapper.get_all_director_types()}"
            )
            return None

        # Get available variants
        variants = self.variant_catalog.get_variants_for_slide_type(slide_type)
        if not variants:
            logger.error(
                f"No variants found for slide_type '{slide_type}' "
                f"(mapped from '{director_classification}')"
            )
            return None

        # Filter variants by layout constraint
        valid_variants = []
        for variant_id in variants:
            is_hero = self.variant_catalog.is_hero_variant(variant_id)

            # L25: Only content variants (not hero)
            if layout_id == "L25" and not is_hero:
                valid_variants.append(variant_id)
                logger.debug(f"✅ Variant '{variant_id}' valid for L25 layout")

            # L29: Only hero variants
            elif layout_id == "L29" and is_hero:
                valid_variants.append(variant_id)
                logger.debug(f"✅ Variant '{variant_id}' valid for L29 layout")

            else:
                logger.debug(
                    f"❌ Filtering out variant '{variant_id}' for {layout_id} layout "
                    f"(is_hero: {is_hero})"
                )

        # Check if any valid variants remain
        if not valid_variants:
            logger.error(
                f"⚠️  No valid variants for '{director_classification}' with layout_id='{layout_id}'. "
                f"Original variants ({len(variants)}): {variants}. "
                f"All filtered out due to layout constraint."
            )
            return None

        # Random selection from valid variants
        selected_variant = random.choice(valid_variants)

        logger.info(
            f"✅ Selected text variant '{selected_variant}' from {len(valid_variants)} valid variants "
            f"for '{director_classification}' (layout: {layout_id}, slide_type: '{slide_type}')"
        )
        logger.debug(f"Valid variants after layout filter: {valid_variants}")

        return selected_variant

    def get_available_variants(
        self,
        director_classification: str,
        layout_id: Optional[str] = None
    ) -> List[str]:
        """
        Get list of all available variant_ids for a classification.

        Args:
            director_classification: Director's classification
            layout_id: Optional layout filter ("L02" for analytics, "L25"/"L29" for text)

        Returns:
            List of variant_ids (empty if none)
            - For analytics: list of chart_ids (e.g., ["line", "bar_vertical", "pie"])
            - For text: list of variant_ids (e.g., ["matrix_2x2", "matrix_2x3"])
        """
        # Route 1: Analytics slide
        if self.is_analytics_slide(director_classification):
            if not self.analytics_catalog:
                return []

            chart_types = self.analytics_catalog.get_all_chart_types()
            return [chart["chart_id"] for chart in chart_types]

        # Route 2: Text slide
        else:
            if not self.variant_catalog:
                return []

            slide_type = self.mapper.map_to_slide_type(director_classification)
            if not slide_type:
                return []

            variants = self.variant_catalog.get_variants_for_slide_type(slide_type)

            # Filter by layout if provided
            if layout_id is not None:
                valid_variants = []
                for variant_id in variants:
                    is_hero = self.variant_catalog.is_hero_variant(variant_id)

                    # L25: Only content variants
                    if layout_id == "L25" and not is_hero:
                        valid_variants.append(variant_id)

                    # L29: Only hero variants
                    elif layout_id == "L29" and is_hero:
                        valid_variants.append(variant_id)

                return valid_variants

            return variants

    def get_variant_count(self, director_classification: str) -> int:
        """
        Get number of available variants for a classification.

        Args:
            director_classification: Director's classification

        Returns:
            Number of available variants (0 if none)
        """
        return len(self.get_available_variants(director_classification))

    def validate_variant_selection(
        self,
        director_classification: str,
        variant_id: str
    ) -> bool:
        """
        Validate if a variant_id is valid for a classification.

        Args:
            director_classification: Director's classification
            variant_id: Variant ID to validate

        Returns:
            True if valid pairing, False otherwise
        """
        available = self.get_available_variants(director_classification)
        is_valid = variant_id in available

        if not is_valid:
            logger.warning(
                f"Invalid variant '{variant_id}' for '{director_classification}'. "
                f"Valid options: {available}"
            )

        return is_valid


# Convenience function
async def create_variant_manager(
    text_service_url: str,
    analytics_catalog: Optional[AnalyticsVariantCatalog] = None
) -> VariantManager:
    """
    Create and initialize variant manager with both catalogs.

    Args:
        text_service_url: Text Service v1.2 URL
        analytics_catalog: Optional pre-loaded analytics catalog

    Returns:
        Initialized VariantManager

    Example:
        >>> manager = await create_variant_manager(
        ...     text_service_url="https://text-service.railway.app",
        ...     analytics_catalog=analytics_catalog
        ... )
        >>> variant = manager.select_variant("analytics", "L02")
    """
    # Load text variant catalog
    from src.utils.variant_catalog import load_variant_catalog

    text_catalog = await load_variant_catalog(text_service_url)

    # Create manager with both catalogs
    manager = VariantManager(
        variant_catalog=text_catalog,
        analytics_catalog=analytics_catalog
    )

    return manager
