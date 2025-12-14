"""
Analytics Service Tools for Director Agent v4.0

HIGH-cost tools that wrap Analytics Service v3 for data visualization:
- GenerateChartTool: Generate various chart types (pie, bar, line, etc.)

These tools require approved strawman and explicit user approval before execution.
"""

from typing import Dict, Any, Optional, List

from .base_tool import BaseTool, ToolDefinition, ToolResult, CostTier
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class GenerateChartTool(BaseTool):
    """
    Tool for generating data visualization charts.

    Wraps Analytics Service v3 endpoints:
    - /analytics/v3/chartjs/generate (Chart.js library)
    - /analytics/v3/d3/generate (D3.js library)

    HIGH cost - requires approved strawman and user approval.
    """

    def __init__(self, analytics_client=None):
        """
        Initialize with optional analytics client.

        Args:
            analytics_client: Analytics service client (injected at runtime)
        """
        self._client = analytics_client

    def set_client(self, client):
        """Set the analytics client (for dependency injection)."""
        self._client = client

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            tool_id="analytics.generate_chart",
            display_name="Generate Chart",
            description=(
                "Generate data visualization charts using Analytics Service v3. "
                "Supports multiple chart types: pie, bar, line, doughnut, radar, "
                "bubble, scatter, treemap, and more. Includes AI-generated observations. "
                "HIGH COST: Requires approved strawman and explicit user approval."
            ),
            cost_tier=CostTier.HIGH,
            requires_context=["strawman"],
            requires_approval=True,
            input_schema={
                "type": "object",
                "required": ["chart_type", "data"],
                "properties": {
                    "chart_type": {
                        "type": "string",
                        "enum": [
                            "pie", "bar", "line", "doughnut", "radar",
                            "bubble", "scatter", "treemap", "stacked_bar",
                            "horizontal_bar", "area", "mixed"
                        ],
                        "description": "Type of chart to generate"
                    },
                    "data": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "label": {"type": "string"},
                                "value": {"type": "number"},
                                "category": {"type": "string"}
                            },
                            "required": ["label", "value"]
                        },
                        "minItems": 2,
                        "maxItems": 20,
                        "description": "Chart data points (2-20 items)"
                    },
                    "narrative": {
                        "type": "string",
                        "description": "Context for AI-generated observations"
                    },
                    "library": {
                        "type": "string",
                        "enum": ["chartjs", "d3"],
                        "default": "chartjs",
                        "description": "Chart library to use"
                    },
                    "include_observations": {
                        "type": "boolean",
                        "default": True,
                        "description": "Include AI-generated observations (L02 layout)"
                    },
                    "context": {
                        "type": "object",
                        "description": "Presentation context (title, tone, audience)"
                    }
                }
            },
            output_schema={
                "type": "object",
                "properties": {
                    "chart_html": {"type": "string"},
                    "observations": {"type": "string"},
                    "variant_id": {"type": "string"},
                    "service_type": {"type": "string"}
                }
            }
        )

    async def execute(
        self,
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> ToolResult:
        """
        Execute chart generation via Analytics Service.

        Args:
            parameters: Chart parameters (chart_type, data, narrative, etc.)
            context: Session context with presentation info

        Returns:
            ToolResult with generated chart HTML and observations
        """
        if not self._client:
            return ToolResult(
                success=False,
                error="Analytics service client not configured",
                tool_id=self.tool_id
            )

        try:
            chart_type = parameters.get('chart_type')
            data = parameters.get('data', [])
            library = parameters.get('library', 'chartjs')

            logger.info(f"Generating {chart_type} chart with {len(data)} data points")

            # Validate data
            if len(data) < 2:
                return ToolResult(
                    success=False,
                    error="Chart data must have at least 2 items",
                    tool_id=self.tool_id
                )

            if len(data) > 20:
                return ToolResult(
                    success=False,
                    error="Chart data must have at most 20 items",
                    tool_id=self.tool_id
                )

            # Build request
            request = {
                "chart_type": chart_type,
                "data": data
            }

            if parameters.get('narrative'):
                request['narrative'] = parameters['narrative']

            if parameters.get('context'):
                request['context'] = parameters['context']
            elif context:
                request['context'] = {
                    "presentation_title": context.get('presentation_title', ''),
                    "tone": context.get('tone', 'professional'),
                    "audience": context.get('audience', 'general')
                }

            # Determine endpoint based on library
            if library == 'd3':
                endpoint = "/analytics/v3/d3/generate"
            else:
                endpoint = "/analytics/v3/chartjs/generate"

            # Call Analytics Service
            response = await self._call_analytics(endpoint, request)

            if not response:
                return ToolResult(
                    success=False,
                    error="Analytics Service returned empty response",
                    tool_id=self.tool_id
                )

            # Analytics Service returns element_3 (chart) and element_2 (observations)
            chart_html = response.get('element_3', response.get('chart_html', ''))
            observations = response.get('element_2', response.get('observations', ''))

            if not chart_html:
                return ToolResult(
                    success=False,
                    error="Analytics Service returned no chart content",
                    tool_id=self.tool_id
                )

            return ToolResult(
                success=True,
                data={
                    "chart_html": chart_html,
                    "html_content": chart_html,  # Alias for compatibility
                    "observations": observations,
                    "element_3": chart_html,  # Keep original field names
                    "element_2": observations,
                    "variant_id": f"{chart_type}_chart",
                    "service_type": "data_visualization",
                    "library": library
                },
                tool_id=self.tool_id
            )

        except Exception as e:
            logger.error(f"Chart generation failed: {e}")
            return ToolResult(
                success=False,
                error=f"Chart generation failed: {str(e)}",
                tool_id=self.tool_id
            )

    async def _call_analytics(
        self,
        endpoint: str,
        request: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Call Analytics Service endpoint."""
        if hasattr(self._client, 'generate'):
            return await self._client.generate(endpoint, request)
        elif hasattr(self._client, 'post'):
            return await self._client.post(endpoint, request)
        raise NotImplementedError("Analytics client not properly configured")

    def validate_parameters(self, parameters: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Extended validation for chart parameters.

        Validates:
        - Required fields (chart_type, data)
        - Data structure (label/value pairs)
        - Data count limits
        """
        # First run base validation
        is_valid, error = super().validate_parameters(parameters)
        if not is_valid:
            return is_valid, error

        # Additional validation for chart data
        data = parameters.get('data', [])

        # Check each data point has required fields
        for i, point in enumerate(data):
            if not isinstance(point, dict):
                return False, f"Data point {i} must be an object"
            if 'label' not in point:
                return False, f"Data point {i} missing 'label' field"
            if 'value' not in point:
                return False, f"Data point {i} missing 'value' field"
            if not isinstance(point['value'], (int, float)):
                return False, f"Data point {i} 'value' must be a number"

        # Validate chart_type specific requirements
        chart_type = parameters.get('chart_type')

        if chart_type == 'bubble':
            # Bubble charts need x, y, r values
            for i, point in enumerate(data):
                if 'x' not in point or 'y' not in point:
                    return False, f"Bubble chart data point {i} requires 'x' and 'y' fields"

        if chart_type in ['scatter', 'bubble']:
            # Scatter/bubble need at least numeric data
            for i, point in enumerate(data):
                if not isinstance(point.get('value'), (int, float)):
                    return False, f"Scatter/bubble chart data point {i} 'value' must be numeric"

        return True, None


class GenerateTableTool(BaseTool):
    """
    Tool for generating data tables.

    Wraps Text Service v1.2 table generation variants.
    HIGH cost - requires approved strawman and user approval.
    """

    def __init__(self, text_service_client=None):
        self._client = text_service_client

    def set_client(self, client):
        self._client = client

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            tool_id="analytics.generate_table",
            display_name="Generate Data Table",
            description=(
                "Generate formatted HTML tables for data presentation. "
                "Supports various table styles and formatting options. "
                "HIGH COST: Requires approved strawman and explicit user approval."
            ),
            cost_tier=CostTier.HIGH,
            requires_context=["strawman"],
            requires_approval=True,
            input_schema={
                "type": "object",
                "required": ["title", "data"],
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Table title"
                    },
                    "data": {
                        "type": "object",
                        "properties": {
                            "headers": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Column headers"
                            },
                            "rows": {
                                "type": "array",
                                "items": {
                                    "type": "array",
                                    "items": {"type": "string"}
                                },
                                "description": "Table rows"
                            }
                        },
                        "required": ["headers", "rows"]
                    },
                    "style": {
                        "type": "string",
                        "enum": ["standard", "comparison", "pricing", "metrics"],
                        "default": "standard",
                        "description": "Table style variant"
                    },
                    "context": {
                        "type": "object",
                        "description": "Presentation context"
                    }
                }
            },
            output_schema={
                "type": "object",
                "properties": {
                    "html_content": {"type": "string"},
                    "variant_id": {"type": "string"}
                }
            }
        )

    async def execute(
        self,
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> ToolResult:
        """Execute table generation."""
        if not self._client:
            return ToolResult(
                success=False,
                error="Text service client not configured",
                tool_id=self.tool_id
            )

        try:
            title = parameters.get('title')
            data = parameters.get('data', {})
            style = parameters.get('style', 'standard')

            logger.info(f"Generating {style} table: {title}")

            # Map style to variant_id
            style_to_variant = {
                "standard": "data_table",
                "comparison": "comparison_table",
                "pricing": "pricing_table",
                "metrics": "metrics_table"
            }
            variant_id = style_to_variant.get(style, "data_table")

            request = {
                "variant_id": variant_id,
                "title": title,
                "table_data": data
            }

            if parameters.get('context'):
                request['context'] = parameters['context']

            # Call Text Service for table generation
            response = await self._call_text_service(request)

            if not response or 'html_content' not in response:
                return ToolResult(
                    success=False,
                    error="Text Service returned invalid response",
                    tool_id=self.tool_id
                )

            return ToolResult(
                success=True,
                data={
                    "html_content": response['html_content'],
                    "variant_id": variant_id,
                    "service_type": "template_based"
                },
                tool_id=self.tool_id
            )

        except Exception as e:
            logger.error(f"Table generation failed: {e}")
            return ToolResult(
                success=False,
                error=f"Table generation failed: {str(e)}",
                tool_id=self.tool_id
            )

    async def _call_text_service(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Call Text Service."""
        if hasattr(self._client, 'generate'):
            return await self._client.generate(request)
        raise NotImplementedError("Text service client not properly configured")
