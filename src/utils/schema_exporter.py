"""
JSON Schema Exporter

Utilities for exporting JSON schemas for variant parameters and responses.

Services can use these to generate JSON schemas that describe their
input parameters and output formats for better validation and documentation.

Version: 1.0.0
Created: 2025-11-29
"""

from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel, Field
from enum import Enum


class SchemaType(str, Enum):
    """JSON Schema types"""
    STRING = "string"
    NUMBER = "number"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"
    NULL = "null"


class SchemaFormat(str, Enum):
    """Common JSON Schema formats"""
    DATE_TIME = "date-time"
    DATE = "date"
    TIME = "time"
    EMAIL = "email"
    URI = "uri"
    UUID = "uuid"


class SchemaProperty(BaseModel):
    """JSON Schema property definition"""
    type: Union[SchemaType, List[SchemaType]] = Field(..., description="Property type")
    description: Optional[str] = Field(None, description="Property description")
    format: Optional[str] = Field(None, description="Property format (e.g., date-time, email)")
    enum: Optional[List[Any]] = Field(None, description="Allowed values (enum)")
    minimum: Optional[float] = Field(None, description="Minimum value (for numbers)")
    maximum: Optional[float] = Field(None, description="Maximum value (for numbers)")
    minLength: Optional[int] = Field(None, description="Minimum length (for strings)")
    maxLength: Optional[int] = Field(None, description="Maximum length (for strings)")
    pattern: Optional[str] = Field(None, description="Regex pattern (for strings)")
    items: Optional[Dict[str, Any]] = Field(None, description="Array item schema")
    properties: Optional[Dict[str, Any]] = Field(None, description="Object properties")
    required: Optional[List[str]] = Field(None, description="Required properties (for objects)")
    default: Optional[Any] = Field(None, description="Default value")
    examples: Optional[List[Any]] = Field(None, description="Example values")


class JSONSchemaExporter:
    """
    JSON Schema exporter for variant parameters and responses.

    Creates JSON schemas compliant with JSON Schema Draft 7.

    Usage:
        exporter = JSONSchemaExporter()

        # Define input schema for variant
        input_schema = exporter.create_object_schema(
            title="PieChartInput",
            description="Input parameters for pie chart generation",
            properties={
                "data": exporter.array_property(
                    description="Chart data points",
                    items=exporter.object_schema({
                        "label": exporter.string_property("Category label"),
                        "value": exporter.number_property("Data value", minimum=0)
                    }),
                    min_items=1
                ),
                "title": exporter.string_property("Chart title"),
                "colors": exporter.array_property(
                    description="Optional custom colors",
                    items=exporter.string_property("Hex color code", pattern="^#[0-9A-Fa-f]{6}$")
                )
            },
            required=["data", "title"]
        )

        # Export to JSON
        schema_json = exporter.export_schema(input_schema)
    """

    def __init__(self, schema_version: str = "http://json-schema.org/draft-07/schema#"):
        """
        Initialize schema exporter.

        Args:
            schema_version: JSON Schema version URL
        """
        self.schema_version = schema_version

    def string_property(
        self,
        description: Optional[str] = None,
        format: Optional[str] = None,
        enum: Optional[List[str]] = None,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        pattern: Optional[str] = None,
        default: Optional[str] = None,
        examples: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Create a string property schema.

        Args:
            description: Property description
            format: String format (date-time, email, uri, etc.)
            enum: Allowed values
            min_length: Minimum string length
            max_length: Maximum string length
            pattern: Regex pattern
            default: Default value
            examples: Example values

        Returns:
            Property schema dict
        """
        prop = {"type": "string"}

        if description:
            prop["description"] = description
        if format:
            prop["format"] = format
        if enum:
            prop["enum"] = enum
        if min_length is not None:
            prop["minLength"] = min_length
        if max_length is not None:
            prop["maxLength"] = max_length
        if pattern:
            prop["pattern"] = pattern
        if default is not None:
            prop["default"] = default
        if examples:
            prop["examples"] = examples

        return prop

    def number_property(
        self,
        description: Optional[str] = None,
        minimum: Optional[float] = None,
        maximum: Optional[float] = None,
        default: Optional[float] = None,
        examples: Optional[List[float]] = None
    ) -> Dict[str, Any]:
        """
        Create a number property schema.

        Args:
            description: Property description
            minimum: Minimum value
            maximum: Maximum value
            default: Default value
            examples: Example values

        Returns:
            Property schema dict
        """
        prop = {"type": "number"}

        if description:
            prop["description"] = description
        if minimum is not None:
            prop["minimum"] = minimum
        if maximum is not None:
            prop["maximum"] = maximum
        if default is not None:
            prop["default"] = default
        if examples:
            prop["examples"] = examples

        return prop

    def integer_property(
        self,
        description: Optional[str] = None,
        minimum: Optional[int] = None,
        maximum: Optional[int] = None,
        default: Optional[int] = None,
        examples: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """
        Create an integer property schema.

        Args:
            description: Property description
            minimum: Minimum value
            maximum: Maximum value
            default: Default value
            examples: Example values

        Returns:
            Property schema dict
        """
        prop = {"type": "integer"}

        if description:
            prop["description"] = description
        if minimum is not None:
            prop["minimum"] = minimum
        if maximum is not None:
            prop["maximum"] = maximum
        if default is not None:
            prop["default"] = default
        if examples:
            prop["examples"] = examples

        return prop

    def boolean_property(
        self,
        description: Optional[str] = None,
        default: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Create a boolean property schema.

        Args:
            description: Property description
            default: Default value

        Returns:
            Property schema dict
        """
        prop = {"type": "boolean"}

        if description:
            prop["description"] = description
        if default is not None:
            prop["default"] = default

        return prop

    def array_property(
        self,
        description: Optional[str] = None,
        items: Optional[Dict[str, Any]] = None,
        min_items: Optional[int] = None,
        max_items: Optional[int] = None,
        unique_items: bool = False
    ) -> Dict[str, Any]:
        """
        Create an array property schema.

        Args:
            description: Property description
            items: Schema for array items
            min_items: Minimum array length
            max_items: Maximum array length
            unique_items: Whether items must be unique

        Returns:
            Property schema dict
        """
        prop = {"type": "array"}

        if description:
            prop["description"] = description
        if items:
            prop["items"] = items
        if min_items is not None:
            prop["minItems"] = min_items
        if max_items is not None:
            prop["maxItems"] = max_items
        if unique_items:
            prop["uniqueItems"] = True

        return prop

    def object_schema(
        self,
        properties: Dict[str, Dict[str, Any]],
        required: Optional[List[str]] = None,
        additional_properties: bool = True
    ) -> Dict[str, Any]:
        """
        Create an object schema (for nested objects).

        Args:
            properties: Object properties
            required: Required property names
            additional_properties: Allow additional properties

        Returns:
            Object schema dict
        """
        schema = {
            "type": "object",
            "properties": properties
        }

        if required:
            schema["required"] = required

        schema["additionalProperties"] = additional_properties

        return schema

    def create_object_schema(
        self,
        title: str,
        description: str,
        properties: Dict[str, Dict[str, Any]],
        required: Optional[List[str]] = None,
        additional_properties: bool = False
    ) -> Dict[str, Any]:
        """
        Create a complete object schema with metadata.

        Args:
            title: Schema title
            description: Schema description
            properties: Object properties
            required: Required property names
            additional_properties: Allow additional properties

        Returns:
            Complete JSON schema
        """
        schema = {
            "$schema": self.schema_version,
            "title": title,
            "description": description,
            "type": "object",
            "properties": properties,
            "additionalProperties": additional_properties
        }

        if required:
            schema["required"] = required

        return schema

    def create_variant_input_schema(
        self,
        variant_id: str,
        variant_name: str,
        properties: Dict[str, Dict[str, Any]],
        required: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Create input schema for a variant.

        Args:
            variant_id: Variant identifier
            variant_name: Human-readable variant name
            properties: Input properties
            required: Required property names

        Returns:
            Complete input schema
        """
        return self.create_object_schema(
            title=f"{variant_name}Input",
            description=f"Input parameters for {variant_name} ({variant_id})",
            properties=properties,
            required=required,
            additional_properties=False
        )

    def create_variant_output_schema(
        self,
        variant_id: str,
        variant_name: str,
        output_format: str = "html"
    ) -> Dict[str, Any]:
        """
        Create output schema for a variant.

        Args:
            variant_id: Variant identifier
            variant_name: Human-readable variant name
            output_format: Output format (html, json, svg, etc.)

        Returns:
            Complete output schema
        """
        if output_format == "html":
            properties = {
                "html_content": self.string_property(
                    description="Generated HTML content",
                    min_length=1
                ),
                "success": self.boolean_property(
                    description="Whether generation was successful",
                    default=True
                ),
                "variant_id": self.string_property(
                    description="Variant identifier",
                    default=variant_id
                ),
                "error": self.string_property(
                    description="Error message (if failed)"
                )
            }
            required = ["html_content", "success", "variant_id"]

        elif output_format == "json":
            properties = {
                "data": {
                    "type": "object",
                    "description": "Generated data"
                },
                "success": self.boolean_property(
                    description="Whether generation was successful",
                    default=True
                ),
                "variant_id": self.string_property(
                    description="Variant identifier",
                    default=variant_id
                )
            }
            required = ["data", "success", "variant_id"]

        else:
            # Generic output schema
            properties = {
                "content": self.string_property(
                    description=f"Generated {output_format} content"
                ),
                "success": self.boolean_property(
                    description="Whether generation was successful"
                ),
                "variant_id": self.string_property(
                    description="Variant identifier",
                    default=variant_id
                )
            }
            required = ["content", "success", "variant_id"]

        return self.create_object_schema(
            title=f"{variant_name}Output",
            description=f"Output schema for {variant_name} ({variant_id})",
            properties=properties,
            required=required
        )

    def export_schema(self, schema: Dict[str, Any], indent: int = 2) -> str:
        """
        Export schema as JSON string.

        Args:
            schema: Schema dict
            indent: JSON indentation

        Returns:
            JSON string
        """
        import json
        return json.dumps(schema, indent=indent)

    def export_to_file(self, schema: Dict[str, Any], filepath: str, indent: int = 2):
        """
        Export schema to file.

        Args:
            schema: Schema dict
            filepath: Output file path
            indent: JSON indentation
        """
        import json
        with open(filepath, 'w') as f:
            json.dump(schema, f, indent=indent)


# Convenience functions

def create_chart_data_schema(
    require_labels: bool = True,
    require_values: bool = True,
    allow_additional_fields: bool = True
) -> Dict[str, Any]:
    """
    Create common chart data schema.

    Standard schema for chart data points used by Analytics Service.

    Args:
        require_labels: Whether labels are required
        require_values: Whether values are required
        allow_additional_fields: Allow additional fields in data points

    Returns:
        Chart data array schema

    Example:
        data_schema = create_chart_data_schema()
        # Returns schema for: [{label: "A", value: 100}, ...]
    """
    exporter = JSONSchemaExporter()

    properties = {}
    required = []

    if require_labels:
        properties["label"] = exporter.string_property("Data point label")
        required.append("label")

    if require_values:
        properties["value"] = exporter.number_property(
            "Data point value"
        )
        required.append("value")

    # Common optional fields
    properties["color"] = exporter.string_property(
        "Custom color for this data point",
        pattern="^#[0-9A-Fa-f]{6}$"
    )
    properties["metadata"] = {
        "type": "object",
        "description": "Additional metadata for this data point"
    }

    item_schema = exporter.object_schema(
        properties=properties,
        required=required if (require_labels or require_values) else None,
        additional_properties=allow_additional_fields
    )

    return exporter.array_property(
        description="Array of data points for the chart",
        items=item_schema,
        min_items=1
    )


def create_pie_chart_schema() -> Dict[str, Dict[str, Any]]:
    """
    Create input and output schemas for pie chart variant.

    Returns:
        Dict with "input" and "output" schemas

    Example:
        schemas = create_pie_chart_schema()
        input_schema = schemas["input"]
        output_schema = schemas["output"]
    """
    exporter = JSONSchemaExporter()

    # Input schema
    input_schema = exporter.create_variant_input_schema(
        variant_id="pie_chart",
        variant_name="Pie Chart",
        properties={
            "data": create_chart_data_schema(),
            "title": exporter.string_property(
                "Chart title",
                max_length=100
            ),
            "colors": exporter.array_property(
                description="Custom color palette (hex codes)",
                items=exporter.string_property(
                    pattern="^#[0-9A-Fa-f]{6}$"
                )
            ),
            "show_legend": exporter.boolean_property(
                "Display legend",
                default=True
            ),
            "show_percentages": exporter.boolean_property(
                "Show percentages on segments",
                default=True
            )
        },
        required=["data", "title"]
    )

    # Output schema
    output_schema = exporter.create_variant_output_schema(
        variant_id="pie_chart",
        variant_name="Pie Chart",
        output_format="html"
    )

    return {
        "input": input_schema,
        "output": output_schema
    }


def create_bar_chart_schema() -> Dict[str, Dict[str, Any]]:
    """
    Create input and output schemas for bar chart variant.

    Returns:
        Dict with "input" and "output" schemas
    """
    exporter = JSONSchemaExporter()

    input_schema = exporter.create_variant_input_schema(
        variant_id="bar_chart",
        variant_name="Bar Chart",
        properties={
            "data": create_chart_data_schema(),
            "title": exporter.string_property(
                "Chart title",
                max_length=100
            ),
            "orientation": exporter.string_property(
                "Chart orientation",
                enum=["vertical", "horizontal"],
                default="vertical"
            ),
            "colors": exporter.array_property(
                description="Custom color palette",
                items=exporter.string_property(pattern="^#[0-9A-Fa-f]{6}$")
            ),
            "show_values": exporter.boolean_property(
                "Display values on bars",
                default=True
            )
        },
        required=["data", "title"]
    )

    output_schema = exporter.create_variant_output_schema(
        variant_id="bar_chart",
        variant_name="Bar Chart",
        output_format="html"
    )

    return {
        "input": input_schema,
        "output": output_schema
    }
