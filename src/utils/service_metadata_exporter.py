"""
Service Metadata Exporter

Utilities for content generation services to export their variant metadata
in a format compatible with the unified variant registry.

This allows services to:
1. Generate their own variant definitions programmatically
2. Export metadata for Director integration
3. Validate their own variant configurations
4. Provide schema information for validation

Version: 1.0.0
Created: 2025-11-29
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import json
from pydantic import BaseModel, Field


class VariantMetadata(BaseModel):
    """
    Metadata for a single variant that a service provides.

    This model matches the unified registry variant schema.
    """
    variant_id: str = Field(..., description="Unique variant identifier")
    display_name: str = Field(..., description="Human-readable variant name")
    description: str = Field(..., description="Variant purpose and use case")
    status: str = Field("production", description="Variant status (production, beta, deprecated)")
    endpoint: str = Field(..., description="Service endpoint for this variant")
    layout_id: Optional[str] = Field(None, description="Associated layout ID (if applicable)")

    # Classification keywords
    keywords: List[str] = Field(..., min_length=5, description="Keywords for classification (min 5)")
    priority: int = Field(5, ge=1, le=10, description="Classification priority (1=highest, 10=lowest)")

    # LLM guidance
    use_cases: List[str] = Field(default_factory=list, description="Common use cases")
    best_for: Optional[str] = Field(None, description="What this variant is best for")
    avoid_when: Optional[str] = Field(None, description="When to avoid this variant")

    # Schema information
    required_fields: List[str] = Field(default_factory=list, description="Required input fields")
    optional_fields: List[str] = Field(default_factory=list, description="Optional input fields")
    output_format: str = Field("html", description="Output format (html, json, svg, etc.)")

    class Config:
        json_schema_extra = {
            "example": {
                "variant_id": "pie_chart",
                "display_name": "Pie Chart",
                "description": "Circular chart showing proportional data",
                "status": "production",
                "endpoint": "/v3/charts/pie",
                "layout_id": "L01",
                "keywords": ["pie", "donut", "chart", "percentage", "proportion"],
                "priority": 2,
                "use_cases": ["Market share analysis", "Budget breakdown"],
                "best_for": "Showing parts of a whole (3-7 segments)",
                "avoid_when": "More than 7 categories or comparing trends",
                "required_fields": ["data", "title"],
                "optional_fields": ["colors", "show_legend"],
                "output_format": "html"
            }
        }


class ServiceMetadata(BaseModel):
    """
    Complete metadata for a content generation service.

    Contains all variants the service provides.
    """
    service_name: str = Field(..., description="Unique service name (e.g., 'analytics_service_v3')")
    service_version: str = Field(..., description="Service version")
    service_type: str = Field(..., description="Service type (template_based, llm_generated, data_visualization)")
    base_url: str = Field(..., description="Service base URL")

    # Service capabilities
    supports_batch: bool = Field(False, description="Whether service supports batch processing")
    supports_streaming: bool = Field(False, description="Whether service supports streaming")
    authentication_required: bool = Field(False, description="Whether authentication is required")

    # Variants
    variants: List[VariantMetadata] = Field(..., description="All variants this service provides")

    # Metadata
    last_updated: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    maintainer: Optional[str] = Field(None, description="Service maintainer contact")
    documentation_url: Optional[str] = Field(None, description="Link to service documentation")

    class Config:
        json_schema_extra = {
            "example": {
                "service_name": "analytics_service_v3",
                "service_version": "3.0.0",
                "service_type": "data_visualization",
                "base_url": "https://analytics-v30-production.up.railway.app",
                "supports_batch": True,
                "supports_streaming": False,
                "authentication_required": False,
                "variants": [],  # Would contain VariantMetadata objects
                "last_updated": "2025-11-29T12:00:00",
                "maintainer": "analytics-team@example.com",
                "documentation_url": "https://docs.example.com/analytics-v3"
            }
        }


class ServiceMetadataExporter:
    """
    Exporter for generating service metadata in unified registry format.

    Usage:
        exporter = ServiceMetadataExporter(
            service_name="analytics_service_v3",
            service_version="3.0.0",
            service_type="data_visualization",
            base_url="https://analytics-v30-production.up.railway.app"
        )

        # Add variants
        exporter.add_variant(
            variant_id="pie_chart",
            display_name="Pie Chart",
            description="Circular chart showing proportional data",
            endpoint="/v3/charts/pie",
            keywords=["pie", "donut", "chart", "percentage", "proportion"],
            layout_id="L01"
        )

        # Export to registry format
        registry_section = exporter.export_to_registry_format()

        # Or export to JSON file
        exporter.export_to_file("service_metadata.json")
    """

    def __init__(
        self,
        service_name: str,
        service_version: str,
        service_type: str,
        base_url: str,
        supports_batch: bool = False,
        supports_streaming: bool = False,
        authentication_required: bool = False,
        maintainer: Optional[str] = None,
        documentation_url: Optional[str] = None
    ):
        """
        Initialize service metadata exporter.

        Args:
            service_name: Unique service identifier
            service_version: Service version (semantic versioning)
            service_type: Service type (template_based, llm_generated, data_visualization)
            base_url: Service base URL
            supports_batch: Whether service supports batch processing
            supports_streaming: Whether service supports streaming
            authentication_required: Whether authentication is required
            maintainer: Service maintainer contact
            documentation_url: Link to service documentation
        """
        self.metadata = ServiceMetadata(
            service_name=service_name,
            service_version=service_version,
            service_type=service_type,
            base_url=base_url,
            supports_batch=supports_batch,
            supports_streaming=supports_streaming,
            authentication_required=authentication_required,
            maintainer=maintainer,
            documentation_url=documentation_url,
            variants=[]
        )

    def add_variant(
        self,
        variant_id: str,
        display_name: str,
        description: str,
        endpoint: str,
        keywords: List[str],
        priority: int = 5,
        layout_id: Optional[str] = None,
        status: str = "production",
        use_cases: Optional[List[str]] = None,
        best_for: Optional[str] = None,
        avoid_when: Optional[str] = None,
        required_fields: Optional[List[str]] = None,
        optional_fields: Optional[List[str]] = None,
        output_format: str = "html"
    ) -> "ServiceMetadataExporter":
        """
        Add a variant to the service metadata.

        Args:
            variant_id: Unique variant identifier
            display_name: Human-readable variant name
            description: Variant purpose and use case
            endpoint: Service endpoint for this variant
            keywords: Keywords for classification (minimum 5)
            priority: Classification priority (1=highest, 10=lowest)
            layout_id: Associated layout ID (if applicable)
            status: Variant status (production, beta, deprecated)
            use_cases: Common use cases for this variant
            best_for: What this variant is best for
            avoid_when: When to avoid this variant
            required_fields: Required input fields
            optional_fields: Optional input fields
            output_format: Output format (html, json, svg, etc.)

        Returns:
            Self for method chaining
        """
        variant = VariantMetadata(
            variant_id=variant_id,
            display_name=display_name,
            description=description,
            endpoint=endpoint,
            keywords=keywords,
            priority=priority,
            layout_id=layout_id,
            status=status,
            use_cases=use_cases or [],
            best_for=best_for,
            avoid_when=avoid_when,
            required_fields=required_fields or [],
            optional_fields=optional_fields or [],
            output_format=output_format
        )

        self.metadata.variants.append(variant)
        return self

    def export_to_registry_format(self) -> Dict[str, Any]:
        """
        Export metadata in unified registry format.

        Returns:
            Dict suitable for inclusion in unified_variant_registry.json

        Example:
            {
                "analytics_service_v3": {
                    "service_name": "analytics_service_v3",
                    "base_url": "https://...",
                    "endpoint_pattern": "typed",
                    "variants": {
                        "pie_chart": { ... },
                        "bar_chart": { ... }
                    }
                }
            }
        """
        # Determine endpoint pattern
        if len(self.metadata.variants) == 1:
            endpoint_pattern = "single"
        else:
            # Check if endpoints are per-variant or typed
            endpoints = [v.endpoint for v in self.metadata.variants]
            if len(set(endpoints)) == 1:
                endpoint_pattern = "single"
            elif all("/charts/" in ep or "/diagrams/" in ep for ep in endpoints):
                endpoint_pattern = "typed"
            else:
                endpoint_pattern = "per_variant"

        # Build variants dict
        variants_dict = {}
        for variant in self.metadata.variants:
            variants_dict[variant.variant_id] = {
                "variant_id": variant.variant_id,
                "display_name": variant.display_name,
                "description": variant.description,
                "status": variant.status,
                "endpoint": variant.endpoint,
                "layout_id": variant.layout_id,
                "classification": {
                    "priority": variant.priority,
                    "keywords": variant.keywords
                },
                "llm_guidance": {
                    "use_cases": variant.use_cases,
                    "best_for": variant.best_for,
                    "avoid_when": variant.avoid_when
                },
                "parameters": {
                    "required_fields": variant.required_fields,
                    "optional_fields": variant.optional_fields,
                    "output_format": variant.output_format
                }
            }

        return {
            self.metadata.service_name: {
                "service_name": self.metadata.service_name,
                "service_version": self.metadata.service_version,
                "service_type": self.metadata.service_type,
                "base_url": self.metadata.base_url,
                "endpoint_pattern": endpoint_pattern,
                "authentication": {
                    "required": self.metadata.authentication_required
                },
                "capabilities": {
                    "batch_processing": self.metadata.supports_batch,
                    "streaming": self.metadata.supports_streaming
                },
                "metadata": {
                    "last_updated": self.metadata.last_updated,
                    "maintainer": self.metadata.maintainer,
                    "documentation_url": self.metadata.documentation_url
                },
                "variants": variants_dict
            }
        }

    def export_to_json(self, indent: int = 2) -> str:
        """
        Export metadata as JSON string.

        Args:
            indent: JSON indentation (default: 2)

        Returns:
            JSON string in registry format
        """
        registry_format = self.export_to_registry_format()
        return json.dumps(registry_format, indent=indent)

    def export_to_file(self, filepath: str, indent: int = 2) -> None:
        """
        Export metadata to JSON file.

        Args:
            filepath: Path to output file
            indent: JSON indentation (default: 2)
        """
        registry_format = self.export_to_registry_format()
        with open(filepath, 'w') as f:
            json.dump(registry_format, f, indent=indent)

    def get_variant_count(self) -> int:
        """Get number of variants."""
        return len(self.metadata.variants)

    def get_keyword_count(self) -> int:
        """Get total number of keywords across all variants."""
        return sum(len(v.keywords) for v in self.metadata.variants)

    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about service metadata.

        Returns:
            Dict with statistics
        """
        return {
            "service_name": self.metadata.service_name,
            "service_version": self.metadata.service_version,
            "variant_count": self.get_variant_count(),
            "total_keywords": self.get_keyword_count(),
            "avg_keywords_per_variant": (
                self.get_keyword_count() / self.get_variant_count()
                if self.get_variant_count() > 0 else 0
            ),
            "status_breakdown": self._get_status_breakdown(),
            "priority_distribution": self._get_priority_distribution(),
            "layout_ids": self._get_layout_ids()
        }

    def _get_status_breakdown(self) -> Dict[str, int]:
        """Get breakdown of variants by status."""
        breakdown = {}
        for variant in self.metadata.variants:
            breakdown[variant.status] = breakdown.get(variant.status, 0) + 1
        return breakdown

    def _get_priority_distribution(self) -> Dict[int, int]:
        """Get distribution of variants by priority."""
        distribution = {}
        for variant in self.metadata.variants:
            distribution[variant.priority] = distribution.get(variant.priority, 0) + 1
        return distribution

    def _get_layout_ids(self) -> List[str]:
        """Get list of unique layout IDs."""
        layout_ids = [v.layout_id for v in self.metadata.variants if v.layout_id]
        return sorted(set(layout_ids))


def create_exporter_from_registry(
    registry_data: Dict[str, Any],
    service_name: str
) -> ServiceMetadataExporter:
    """
    Create exporter from existing registry data.

    Useful for converting existing registry entries back to exporters
    for modification and re-export.

    Args:
        registry_data: Registry data (from unified_variant_registry.json)
        service_name: Service name to extract

    Returns:
        ServiceMetadataExporter with data from registry
    """
    service_data = registry_data["services"][service_name]

    exporter = ServiceMetadataExporter(
        service_name=service_name,
        service_version=service_data.get("service_version", "1.0.0"),
        service_type=service_data.get("service_type", "template_based"),
        base_url=service_data["base_url"],
        supports_batch=service_data.get("capabilities", {}).get("batch_processing", False),
        supports_streaming=service_data.get("capabilities", {}).get("streaming", False),
        authentication_required=service_data.get("authentication", {}).get("required", False),
        maintainer=service_data.get("metadata", {}).get("maintainer"),
        documentation_url=service_data.get("metadata", {}).get("documentation_url")
    )

    # Add variants
    for variant_id, variant_data in service_data["variants"].items():
        exporter.add_variant(
            variant_id=variant_id,
            display_name=variant_data["display_name"],
            description=variant_data["description"],
            endpoint=variant_data["endpoint"],
            keywords=variant_data["classification"]["keywords"],
            priority=variant_data["classification"]["priority"],
            layout_id=variant_data.get("layout_id"),
            status=variant_data.get("status", "production"),
            use_cases=variant_data.get("llm_guidance", {}).get("use_cases", []),
            best_for=variant_data.get("llm_guidance", {}).get("best_for"),
            avoid_when=variant_data.get("llm_guidance", {}).get("avoid_when"),
            required_fields=variant_data.get("parameters", {}).get("required_fields", []),
            optional_fields=variant_data.get("parameters", {}).get("optional_fields", []),
            output_format=variant_data.get("parameters", {}).get("output_format", "html")
        )

    return exporter
