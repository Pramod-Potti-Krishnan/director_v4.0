"""
Analytics Variant Catalog Loader for Director v3.4
===================================================

Loads and caches the analytics chart type variants from local configuration
and/or Analytics Service API.

The catalog provides:
- 9 Chart.js chart types for L02 layout
- Chart metadata (use cases, data requirements, optimal data points)
- Mapping from chart_id to Analytics Service analytics_type endpoints
- Integration with Director's variant selection system

Author: Director v3.4 Integration Team
Date: November 16, 2025
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from src.utils.logger import setup_logger
from src.clients.analytics_client import AnalyticsClient

logger = setup_logger(__name__)


class AnalyticsVariantCatalog:
    """
    Loads and manages analytics chart type variants.

    Provides two data sources:
    1. Local configuration (config/analytics_variants.json)
    2. Live Analytics Service API (/api/v1/chart-types)

    Strategy:
    - Use local config for offline operation and fast access
    - Optionally sync with Analytics Service API for latest updates
    - Cache results for performance
    """

    def __init__(
        self,
        config_path: Optional[Path] = None,
        analytics_client: Optional[AnalyticsClient] = None
    ):
        """
        Initialize analytics variant catalog.

        Args:
            config_path: Path to analytics_variants.json config file
                        If None, uses default: config/analytics_variants.json
            analytics_client: Optional AnalyticsClient for live API queries
        """
        # Set config path
        if config_path is None:
            # Default to config/analytics_variants.json relative to project root
            project_root = Path(__file__).parent.parent.parent
            config_path = project_root / "config" / "analytics_variants.json"

        self.config_path = config_path
        self.analytics_client = analytics_client
        self.catalog: Optional[Dict[str, Any]] = None
        self._loaded = False

        logger.info(
            f"AnalyticsVariantCatalog initialized",
            extra={"config_path": str(self.config_path)}
        )

    def load_catalog(self, force_reload: bool = False) -> Dict[str, Any]:
        """
        Load analytics variant catalog from local configuration.

        Reads config/analytics_variants.json and caches the result.

        Args:
            force_reload: Force reload even if already cached

        Returns:
            Catalog dict with structure:
            {
                "version": "1.0.0",
                "total_variants": 9,
                "slide_type": "analytics",
                "default_layout": "L02",
                "chart_types": [
                    {
                        "chart_id": "line",
                        "chart_name": "Line Chart",
                        "description": "...",
                        "use_cases": [...],
                        "data_requirements": {...},
                        ...
                    },
                    ...
                ],
                "chart_type_mappings": {
                    "line": "revenue_over_time",
                    ...
                }
            }

        Raises:
            FileNotFoundError: If config file doesn't exist
            json.JSONDecodeError: If config file is invalid JSON
        """
        if self._loaded and not force_reload:
            logger.debug("Using cached analytics variant catalog")
            return self.catalog

        try:
            logger.info(f"Loading analytics variant catalog from {self.config_path}")

            with open(self.config_path, 'r') as f:
                self.catalog = json.load(f)

            self._loaded = True

            total = self.catalog.get("total_variants", 0)
            version = self.catalog.get("version", "unknown")

            logger.info(
                f"✅ Analytics variant catalog loaded: {total} chart types (v{version})",
                extra={"total_variants": total, "version": version}
            )

            return self.catalog

        except FileNotFoundError:
            logger.error(
                f"Analytics variant config file not found: {self.config_path}",
                extra={"config_path": str(self.config_path)}
            )
            raise

        except json.JSONDecodeError as e:
            logger.error(
                f"Invalid JSON in analytics variant config: {str(e)}",
                extra={"config_path": str(self.config_path), "error": str(e)}
            )
            raise

    def get_all_chart_types(self) -> List[Dict[str, Any]]:
        """
        Get all analytics chart types.

        Returns:
            List of chart type definitions (all 9 Chart.js types)

        Example:
            chart_types = catalog.get_all_chart_types()
            for chart in chart_types:
                print(f"{chart['chart_name']}: {chart['description']}")
        """
        if not self._loaded:
            self.load_catalog()

        return self.catalog.get("chart_types", [])

    def get_chart_type_by_id(self, chart_id: str) -> Optional[Dict[str, Any]]:
        """
        Get specific chart type definition by ID.

        Args:
            chart_id: Chart type ID (e.g., "line", "bar_vertical", "pie")

        Returns:
            Chart type definition dict or None if not found

        Example:
            line_chart = catalog.get_chart_type_by_id("line")
            print(line_chart["use_cases"])
        """
        if not self._loaded:
            self.load_catalog()

        chart_types = self.catalog.get("chart_types", [])

        for chart in chart_types:
            if chart.get("chart_id") == chart_id:
                return chart

        logger.warning(
            f"Chart type not found: {chart_id}",
            extra={"chart_id": chart_id}
        )
        return None

    def get_analytics_endpoint(self, chart_id: str) -> Optional[str]:
        """
        Get Analytics Service endpoint (analytics_type) for a chart ID.

        Maps chart_id to the corresponding Analytics Service analytics_type.

        Args:
            chart_id: Chart type ID (e.g., "line", "pie")

        Returns:
            Analytics type endpoint name (e.g., "revenue_over_time", "market_share")
            or None if not found

        Example:
            endpoint = catalog.get_analytics_endpoint("line")
            # Returns: "revenue_over_time"
        """
        if not self._loaded:
            self.load_catalog()

        mappings = self.catalog.get("chart_type_mappings", {})
        endpoint = mappings.get(chart_id)

        if not endpoint:
            logger.warning(
                f"No analytics endpoint mapping for chart_id: {chart_id}",
                extra={"chart_id": chart_id, "available_mappings": list(mappings.keys())}
            )

        return endpoint

    def get_chart_types_for_use_case(self, keyword: str) -> List[Dict[str, Any]]:
        """
        Find chart types matching a use case keyword.

        Searches chart type use_cases, descriptions, and best_for fields.

        Args:
            keyword: Search keyword (e.g., "revenue", "comparison", "trend")

        Returns:
            List of matching chart type definitions

        Example:
            revenue_charts = catalog.get_chart_types_for_use_case("revenue")
            # Returns: [line chart, bar chart, ...]
        """
        if not self._loaded:
            self.load_catalog()

        keyword_lower = keyword.lower()
        matching_charts = []

        for chart in self.catalog.get("chart_types", []):
            # Search in use_cases
            use_cases = chart.get("use_cases", [])
            if any(keyword_lower in use_case.lower() for use_case in use_cases):
                matching_charts.append(chart)
                continue

            # Search in description
            description = chart.get("description", "")
            if keyword_lower in description.lower():
                matching_charts.append(chart)
                continue

            # Search in best_for
            best_for = chart.get("best_for", [])
            if any(keyword_lower in item.lower() for item in best_for):
                matching_charts.append(chart)
                continue

        logger.debug(
            f"Found {len(matching_charts)} chart types for use case: {keyword}",
            extra={"keyword": keyword, "matches": len(matching_charts)}
        )

        return matching_charts

    def get_chart_types_by_data_points(
        self,
        data_point_count: int
    ) -> List[Dict[str, Any]]:
        """
        Get chart types suitable for a given data point count.

        Filters by optimal_data_points range for each chart type.

        Args:
            data_point_count: Number of data points available

        Returns:
            List of chart types that work well with this data point count

        Example:
            # For 5 data points
            suitable_charts = catalog.get_chart_types_by_data_points(5)
            # Returns: line, bar, pie, doughnut (not scatter which needs 10+)
        """
        if not self._loaded:
            self.load_catalog()

        suitable_charts = []

        for chart in self.catalog.get("chart_types", []):
            requirements = chart.get("data_requirements", {})
            min_points = requirements.get("min_data_points", 2)
            max_points = requirements.get("max_data_points", 50)

            # Check if data point count is within min/max range
            if min_points <= data_point_count <= max_points:
                suitable_charts.append(chart)

        logger.debug(
            f"Found {len(suitable_charts)} suitable chart types for {data_point_count} data points",
            extra={"data_points": data_point_count, "matches": len(suitable_charts)}
        )

        return suitable_charts

    def get_recommended_chart_types(
        self,
        data_point_count: int,
        use_case_keyword: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get recommended chart types based on data and use case.

        Combines data point filtering with use case matching.

        Args:
            data_point_count: Number of data points available
            use_case_keyword: Optional use case keyword ("revenue", "comparison", etc.)

        Returns:
            List of recommended chart types, sorted by suitability

        Example:
            # For 6 data points showing revenue trend
            recommended = catalog.get_recommended_chart_types(
                data_point_count=6,
                use_case_keyword="revenue"
            )
            # Returns: [line chart, bar chart] (suitable for 6 points + revenue)
        """
        if not self._loaded:
            self.load_catalog()

        # Start with data point filtering
        suitable_charts = self.get_chart_types_by_data_points(data_point_count)

        # Further filter by use case if provided
        if use_case_keyword:
            use_case_matches = self.get_chart_types_for_use_case(use_case_keyword)
            # Intersection: charts that match both data points AND use case
            chart_ids_use_case = {chart["chart_id"] for chart in use_case_matches}
            suitable_charts = [
                chart for chart in suitable_charts
                if chart["chart_id"] in chart_ids_use_case
            ]

        logger.info(
            f"Recommended {len(suitable_charts)} chart types",
            extra={
                "data_points": data_point_count,
                "use_case": use_case_keyword,
                "recommendations": len(suitable_charts)
            }
        )

        return suitable_charts

    async def sync_with_analytics_service(self) -> Dict[str, Any]:
        """
        Sync local catalog with live Analytics Service API.

        Optionally fetches latest chart types from Analytics Service
        /api/v1/chart-types endpoint to ensure local config is up-to-date.

        Returns:
            Dict containing:
                - local_count: Number of chart types in local config
                - remote_count: Number of chart types from Analytics Service
                - matches: Number of chart types present in both
                - local_only: Chart types only in local config
                - remote_only: Chart types only in Analytics Service

        Raises:
            RuntimeError: If analytics_client is not configured
            httpx.HTTPError: If API call fails

        Example:
            sync_result = await catalog.sync_with_analytics_service()
            if sync_result["remote_only"]:
                print(f"New chart types available: {sync_result['remote_only']}")
        """
        if not self.analytics_client:
            raise RuntimeError(
                "Cannot sync: analytics_client not configured. "
                "Pass AnalyticsClient instance to __init__"
            )

        if not self._loaded:
            self.load_catalog()

        # Fetch from Analytics Service
        remote_catalog = await self.analytics_client.get_available_chart_types(
            layout="L02",
            library="chartjs"
        )

        # Compare local vs remote
        local_chart_ids = {chart["chart_id"] for chart in self.catalog["chart_types"]}
        remote_chart_ids = {chart["id"] for chart in remote_catalog["chart_types"]}

        matches = local_chart_ids & remote_chart_ids
        local_only = local_chart_ids - remote_chart_ids
        remote_only = remote_chart_ids - local_chart_ids

        logger.info(
            "Analytics Service sync complete",
            extra={
                "local_count": len(local_chart_ids),
                "remote_count": len(remote_chart_ids),
                "matches": len(matches),
                "local_only": list(local_only),
                "remote_only": list(remote_only)
            }
        )

        return {
            "local_count": len(local_chart_ids),
            "remote_count": len(remote_chart_ids),
            "matches": len(matches),
            "local_only": list(local_only),
            "remote_only": list(remote_only),
            "remote_catalog": remote_catalog
        }
